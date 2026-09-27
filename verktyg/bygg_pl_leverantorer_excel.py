"""Bygg kortdata/PL_leverantörer.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/2. Planering/PL_Leverantörer.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PL_leverantörer_S1_tryckeri.txt   (text utläst ur tryckfilen, 2 rader per kort)

Korttypen trycktes i fyra filer PL_leverantörer_S1…S4_tryckeri.pdf. Korten är identiska,
enda skillnaden är sorteringsmärket S1–S4 på bildsidan (så korten kan sorteras per spel).
Här blir det därför ett kort per rad med 4 exemplar; S1-filen är fullständigt kontrollerad.

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python verktyg/bygg_pl_leverantorer_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "PL_leverantörer_S1_tryckeri.txt"

# Korrigeringar CSV -> tryck: {(kategori, id, csv-kolumn): tryckt värde}. Det tryckta är facit.
# (Id är inte unikt: 'STO - 1…4' används av både STOMME och STOMKOMPLETTERING.)
# Tom — kontrollen gav 0 avvikelser.
KORRIGERINGAR = {}

# (rubrik i Excel, CSV-kolumn, tryckt på kortet?, förklaring)
KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–36 i tryckordning (unikt, till skillnad från Id)"),
    ("Id", "ID", True, "Kortets id, t.ex. 'MARK - 1'. OBS: 'STO - 1…4' finns både för STOMME och STOMKOMPLETTERING"),
    ("Kategori", "Namn", True, "Byggdel: MARK, HUSUNDERBYGGNAD, STOMME, YTTERTAK, FASADER, STOMKOMPLETTERING, "
                               "INV YTSKIKT, INSTALLATIONER, GEMENSAMMA ARBETEN (båda sidor)"),
    ("Företag", "Beskrivning", True, "Företagsnamnet (båda sidor)"),
    ("Beskrivning", "Ny beskrivning", True, "Löptext på textsidan"),
    ("Fas", "Fas", True, "Talet efter 'PL' på bildsidan"),
    ("Nivå", "Nivå", True, "NIVÅ 1–4"),
    ("Kostnaden beror av", "Beror_av", True, "BYA eller BTA — 'KOSTNADEN BEROR AV DIN …-KLASS'"),
    ("Kostnad klass A (Mkr)", "Klass_A", True, ""),
    ("Kostnad klass B (Mkr)", "Klass_B", True, ""),
    ("Kostnad klass C (Mkr)", "Klass_C", True, ""),
    ("Kostnad klass D (Mkr)", "Klass_D", True, "Trycks utan mellanslag före 'Mkr' (t.ex. '5Mkr')"),
    ("H", "H", True, "Hållbarhet; '-' = ingen påverkan"),
    ("Q", "Q", True, "Kvalitet; '-' = ingen påverkan"),
    ("T (mån)", "T_mån", True, "Tidspåverkan; '-' = ingen påverkan"),
    ("Erfarenhet", "erfarenhet", True, "Tryckt med etiketten 'erfa'; '-' = ingen"),
    ("STA Stabilitet", "STA", True, "Företagskultur, används i genomförandefasen"),
    ("KOM Kommunikation", "KOM", True, "Företagskultur"),
    ("SAM Samarbete", "SAM", True, "Företagskultur"),
    ("NOG Noggrannhet", "NOG", True, "Företagskultur"),
    ("INN Innovation", "INN", True, "Företagskultur"),
    ("ABM Arbetsmiljö", "ABM", True, "Företagskultur"),
    ("Antal exemplar", None, False, "4 per spel-sats: ett vardera med sorteringsmärke S1, S2, S3, S4"),
]

PRODUKTION_KOLUMNER = ["@bildsida", "@textsida", "fill_color", "line_color", "ordning_bild",
                       "ordning_text", "skede_color", "bakskede", "bakgrund_color"]

MALLTEXT = [
    ("Bildsida", "Etikett", "PL (före fasnumret)"),
    ("Bildsida", "Sorteringsmärke", "S1 / S2 / S3 / S4 — enda skillnaden mellan de fyra tryckfilerna"),
    ("Textsida", "Skede", "PL · PLANERING"),
    ("Textsida", "Regel", "BEHÅLL UNDER SKEDET"),
    ("Textsida", "Etiketter", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · NOG Noggrannhet · "
                              "INN Innovation · ABM Arbetsmiljö"),
    ("Textsida", "Rubrik", "FÖRETAGSKULTUR — används i genomförandefasen"),
    ("Textsida", "Etiketter", "A · B · C · D (… Mkr; D utan mellanslag: '…Mkr') · H · Q · T · erfa · NIVÅ"),
    ("Textsida", "Regel", "KOSTNADEN BEROR AV DIN «BYA/BTA»-KLASS (PDF-texten: 'BYA - KLASS')"),
]


def _prep(v):
    v = (v or "").replace("­", "")
    v = v.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", v).strip()


def lika_text(csv_varde, tryckt):
    """Löptext: tryckets ' - ' mellan ordtecken är antingen avstavning eller ett riktigt bindestreck."""
    delar = re.split(r"(?<=\w) - (?=\w)", _prep(tryckt))
    return re.fullmatch("-?".join(re.escape(d) for d in delar), _prep(csv_varde)) is not None


FRAM = re.compile(r"(?P<text>.*)  PL  (?P<Fas>\d+) S1$")
BAK = re.compile(
    r"(?P<text>.*)  PL   PLANERING  BEHÅLL UNDER SKEDET   (?P<ID>.+?)  STA   Stabilitet  KOM   Kommunikation  "
    r"SAM   Samarbete  NOG   Noggrannhet  INN   Innovation  ABM   Arbetsmiljö  "
    r"(?P<STA>\S+)  (?P<KOM>\S+)  (?P<SAM>\S+)  (?P<NOG>\S+)  (?P<INN>\S+)  (?P<ABM>\S+)  "
    r"FÖRETAGSKULTUR  används i genomförandefasen  "
    r"A  (?P<Klass_A>\S+) Mkr  C  (?P<Klass_C>\S+) Mkr  B  (?P<Klass_B>\S+) Mkr  D  (?P<Klass_D>[^\sM]+)Mkr  "
    r"H   (?P<H>\S+)   (?P<Q>\S+) Q   (?P<T_mån>\S+) T   (?P<erfarenhet>\S+) erfa  "
    r"NIVÅ  KOSTNADEN BEROR AV DIN (?P<Beror_av>\S+) - KLASS  (?P<Nivå>\S+)$")


def las_tryck():
    """Rad 1 = bildsida, rad 2 = textsida. Ordningen 'H x y Q z T w erfa' läses som H=x, Q=y, T=z,
    erfarenhet=w (samma mönster som PU_projekt, bekräftat mot fysiskt kort där). Klasskostnaderna
    står i PDF-texten i ordningen A, C, B, D men varje värde följer direkt på sin etikett."""
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    kort = []
    for fram, bak in zip(rader[0::2], rader[1::2]):
        f, b = FRAM.match(fram), BAK.match(bak)
        if not f or not b:
            sys.exit(f"Kan inte tolka tryckt kort:\n{fram}\n{bak}")
        kort.append({"fram_text": f["text"], "bak_text": b["text"], "Fas": f["Fas"],
                     **{k: v for k, v in b.groupdict().items() if k != "text"}})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avvikelser = []
    for r, t in zip(csv_rader, tryck):
        nyckel = f"{r['Namn']} {r['ID']}"
        if not lika_text(f"{r['Namn']} {r['Beskrivning']}", t["fram_text"]):
            avvikelser.append((nyckel, "bildsida: Namn + Beskrivning", t["fram_text"]))
        if not lika_text(f"{r['Beskrivning']} {r['Ny beskrivning']} {r['Namn']}", t["bak_text"]):
            avvikelser.append((nyckel, "textsida: Beskrivning + Ny beskrivning + Namn", t["bak_text"]))
        for falt, tryckt in t.items():
            if falt.endswith("_text"):
                continue
            if normalisera(r.get(falt, "")) != normalisera(tryckt):
                avvikelser.append((nyckel, falt, tryckt, r.get(falt, "")))
    return avvikelser


def main():
    rader = las_csv("2. Planering/PL_Leverantörer.csv", "ID")
    for r in rader:
        for (kat, kid, kol), varde in KORRIGERINGAR.items():
            if (r["Namn"], r["ID"]) == (kat, kid):
                r[kol] = varde
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda (KORRIGERINGAR) innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="PL_leverantörer.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Beskrivning",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=4,
        langa_kolumner=("Ny beskrivning",),
        kalla=[
            ("Korttyp", "PL_leverantörer — leverantörskort (entreprenörer per byggdel), Skede 2.1 Planering"),
            ("Antal kort", f"{len(rader)} unika × 4 exemplar = {4 * len(rader)} tryckta kort"),
            ("Exemplar S1–S4", "Varje kort trycktes i fyra tryckfiler _S1…_S4. Korten är identiska; enda "
                               "skillnaden är sorteringsmärket S1–S4 på bildsidan (för att sortera korten per spel)."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/PL_leverantörer_bildsida_S1_layout.json"),
            ("Tryckfiler", "OneDrive: SPELET 2/PDF/Tryckbara/PL_leverantörer_S1_tryckeri.pdf … _S4_tryckeri.pdf "
                           "(2026-04-27 ca 20:58 UTC), 72 sidor vardera"),
            ("Tryckfilens text", "arv/tryckt_text/PL_leverantörer_S1_tryckeri.txt (utläst via OneDrive, 72 sidor)"),
            ("Datakälla", "arv/spelet2_v1/2. Planering/PL_Leverantörer.csv"),
            ("CSV-datum", "2026-04-26 16:20 UTC — före tryck"),
            ("Kontroll S1", "Alla tryckta fält (id, kategori, företag, beskrivning, fas, nivå, BYA/BTA, "
                            "kostnad klass A–D, H, Q, T, erfarenhet, sex kompetenser) jämförda kort för kort: "
                            "0 avvikelser. Typografiska apostrofer (’) och avstavning i trycket räknas inte som avvikelse."),
            ("Kontroll S2–S4", "Stickprov första kortet (MARK - 1) och sista (GEM - 4) i S2, S3 och S4: "
                               "ordagrant lika S1 utom märket S2/S3/S4. Alla fyra filerna har 72 sidor."),
            ("Etiketter", "Värdeordningen 'H x y Q z T w erfa' tolkas H=x, Q=y, T=z, erfarenhet=w "
                          "(samma layout som PU_projekt); stämmer med CSV för alla 36 kort."),
            ("Anmärkning", "Id är inte unikt: STOMME och STOMKOMPLETTERING har båda 'STO - 1' … 'STO - 4' "
                           "(så trycks det också). Använd Kort-id som nyckel."),
            ("Byggd med", "verktyg/bygg_pl_leverantorer_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
