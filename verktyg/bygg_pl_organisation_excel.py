"""Bygg kortdata/PL_organisation.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/2. Planering/PL_Organisation.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PL_organisation_S1_tryckeri.txt   (text utläst ur tryckfilen, 2 rader per kort)

Korttypen trycktes i fyra filer PL_organisation_S1…S4_tryckeri.pdf. Korten är identiska,
enda skillnaden är sorteringsmärket S1–S4 på bildsidan (så korten kan sorteras per spel).
Här blir det därför ett kort per rad med 4 exemplar; S1-filen är fullständigt kontrollerad.

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python verktyg/bygg_pl_organisation_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "PL_organisation_S1_tryckeri.txt"
KOMPETENSER = ["STA", "KOM", "SAM", "NOG", "INN", "ABM"]

# Korrigeringar CSV -> tryck: {(id, csv-kolumn): tryckt värde}. Det tryckta är facit.
# Tom — kontrollen gav 0 avvikelser.
KORRIGERINGAR = {}

# (rubrik i Excel, CSV-kolumn, tryckt på kortet?, förklaring)
KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–16 i tryckordning"),
    ("Id", "id", True, "Kortets id, t.ex. 'OPE - 1' (textsidan)"),
    ("Kategori", "Namn", True, "OPERATIVT TEAM, STÖDFUNKTIONER, MARKNADSTEAM, DIGITALISERING (båda sidor)"),
    ("Företag", "Beskrivning", True, "Företagsnamnet (båda sidor)"),
    ("Beskrivning", "Ny beskrivning", True, "Löptext på textsidan"),
    ("Fas", "FAS", True, "Talet efter 'PL' på bildsidan"),
    ("Nivå", "Nivå", True, "NIVÅ 1–4"),
    ("Fast kostnad (Mkr)", "Kostnad_Mkr", True, "FAST KOSTNAD"),
    ("Riskbuffert", "Riskbuffert", True, "RISKBUFFERT; '-' = ingen"),
    ("H", "H", True, "Hållbarhet; '-' = ingen påverkan"),
    ("Q", "Q", True, "Kvalitet; '-' = ingen påverkan"),
    ("T (mån)", "T_mån", True, "Tidspåverkan; '-' = ingen påverkan"),
    ("Erfarenhet", "erfarenhet", True, "Tryckt med etiketten 'erfa'; '-' = ingen"),
    ("STA Stabilitet", "STA", True, "Företagskultur, används i genomförandefasen"),
    ("KOM Kommunikation", "KOM", True, "Företagskultur"),
    ("SAM Samarbete", "SAM", True, "Företagskultur"),
    ("NOG Noggrannhet", "NOG", True, "Företagskultur"),
    ("INN Innovation", "INN", True, "Företagskultur"),
    ("ARB Arbetsmiljö", "ABM", True, "Företagskultur — CSV-kolumnen heter ABM, kortet trycker 'ARB'"),
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
                              "INN Innovation · ARB Arbetsmiljö"),
    ("Textsida", "Rubrik", "FÖRETAGSKULTUR — används i genomförandefasen"),
    ("Textsida", "Etiketter", "FAST KOSTNAD (… Mkr) · RISKBUFFERT · NIVÅ · H · Q · T · erfa"),
]


def _prep(v):
    v = (v or "").replace("­", "")
    v = v.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", v).strip()


def lika_text(csv_varde, tryckt):
    """Löptext: tryckets ' - ' mellan ordtecken är antingen avstavning eller ett riktigt bindestreck."""
    delar = re.split(r"(?<=\w) - (?=\w)", _prep(tryckt))
    return re.fullmatch("-?".join(re.escape(d) for d in delar), _prep(csv_varde)) is not None


FRAM = re.compile(r"(?P<text>.*)  PL  (?P<FAS>\d+) S1$")
BAK = re.compile(
    r"(?P<text>.*)  PL   PLANERING  BEHÅLL UNDER SKEDET   (?P<id>.+?)  STA   Stabilitet  KOM   Kommunikation  "
    r"SAM   Samarbete  NOG   Noggrannhet  INN   Innovation  ARB   Arbetsmiljö  "
    r"(?P<STA>\S+)  (?P<KOM>\S+)  (?P<SAM>\S+)  (?P<NOG>\S+)  (?P<INN>\S+)  (?P<ABM>\S+)  "
    r"FÖRETAGSKULTUR  används i genomförandefasen  FAST KOSTNAD  (?P<Kostnad_Mkr>\S+) Mkr  "
    r"RISKBUFFERT  (?P<Riskbuffert>\S+)  NIVÅ   (?P<Nivå>\S+)  "
    r"H   (?P<H>\S+)   (?P<Q>\S+) Q   (?P<T_mån>\S+) T   (?P<erfarenhet>\S+) erfa$")


def las_tryck():
    """Rad 1 = bildsida, rad 2 = textsida. Ordningen 'H x y Q z T w erfa' läses som H=x, Q=y, T=z,
    erfarenhet=w (samma mönster som PU_projekt, bekräftat mot fysiskt kort där)."""
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    kort = []
    for fram, bak in zip(rader[0::2], rader[1::2]):
        f, b = FRAM.match(fram), BAK.match(bak)
        if not f or not b:
            sys.exit(f"Kan inte tolka tryckt kort:\n{fram}\n{bak}")
        kort.append({"fram_text": f["text"], "bak_text": b["text"], "FAS": f["FAS"],
                     **{k: v for k, v in b.groupdict().items() if k != "text"}})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avvikelser = []
    for r, t in zip(csv_rader, tryck):
        if not lika_text(f"{r['Namn']} {r['Beskrivning']}", t["fram_text"]):
            avvikelser.append((r["id"], "bildsida: Namn + Beskrivning", t["fram_text"]))
        if not lika_text(f"{r['Beskrivning']} {r['Ny beskrivning']} {r['Namn']}", t["bak_text"]):
            avvikelser.append((r["id"], "textsida: Beskrivning + Ny beskrivning + Namn", t["bak_text"]))
        for falt, tryckt in t.items():
            if falt.endswith("_text"):
                continue
            if normalisera(r.get(falt, "")) != normalisera(tryckt):
                avvikelser.append((r["id"], falt, tryckt, r.get(falt, "")))
    return avvikelser


def main():
    rader = las_csv("2. Planering/PL_Organisation.csv", "id")
    for r in rader:
        for (kid, kol), varde in KORRIGERINGAR.items():
            if r["id"] == kid:
                r[kol] = varde
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda (KORRIGERINGAR) innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="PL_organisation.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Beskrivning",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=4,
        langa_kolumner=("Ny beskrivning",),
        kalla=[
            ("Korttyp", "PL_organisation — organisationskort (konsulter/team), Skede 2.1 Planering"),
            ("Antal kort", f"{len(rader)} unika × 4 exemplar = {4 * len(rader)} tryckta kort"),
            ("Exemplar S1–S4", "Varje kort trycktes i fyra tryckfiler _S1…_S4. Korten är identiska; enda "
                               "skillnaden är sorteringsmärket S1–S4 på bildsidan (för att sortera korten per spel)."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/PL_organisation_bildsida_S1_layout.json"),
            ("Tryckfiler", "OneDrive: SPELET 2/PDF/Tryckbara/PL_organisation_S1_tryckeri.pdf … _S4_tryckeri.pdf "
                           "(2026-04-27 ca 21:02 UTC), 32 sidor vardera"),
            ("Tryckfilens text", "arv/tryckt_text/PL_organisation_S1_tryckeri.txt (utläst via OneDrive, 32 sidor)"),
            ("Datakälla", "arv/spelet2_v1/2. Planering/PL_Organisation.csv"),
            ("CSV-datum", "2026-04-26 16:21 UTC — före tryck"),
            ("Kontroll S1", "Alla tryckta fält (id, kategori, företag, beskrivning, fas, nivå, fast kostnad, "
                            "riskbuffert, H, Q, T, erfarenhet, sex kompetenser) jämförda kort för kort: 0 avvikelser. "
                            "Typografiska citattecken (”) och avstavning i trycket räknas inte som avvikelse."),
            ("Kontroll S2–S4", "Stickprov första kortet (OPE - 1) och sista (DIG - 4) i S2, S3 och S4: "
                               "ordagrant lika S1 utom märket S2/S3/S4. Alla fyra filerna har 32 sidor."),
            ("Etiketter", "Värdeordningen 'H x y Q z T w erfa' tolkas H=x, Q=y, T=z, erfarenhet=w "
                          "(samma layout som PU_projekt); stämmer med CSV för alla 16 kort. "
                          "Kompetensen ABM trycks med etiketten 'ARB Arbetsmiljö'."),
            ("Byggd med", "verktyg/bygg_pl_organisation_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
