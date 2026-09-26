"""Bygg kortdata/PU_projekt.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/1. Projektutveckling/PU_projekt.csv  (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PU_projekt_tryckeri.txt             (text utläst ur tryckfilen, 2 rader per kort)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python verktyg/bygg_pu_projekt_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "PU_projekt_tryckeri.txt"

NIVAER = ["MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER",
          "STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"]
NIVA_ETIKETT = ["Mark", "Husunderbyggnad", "Stomme", "Yttertak", "Fasader",
                "Stomkomplettering", "Ytskikt", "Installationer", "Gemensamma arbeten"]

# (rubrik i Excel, CSV-kolumn, tryckt på kortet?, förklaring)
KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–45 i tryckordning"),
    ("Typ", "Typ", True, "Projekttyp: BRF, FÖRSKOLA, LOKAL, KONTOR, HYRESRÄTT"),
    ("Namn", "Namn", True, "Fullt namn (kortets baksida), t.ex. 'Förskolan Draklyan'"),
    ("Kortnamn", "Namn2", True, "Namn på framsidan, t.ex. 'Draklyan'"),
    ("Beskrivning", "Beskrivning", True, "Mäklartext på framsidan"),
    ("BTA (kvm)", "BTA", True, "Bruttoarea"),
    ("Utvecklingskostnad (Mkr)", "Kostnad", True, "Kostnad för att ta projektet i Skede 1"),
    ("Anskaffning (Mkr)", "Anskaffning", True, ""),
    ("Hållbarhetskrav H", "Hållbarhet", True, ""),
    ("Kvalitetskrav Q", "Kvalitet", True, ""),
    ("Tidspåverkan T", "Tid", True, "'-' = ingen påverkan"),
    ("Riskbuffert", "Riskbuffert", True, "'-' = ingen"),
    ("Passera nämnden (>)", "Nämndbeslut", True, "Tärningsresultatet måste överstiga detta"),
    ("Marknadsvärde (Mkr)", "Marknadsvärde", True, ""),
    ("Rörligt marknadsvärde", "Rörligt marknadsvärde", True, "Endast BRF — text på kortet"),
    ("Energiklass", "Energiklass", True, "Tryckt endast på förvaltningsbara typer (ej BRF)"),
    ("Driftnetto (Mkr/kvartal)", "Driftnetto", True, "Tryckt endast på förvaltningsbara typer (ej BRF)"),
] + [(f"Nivåkrav {etikett}", niva, True, "'-' = inget krav") for niva, etikett in zip(NIVAER, NIVA_ETIKETT)] + [
    ("Förekomst", "Förekomst", False, "Ej tryckt — speldata"),
    ("Formfaktor", "Formfaktor", False, "Ej tryckt — styr brickans form (1–8)"),
    ("Linjetyp", "linjetyp", False, "Ej tryckt — ramens linjestil"),
    ("Antal krav", "Antal krav", False, "Ej tryckt"),
    ("STA", "STA", False, "Ej tryckt — kompetens"),
    ("KOM", "KOM", False, "Ej tryckt — kompetens"),
    ("SAM", "SAM", False, "Ej tryckt — kompetens"),
    ("NOG", "NOG", False, "Ej tryckt — kompetens"),
    ("INN", "INN", False, "Ej tryckt — kompetens"),
    ("ABM", "ABM", False, "Ej tryckt — kompetens"),
    ("Skalfaktor", "Skalfaktor", False, "Ej tryckt"),
    ("Intäkt/kvm nu", "intäkt/kvm nu", False, "Ej tryckt — beräkningsunderlag"),
    ("Förslag intäkt", "förslag intäkt", False, "Ej tryckt — beräkningsunderlag"),
    ("Bildprompt (en)", "namn_en", False, "Ej tryckt — underlag för bildgenerering"),
    ("Antal exemplar", None, False, "Antal tryckta kort (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@formbild", "@titelbild", "fill_color", "line_color", "skede_color",
                       "bakskede", "bakgrund_color", "ordning_bild", "ordning_text", "status fb", "temp", "temp2"]

MALLTEXT = [
    ("Framsida", "Etiketter", "H · Q · BTA · Utvecklingskostnad · Anskaffning"),
    ("Baksida", "Etiketter", "Marknadsvärde · Mark: · Husunderbyggnad: · Stomme: · Yttertak: · Fasader: · "
                             "Stomkomplettering: · Ytskikt: · Installationer: · Gemensamma arbeten:"),
    ("Baksida", "Etiketter", "BTA · Utvecklingskostnad · Anskaffning · Riskbuffert · Passera nämnden · "
                             "Hållbarhetskrav · Kvalitetskrav · Tidspåverkan"),
    ("Baksida", "Sektion", "PLANERING"),
    ("Baksida (ej BRF)", "Sektion", "KÖP OCH SÄLJ FÖRVALTNING"),
    ("Baksida (ej BRF)", "Etiketter", "Aktuellt marknadsvärde · Driftnetto / Yield · Driftnetto · Energiklass · /kvartal"),
    ("Baksida (ej BRF)", "Regel", "Min. accepterat bud: 80 % av marknadsvärde"),
    ("Baksida (ej BRF)", "Regel", "Kontantinsats: 30 % av köpeskillingen"),
    ("Baksida", "Regel", "BEHÅLL KORTET UNDER HELA SPELET SÅ LÄNGE NI ÄGER DET"),
]


def las_tryck():
    """Tolka tryckfilens text: rad 1 = framsida, rad 2 = baksida."""
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    kort = []
    for fram, bak in zip(rader[0::2], rader[1::2]):
        f = re.split(r"\s{2,}", fram.strip())
        b = re.split(r"\s{2,}", bak.strip())
        m = re.search(r"H\s+(\d)\s+(\d)\s+Q$", fram)
        gi = b.index("Gemensamma arbeten:")
        j = b.index("PLANERING") + 1
        if b[j] == "KÖP OCH SÄLJ FÖRVALTNING":
            j += 1
        bta = b[j + 2].replace(" kvm", "")
        bi = b.index("BTA", j + 2)
        rest = b[b.index("Tidspåverkan") + 4:-1]
        ek = rest.pop(0) if re.fullmatch(r"[A-G]", rest[0]) else ""
        rorligt = dn = ""
        if len(rest) > 1:
            if rest[1].startswith("Vid"):
                rorligt = rest[1]
            else:
                dn = rest[1].replace(" Mkr", "")
        besk = " ".join(f[2:f.index(bta + " kvm")])
        kort.append({
            "Typ": f[0], "Namn": b[0], "Namn2": f[1],
            "Beskrivning": besk,
            "BTA": bta, "Kostnad": b[bi + 1].replace(" Mkr", ""), "Anskaffning": b[bi + 2].replace(" Mkr", ""),
            "Hållbarhet": m.group(1), "Kvalitet": m.group(2), "Tid": b[j + 1],
            "Riskbuffert": b[bi + 3], "Nämndbeslut": b[bi + 4].replace("> ", ""),
            "Marknadsvärde": rest[0].replace(" Mkr", ""), "Rörligt marknadsvärde": rorligt,
            "Energiklass": ek, "Driftnetto": dn,
            **dict(zip(NIVAER, b[gi + 1:gi + 10])),
        })
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avvikelser = []
    for r, t in zip(csv_rader, tryck):
        for falt, tryckt in t.items():
            if falt in ("Energiklass", "Driftnetto", "Rörligt marknadsvärde") and not tryckt:
                continue  # inte tryckt på denna korttyp
            if normalisera(r.get(falt, "")) != normalisera(tryckt):
                avvikelser.append((r["Namn"], falt, tryckt, r.get(falt, "")))
    return avvikelser


def main():
    rader = las_csv("1. Projektutveckling/PU_projekt.csv", "Namn")
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="PU_projekt.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="88 × 146",
        exemplar=1,
        langa_kolumner=("Beskrivning", "Rörligt marknadsvärde"),
        kalla=[
            ("Korttyp", "PU_projekt — projektkort, Skede 1 Projektutveckling"),
            ("Antal kort", f"{len(rader)} unika, 1 exemplar vardera per spel (8 spel tryckta)"),
            ("Format", "88 × 146 mm, dubbelsidigt (bildsida + textsida)"),
            ("Tryckfil", "Dropbox: Åkepol tryckfiler/Kort/PU_projekt_tryckeri.pdf (2026-04-27 22:14 UTC)"),
            ("Tryckfilens text", "arv/tryckt_text/PU_projekt_tryckeri.txt (utläst via OneDrive, 90 sidor)"),
            ("Datakälla", "arv/spelet2_v1/1. Projektutveckling/PU_projekt.csv"),
            ("CSV-datum", "2026-05-02 21:03 — efter tryck, men innehållet är oförändrat "
                          "(endast omkodning cp1252→UTF-8)"),
            ("Kontroll", "Alla speldatafält och beskrivningar jämförda kort för kort mot tryckfilen: 0 avvikelser."),
            ("Etiketter", "Bekräftat mot fysiskt kort (BRF Eldningen): Utvecklingskostnad = CSV 'Kostnad', "
                          "Anskaffning = CSV 'Anskaffning'. Textordningen i PDF:en följer inte layouten."),
            ("Beslut", "Förvaltningssektionen på baksidan görs om; alla 45 kort trycks om (360 kort)."),
            ("Byggd med", "verktyg/bygg_pu_projekt_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
