"""Frågorna som människor ser: en svensk rubrik, en typ och läsbara alternativ för varje beslut.

Motorn frågar med strategimetodens namn och Python-objekt. Här blir det något ett gränssnitt kan visa:

    {"rubrik": "Vilket projekt tar ni?", "typ": "val", "alternativ": [{"text": ..., "kod": ...}], ...}

Typer: "janej" (svar true/false), "val" (svar = ett alternativs kod), "flerval" (svar = {"lista": [kod, ...]}),
"tal" (svar = heltal mellan min och max), "pussel" och "markexpansion" (4.3; se pussel-fälten).
Varje alternativ bär sin egen svarskod (styrning.koda), så gränssnittet behöver inte känna motorn.
Förslaget (bottens svar) följer alltid med, så att varje fråga kan besvaras med "gör som förslaget".
"""
from .pu import markid
from .pussel import GRUNDMARK, form_av
from .slump import kortnamn, kortrubrik
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
        if obj.get("Företag"):                                # leverantör eller organisation (Skede 2.1)
            return f'{obj["Företag"]} (nivå {obj.get("Nivå")})'
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


# nätverkskort som spelas i Ekonomi (motor.spela_hand); övriga väntar på sitt tillfälle (bud, duell, energi …)
SPELBARA_NU = ("lagg_dn_plus_egen", "lagg_energi_plus_egen", "direkt_dn_plus_egen", "stada", "dra_natverkskort",
               "riskbuffert", "utveckling", "headhunting", "hyresgastvarvning", "gratis_uppgradering", "omforhandlat_lan", "konvertering")


def _med_effekt(hand, *effekter):
    """Bara de kort på handen som går att spela här (frågan visar inte resten)."""
    return [k for k in hand if isinstance(k, dict) and k.get("Effekt") in effekter]


BESLUT = {
    # Skede 1 — projektutveckling
    "valj_pc": ("val", lambda m, s, a: "Välj projektchef (PC)", lambda m, s, a: a[0], False),
    "starttyp": ("val", lambda m, s, a: "Vilken projekttyp börjar ni med?",
                 lambda m, s, a: [t for t in m.hogar if m.hogar[t]], False),
    "valj_projekt": ("val", lambda m, s, a: (f"{m.orsak}: " if getattr(m, "orsak", None) else "") + "vilket projekt tar ni?",
                     lambda m, s, a: a[0], True),
    "vill_expandera": ("janej", lambda m, s, a: "Ta en markexpansion?", None, False),
    "stadshuset": ("val", lambda m, s, a: "Stadshuset: lämna tillbaka ett projekt?", lambda m, s, a: s.projekt, True),
    "fordela_krav": ("val", lambda m, s, a: (f"{m.orsak}: " if getattr(m, "orsak", None) else "")
                     + f"{'sänk' if a[0] < 0 else 'höj'} kraven {abs(a[0])} steg. Hur fördelar ni mellan Q och H?",
                     lambda m, s, a: _fordelningar(a[0]), False),
    "sla_om_handelse": ("janej", lambda m, s, a: f"Händelsekortet ”{a[0].get('Rubrik') or ''}” gav: {a[1]}. Slå om med en riskbuffert?",
                        None, False),
    "sla_om_kort": ("janej", lambda m, s, a: f"Kortet ”{kortrubrik(a[0]) or kortnamn(a[0])}” gav: {a[1]}. "
                    "Slå om med en riskbuffert?", None, False),
    "byt_samma_typ": ("val", lambda m, s, a: "Byt ett projekt mot översta kortet i samma hög?",
                      lambda m, s, a: s.projekt, True),
    "samsta_projekt": ("val", lambda m, s, a: "Vilket projekt lämnar ni tillbaka?",
                       lambda m, s, a: a[0] if a and a[0] is not None else s.projekt, False),
    "ta_tva_projekt": ("janej", lambda m, s, a: "Ta två projekt?", None, False),
    "hellre_lamna_an_krav": ("janej", lambda m, s, a: f"Lämna tillbaka ett projekt i stället för att höja kraven {a[0]} steg?", None, False),
    "sla_namnd": ("val", lambda m, s, a: f"Nämnden (4.1): nämndsumman är {a[0]:g}. Slå {a[1]} D20 – över {a[0]:g} är mixen godkänd",
                  lambda m, s, a: [True], False),
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
    "spela_fas": ("fasspel", lambda m, s, a: f"Fas {getattr(m, 'steg_nr', '')}: lägg kompetenskort på bordet",
                  lambda m, s, a: s.hand, False),
    # Förvaltning
    "valj_fc": ("val", lambda m, s, a: "Välj fastighetschef (FC)", lambda m, s, a: a[0], False),
    "valj_fs": ("val", lambda m, s, a: "Välj förvaltningsstöd (FS)", lambda m, s, a: a[0], False),
    "vill_kopa": ("janej", lambda m, s, a: f"Köpa {etikett(a[0], m)} för {a[1]:g} Mkr?", None, False),
    "forhandlingskort": ("flerval", lambda m, s, a: "Spela förhandlingskort?",
                         lambda m, s, a: _med_effekt(s.hand, "forhandling_mod", "forhandling_auto"), False),
    "vill_sanera": ("janej", lambda m, s, a: f"Ta saneringsuppdraget för {etikett(a[0], m)} (skuld {a[1]:g} Mkr)?", None, False),
    "tvangsbud": ("val", lambda m, s, a: "Lägga ett tvångsbud?",
                  lambda m, s, a: [(o, f) for o in _andra(m, s) for f in o.fastigheter if m.kan_tvangsbudas(f)], True),
    "stoppa": ("val", lambda m, s, a: f"Stoppa tvångsbudet på {etikett(a[0], m)}?", lambda m, s, a: a[1], True),
    "duellkort": ("flerval", lambda m, s, a: "Spela kort i duellen?",
                  lambda m, s, a: _med_effekt(s.hand, "forhandling_mod"), False),
    "motbudsmal": ("val", lambda m, s, a: "Motbud: vilken av budgivarens fastigheter vill ni ha?",
                   lambda m, s, a: a[0].fastigheter, True),
    "salj": ("flerval", lambda m, s, a: "Sälja fastigheter till banken?", lambda m, s, a: s.fastigheter, False),
    "salj_for_likviditet": ("val", lambda m, s, a: "Kassan är negativ: vilken fastighet säljer ni?",
                            lambda m, s, a: s.fastigheter, False),
    "roj": ("flerval", lambda m, s, a: "Röja underhållsvarningar?",
            lambda m, s, a: [(f, i) for f in s.fastigheter for i in range(len(f.varningar))], False),
    "visa_plus": ("janej", lambda m, s, a: f"Visa plusbrickan på {etikett(a[0], m)}?", None, False),
    "eliminera": ("janej", lambda m, s, a: f"Stoppa händelsen {etikett(a[1], m)} på {etikett(a[0], m)}?", None, False),
    "valj_dd": ("val", lambda m, s, a: f"Due diligence för {etikett(a[0], m)}: två DD-kort – vilket gäller?",
                lambda m, s, a: a[1], False),
    "slang": ("val", lambda m, s, a: "Handen är full: vilket kort slänger ni?", lambda m, s, a: s.hand, False),
    "spela_nu": ("flerval", lambda m, s, a: "Spela nätverkskort nu?",
                 lambda m, s, a: _med_effekt(s.hand, *SPELBARA_NU), False),
    "konverteringsmal": ("val", lambda m, s, a: "Vilken fastighet konverterar ni till hyresrätt?",
                         lambda m, s, a: s.fastigheter, True),
    "valj_plusfastighet": ("val", lambda m, s, a: "Vilken fastighet får plusbrickan?", lambda m, s, a: s.fastigheter, False),
    "valj_energifastighet": ("val", lambda m, s, a: "Vilken fastighet får energibrickan?",
                             lambda m, s, a: s.fastigheter, True),
    "varvningsmal": ("val", lambda m, s, a: "Hyresgästvärvning: från vilken fastighet till vilken?",
                     lambda m, s, a: [(e, f) for e in s.fastigheter for o in _andra(m, s) for f in o.fastigheter], True),
    "valj_typ": ("val", lambda m, s, a: (f"Omvärldskortet ”{getattr(m, 'orsak_kort', {}).get('Rubrik', '')}”: vilken fastighetstyp "
                                        f"får {'+1' if a[0] > 0 else '−1'} i driftnetto hos alla spelare?")
                 if getattr(m, "orsak_kort", None) else "Vilken fastighetstyp väljer ni?",
                 lambda m, s, a: ["HYRESRÄTT", "LOKAL", "KONTOR", "FÖRSKOLA"], False),
    "uppgradera": ("flerval", lambda m, s, a: f"Energiuppgradera (högst {a[0]} fastigheter)?",
                   lambda m, s, a: s.fastigheter, False),
    "energikort": ("flerval", lambda m, s, a: "Spela energikort?", lambda m, s, a: _med_effekt(s.hand, "energi_mod"), False),
    "fortsatt_uppgradera": ("janej", lambda m, s, a: f"Fortsätta uppgradera {etikett(a[0], m)}?", None, False),
}
# ---------------------------------------------------------------------------- förklaringar
# Vad beslutet betyder och vad som händer, med spelets ord. metod -> text(m, s, a).
EFFEKT = {
    "dolt_plus_dn": "en dold plusbricka på fastigheten (+1 i driftnetto)",
    "dolt_minus_dn": "en dold minusbricka på fastigheten (−1 i driftnetto)",
    "energi_plus": "en energibricka plus (kan ge bättre energiklass)",
    "energi_minus": "en energibricka minus (kan ge sämre energiklass)",
    "direkt_dn_plus": "+1 i driftnetto direkt",
    "direkt_dn_minus": "−1 i driftnetto direkt",
    "direkt_ek_plus": "ett steg bättre energiklass",
    "direkt_ek_minus": "ett steg sämre energiklass",
    "underhallsvarning": "en underhållsvarning (tre varningar ger −1 i driftnetto tills de tas bort med kort)",
    "villkorskort": "ett villkor som följer fastigheten",
    "engangskassa_plus": "pengar in i kassan nästa kvartal",
    "typbred_dolt_minus": "en dold minusbricka på alla fastigheter av typen",
    "engangskassa_minus": "en kostnad som dras från kassan nästa kvartal",
}


def _effekt(kort):
    e = EFFEKT.get(kort.get("Effekt"), "")
    v = kort.get("Värde")
    if v not in (None, "", "-") and kort.get("Effekt", "").startswith("engangskassa"):
        e += f" ({_tal(v):g} Mkr)"
    return e


def konsekvens(m, f, kort):
    """Vad ett händelsekort gör med just den här fastigheten, i klartext (för frågan)."""
    e, v = kort.get("Effekt"), kort.get("Värde")
    namn = f.namn
    try:
        dn = m.eff_dn(f)
    except Exception:                                        # noqa: BLE001
        dn = None
    if e == "underhallsvarning":
        n = len(f.varningar) + 1
        try:                                                  # Bostadsveteranen: straff först vid fyra på hyresrätter
            grans = 4 if m.ar_fc(m.agare(f), "Bostadsveteranen") and f.typ == "HYRESRÄTT" else 3
        except Exception:                                    # noqa: BLE001
            grans = 3
        return (f"{namn} får en underhållsvarning – {n} av {grans}. "
                + (f"Vid {grans} sjunker driftnettot med 1 Mkr/år och energiuppgraderingar stoppas." if n < grans
                   else "Då sjunker driftnettot med 1 Mkr/år och energiuppgraderingar stoppas."))
    if e == "direkt_dn_minus":
        return f"Driftnettot på {namn} sjunker med 1 Mkr/år" + (f" (från {dn:g} till {max(0, dn - 1):g})." if dn is not None else ".")
    if e == "dolt_minus_dn":
        return (f"En dold minusbricka läggs på {namn} (nettot blir {f.dn_brickor - 1:+d}). "
                "När nettot når −3 sjunker driftnettot med 1 Mkr/år.")
    if e == "energi_minus":
        return (f"En energibricka minus läggs på {namn} (nettot blir {f.ek_brickor - 1:+d}); "
                f"vid −3 blir energiklassen ett steg sämre (nu {f.ek}).")
    if e == "engangskassa_minus":
        return f"Ni betalar {_tal(v):g} Mkr, som dras från kassan vid nästa marknad."
    if e == "villkorskort":
        return f"Villkoret följer {namn}: {kort.get('Beskrivning') or ''}"
    return _effekt(kort)


def _eliminera(m, s, a):
    f, kort, gratis = a[0], a[1], bool(a[2]) if len(a) > 2 else False
    if gratis:
        return "Er fastighetschef Skölden kan stoppa det gratis (en gång per kvartal)."
    return f"Ni kan stoppa det genom att lämna en riskbuffert (ni har {s.riskbuffert})."


HJALP = {
    "eliminera": _eliminera,
    "valj_fc": lambda m, s, a: "Fastighetschefen ger en styrka hela Förvaltningen. Efter några kvartal blir hen senior och blir starkare.",
    "valj_fs": lambda m, s, a: "Förvaltningsstödet är en specialist med en egen förmåga, t.ex. bättre due diligence eller energiarbete.",
    "vill_kopa": lambda m, s, a: "Köper ni får ni fastigheten med dess driftnetto varje kvartal. Priset betalas ur kassan, resten lånas.",
    "forhandlingskort": lambda m, s, a: "Förhandlingskort förbättrar ert slag i förhandlingen om priset.",
    "vill_sanera": lambda m, s, a: "En fastighet med för stor skuld säljs ut. Tar ni uppdraget köper ni den billigt men tar över skulden.",
    "tvangsbud": lambda m, s, a: "Ett tvångsbud är ett fientligt köp av en annan spelares fastighet. Budet kostar en avgift oavsett utfall, och ägaren kan försöka stoppa det.",
    "stoppa": lambda m, s, a: "Någon vill tvångsköpa er fastighet. Ni kan stoppa det med ett motbud, ett kort eller riskbuffertar, eller låta det gå till duell.",
    "duellkort": lambda m, s, a: "I duellen slår båda; kort ni spelar här lägger till på ert slag.",
    "motbudsmal": lambda m, s, a: "Ett motbud: i stället för att förlora fastigheten tar ni en av budgivarens.",
    "salj": lambda m, s, a: "Banken köper till marknadsvärdet minus lånet. Sälj om ni behöver kassa eller vill bli av med en svag fastighet.",
    "salj_for_likviditet": lambda m, s, a: "Kassan får inte vara negativ. En fastighet måste säljas till banken.",
    "roj": lambda m, s, a: "Att röja en underhållsvarning kostar pengar nu men tar bort risken för sänkt driftnetto.",
    "visa_plus": lambda m, s, a: "En dold plusbricka höjer värdet när den visas. Visar ni den nu syns den för alla.",
    "valj_dd": lambda m, s, a: (f"Normalt dras ett DD-kort som gäller direkt. {getattr(m, 'orsak_dd', None) or 'Ett kort ni har'} "
                               "låter er dra två och välja vilket som gäller (9.9)."),
    "slang": lambda m, s, a: "Ni får bara ha ett visst antal kort på handen. Välj vilket som ska bort.",
    "spela_nu": lambda m, s, a: "Nätverkskort kan spelas nu eller sparas till senare.",
    "uppgradera": lambda m, s, a: "Energiuppgradering kostar pengar och kräver ett lyckat slag, men bättre energiklass höjer driftnettot.",
    "fortsatt_uppgradera": lambda m, s, a: "Försöket misslyckades. Ni kan betala för ett nytt försök.",
    "vill_expandera": lambda m, s, a: "En markexpansion kostar 5 Mkr och ger mer mark att bygga på i 4.3.",
    "fordela_krav": lambda m, s, a: (
        f"Kraven sänks – det är bra för er. Ni har nu Q-krav {s.q_krav} och H-krav {s.h_krav}; ju lägre krav, desto "
        "lättare att nå dem i Skede 2." if a[0] < 0 else
        f"Kraven höjs. Ni har nu Q-krav {s.q_krav} och H-krav {s.h_krav}; lägg höjningen där ni har lättast att nå kravet."),
    "valj_projekt": lambda m, s, a: (
        "Ta det översta kortet eller ett projekt av samma typ ur projektbanken. Tar ni inget läggs det dragna "
        "kortet i projektbanken (3.3)." if len(getattr(m, "projektval_typer", [])) == 1 else
        "Ni får ta det översta kortet i valfri hög eller ett projekt ur projektbanken. Tar ni inget händer inget"
        + (" – vid Stadshuset kan ni i stället lämna tillbaka ett projekt (3.7)." if "Stadshuset" in str(getattr(m, "orsak", "")) else ".")),
    "sla_namnd": lambda m, s, a: (
        f"Summan av projektens nämndsiffror minus projektchefens nämndslag är {a[0]:g}. "
        f"Chansen att klara det: {100 * (1 - (min(20, max(0, a[0])) / 20) ** a[1]):.0f} %."),
    "kulturkort": lambda m, s, a: (f"Kulturkort ger kompetens att spela i fasen. {len(getattr(m, 'kulturhog', []))} kort finns kvar i högen; "
                                   f"ni har {s.kvar:.0f} Mkr kvar av ABT-budgeten."),
    "sla_om_handelse": lambda m, s, a: (f"Ni har {s.riskbuffert} riskbuffertar. Ett omslag kostar en och ger ett nytt D20-slag "
                                        "(plus erfarenhet); det nya utfallet gäller, även om det blir sämre (3.6)."),
    "sla_om_kort": lambda m, s, a: (f"Ni har {s.riskbuffert} riskbuffertar. Ett omslag kostar en och ger ett nytt D20-slag "
                                    "(plus erfarenhet); det nya utfallet gäller, även om det blir sämre (3.6)."),
    "sla_om_namnd": lambda m, s, a: "Nämnden kräver att tärningen visar mer än summan av projektens nämndsiffror.",
    "namnd_miss_hoj_krav": lambda m, s, a: "Regelboken 4.1: Ja betyder att ni höjer Q- eller H-kravet med 1 (ni väljer vilket i nästa fråga) och slår igen med en tärning mer. Nej betyder att ni lämnar tillbaka ett projekt i stället.",
}


MAX_TAL = {"rb_sank_krav": lambda m, s, a: getattr(s, "riskbuffert", 0), "kulturkort": lambda m, s, a: max(0, len(getattr(m, "kulturhog", [])) or 5)}
MAX_FLERVAL = {"uppgradera": lambda m, s, a: a[0]}


def _ar_kort(x):
    """Ett kort ur en lek (inte en fastighet, ett projekt på brädet eller ett tal)."""
    return isinstance(x, dict) and any(k in x for k in ("Kort-id", "ID", "Id")) and "Anskaffning (Mkr)" not in x


def beskriv_beslut(metod, motor, subjekt, args, rotter, forslag, analog=False):
    """Vy för en fråga till en människa. `forslag` är bottens svar (objekt), kodat blir det standardvalet.
    `analog`: spel vid brädet — pusslet läggs på riktigt, så 4.3 frågar bara vilka projekt som fick plats."""
    if analog and metod == "placering":
        projekt = args[0]
        return {"typ": "flerval", "rubrik": "4.3 Placering: vilka projekt fick plats på tomten?",
                "kvarter": getattr(subjekt, "namn", None),
                "forslag_text": ", ".join(forslag) or "Inga",
                "alternativ": [{"text": p["Namn"], "detalj": detalj(p, motor), "kod": p["Namn"], **bild(p)} for p in projekt],
                "valda": list(range(len(projekt))),
                "hjalp": "Det som inte fick plats går till projektbanken och tar med sig sina krav."}
    typ, rubrik, pool, inget = BESLUT.get(metod, ("forslag", lambda m, s, a: metod.replace("_", " ").capitalize(), None, False))
    rub = rubrik(motor, subjekt, args)
    vy = {"typ": typ, "rubrik": rub[:1].upper() + rub[1:], "kvarter": getattr(subjekt, "namn", None),
          "forslag_text": etikett(forslag, motor) if not isinstance(forslag, list)
          else (", ".join(etikett(x, motor) for x in forslag) or "Inga")}
    if metod in HJALP:
        try:
            vy["hjalp"] = HJALP[metod](motor, subjekt, args).strip()
        except Exception:                                    # noqa: BLE001 — bara presentation
            pass
    if metod == "valj_typ" and getattr(motor, "orsak_kort", None):
        from .parti import kortvy
        vy["kort"] = {**kortvy(motor.orsak_kort), "lek": "omvärld"}
        vy["hjalp"] = ("Ni har dragits att välja. Valet gäller alla spelares fastigheter av typen – "
                       + ("välj en typ ni själva har mycket av." if args[0] > 0 else "välj en typ ni själva har lite av."))
    if metod in ("sla_om_handelse", "sla_om_kort") and isinstance(args[0], dict):
        from .parti import kortvy
        vy["kort"] = {**kortvy(args[0]), "lek": "händelse"}
        vy["ja"], vy["nej"] = "Ja, slå om (−1 riskbuffert)", "Nej, behåll utfallet"
    if metod == "eliminera":
        from .parti import kortvy
        vy["rubrik"] = f"Stoppa händelsen ”{args[1].get('Rubrik') or kortnamn(args[1])}” på {etikett(args[0], motor)}?"
        gratis = len(args) > 2 and bool(args[2])
        vy["ja"] = "Ja, stoppa den (gratis med Skölden)" if gratis else "Ja, stoppa den (−1 riskbuffert)"
        vy["nej"] = "Nej, låt den gälla"
        vy["kort"] = {**kortvy(args[1]), "lek": f"händelse {args[0].typ.lower()}"}
        vy["konsekvens"] = konsekvens(motor, args[0], args[1])
        vy["kort"]["rader"] = vy["kort"]["rader"] + [["Effekt", _effekt(args[1]) or "–"]]
    if pool:
        text = (lambda x: f"Q {x[0]:+d} · H {x[1]:+d}") if metod == "fordela_krav" else (lambda x: etikett(x, motor))
        from .parti import kortvy
        vy["alternativ"] = [{"text": text(x), "detalj": detalj(x, motor), "kod": koda(x, rotter), **bild(x),
                             **({"kort": kortvy(x)} if _ar_kort(x) else {})}
                            for x in pool(motor, subjekt, args)]
        if metod in ("valj_projekt", "komplettera"):          # var projektet kommer ifrån
            bank = getattr(motor, "bank", [])
            for a_, x in zip(vy["alternativ"], pool(motor, subjekt, args)):
                if isinstance(x, dict):
                    kalla = "Ur projektbanken" if any(x is b for b in bank) else "Översta i högen"
                    a_["detalj"] = f"{kalla} · {a_['detalj']}" if a_.get("detalj") else kalla
        if metod == "sla_namnd":
            vy["alternativ"][0].update(text="Slå tärningen", detalj="")
            vy["forslag_text"] = "slå"
        if metod == "fordela_krav":
            vy["forslag_text"] = text(forslag)
            for a_, x in zip(vy["alternativ"], pool(motor, subjekt, args)):   # vad kraven blir
                a_["detalj"] = (f"Q-krav {subjekt.q_krav} → {subjekt.q_krav + x[0]} · "
                                f"H-krav {subjekt.h_krav} → {subjekt.h_krav + x[1]}")
        if inget:
            vy["alternativ"].append({"text": "Inget", "kod": None,
                                     "detalj": "Det dragna kortet läggs i projektbanken (3.3)"
                                     if metod == "valj_projekt" and len(getattr(motor, "projektval_typer", [])) == 1 else ""})
    if typ == "tal":
        vy["min"], vy["max"] = 0, int(MAX_TAL.get(metod, lambda m, s, a: 10)(motor, subjekt, args))
    if typ == "flerval" and metod in MAX_FLERVAL:
        vy["max"] = int(MAX_FLERVAL[metod](motor, subjekt, args))
    if typ == "fasspel":                                    # Genomförandet: korten, nivåerna och kraven
        from .parti import kortvy
        from .skede2 import kompetenser
        fas, nivaer = args[0], args[1]
        vy["fas_kort"] = {**kortvy(fas), "lek": f"FAS {getattr(motor, 'steg_nr', '')}"}
        vy["nivaer"] = [[n, kr, str(fas.get(f"Effekt {n.lower()}") or "")] for n, kr in nivaer]
        for a_, k in zip(vy["alternativ"], subjekt.hand):
            a_["komp"] = kompetenser(k)
            a_["kort"] = kortvy(k)
        vy["forslag_text"] = ", ".join(etikett(k, motor) for k in forslag) if forslag else "Inga kort"
        vy["hjalp"] = ("Tryck på korten ni vill spela så läggs de på bordet. Summan visar vilken nivå ni når. "
                       "Når ni ingen nivå över Negativt går korten tillbaka till handen (7.5).")
    if typ in ("pussel", "markexpansion"):
        vy["mark"] = sorted(list(c) for c in subjekt.mark)
        vy["grundmark"] = sorted(list(c) for c in GRUNDMARK)
        former = motor.markformer(subjekt)                   # lagda markexpansioner: får flyttas
        vy["markbitar"] = [{"id": i, "form": [list(c) for c in former[i]], "celler": sorted(list(c) for c in celler)}
                           for i, celler in sorted(subjekt.markbitar.items())]
    if typ == "pussel":
        vy["forslag_text"] = f"{len(forslag)} av {len(args[0])} projekt placerade (visa med ”Visa en lösning”)"
        vy["projekt"] = [{"namn": p["Namn"], "typ": p["Typ"], "form": [list(c) for c in form_av(p)]} for p in args[0]]
    if typ == "markexpansion":
        vy["form"] = [list(c) for c in form_av(args[0])]
        vy["id"] = markid(args[0])
        vy["forslag_text"] = "den mest kompakta platsen"
        vy["platser"] = [sorted(list(c) for c in celler) for celler in args[1]]
    return vy


# ---------------------------------------------------------------------------- slumpens frågor
def _hognamn(hog):
    """'handelse_HYRESRÄTT' -> 'händelsekort hyresrätt' — högens namn som spelarna säger det."""
    s = str(hog).replace("handelse_", "händelsekort ").replace("kvartal_", "kvartalskort ").replace("yield_", "yieldkort ")
    s = {"natverk": "nätverkskort", "omvarld": "omvärldskort", "dd": "DD-kort"}.get(s, s)
    return s.replace("_", " ").replace("HYRESRÄTT", "hyresrätt").replace("FÖRSKOLA", "förskola") \
        .replace("LOKAL", "lokal").replace("KONTOR", "kontor")


def beskriv_slump(metod, argument):
    """Vy för en slumpfråga i fysiskt spel (läge 2). Svaret är ett tal eller ett index i alternativen."""
    if metod in ("d20", "tarning", "heltal", "index"):
        lag, hog = argument
        rubrik = {"d20": "Slå D20: vad visade tärningen?", "tarning": f"Slå D{hog}: vad visade tärningen?"}.get(
            metod, f"Ange ett tal mellan {lag} och {hog}")
        return {"typ": "tal", "rubrik": rubrik, "min": lag, "max": hog}
    if metod == "dra":
        hog, kort = argument[0], argument[1]
        rubriker = argument[2] if len(argument) > 2 else [""] * len(kort)
        return {"typ": "val", "rubrik": f"Dra ett kort ur högen {_hognamn(hog)}: vilket fick ni?",
                "alternativ": [{"text": k, "detalj": r if r != k else "", "kod": i}
                               for i, (k, r) in enumerate(zip(kort, rubriker))], "sok": True}
    return {"typ": "val", "rubrik": "Välj blint: vilket blev det?",
            "alternativ": [{"text": k, "detalj": "", "kod": i} for i, k in enumerate(argument)]}
