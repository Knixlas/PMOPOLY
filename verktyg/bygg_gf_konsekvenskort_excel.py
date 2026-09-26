"""Bygg kortdata/GF_Konsekvenskort.xlsx ur det tryckta spelet.

Konsekvenskort i Skede 2.2 Genomförande (TID T1–T10, KVALITET Q1–Q10, HÅLLBARHET H1–H10).
Utfallet styrs av ett D20-slag + ER (erfarenhet).

Källor:
  - arv/spelet2_v1/3. Genomförande/GF_konsekvenskort.csv  (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/GF_Konsekvenskort_tryckeri.txt        (text utläst ur tryckfilen, 2 rader per kort:
                                                            rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python3 verktyg/bygg_gf_konsekvenskort_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "GF_Konsekvenskort_tryckeri.txt"

# Tryckt intervall-etikett -> CSV-kolumn. I PDF-texten står varje utfall FÖRE sin etikett
# ("-18 Mkr, -2 Q 1-9  -2 Mkr 25+  -10 Mkr, -1 Q 10-17  -4 Mkr, -1 Q 18-24"). Läsningen är entydig:
# den omvända läsningen (etikett före utfall) lämnar ett utfall utan etikett och ger icke-monotona
# utfall, medan denna ger fallande kostnad med stigande slag på alla 30 kort — och stämmer med CSV:n.
# OBS: etiketterna i InDesign-mallen (1-9/10-17/18-24/25+) skiljer sig från CSV-rubrikerna
# (1_8/9_15/16_21/22_plus). Det tryckta gäller, så Excel-rubrikerna följer trycket.
UTFALL = [("1-9", "Tröskel_1_8"), ("10-17", "Tröskel_9_15"),
          ("18-24", "Tröskel_16_21"), ("25+", "Tröskel_22_plus")]

KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–30 i tryckordning"),
    ("Nr", "Nr", True, "Kortnummer på textsidan: T1–T10, Q1–Q10, H1–H10"),
    ("Typ", "Typ", True, "TID, KVALITET eller HÅLLBARHET — tryckt på bild- och textsidan"),
    ("Namn", "Namn", True, "Konsekvensens rubrik"),
] + [(f"Utfall D20+ER {etikett}", kol, True,
      f"Konsekvens vid slag {etikett} (D20 + ER erfarenhet). CSV-kolumn '{kol}' — OBS: tryckt "
      f"intervall '{etikett}' skiljer från CSV-rubriken")
     for etikett, kol in UTFALL] + [
    ("Energiklass projekt", "Energiklass_projekt", False,
     "Ej tryckt — speldata (0/1/2; troligen påverkan på projektets energiklass)"),
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@bild", "fill_color", "line_color", "skede_color", "bakskede",
                       "bakgrund_color", "ordning_bild", "ordning_text"]

MALLTEXT = [
    ("Bildsida", "Etiketter", "KONSEKVENSKORT · <Typ> · GF"),
    ("Textsida", "Sidhuvud", "KONSEKVENSKORT · GF · GENOMFÖRANDE"),
    ("Textsida", "Rubrik", "KONSEKVENSEN BLIR"),
    ("Textsida", "Regel", "Slå D20 + ER erfarenhet"),
    ("Textsida", "Etiketter", "Intervall: 1-9 · 10-17 · 18-24 · 25+"),
    ("Textsida", "Regel", "LÄS - SLÅ - KASTA"),
    ("Tomma kort", "Obs", "Två tomma kort (CSV-platshållare) trycktes med enbart malltexten "
                          "(KONSEKVENSKORT · GF, rubriker och intervall utan värden)."),
]

TEXT_MONSTER = re.compile(
    r"(?P<typ>\S+)  (?P<namn>.+?)  KONSEKVENSKORT  GF   GENOMFÖRANDE  KONSEKVENSEN BLIR  "
    r"Slå D20 \+ ER   erfarenhet  (?P<utfall>.+?)  LÄS   -   SLÅ   -   KASTA   (?P<nr>\S+)")
TOMT_KORT = ("KONSEKVENSKORT  GF",
             "KONSEKVENSKORT  GF   GENOMFÖRANDE  KONSEKVENSEN BLIR  Slå D20 + ER   erfarenhet  "
             "1-9  25+  10-17  18-24  LÄS   -   SLÅ   -   KASTA")


def las_tryck():
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{TRYCK_FIL.name}: udda antal sidor ({len(rader)})")
    kort, tomma = [], 0
    for bild, text in zip(rader[0::2], rader[1::2]):
        if (bild.strip(), text.strip()) == TOMT_KORT:
            tomma += 1
            continue
        mb = re.fullmatch(r"KONSEKVENSKORT  (\S+)  GF", bild.strip())
        mt = TEXT_MONSTER.fullmatch(text.strip())
        if not (mb and mt):
            sys.exit(f"Kunde inte tolka kortet: {bild!r} / {text!r}")
        delar = re.split(r"\s+(1-9|10-17|18-24|25\+)(?=\s|$)", mt["utfall"])
        par = dict(zip(delar[1::2], [d.strip() for d in delar[0::2]]))
        if sorted(par) != sorted(e for e, _ in UTFALL) or delar[-1].strip():
            sys.exit(f"{mt['nr']}: kunde inte tolka utfallen: {mt['utfall']!r}")
        kort.append({"Nr": mt["nr"], "Typ": mb.group(1), "_typ_text": mt["typ"], "Namn": mt["namn"],
                     **{kol: par[etikett] for etikett, kol in UTFALL}})
    return kort, tomma


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        if t["_typ_text"] != t["Typ"]:
            avv.append((r["Nr"], "Typ (textsida)", t["_typ_text"], r["Typ"]))
        for falt in ["Nr", "Typ", "Namn"] + [k for _, k in UTFALL]:
            if normalisera(t[falt]) != normalisera(r[falt]):
                avv.append((r["Nr"], falt, t[falt], r[falt]))
    return avv


def main():
    rader = las_csv("3. Genomförande/GF_konsekvenskort.csv", "Nr")
    tryck, tomma = las_tryck()
    avvikelser = jamfor(rader, tryck)
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="GF_Konsekvenskort.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=("Namn",),
        kalla=[
            ("Korttyp", "GF_Konsekvenskort — konsekvenskort, Skede 2.2 Genomförande"),
            ("Antal kort", f"{len(rader)} unika (10 TID, 10 KVALITET, 10 HÅLLBARHET), 1 exemplar vardera "
                           f"per spel. Därtill {tomma} tomma kort (CSV:ns platshållarrader) som trycktes "
                           f"med enbart malltext — totalt {len(rader) + tomma} kort, {2 * (len(rader) + tomma)} "
                           "sidor i tryckfilen."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/GF_Konsekvenskort_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/GF_Konsekvenskort_tryckeri.pdf "
                         "(2026-04-27 21:14 UTC)"),
            ("Tryckfilens text", f"arv/tryckt_text/GF_Konsekvenskort_tryckeri.txt (utläst via OneDrive, "
                                 f"{2 * (len(rader) + tomma)} sidor)"),
            ("Datakälla", "arv/spelet2_v1/3. Genomförande/GF_konsekvenskort.csv"),
            ("CSV-datum", "2026-04-26 16:23 — före tryck"),
            ("Kontroll", "Nr, Typ (bild- och textsida), Namn och alla fyra utfall jämförda kort för kort "
                         "mot tryckfilen: 0 avvikelser i värden."),
            ("Intervall", "Trycket har intervallen 1-9 / 10-17 / 18-24 / 25+ (fast text i mallen), CSV-rubrikerna "
                          "säger 1_8 / 9_15 / 16_21 / 22_plus. Trycket gäller: Excel-rubrikerna följer trycket. "
                          "Varje utfall står före sin etikett i PDF-texten; läsningen är entydig (se skriptet)."),
            ("Ej tryckt", "Energiklass_projekt finns bara i CSV:n (speldata)."),
            ("Byggd med", "verktyg/bygg_gf_konsekvenskort_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort (+{tomma} tomma), 0 avvikelser")


if __name__ == "__main__":
    main()
