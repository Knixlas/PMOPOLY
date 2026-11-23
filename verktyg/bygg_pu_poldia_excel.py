"""Bygg kortdata/PU_poldia.xlsx och kortdata/PU_poldia_spec.xlsx ur det tryckta spelet.

Politik- och dialogkort (händelsekort) i Skede 1 Projektutveckling:
  PU_poldia       40 kort (P01–P20 politik, D01–D20 dialog) — utfall styrs av D20-slag
  PU_poldia_spec  12 kort (PS1–PS6, DS1–DS6) — specialkort utan tärningsslag

Källor per korttyp:
  - arv/spelet2_v1/1. Projektutveckling/<typ>.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/<typ>_tryckeri.txt              (text utläst ur tryckfilen, 2 rader per kort:
                                                     rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python3 verktyg/bygg_pu_poldia_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

PRODUKTION_KOLUMNER = ["@bildsida", "@textsida", "fill_color", "line_color", "skede_color",
                       "bakskede", "bakgrund_color", "ordning_bild", "ordning_text"]

MALLHUVUD = "HÄNDELSEKORT  PU   PROJEKTUTVECKLING"


def jamforbar(v):
    """Striktare än normalisera räcker inte för radbrytningar i löptext:
    tryckets avstavning ('fuktpro -  blem', 'K+Q-  krav', 'H - KRAV') och ordinterna
    bindestreck jämnas ut, liksom alla blanksteg. Minustecken framför tal ('-1') behålls."""
    v = normalisera(re.sub(r"\s+", " ", v or ""))
    v = re.sub(r"-\s+", "", v)
    v = re.sub(r"(?<=\w)-(?=\w)", "", v)
    return re.sub(r"\s+", "", v)


def las_rader(filnamn):
    rader = [r for r in (TRYCKT_TEXT / filnamn).read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{filnamn}: udda antal sidor ({len(rader)})")
    return list(zip(rader[0::2], rader[1::2]))


# ---------------------------------------------------------------- PU_poldia

# Tryckt intervall-etikett -> CSV-kolumn. I PDF-texten står varje utfall FÖRE sin etikett
# ("Lämna tillbaka … 1-4  +1 riskbuffert 20+  …"). Etiketterna på kortet skiljer sig från
# CSV-rubrikerna för de två lägsta intervallen (CSV '1' / '2 till 10', tryck '1-4' / '5-10').
POLDIA_UTFALL = [("1-4", "1"), ("5-10", "2 till 10"), ("11-15", "11 till 15"),
                 ("16-19", "16 till 19"), ("20+", "20+")]

POLDIA_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–40 i tryckordning"),
    ("Nr", "Nr", True, "Kortnummer på textsidan: P01–P20 (politik), D01–D20 (dialog)"),
    ("Korttyp", "Typ", True, "Står på bild- och textsidan: HÄNDELSEKORT"),
    ("Rubrik", "Rubrik", True, ""),
    ("Text", "Text", True, "Händelsebeskrivning"),
] + [(f"Utfall D20 {etikett}", kol, True,
      f"Konsekvens vid slag {etikett} (D20 + samlad erfarenhet). CSV-kolumn '{kol}'"
      + ("" if etikett.replace("-", " till ") == kol or etikett == kol
         else f" — OBS: tryckt etikett '{etikett}' skiljer från CSV-rubriken '{kol}'"))
     for etikett, kol in POLDIA_UTFALL] + [
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

POLDIA_MALLTEXT = [
    ("Bildsida", "Etiketter", "HÄNDELSEKORT (från CSV 'Typ') · PU"),
    ("Textsida", "Sidhuvud", "HÄNDELSEKORT (från CSV 'Typ') · PU · PROJEKTUTVECKLING"),
    ("Textsida", "Rubrik", "KONSEKVENSEN BLIR"),
    ("Textsida", "Regel", "Slå D20-TÄRNING, lägg till samlad erfarenhet"),
    ("Textsida", "Etiketter", "Intervall: 1-4 · 5-10 · 11-15 · 16-19 · 20+"),
    ("Textsida", "Regel", "LÄS - SLÅ - LÖS - KASTA"),
]


def tolka_poldia():
    kort = []
    for bild, text in las_rader("PU_poldia_tryckeri.txt"):
        typ_bild = re.fullmatch(r"(.+?)\s+PU", bild.strip()).group(1)
        fore, _, efter = text.partition("  " + MALLHUVUD + "  ")
        typ_text = text[len(fore):].split("  PU")[0].strip()
        m = re.fullmatch(r"KONSEKVENSEN BLIR\s+Slå D20-TÄRNING, lägg till samlad erfarenhet\s+(.+?)"
                         r"\s+LÄS\s+-\s+SLÅ\s+-\s+LÖS\s+-\s+KASTA\s+(\S+)", efter.strip())
        utfall_text, nr = m.group(1), m.group(2)
        # Dela i (utfall, etikett); etiketten följer efter sitt utfall.
        delar = re.split(r"\s+(1-4|5-10|11-15|16-19|20\+)(?=\s|$)", utfall_text)
        par = dict(zip(delar[1::2], [d.strip() for d in delar[0::2]]))
        if sorted(par) != sorted(e for e, _ in POLDIA_UTFALL) or delar[-1].strip():
            sys.exit(f"{nr}: kunde inte tolka utfallen: {utfall_text!r}")
        kort.append({"Nr": nr, "Typ": typ_bild, "_typ_text": typ_text, "Rubrik+Text": fore,
                     **{kol: par[etikett] for etikett, kol in POLDIA_UTFALL}})
    return kort


def jamfor_poldia(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"PU_poldia: antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        if t["_typ_text"] != t["Typ"]:
            avv.append((r["Nr"], "Typ (textsida)", t["_typ_text"], r["Typ"]))
        for falt in ["Nr", "Typ"] + [k for _, k in POLDIA_UTFALL]:
            if normalisera(t[falt]) != normalisera(r[falt]):
                avv.append((r["Nr"], falt, t[falt], r[falt]))
        if not jamforbar(t["Rubrik+Text"]).startswith(jamforbar(r["Rubrik"])):
            avv.append((r["Nr"], "Rubrik", t["Rubrik+Text"], r["Rubrik"]))
        if jamforbar(t["Rubrik+Text"]) != jamforbar(r["Rubrik"] + " " + r["Text"]):
            avv.append((r["Nr"], "Text", t["Rubrik+Text"], r["Rubrik"] + " | " + r["Text"]))
    return avv


# ----------------------------------------------------------- PU_poldia_spec

SPEC_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–12 i tryckordning"),
    ("Nr", "Nr", True, "Kortnummer på textsidan: PS1–PS6 (politik), DS1–DS6 (dialog)"),
    ("Korttyp", "Typ", True, "Står på bild- och textsidan: HÄNDELSEKORT"),
    ("Rubrik", "Rubrik", True, ""),
    ("Text", "Text", True, "Händelsebeskrivning"),
    ("Påverkar", "Påverkar", True, "Vem kortet drabbar, t.ex. ALLA SPELARE"),
    ("Effekt", "Effekt", True, "Vad som händer — utförs direkt, inget tärningsslag"),
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

SPEC_MALLTEXT = [
    ("Bildsida", "Etiketter", "HÄNDELSEKORT (från CSV 'Typ') · PU"),
    ("Textsida", "Sidhuvud", "HÄNDELSEKORT (från CSV 'Typ') · PU · PROJEKTUTVECKLING"),
    ("Textsida", "Regel", "LÄS - UTFÖR - KASTA"),
]


def tolka_spec():
    kort = []
    for bild, text in las_rader("PU_poldia_spec_tryckeri.txt"):
        typ_bild = re.fullmatch(r"(.+?)\s+PU", bild.strip()).group(1)
        fore, _, efter = text.partition("  " + MALLHUVUD + "  ")
        typ_text = text[len(fore):].split("  PU")[0].strip()
        m = re.fullmatch(r"(.+?)\s+LÄS\s+-\s+UTFÖR\s+-\s+KASTA\s+(\S+)\s+(.+)", efter.strip())
        kort.append({"Nr": m.group(2), "Typ": typ_bild, "_typ_text": typ_text,
                     "Rubrik+Text": fore, "Påverkar": m.group(1), "Effekt": m.group(3)})
    return kort


def jamfor_spec(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"PU_poldia_spec: antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        if t["_typ_text"] != t["Typ"]:
            avv.append((r["Nr"], "Typ (textsida)", t["_typ_text"], r["Typ"]))
        for falt in ("Nr", "Typ", "Påverkar", "Effekt"):
            if jamforbar(t[falt]) != jamforbar(r[falt]):
                avv.append((r["Nr"], falt, t[falt], r[falt]))
        if not jamforbar(t["Rubrik+Text"]).startswith(jamforbar(r["Rubrik"])):
            avv.append((r["Nr"], "Rubrik", t["Rubrik+Text"], r["Rubrik"]))
        if jamforbar(t["Rubrik+Text"]) != jamforbar(r["Rubrik"] + " " + r["Text"]):
            avv.append((r["Nr"], "Text", t["Rubrik+Text"], r["Rubrik"] + " | " + r["Text"]))
    return avv


def avbryt_vid(avvikelser, typ):
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", typ, a)
        sys.exit(f"{typ}: CSV och tryck skiljer — åtgärda innan Excel byggs.")


def main():
    # PU_poldia
    rader = las_csv("1. Projektutveckling/PU_poldia.csv", "Nr")
    avbryt_vid(jamfor_poldia(rader, tolka_poldia()), "PU_poldia")
    ut = bygg_arbetsbok(
        filnamn="PU_poldia.xlsx",
        kort_kolumner=POLDIA_KOLUMNER,
        rader=rader,
        namn_kolumn="Rubrik",
        malltext=POLDIA_MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=("Text",),
        kalla=[
            ("Korttyp", "PU_poldia — politik- och dialogkort (händelsekort), Skede 1 Projektutveckling"),
            ("Antal kort", f"{len(rader)} unika (P01–P20, D01–D20), 1 exemplar vardera per spel "
                           "(utskrift_config 'PU_poldia _kombinerad': 1; exemplar_map: 1)"),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — PU_poldia_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/PU_poldia_tryckeri.pdf "
                         "(senast ändrad 2026-04-27 20:13 UTC, 80 sidor)"),
            ("Tryckfilens text", "arv/tryckt_text/PU_poldia_tryckeri.txt (utläst via OneDrive, 80 sidor, "
                                 "rad 1 = bildsida, rad 2 = textsida per kort)"),
            ("Datakälla", "arv/spelet2_v1/1. Projektutveckling/PU_poldia.csv"),
            ("CSV-datum", "2026-04-26 13:31 — före tryck"),
            ("Kontroll", "Nr, Typ, Rubrik, Text och alla fem utfall jämförda kort för kort mot tryckfilen: "
                         "0 avvikelser i speldata."),
            ("Etiketter", "I PDF-texten står varje utfall före sin intervalletikett; tolkningen ger exakt "
                          "CSV:ns värden för alla 40 kort. Tryckta intervall är 1-4, 5-10, 11-15, 16-19, 20+ "
                          "medan CSV-rubrikerna är '1', '2 till 10', '11 till 15', '16 till 19', '20+'. "
                          "Excel använder tryckets intervall som kolumnrubriker."),
            ("Byggd med", "verktyg/bygg_pu_poldia_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")

    # PU_poldia_spec
    rader = las_csv("1. Projektutveckling/PU_poldia_spec.csv", "Nr")
    avbryt_vid(jamfor_spec(rader, tolka_spec()), "PU_poldia_spec")
    ut = bygg_arbetsbok(
        filnamn="PU_poldia_spec.xlsx",
        kort_kolumner=SPEC_KOLUMNER,
        rader=rader,
        namn_kolumn="Rubrik",
        malltext=SPEC_MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=("Text", "Effekt"),
        kalla=[
            ("Korttyp", "PU_poldia_spec — special-händelsekort (politik/dialog), Skede 1 Projektutveckling"),
            ("Antal kort", f"{len(rader)} unika (PS1–PS6, DS1–DS6), 1 exemplar vardera per spel "
                           "(utskrift_config 'PU_PolDia-speckort _kombinerad': 1; exemplar_map: 1)"),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — PU_poldia_spec_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/PU_poldia_spec_tryckeri.pdf "
                         "(senast ändrad 2026-04-27 20:33 UTC, 24 sidor)"),
            ("Tryckfilens text", "arv/tryckt_text/PU_poldia_spec_tryckeri.txt (utläst via OneDrive, 24 sidor, "
                                 "rad 1 = bildsida, rad 2 = textsida per kort)"),
            ("Datakälla", "arv/spelet2_v1/1. Projektutveckling/PU_poldia_spec.csv"),
            ("CSV-datum", "2026-04-26 13:31 — före tryck"),
            ("Kontroll", "Nr, Typ, Rubrik, Text, Påverkar och Effekt jämförda kort för kort mot tryckfilen "
                         "(avstavning och blanksteg utjämnade): 0 avvikelser."),
            ("Anmärkning", "Stavfel finns både i CSV och tryck (PS1 'mediaavslöjar'); dubbla blanksteg i "
                           "CSV:ns Effekt (PS5, DS1) syns inte i trycket. Oförändrat i Excel."),
            ("Byggd med", "verktyg/bygg_pu_poldia_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
