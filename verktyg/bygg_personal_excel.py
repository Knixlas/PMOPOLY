"""Bygg kortdata/L_personal.xlsx, PU_personal.xlsx och PL_personal.xlsx ur det tryckta spelet.

De tre personalkorttyperna (Ledning CEO/CFO/COO, projektchefer, arbetschefer) har samma
CSV-struktur och nästan samma mall, så de byggs av ett och samma skript.

Källor per korttyp <typ>:
  - arv/spelet2_v1/<skede>/<typ>.csv          (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/<typ>_tryckeri.txt        (text utläst ur tryckfilen, 2 rader per kort:
                                               rad 1 = bildsida/framsida, rad 2 = textsida/baksida)

Det tryckta är facit. Skriptet jämför varje tryckt fält kort för kort mot CSV:n. Kända
avvikelser ligger i KORRIGERINGAR (tryckets värde skrivs då till Excel); okända avvikelser
avbryter bygget.

Kör:  python verktyg/bygg_personal_excel.py            (alla tre)
      python verktyg/bygg_personal_excel.py PU_personal (en)
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

KOMPETENSER = [("STA", "Stabilitet"), ("KOM", "Kommunikation"), ("SAM", "Samarbete"),
               ("NOG", "Noggrannhet"), ("INN", "Innovation"), ("ABM", "Arbetsmiljö")]
KOMPETENS_ETIKETTER = "  ".join(f"{k}   {n}" for k, n in KOMPETENSER)

PRODUKTION_KOLUMNER = ["@bild", "fill_color", "line_color", "skede_color", "bakskede",
                       "bakgrund_color", "ordning_bild", "ordning_text"]

# Tryckta etiketter på baksidan -> CSV-kolumn. Värdet står direkt efter etiketten
# i PDF:ens läsordning (siffra eller '-'; saknas värde följer nästa etikett direkt).
ETIKETT_TILL_KOLUMN = {
    "erfarenhet": "Erfarenhet",
    "riskbuffert": "Rb",
    "nämndslag": "Nämnd",
    "kvalitet": "Q",
    "tid": "T",
    "hållbarhet": "H",
}

# Kända avvikelser CSV ↔ tryck: {(ID, CSV-kolumn): (värde i CSV, tryckt värde, kommentar)}.
# Tryckets värde skrivs till Excel. CSV-värdet kontrolleras så att tabellen inte blir inaktuell.
# Kontrollen 2026-09-26 gav 0 avvikelser i tryckta fält för alla tre typer — tabellerna är tomma.
KORRIGERINGAR = {
    "L_personal": {},
    "PU_personal": {},
    "PL_personal": {},
}


def _kompetenser_forklaring(kod, namn):
    return (f"Kompetens {kod} ({namn}), sektionen FÖRETAGSKULTUR — används i genomförandefasen. "
            "'-' = ingen")


def _kompetenskolumner():
    return [(f"{kod} {namn}", kod, True, _kompetenser_forklaring(kod, namn)) for kod, namn in KOMPETENSER]


# ---------------------------------------------------------------------------
# Korttyperna
# ---------------------------------------------------------------------------
TYPER = {
    "L_personal": {
        "csv": "0. Ledning/L_personal.csv",
        "csv_datum": "2026-04-29 19:36 UTC — EFTER tryck (tryck 2026-04-27 ca 22:14 UTC)",
        "markering": "L",
        "sektion": None,
        "etiketter": [],
        "kravrubrik": None,
        "korttyp": "L_personal — ledningskort (CEO, COO, CFO), skede 0 Ledning",
        "tryckfil": "OneDrive: SPELET 2/PDF/Tryckbara/L_personal_tryckeri.pdf "
                    "(senast ändrad 2026-04-27 18:35 UTC), 36 sidor",
        "tryckta_extra": [],
        "ej_tryckta": [
            ("Specialisering", "Specialisering", False, "Ej tryckt — t.ex. 'Vision & strategi'"),
            ("Projekt 1", "Projekt1", False, "Ej tryckt — meritlista (tillagd/ändrad i CSV efter tryck?)"),
            ("Projekt 2", "Projekt2", False, "Ej tryckt — meritlista"),
            ("Projekt 3", "Projekt3", False, "Ej tryckt — meritlista"),
            ("Projekt 4", "Projekt4", False, "Ej tryckt — meritlista"),
            ("Riskbuffert (Rb)", "Rb", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Lindring", "Lindring", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Händelsemotstånd", "Händelsemotstand", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Nämnd", "Nämnd", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Kvalitet Q", "Q", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Hållbarhet H", "H", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Tid T", "T", False, "Ej tryckt — '-' på alla ledningskort"),
            ("Erfarenhet", "Erfarenhet", False, "Ej tryckt — '-' på alla ledningskort"),
        ],
        "malltext": [
            ("Framsida", "Skedesmärke", "L"),
            ("Baksida", "Skedesmärke", "L"),
            ("Baksida", "Etiketter", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · "
                                     "NOG Noggrannhet · INN Innovation · ABM Arbetsmiljö"),
            ("Baksida", "Sektion", "FÖRETAGSKULTUR"),
            ("Baksida", "Undertext", "används i genomförandefasen"),
            ("Baksida", "Regel", "KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE"),
        ],
        "fasta_baksida": ["FÖRETAGSKULTUR  används i genomförandefasen",
                          "KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE"],
        "exemplar_kalla": "exemplar_map.json: L_personal_bildsida/textsida = 1 "
                          "(L_personal saknas i utskrift_config.json)",
    },
    "PU_personal": {
        "csv": "1. Projektutveckling/PU_personal.csv",
        "csv_datum": "2026-04-26 17:27 UTC — före tryck",
        "markering": "PU",
        "sektion": "PROJEKTUTVECKLING",
        "etiketter": ["erfarenhet", "riskbuffert", "nämndslag", "kvalitet", "tid", "hållbarhet"],
        "kravrubrik": "MINSKAR KRAVEN ENLIGT NEDAN",
        "korttyp": "PU_personal — projektchefskort, skede 1 Projektutveckling",
        "tryckfil": "OneDrive: SPELET 2/PDF/Tryckbara/PU_personal_tryckeri.pdf "
                    "(senast ändrad 2026-04-27 20:12 UTC), 20 sidor",
        "tryckta_extra": [
            ("Erfarenhet", "Erfarenhet", True, "Tryckt som 'erfarenhet:'; tomt = inget värde tryckt"),
            ("Riskbuffert", "Rb", True, "Tryckt som 'riskbuffert:'; '-' = ingen"),
            ("Nämndslag", "Nämnd", True, "Tryckt som 'nämndslag:'; tomt = inget värde tryckt"),
            ("Minskar krav: kvalitet (Q)", "Q", True, "Under 'MINSKAR KRAVEN ENLIGT NEDAN', etikett 'kvalitet:'"),
            ("Minskar krav: tid (T)", "T", True, "Under 'MINSKAR KRAVEN ENLIGT NEDAN', etikett 'tid:'"),
            ("Minskar krav: hållbarhet (H)", "H", True,
             "Under 'MINSKAR KRAVEN ENLIGT NEDAN', etikett 'hållbarhet:'"),
        ],
        "ej_tryckta": [
            ("Specialisering", "Specialisering", False, "Ej tryckt — t.ex. 'Politik', 'Nämnd'"),
            ("Lindring", "Lindring", False, "Ej tryckt — speldata"),
            ("Händelsemotstånd", "Händelsemotstand", False, "Ej tryckt — kortslag som lindras "
                                                            "(Politikkort, Dialogkort, Nämnd)"),
        ],
        "malltext": [
            ("Framsida", "Skedesmärke", "PU"),
            ("Baksida", "Skedesmärke", "PU"),
            ("Baksida", "Sektion", "PROJEKTUTVECKLING"),
            ("Baksida", "Etiketter", "erfarenhet: · riskbuffert: · nämndslag:"),
            ("Baksida", "Etiketter", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · "
                                     "NOG Noggrannhet · INN Innovation · ABM Arbetsmiljö"),
            ("Baksida", "Sektion", "FÖRETAGSKULTUR"),
            ("Baksida", "Undertext", "används i genomförandefasen"),
            ("Baksida", "Rubrik", "MINSKAR KRAVEN ENLIGT NEDAN"),
            ("Baksida", "Etiketter", "kvalitet: · tid: · hållbarhet:"),
            ("Baksida", "Regel", "KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE"),
        ],
        "fasta_baksida": ["PU   PROJEKTUTVECKLING", "FÖRETAGSKULTUR  används i genomförandefasen",
                          "MINSKAR KRAVEN ENLIGT NEDAN", "KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE"],
        "exemplar_kalla": "exemplar_map.json: PU_personal_bildsida/textsida = 1; "
                          "utskrift_config.json: 'PU_PL_personal _kombinerad' = 1",
    },
    "PL_personal": {
        "csv": "2. Planering/PL_personal.csv",
        "csv_datum": "2026-04-26 17:27 UTC — före tryck",
        "markering": "PL",
        "sektion": "PLANERING",
        "etiketter": ["erfarenhet", "riskbuffert", "kvalitet", "tid", "hållbarhet"],
        "kravrubrik": "FÖRBÄTTRAR KRAVUPPFYLLNADEN MED",
        "korttyp": "PL_personal — arbetschefskort, skede 2 Planering",
        "tryckfil": "OneDrive: SPELET 2/PDF/Tryckbara/PL_personal_tryckeri.pdf "
                    "(senast ändrad 2026-04-27 21:11 UTC), 20 sidor",
        "tryckta_extra": [
            ("Erfarenhet", "Erfarenhet", True, "Tryckt som 'erfarenhet:'"),
            ("Riskbuffert", "Rb", True, "Tryckt som 'riskbuffert:'; tomt = inget värde tryckt"),
            ("Förbättrar krav: kvalitet (Q)", "Q", True,
             "Under 'FÖRBÄTTRAR KRAVUPPFYLLNADEN MED', etikett 'kvalitet:'"),
            ("Förbättrar krav: tid (T)", "T", True, "Under 'FÖRBÄTTRAR KRAVUPPFYLLNADEN MED', etikett 'tid:'"),
            ("Förbättrar krav: hållbarhet (H)", "H", True,
             "Under 'FÖRBÄTTRAR KRAVUPPFYLLNADEN MED', etikett 'hållbarhet:'"),
        ],
        "ej_tryckta": [
            ("Specialisering", "Specialisering", False, "Ej tryckt — t.ex. 'Samordning', 'Produktion'"),
            ("Lindring", "Lindring", False, "Ej tryckt — speldata"),
            ("Händelsemotstånd", "Händelsemotstand", False, "Ej tryckt — kortslag som lindras "
                                                            "(Politikkort, Dialogkort, Nämnd)"),
            ("Nämnd", "Nämnd", False, "Ej tryckt — tom på alla arbetschefskort"),
        ],
        "malltext": [
            ("Framsida", "Skedesmärke", "PL"),
            ("Baksida", "Skedesmärke", "PL"),
            ("Baksida", "Sektion", "PLANERING"),
            ("Baksida", "Regel", "KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE"),
            ("Baksida", "Etiketter", "erfarenhet: · riskbuffert:"),
            ("Baksida", "Etiketter", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · "
                                     "NOG Noggrannhet · INN Innovation · ABM Arbetsmiljö"),
            ("Baksida", "Sektion", "FÖRETAGSKULTUR"),
            ("Baksida", "Undertext", "används i genomförandefasen"),
            ("Baksida", "Rubrik", "FÖRBÄTTRAR KRAVUPPFYLLNADEN MED"),
            ("Baksida", "Etiketter", "kvalitet: · tid: · hållbarhet:"),
        ],
        "fasta_baksida": ["PL   PLANERING  KASTAS NÄR DET ANVÄNDS I GENOMFÖRANDE",
                          "FÖRETAGSKULTUR  används i genomförandefasen",
                          "FÖRBÄTTRAR KRAVUPPFYLLNADEN MED"],
        "exemplar_kalla": "exemplar_map.json: PL_personal_bildsida/textsida = 1; "
                          "utskrift_config.json: 'PU_PL_personal _kombinerad' = 1",
    },
}


# ---------------------------------------------------------------------------
# Tolkning av tryckt text
# ---------------------------------------------------------------------------
def las_tryck(typ, cfg):
    """Tolka tryckfilens text: rad 1 = framsida (bildsida), rad 2 = baksida (textsida)."""
    fil = TRYCKT_TEXT / f"{typ}_tryckeri.txt"
    rader = [r for r in fil.read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{fil.name}: udda antal rader ({len(rader)})")
    mark = cfg["markering"]
    kort = []
    for nr, (fram, bak) in enumerate(zip(rader[0::2], rader[1::2]), 1):
        # Framsida: "<Roll>  <Namn>  <skedesmärke>"
        f = re.split(r"\s{2,}", fram.strip())
        if len(f) != 3 or f[2] != mark:
            sys.exit(f"{typ} kort {nr}: oväntad framsida {fram!r}")
        roll, namn = f[0], f[1]

        # Baksida: "<Namn>  <Beskrivning>  <Roll>  <skedesmärke> ..."
        m = re.match(rf"(.+?)\s{{2,}}(.+)\s{{2,}}{re.escape(roll)}\s{{2,}}{mark}\s", bak)
        if not m:
            sys.exit(f"{typ} kort {nr}: hittar inte namn/beskrivning på baksidan")
        namn_bak = m.group(1)
        # Radbrytningar i beskrivningen blir ett blanksteg; avstavningen "ord -  ord"
        # utjämnas sedan av normalisera().
        besk = re.sub(r"\s+", " ", m.group(2))
        rest = bak[m.end():]

        for fast in cfg["fasta_baksida"]:
            if fast not in bak:
                sys.exit(f"{typ} kort {nr}: fast malltext saknas: {fast!r}")

        # Kompetenser: etiketterna i ordning, sedan sex värden i samma ordning.
        k = re.search(re.escape(KOMPETENS_ETIKETTER) + r"((?:\s+(?:\d+|-)){6})\s", rest)
        if not k:
            sys.exit(f"{typ} kort {nr}: hittar inte kompetensvärdena")
        komp = dict(zip([kod for kod, _ in KOMPETENSER], k.group(1).split()))

        t = {"Roll": roll, "Roll (baksida)": roll, "Namn": namn, "Namn (baksida)": namn_bak,
             "Beskrivning": besk, **komp}

        # Etikett: värde. Värdet (siffra eller '-') följer direkt; annars kommer nästa etikett.
        for etikett in cfg["etiketter"]:
            e = re.findall(rf"(?<![\wåäö]){etikett}:(?:\s+(\d+|-)(?=\s|$))?", rest)
            if len(e) != 1:
                sys.exit(f"{typ} kort {nr}: etiketten {etikett!r} hittades {len(e)} gånger")
            t[ETIKETT_TILL_KOLUMN[etikett]] = e[0]
        if cfg["kravrubrik"]:
            # Kravvärdena ska stå efter kravrubriken (skyddar mot fel sektion).
            if rest.find(cfg["kravrubrik"]) > rest.find("kvalitet:"):
                sys.exit(f"{typ} kort {nr}: 'kvalitet:' står före {cfg['kravrubrik']!r}")
        kort.append(t)
    return kort


# ---------------------------------------------------------------------------
# Jämförelse och korrigering
# ---------------------------------------------------------------------------
def tillampa_korrigeringar(typ, rader):
    """Skriv tryckets värde över CSV:ns för kända avvikelser. Returnerar beskrivningar för kalla."""
    noteringar = []
    per_id = {r["ID"]: r for r in rader}
    for (kid, kol), (csv_varde, tryckt, kommentar) in KORRIGERINGAR[typ].items():
        r = per_id.get(kid)
        if r is None:
            sys.exit(f"{typ}: korrigering för okänt kort {kid}")
        if r.get(kol, "") != csv_varde:
            sys.exit(f"{typ}: korrigeringstabellen är inaktuell för {kid}/{kol}: "
                     f"CSV har {r.get(kol, '')!r}, tabellen väntar {csv_varde!r}")
        r[kol] = tryckt
        noteringar.append(f"{kid} {kol}: CSV {csv_varde!r} → tryckt {tryckt!r} ({kommentar})")
    return noteringar


def jamfor(typ, cfg, rader, tryck):
    if len(rader) != len(tryck):
        sys.exit(f"{typ}: antal kort skiljer: CSV {len(rader)}, tryck {len(tryck)}")
    avvikelser = []
    for r, t in zip(rader, tryck):
        for falt, tryckt in t.items():
            kol = {"Roll (baksida)": "Roll", "Namn (baksida)": "Namn"}.get(falt, falt)
            if normalisera(r.get(kol, "")) != normalisera(tryckt):
                avvikelser.append((r["ID"], r["Namn"], falt, tryckt, r.get(kol, "")))
    return avvikelser


def antal_jamforda_falt(tryck):
    return sum(len(t) for t in tryck)


# ---------------------------------------------------------------------------
def bygg(typ):
    cfg = TYPER[typ]
    rader = las_csv(cfg["csv"], "Namn")
    tryck = las_tryck(typ, cfg)
    noteringar = tillampa_korrigeringar(typ, rader)
    avvikelser = jamfor(typ, cfg, rader, tryck)
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", typ, a)
        sys.exit(f"{typ}: CSV och tryck skiljer — lägg in i KORRIGERINGAR innan Excel byggs.")

    kort_kolumner = (
        [("Kort-id", None, False, f"Löpnummer 1–{len(rader)} i tryckordning"),
         ("Roll", "Roll", True, "Tryckt på fram- och baksida"),
         ("Namn", "Namn", True, "Tryckt på fram- och baksida"),
         ("Beskrivning", "Beskrivning", True, "Löptext på baksidan")]
        + cfg["tryckta_extra"]
        + _kompetenskolumner()
        + [("ID", "ID", False, "Ej tryckt — kortets id i CSV")]
        + cfg["ej_tryckta"]
        + [("Antal exemplar", None, False, "Antal tryckta kort per spel (exemplar_map: 1)")]
    )
    langa = ("Beskrivning", "Projekt1", "Projekt2", "Projekt3", "Projekt4")

    csv_rader_totalt = len(las_csv(cfg["csv"], "bakgrund_color"))
    kontroll = (f"Alla tryckta fält jämförda kort för kort mot tryckfilen "
                f"({len(rader)} kort, {antal_jamforda_falt(tryck)} fält: roll och namn på båda sidor, "
                f"beskrivning, kompetenser"
                + (", " + ", ".join(cfg["etiketter"]) if cfg["etiketter"] else "")
                + f"): {len(noteringar)} avvikelser. Fast malltext kontrollerad på varje kort.")
    kalla = [
        ("Korttyp", cfg["korttyp"]),
        ("Antal kort", f"{len(rader)} unika, 1 exemplar vardera per spel"),
        ("Exemplar", cfg["exemplar_kalla"]),
        ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                   f"PDF/Tryckbara/_tryckeri_temp/{typ}_bildsida_layout.json"),
        ("Tryckfil", cfg["tryckfil"]),
        ("Tryckfilens text", f"arv/tryckt_text/{typ}_tryckeri.txt (utläst via OneDrive, 2 rader per kort)"),
        ("Datakälla", f"arv/spelet2_v1/{cfg['csv']}"),
        ("CSV-datum", cfg["csv_datum"]),
        ("Platshållare", f"CSV:n har {csv_rader_totalt} rader, varav {csv_rader_totalt - len(rader)} "
                         f"tomma platshållare utan namn; layout-JSON har {csv_rader_totalt} sidor, "
                         f"men tryckfilen innehåller bara de {len(rader)} ifyllda korten."),
        ("Kontroll", kontroll),
        ("Korrigeringar", "; ".join(noteringar) if noteringar else "Inga — CSV-värdena stämmer med trycket."),
        ("Byggd med", "verktyg/bygg_personal_excel.py"),
    ]
    kalla += cfg.get("extra_kalla", [])

    ut = bygg_arbetsbok(
        filnamn=f"{typ}.xlsx",
        kort_kolumner=kort_kolumner,
        rader=rader,
        namn_kolumn="Namn",
        malltext=cfg["malltext"],
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=langa,
        kalla=kalla,
    )
    print(f"Skrev {ut}: {len(rader)} kort, {len(noteringar)} korrigeringar, 0 okända avvikelser")


# Särskilt för L_personal: CSV:n ändrades efter tryck.
TYPER["L_personal"]["extra_kalla"] = [
    ("Ändrad efter tryck", "L_personal.csv sparades 2026-04-29, två dagar efter tryck. Alla tryckta fält "
                           "(roll, namn, beskrivning, sex kompetenser) stämmer ändå med trycket, så "
                           "ändringen gäller ej tryckta kolumner (t.ex. Specialisering, Projekt1–4) eller "
                           "produktionskolumner — vilka kan inte avgöras, ingen tidigare version finns "
                           "arkiverad. Ej tryckta värden i Excel kommer från den senare CSV:n."),
    ("Observation", "Beskrivningarna nämner äldre kortnamn: Skepparen-kortet säger 'Riktningsgivaren', "
                    "Urmakaren-kortet säger 'Maskinrumsmästaren'. Så står det både i CSV och tryck."),
]


def main():
    typer = sys.argv[1:] or list(TYPER)
    for typ in typer:
        if typ not in TYPER:
            sys.exit(f"Okänd korttyp {typ}; välj bland {', '.join(TYPER)}")
        bygg(typ)


if __name__ == "__main__":
    main()
