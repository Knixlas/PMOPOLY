"""Frågorna som människor ser: en svensk rubrik, en typ och läsbara alternativ för varje beslut.

Motorn frågar med strategimetodens namn och Python-objekt. Här blir det något ett gränssnitt kan visa:

    {"rubrik": "Vilket projekt tar ni?", "typ": "val", "alternativ": [{"text": ..., "kod": ...}], ...}

Typer: "janej" (svar true/false), "val" (svar = ett alternativs kod), "flerval" (svar = {"lista": [kod, ...]}),
"tal" (svar = heltal mellan min och max), "pussel" och "markexpansion" (4.3; se pussel-fälten).
Varje alternativ bär sin egen svarskod (styrning.koda), så gränssnittet behöver inte känna motorn.
Förslaget (bottens svar) följer alltid med, så att varje fråga kan besvaras med "gör som förslaget".
"""
from .pussel import GRUNDMARK, form_av
from .slump import kortnamn
from .styrning import koda

TYPNAMN = {"BRF": "BRF", "HYRESRÄTT": "Hyresrätt", "FÖRSKOLA": "Förskola", "LOKAL": "Lokal", "KONTOR": "Kontor"}


def _tal(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def etikett(obj, m=None):
    """Kort text för ett objekt i motorn: kort, projekt, fastighet, kvarter, typ eller par av dem."""
    if obj is None:
        return "Inget"
    if isinstance(obj, bool):
        return "Ja" if obj else "Nej"
    if isinstance(obj, str):
        return TYPNAMN.get(obj, obj.capitalize() if obj.isupper() else obj)
    if isinstance(obj, tuple):
        return " → ".join(etikett(o, m) for o in obj)
    if isinstance(obj, dict):
        if "Anskaffning (Mkr)" in obj:                       # projektkort
            return f'{obj["Namn"]} ({TYPNAMN.get(obj["Typ"], obj["Typ"])})'
        rubrik = obj.get("Rubrik") or obj.get("Namn") or ""
        id_ = kortnamn(obj)
        return f"{rubrik} ({id_})" if rubrik and rubrik != id_ else id_
    if hasattr(obj, "bas_dn"):                              # fastighet
        return f"{obj.namn} ({TYPNAMN.get(obj.typ, obj.typ)})"
    return getattr(obj, "namn", str(obj))


def detalj(obj, m=None):
    """En rad till under etiketten: siffrorna man väljer på."""
    if isinstance(obj, dict):
        if "Anskaffning (Mkr)" in obj:
            return (f'BTA {int(_tal(obj["BTA (kvm)"]))} kvm · anskaffning {_tal(obj["Anskaffning (Mkr)"]):g} Mkr · '
                    f'utv {_tal(obj["Utvecklingskostnad (Mkr)"]):g} Mkr · Q {obj.get("Kvalitetskrav Q") or 0} · '
                    f'H {obj.get("Hållbarhetskrav H") or 0} · nämnd +{obj.get("Passera nämnden (>)") or 0}')
        text = obj.get("Beskrivning") or obj.get("Effekt") or ""
        return str(text)[:160]
    if hasattr(obj, "bas_dn") and m is not None and hasattr(m, "mv"):
        try:
            return f"DN {m.eff_dn(obj)} · MV {m.mv(obj):g} · lån {obj.lan} · energiklass {obj.ek}"
        except Exception:                                    # noqa: BLE001 — bara presentation
            return ""
    if isinstance(obj, tuple):
        return " · ".join(filter(None, (detalj(o, m) for o in obj)))
    return ""


def bild(obj):
    """Projektkortets bild i webbklienten (spel/webb/public/bilder/<Kort-id>.jpg), om det finns en."""
    if isinstance(obj, dict) and "Anskaffning (Mkr)" in obj and obj.get("Kort-id") is not None:
        return {"bild": f"bilder/{obj['Kort-id']}.jpg", "typ": obj.get("Typ")}
    return {}


# ---------------------------------------------------------------------------- beslutens beskrivningar
# metod -> (typ, rubrik(m, s, a), pool(m, s, a) eller None, "inget" tillåtet)
def _andra(m, s):
    return [o for o in getattr(getattr(m, "spel", None), "spelare", []) if o is not s]


def _fordelningar(n):
    steg, tecken = abs(n), (1 if n > 0 else -1)
    return [(tecken * q, tecken * (steg - q)) for q in range(steg, -1, -1)]


BESLUT = {
    # Skede 1 — projektutveckling
    "valj_pc": ("val", lambda m, s, a: "Välj projektchef (PC)", lambda m, s, a: a[0], False),
    "starttyp": ("val", lambda m, s, a: "Vilken projekttyp börjar ni med?",
                 lambda m, s, a: [t for t in m.hogar if m.hogar[t]], False),
    "valj_projekt": ("val", lambda m, s, a: "Vilket projekt tar ni?", lambda m, s, a: a[0], True),
    "dra_anda": ("janej", lambda m, s, a: f"Dra översta {etikett(a[0]).lower()}-kortet till projektbanken?", None, False),
    "vill_expandera": ("janej", lambda m, s, a: "Ta en markexpansion?", None, False),
    "stadshuset": ("val", lambda m, s, a: "Stadshuset: lämna tillbaka ett projekt?", lambda m, s, a: s.projekt, True),
    "fordela_krav": ("val", lambda m, s, a: f"Fördela {abs(a[0])} steg mellan kvalitet (Q) och hållbarhet (H)",
                     lambda m, s, a: _fordelningar(a[0]), False),
    "sla_om_handelse": ("janej", lambda m, s, a: "Slå om händelsen med en riskbuffert?", None, False),
    "byt_samma_typ": ("val", lambda m, s, a: "Byt ett projekt mot översta kortet i samma hög?",
                      lambda m, s, a: s.projekt, True),
    "samsta_projekt": ("val", lambda m, s, a: "Vilket projekt lämnar ni tillbaka?",
                       lambda m, s, a: a[0] if a and a[0] is not None else s.projekt, False),
    "ta_tva_projekt": ("janej", lambda m, s, a: "Ta två projekt?", None, False),
    "hellre_lamna_an_krav": ("janej", lambda m, s, a: f"Lämna tillbaka ett projekt i stället för att höja kraven {a[0]} steg?", None, False),
    "sla_om_namnd": ("janej", lambda m, s, a: f"Nämnden: {a[0]:g} räckte inte. Slå om med en riskbuffert?", None, False),
    "namnd_miss_hoj_krav": ("janej", lambda m, s, a: "Nämnden sa nej. Höj kraven och försök igen?", None, False),
    "komplettera": ("val", lambda m, s, a: "Komplettera med ett projekt (3 × utvecklingskostnaden)?",
                    lambda m, s, a: list(m.bank) + [m.hogar[t][-1] for t in m.hogar if m.hogar[t]], True),
    "rb_sank_krav": ("tal", lambda m, s, a: "Hur många riskbuffertar använder ni för att sänka kraven?", None, False),
    "placera_markexpansion": ("markexpansion", lambda m, s, a: "Lägg markexpansionen kant i kant med marken",
                              lambda m, s, a: a[1], False),
    "placering": ("pussel", lambda m, s, a: "4.3 Placering: lägg kvarteret", None, False),
    # Skede 2 — planering och genomförande
    "valj_ac": ("val", lambda m, s, a: "Välj arbetschef (AC)", lambda m, s, a: a[0], False),
    "valj_niva": ("val", lambda m, s, a: "Välj nivå", lambda m, s, a: a[0], False),
    "sla_om": ("janej", lambda m, s, a: "Slå om med en riskbuffert?", None, False),
    "kulturkort": ("tal", lambda m, s, a: f"Hur många kulturkort köper ni ({_tal(a[1]):g} Mkr styck)?", None, False),
    "spela_niva": ("janej", lambda m, s, a: f"Spela korten och nå nivå {a[0]}?", None, False),
    # Förvaltning
    "valj_fc": ("val", lambda m, s, a: "Välj fastighetschef (FC)", lambda m, s, a: a[0], False),
    "valj_fs": ("val", lambda m, s, a: "Välj förvaltningsstöd (FS)", lambda m, s, a: a[0], False),
    "vill_kopa": ("janej", lambda m, s, a: f"Köpa {etikett(a[0], m)} för {a[1]:g} Mkr?", None, False),
    "forhandlingskort": ("flerval", lambda m, s, a: "Spela förhandlingskort?", lambda m, s, a: s.hand, False),
    "vill_sanera": ("janej", lambda m, s, a: f"Ta saneringsuppdraget för {etikett(a[0], m)} (skuld {a[1]:g} Mkr)?", None, False),
    "tvangsbud": ("val", lambda m, s, a: "Lägga ett tvångsbud?",
                  lambda m, s, a: [(o, f) for o in _andra(m, s) for f in o.fastigheter if m.kan_tvangsbudas(f)], True),
    "stoppa": ("val", lambda m, s, a: f"Stoppa tvångsbudet på {etikett(a[0], m)}?", lambda m, s, a: a[1], True),
    "duellkort": ("flerval", lambda m, s, a: "Spela kort i duellen?", lambda m, s, a: s.hand, False),
    "motbudsmal": ("val", lambda m, s, a: "Motbud: vilken av budgivarens fastigheter vill ni ha?",
                   lambda m, s, a: a[0].fastigheter, True),
    "salj": ("flerval", lambda m, s, a: "Sälja fastigheter till banken?", lambda m, s, a: s.fastigheter, False),
    "salj_for_likviditet": ("val", lambda m, s, a: "Kassan är negativ: vilken fastighet säljer ni?",
                            lambda m, s, a: s.fastigheter, False),
    "roj": ("flerval", lambda m, s, a: "Röja underhållsvarningar?",
            lambda m, s, a: [(f, i) for f in s.fastigheter for i in range(len(f.varningar))], False),
    "visa_plus": ("janej", lambda m, s, a: f"Visa plusbrickan på {etikett(a[0], m)}?", None, False),
    "eliminera": ("janej", lambda m, s, a: f"Stoppa händelsen {etikett(a[1], m)} på {etikett(a[0], m)}?", None, False),
    "valj_dd": ("val", lambda m, s, a: f"Due diligence för {etikett(a[0], m)}: vilket kort behåller ni?",
                lambda m, s, a: a[1], False),
    "slang": ("val", lambda m, s, a: "Handen är full: vilket kort slänger ni?", lambda m, s, a: s.hand, False),
    "spela_nu": ("flerval", lambda m, s, a: "Spela nätverkskort nu?", lambda m, s, a: s.hand, False),
    "konverteringsmal": ("val", lambda m, s, a: "Vilken fastighet konverterar ni till hyresrätt?",
                         lambda m, s, a: s.fastigheter, True),
    "valj_plusfastighet": ("val", lambda m, s, a: "Vilken fastighet får plusbrickan?", lambda m, s, a: s.fastigheter, False),
    "valj_energifastighet": ("val", lambda m, s, a: "Vilken fastighet får energibrickan?",
                             lambda m, s, a: s.fastigheter, True),
    "varvningsmal": ("val", lambda m, s, a: "Hyresgästvärvning: från vilken fastighet till vilken?",
                     lambda m, s, a: [(e, f) for e in s.fastigheter for o in _andra(m, s) for f in o.fastigheter], True),
    "valj_typ": ("val", lambda m, s, a: "Vilken fastighetstyp väljer ni?",
                 lambda m, s, a: ["HYRESRÄTT", "LOKAL", "KONTOR", "FÖRSKOLA"], False),
    "uppgradera": ("flerval", lambda m, s, a: f"Energiuppgradera (högst {a[0]} fastigheter)?",
                   lambda m, s, a: s.fastigheter, False),
    "energikort": ("flerval", lambda m, s, a: "Spela energikort?", lambda m, s, a: s.hand, False),
    "fortsatt_uppgradera": ("janej", lambda m, s, a: f"Fortsätta uppgradera {etikett(a[0], m)}?", None, False),
}
MAX_TAL = {"rb_sank_krav": lambda m, s, a: getattr(s, "riskbuffert", 0), "kulturkort": lambda m, s, a: 5}
MAX_FLERVAL = {"uppgradera": lambda m, s, a: a[0]}


def beskriv_beslut(metod, motor, subjekt, args, rotter, forslag):
    """Vy för en fråga till en människa. `forslag` är bottens svar (objekt), kodat blir det standardvalet."""
    typ, rubrik, pool, inget = BESLUT.get(metod, ("forslag", lambda m, s, a: metod.replace("_", " ").capitalize(), None, False))
    vy = {"typ": typ, "rubrik": rubrik(motor, subjekt, args), "kvarter": getattr(subjekt, "namn", None),
          "forslag_text": etikett(forslag, motor) if not isinstance(forslag, list)
          else (", ".join(etikett(x, motor) for x in forslag) or "Inga")}
    if pool:
        text = (lambda x: f"Q {x[0]:+d} · H {x[1]:+d}") if metod == "fordela_krav" else (lambda x: etikett(x, motor))
        vy["alternativ"] = [{"text": text(x), "detalj": detalj(x, motor), "kod": koda(x, rotter), **bild(x)}
                            for x in pool(motor, subjekt, args)]
        if metod == "fordela_krav":
            vy["forslag_text"] = text(forslag)
        if inget:
            vy["alternativ"].append({"text": "Inget", "detalj": "", "kod": None})
    if typ == "tal":
        vy["min"], vy["max"] = 0, int(MAX_TAL.get(metod, lambda m, s, a: 10)(motor, subjekt, args))
    if typ == "flerval" and metod in MAX_FLERVAL:
        vy["max"] = int(MAX_FLERVAL[metod](motor, subjekt, args))
    if typ in ("pussel", "markexpansion"):
        vy["mark"] = sorted(list(c) for c in subjekt.mark)
        vy["grundmark"] = sorted(list(c) for c in GRUNDMARK)
    if typ == "pussel":
        vy["projekt"] = [{"namn": p["Namn"], "typ": p["Typ"], "form": [list(c) for c in form_av(p)]} for p in args[0]]
    if typ == "markexpansion":
        vy["form"] = [list(c) for c in form_av(args[0])]
        vy["platser"] = [sorted(list(c) for c in celler) for celler in args[1]]
    return vy


# ---------------------------------------------------------------------------- slumpens frågor
def beskriv_slump(metod, argument):
    """Vy för en slumpfråga i fysiskt spel (läge 2). Svaret är ett tal eller ett index i alternativen."""
    if metod in ("d20", "tarning", "heltal", "index"):
        lag, hog = argument
        rubrik = {"d20": "Slå D20: vad visade tärningen?", "tarning": f"Slå D{hog}: vad visade tärningen?"}.get(
            metod, f"Ange ett tal mellan {lag} och {hog}")
        return {"typ": "tal", "rubrik": rubrik, "min": lag, "max": hog}
    if metod == "dra":
        hog, kort = argument
        return {"typ": "val", "rubrik": f"Dra ett kort ur högen {hog}: vilket fick ni?",
                "alternativ": [{"text": k, "detalj": "", "kod": i} for i, k in enumerate(kort)], "sok": True}
    return {"typ": "val", "rubrik": "Välj blint: vilket blev det?",
            "alternativ": [{"text": k, "detalj": "", "kod": i} for i, k in enumerate(argument)]}
