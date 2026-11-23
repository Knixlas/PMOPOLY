"""Bygg kortdata/GF_garantibesiktning.xlsx ur det tryckta spelet.

Garantibesiktningskort (GARANTIAVSÄTTNING) i Skede 2.2 Genomförande: 44 kort i serierna
G_T (tid), G_Q (kvalitet), G_H (hållbarhet), G_EK (energiklass); *_K är de dyra "katastrofkorten".
Utfallet styrs av ett D20-slag + erfarenhet.

Källor:
  - arv/spelet2_v1/3. Genomförande/GF_garantibesiktning.csv  (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/GF_garantibesiktning_tryckeri.txt        (text utläst ur tryckfilen, 2 rader per kort:
                                                               rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python3 verktyg/bygg_gf_garantibesiktning_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "GF_garantibesiktning_tryckeri.txt"

# Tryckt intervall-etikett -> CSV-kolumn. PDF-texten lyder t.ex.
#   "-5 Mkr 1-9  Ingen effekt  -3 Mkr 10-17  -1 Mkr 18-24 … Slå D20 + erfarenhet  25+"
# dvs. varje utfall står FÖRE sin etikett, utom 25+-utfallet (andra värdet) vars etikett hamnar
# sist i textflödet. Samma mönster som GF_Konsekvenskort och PU_poldia; ger fallande kostnad med
# stigande slag på alla 44 kort och stämmer med CSV:n.
# OBS: etiketterna i mallen (1-9/10-17/18-24/25+) skiljer sig från CSV-rubrikerna
# (1_8/9_15/16_21/22_plus). Det tryckta gäller, så Excel-rubrikerna följer trycket.
UTFALL = [("1-9", "Tröskel_1_8"), ("10-17", "Tröskel_9_15"),
          ("18-24", "Tröskel_16_21"), ("25+", "Tröskel_22_plus")]

KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–44 i tryckordning"),
    ("Nr", "Nr", True, "Kortnummer på textsidan, t.ex. G_T1, G_Q_K, G_EK10"),
    ("Typ", "Typ", True, "KVALITETSBRIST eller HÅLLBARHETSAVVIKELSE — tryckt på textsidan"),
    ("Namn", "Namn", True, "Garantianmärkningens rubrik"),
] + [(f"Utfall D20+erfarenhet {etikett}", kol, True,
      f"Garantiavsättning vid slag {etikett}. CSV-kolumn '{kol}' — OBS: tryckt intervall "
      f"'{etikett}' skiljer från CSV-rubriken")
     for etikett, kol in UTFALL] + [
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@bild", "fill_color", "line_color", "skede_color", "bakskede",
                       "bakgrund_color", "ordning_bild", "ordning_text"]

MALLTEXT = [
    ("Bildsida", "Etiketter", "GARANTI · GF"),
    ("Textsida", "Sidhuvud", "GARANTIAVSÄTTNING · GF · GENOMFÖRANDE"),
    ("Textsida", "Rubrik", "KONSEKVENSEN BLIR"),
    ("Textsida", "Regel", "Slå D20 + erfarenhet"),
    ("Textsida", "Etiketter", "Intervall: 1-9 · 10-17 · 18-24 · 25+"),
    ("Textsida", "Regel", "LÄS - SLÅ - KASTA"),
]

TEXT_MONSTER = re.compile(
    r"KONSEKVENSEN BLIR  (?P<utfall>.+? 18-24)  (?P<typ>[A-ZÅÄÖ]+)  (?P<namn>.+?)  GARANTIAVSÄTTNING  GF   "
    r"GENOMFÖRANDE  LÄS   -   SLÅ   -   KASTA   (?P<nr>\S+)  Slå D20 \+ erfarenhet  25\+")


def las_tryck():
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{TRYCK_FIL.name}: udda antal sidor ({len(rader)})")
    kort = []
    for bild, text in zip(rader[0::2], rader[1::2]):
        mt = TEXT_MONSTER.fullmatch(text.strip())
        if bild.strip() != "GARANTI  GF" or not mt:
            sys.exit(f"Kunde inte tolka kortet: {bild!r} / {text!r}")
        # "A 1-9  B  C 10-17  D 18-24": B saknar etikett här (dess etikett 25+ står sist på sidan).
        m = re.fullmatch(r"(?P<a>.+?) 1-9  (?P<b>.+?)  (?P<c>.+?) 10-17  (?P<d>.+?) 18-24", mt["utfall"])
        if not m:
            sys.exit(f"{mt['nr']}: kunde inte tolka utfallen: {mt['utfall']!r}")
        kort.append({"Nr": mt["nr"], "Typ": mt["typ"], "Namn": mt["namn"],
                     "Tröskel_1_8": m["a"], "Tröskel_22_plus": m["b"],
                     "Tröskel_9_15": m["c"], "Tröskel_16_21": m["d"]})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        for falt in ["Nr", "Typ", "Namn"] + [k for _, k in UTFALL]:
            if normalisera(t[falt]) != normalisera(r[falt]):
                avv.append((r["Nr"], falt, t[falt], r[falt]))
    return avv


def main():
    rader = las_csv("3. Genomförande/GF_garantibesiktning.csv", "Nr")
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    kvalitet = sum(r["Typ"] == "KVALITETSBRIST" for r in rader)
    ut = bygg_arbetsbok(
        filnamn="GF_garantibesiktning.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=("Namn",),
        kalla=[
            ("Korttyp", "GF_garantibesiktning — garantiavsättningskort, Skede 2.2 Genomförande"),
            ("Antal kort", f"{len(rader)} unika ({kvalitet} KVALITETSBRIST, {len(rader) - kvalitet} "
                           "HÅLLBARHETSAVVIKELSE), 1 exemplar vardera per spel. CSV:ns 4 tomma "
                           "platshållarrader trycktes INTE (tryckfilen har 88 sidor = 44 kort, trots att "
                           "layoutfilen i _tryckeri_temp anger 48)."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/GF_garantibesiktning_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/GF_garantibesiktning_tryckeri.pdf"),
            ("Tryckfilens text", "arv/tryckt_text/GF_garantibesiktning_tryckeri.txt (utläst via OneDrive, "
                                 f"{2 * len(rader)} sidor)"),
            ("Datakälla", "arv/spelet2_v1/3. Genomförande/GF_garantibesiktning.csv"),
            ("CSV-datum", "2026-04-26 16:22 — före tryck"),
            ("Kontroll", "Nr, Typ, Namn och alla fyra utfall jämförda kort för kort mot tryckfilen: "
                         "0 avvikelser i värden."),
            ("Intervall", "Trycket har intervallen 1-9 / 10-17 / 18-24 / 25+ (fast text i mallen), CSV-rubrikerna "
                          "säger 1_8 / 9_15 / 16_21 / 22_plus. Trycket gäller: Excel-rubrikerna följer trycket."),
            ("Byggd med", "verktyg/bygg_gf_garantibesiktning_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
