"""Bygg kortdata/PL_Händelsekort.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/2. Planering/PL_Händelsekort.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PL_Händelsekort_S1_tryckeri.txt   (text utläst ur tryckfilen, 2 rader per kort)

Korttypen trycktes i fyra filer PL_Händelsekort_S1…S4_tryckeri.pdf. Korten är identiska,
enda skillnaden är sorteringsmärket S1–S4 på bildsidan (så korten kan sorteras per spel).
Här blir det därför ett kort per rad med 4 exemplar; S1-filen är fullständigt kontrollerad.

CSV:n har två platshållarrader (Kort_ID 'tom', utan Namn). De trycktes som två blanka kort
sist i varje tryckfil men tas inte med i Excel (las_csv hoppar över rader utan Namn).

CSV:n har kolumnen 'Fas' två gånger (kolumn 1 och 6); de är lika på alla rader.

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python verktyg/bygg_pl_handelsekort_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "PL_Händelsekort_S1_tryckeri.txt"
TOMT_KORT = "- tom  PL   PLANERING"

# Korrigeringar CSV -> tryck: {(ID, csv-kolumn): tryckt värde}. Det tryckta är facit.
# Tom — kontrollen gav 0 avvikelser.
KORRIGERINGAR = {}

# (rubrik i Excel, CSV-kolumn, tryckt på kortet?, förklaring)
KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–54 i tryckordning (= CSV 'ID')"),
    ("Rubrik", "Rubrik", True, "Bildsidans rubrik: HÄNDELSEKORT"),
    ("Namn", "Namn", True, "Händelsens rubrik på textsidan"),
    ("Beskrivning", "Beskrivning", True, "Löptext på textsidan"),
    ("Fas", "Fas", True, "Tryckt som '<Fas> - <Kategori>', t.ex. 'Förberedelse - DIGITALISERING'"),
    ("Kategori", "Kort_ID", True, "Berörd funktion/byggdel; tryckt två gånger på textsidan"),
    ("Projekttyp", "Trigger", True, "'PROJEKTTYP: …' — alla tryckta kort: Alla"),
    ("Konsekvens 1–5", "Tröskel_1_5", True, "Resultat av 'Slå D20 + ER' (erfarenhet) 1–5"),
    ("Konsekvens 6–17", "Tröskel_6_17", True, "Resultat 6–17"),
    ("Konsekvens 18–20", "Tröskel_18_20", True, "Resultat 18–20"),
    ("Konsekvens 21+", "Tröskel_21_plus", True, "Resultat 21 eller mer"),
    ("Nr", "ID", False, "Ej tryckt — löpnummer i CSV"),
    ("Typ", "Typ", False, "Ej tryckt — Negativt / Neutralt / Positivt"),
    ("Svårighetsgrad", "Svårighetsgrad", False, "Ej tryckt — Tidig-Medium / Medium / Sen"),
    ("Summering", "Summering", False, "Ej tryckt — berörda områden"),
    ("Klassvillkor", "Klassvillkor", False, "Ej tryckt — Alla / Skalad / Skalad (BTA)"),
    ("Antal exemplar", None, False, "4 per spel-sats: ett vardera med sorteringsmärke S1, S2, S3, S4"),
]

PRODUKTION_KOLUMNER = ["@bildsida", "@textsida", "fill_color", "line_color", "ordning_bild",
                       "ordning_text", "skede_color", "bakskede", "bakgrund_color"]

MALLTEXT = [
    ("Bildsida", "Etikett", "PL"),
    ("Bildsida", "Sorteringsmärke", "S1 / S2 / S3 / S4 — enda skillnaden mellan de fyra tryckfilerna"),
    ("Textsida", "Skede", "PL · PLANERING"),
    ("Textsida", "Rubrik", "KONSEKVENSEN BLIR:"),
    ("Textsida", "Regel", "Slå D20 + ER (erfarenhet)"),
    ("Textsida", "Etiketter", "1-5 · 6-17 · 18-20 · 21+ (tröskelvärden för konsekvenserna)"),
    ("Textsida", "Regel", "LÄS - SLÅ - LÖS - KASTA"),
    ("Textsida", "Etikett", "PROJEKTTYP:"),
    ("Textsida", "Avdelare", "' - ' mellan Fas och Kategori"),
    ("Hela filen", "Tomma kort", "Två platshållarkort ('- tom', utan text) trycktes sist i varje tryckfil "
                                "— 2 × 4 = 8 blanka kort. Ej med på fliken Kort."),
]


def _prep(v):
    v = (v or "").replace("­", "")
    v = v.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", v).strip()


def lika_text(csv_varde, tryckt):
    """Löptext: tryckets ' - ' mellan ordtecken är antingen avstavning eller ett riktigt bindestreck."""
    delar = re.split(r"(?<=\w) - (?=\w)", _prep(tryckt))
    return re.fullmatch("-?".join(re.escape(d) for d in delar), _prep(csv_varde)) is not None


FRAM = re.compile(r"(?P<Rubrik>.+?)  PL  S1$")
BAK = re.compile(
    r"(?P<text>.*)  (?P<Fas>\S+) - (?P<Kort_ID>.+?)  PL   PLANERING  KONSEKVENSEN BLIR:  "
    r"Slå D20 \+ ER   erfarenhet  (?P<Tröskel_1_5>.*?) 1-5  (?P<Tröskel_21_plus>.*?) 21\+  "
    r"(?P<Tröskel_6_17>.*?) 6-17  (?P<Tröskel_18_20>.*?) 18-20  "
    r"LÄS   -   SLÅ   -   LÖS   -   KASTA   (?P<Kort_ID2>.+?)  PROJEKTTYP: (?P<Trigger>.*)$")


def las_tryck():
    """Rad 1 = bildsida, rad 2 = textsida. I PDF-texten står konsekvenserna i ordningen 1-5, 21+, 6-17,
    18-20, och varje text står omedelbart före sin tröskeletikett. Returnerar (kort, antal tomma kort)."""
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    kort, tomma = [], 0
    for fram, bak in zip(rader[0::2], rader[1::2]):
        f = FRAM.match(fram)
        if bak.startswith(TOMT_KORT):
            tomma += 1
            continue
        b = BAK.match(bak)
        if not f or not b:
            sys.exit(f"Kan inte tolka tryckt kort:\n{fram}\n{bak}")
        t = {k: _prep(v) for k, v in b.groupdict().items()}
        if t.pop("Kort_ID2") != t["Kort_ID"]:
            sys.exit(f"Kategorin tryckt olika på samma kort:\n{bak}")
        kort.append({"Rubrik": f["Rubrik"], **t})
    return kort, tomma


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avvikelser = []
    for r, t in zip(csv_rader, tryck):
        if not lika_text(f"{r['Namn']} {r['Beskrivning']}", t["text"]):
            avvikelser.append((r["ID"], "textsida: Namn + Beskrivning", t["text"]))
        for falt, tryckt in t.items():
            if falt == "text":
                continue
            if not lika_text(normalisera(r.get(falt, "")), normalisera(tryckt)):
                avvikelser.append((r["ID"], falt, tryckt, r.get(falt, "")))
    return avvikelser


def main():
    rader = las_csv("2. Planering/PL_Händelsekort.csv", "Namn")
    for r in rader:
        for (kid, kol), varde in KORRIGERINGAR.items():
            if r["ID"] == kid:
                r[kol] = varde
    tryck, tomma = las_tryck()
    avvikelser = jamfor(rader, tryck)
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda (KORRIGERINGAR) innan Excel byggs.")
    if tomma != 2:
        sys.exit(f"Väntade 2 tomma platshållarkort i trycket, hittade {tomma}")

    ut = bygg_arbetsbok(
        filnamn="PL_Händelsekort.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=4,
        langa_kolumner=("Beskrivning", "Summering"),
        kalla=[
            ("Korttyp", "PL_Händelsekort — händelsekort, Skede 2.1 Planering (fas Förberedelse)"),
            ("Antal kort", f"{len(rader)} unika × 4 exemplar = {4 * len(rader)} tryckta kort, "
                           f"plus {tomma} tomma platshållarkort × 4 = {4 * tomma} blanka kort"),
            ("Exemplar S1–S4", "Varje kort trycktes i fyra tryckfiler _S1…_S4. Korten är identiska; enda "
                               "skillnaden är sorteringsmärket S1–S4 på bildsidan (för att sortera korten per spel)."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/PL_Händelsekort_bildsida_S1_layout.json"),
            ("Tryckfiler", "OneDrive: SPELET 2/PDF/Tryckbara/PL_Händelsekort_S1_tryckeri.pdf … _S4_tryckeri.pdf "
                           "(2026-04-27 ca 20:57 UTC), 112 sidor vardera (56 kort varav 2 tomma)"),
            ("Tryckfilens text", "arv/tryckt_text/PL_Händelsekort_S1_tryckeri.txt (utläst via OneDrive, 112 sidor)"),
            ("Datakälla", "arv/spelet2_v1/2. Planering/PL_Händelsekort.csv"),
            ("CSV-datum", "2026-04-26 16:19 UTC — före tryck"),
            ("Kontroll S1", "Alla tryckta fält (rubrik, namn, beskrivning, fas, kategori ×2, projekttyp, "
                            "fyra konsekvenser) jämförda kort för kort: 0 avvikelser. Avstavning i trycket och "
                            "'(B - ÄTA)' i PDF-texten mot '(B-ÄTA)' i CSV räknas inte som avvikelse."),
            ("Kontroll S2–S4", "Stickprov första kortet (IT-system kan inte integreras …) och sista (Beställaren "
                               "vill ändra taklösning (B-ÄTA)) samt de två tomma korten i S2, S3 och S4: ordagrant "
                               "lika S1 utom märket S2/S3/S4. Alla fyra filerna har 112 sidor."),
            ("Etiketter", "Varje konsekvenstext står i PDF-texten omedelbart före sin tröskel (1-5, 21+, 6-17, "
                          "18-20); stämmer med CSV:s Tröskel-kolumner för alla 54 kort. "
                          "'PROJEKTTYP:' = CSV 'Trigger' (Klassvillkor 'Skalad' trycks inte)."),
            ("Byggd med", "verktyg/bygg_pl_handelsekort_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort (+{tomma} tomma i trycket), 0 avvikelser")


if __name__ == "__main__":
    main()
