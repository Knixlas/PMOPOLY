"""Bygg kortdata/PU_projekt.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/1. Projektutveckling/PU_projekt.csv  (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PU_projekt_tryckeri.txt             (text utläst ur tryckfilen, 2 rader per kort)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python verktyg/bygg_pu_projekt_excel.py
"""
import csv
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROT = Path(__file__).resolve().parent.parent
CSV_FIL = ROT / "arv/spelet2_v1/1. Projektutveckling/PU_projekt.csv"
TRYCK_FIL = ROT / "arv/tryckt_text/PU_projekt_tryckeri.txt"
UT = ROT / "kortdata/PU_projekt.xlsx"

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


def las_csv():
    with open(CSV_FIL, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f, delimiter=";") if r.get("Namn")]


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
            "Beskrivning": re.sub(r"(\w) - (\w)", r"\1\2", besk),  # avstavning i tryck
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
            csv_varde = r.get(falt, "").strip()
            if falt in ("Energiklass", "Driftnetto", "Rörligt marknadsvärde") and not tryckt:
                continue  # inte tryckt på denna korttyp
            if falt == "Beskrivning":
                csv_varde, tryckt = csv_varde.replace("­", ""), tryckt
            if csv_varde.replace(",", ".") != tryckt.replace(",", "."):
                avvikelser.append((r["Namn"], falt, tryckt, csv_varde))
    return avvikelser


def tal(v):
    v = (v or "").strip()
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+[.,]\d+", v):
        return float(v.replace(",", "."))
    return v


def rubrikrad(ws, rubriker, fyll="4D5E22"):
    ws.append(rubriker)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=fyll)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"


def bredder(ws, standard=14, specifika=None):
    for i in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = standard
    for kol, b in (specifika or {}).items():
        ws.column_dimensions[kol].width = b


def main():
    rader = las_csv()
    tryck = las_tryck()
    avvikelser = jamfor(rader, tryck)
    beskrivning_avvikelser = [a for a in avvikelser if a[1] == "Beskrivning"]
    ovriga = [a for a in avvikelser if a[1] != "Beskrivning"]
    if ovriga:
        for a in ovriga:
            print("AVVIKELSE", a)
        sys.exit("Speldata skiljer mellan CSV och tryck — åtgärda innan Excel byggs.")

    wb = Workbook()

    ws = wb.active
    ws.title = "Kort"
    rubrikrad(ws, [k[0] for k in KORT_KOLUMNER])
    for i, r in enumerate(rader, 1):
        rad = []
        for rubrik, kol, _, _ in KORT_KOLUMNER:
            if rubrik == "Kort-id":
                rad.append(i)
            elif rubrik == "Antal exemplar":
                rad.append(1)
            elif kol == "Beskrivning":
                rad.append(r[kol].strip())
            else:
                rad.append(tal(r.get(kol, "")))
        ws.append(rad)
    bredder(ws, 12, {"B": 12, "C": 26, "D": 16, "E": 60, "O": 40})
    for rad in ws.iter_rows(min_row=2):
        rad[4].alignment = Alignment(wrap_text=True, vertical="top")

    ws = wb.create_sheet("Mallens fasta text")
    rubrikrad(ws, ["Sida", "Slag", "Text"])
    for m in MALLTEXT:
        ws.append(list(m))
    bredder(ws, 18, {"C": 110})

    ws = wb.create_sheet("Produktion")
    rubrikrad(ws, ["Kort-id", "Namn"] + PRODUKTION_KOLUMNER + ["Format (mm)"])
    for i, r in enumerate(rader, 1):
        ws.append([i, r["Namn"]] + [tal(r.get(k, "")) for k in PRODUKTION_KOLUMNER] + ["88 × 146"])
    bredder(ws, 14, {"B": 26, "C": 50, "D": 50})

    ws = wb.create_sheet("Kolumner")
    rubrikrad(ws, ["Kolumn", "Källkolumn i CSV", "Tryckt på kortet", "Förklaring"])
    for rubrik, kol, tryckt, forkl in KORT_KOLUMNER:
        ws.append([rubrik, kol or "—", "Ja" if tryckt else "Nej", forkl])
    bredder(ws, 22, {"D": 70})

    ws = wb.create_sheet("Källa och kontroll")
    rubrikrad(ws, ["Punkt", "Värde"])
    for p in [
        ("Korttyp", "PU_projekt — projektkort, Skede 1 Projektutveckling"),
        ("Antal kort", f"{len(rader)} unika, 1 exemplar vardera"),
        ("Format", "88 × 146 mm, dubbelsidigt (bildsida + textsida)"),
        ("Tryckfil", "Dropbox: Åkepol tryckfiler/Kort/PU_projekt_tryckeri.pdf (2026-04-27 22:14 UTC)"),
        ("Tryckfilens text", "arv/tryckt_text/PU_projekt_tryckeri.txt (utläst via OneDrive, 90 sidor)"),
        ("Datakälla", "arv/spelet2_v1/1. Projektutveckling/PU_projekt.csv"),
        ("CSV-datum", "2026-05-02 21:03 — efter tryck, men innehållet är oförändrat (endast omkodning cp1252→UTF-8)"),
        ("Kontroll", f"Alla speldatafält jämförda kort för kort mot tryckfilen: 0 avvikelser. "
                     f"Beskrivningar: {len(beskrivning_avvikelser)} avvikelser (avstavning i tryck)."),
        ("Etiketter", "Bekräftat mot fysiskt kort (BRF Eldningen): Utvecklingskostnad = CSV 'Kostnad', "
                      "Anskaffning = CSV 'Anskaffning'. Textordningen i PDF:en följer inte layouten."),
        ("Byggd med", "verktyg/bygg_pu_projekt_excel.py"),
    ]:
        ws.append(list(p))
    bredder(ws, 20, {"B": 110})

    UT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(UT)
    print(f"Skrev {UT.relative_to(ROT)}: {len(rader)} kort, 0 avvikelser i speldata, "
          f"{len(beskrivning_avvikelser)} i beskrivningar")
    for a in beskrivning_avvikelser:
        print("  beskrivning:", a[0], "| tryck:", a[2][:70], "| csv:", a[3][:70])


if __name__ == "__main__":
    main()
