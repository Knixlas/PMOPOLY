"""Bygg kortdata/GF_kultur.xlsx ur det tryckta spelet.

Kulturaktivitetskort (FÖRETAGSKULTUR) i Skede 2.2 Genomförande: 80 kort KUL-001–KUL-080 som ger
kompetenspoäng (STA/KOM/SAM/NOG/INN/ABM) för att hantera utmaningar på faskorten.

Källor:
  - arv/spelet2_v1/3. Genomförande/GF_kultur.csv   (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/GF_kultur_tryckeri.txt         (text utläst ur tryckfilen, 2 rader per kort:
                                                    rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python3 verktyg/bygg_gf_kultur_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "GF_kultur_tryckeri.txt"

KOMPETENSER = [("STA", "Stabilitet"), ("KOM", "Kommunikation"), ("SAM", "Samarbete"),
               ("NOG", "Noggrannhet"), ("INN", "Innovation"), ("ABM", "Arbetsmiljö")]

KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–80 i tryckordning"),
    ("ID", "ID", True, "Kortnummer på textsidan: KUL-001–KUL-080"),
    ("Namn", "Namn", True, "Aktivitetens namn"),
    ("Beskrivning", "Beskrivning", True, "Löptext på textsidan"),
] + [(f"{kod} {namn}", kod, True, f"Kompetenspoäng {namn} ('-' = inget)") for kod, namn in KOMPETENSER] + [
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@bild", "fill_color", "line_color", "skede_color", "bakskede",
                       "bakgrund_color", "ordning_bild", "ordning_text"]

MALLTEXT = [
    ("Bildsida", "Etiketter", "KULTURAKTIVITET · GF"),
    ("Textsida", "Etiketter", "STA Stabilitet · KOM Kommunikation · SAM Samarbete · NOG Noggrannhet · "
                              "INN Innovation · ABM Arbetsmiljö"),
    ("Textsida", "Rubrik", "FÖRETAGSKULTUR"),
    ("Textsida", "Sidhuvud", "KULTURAKTIVITET · GF · GENOMFÖRANDE"),
    ("Textsida", "Regel", "KASTA KORTET NÄR DET SPELAS"),
    ("Textsida", "Regel", "använd för att hantera utmaningar under genomförandefasen"),
]

MALLHUVUD = "  ".join(f"{kod}   {namn}" for kod, namn in KOMPETENSER)
TEXT_MONSTER = re.compile(
    re.escape(MALLHUVUD) + r"  (?P<varden>(?:\S+  ){6})FÖRETAGSKULTUR  (?P<namn>.+?)  (?P<besk>.+)  "
    r"KULTURAKTIVITET  GF   GENOMFÖRANDE  (?P<id>KUL-\d{3}) KASTA KORTET NÄR DET SPELAS  "
    r"använd för att hantera utmaningar under  genomförandefasen")


def jamforbar(v):
    """För löptext: tryckets radbrytningar ('uppfin -  na', dubbla blanksteg) utjämnas."""
    v = re.sub(r"\s+", " ", v or "")
    v = re.sub(r"(\w) - (\w)", r"\1\2", v)
    return normalisera(v)


def las_tryck():
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    if len(rader) % 2:
        sys.exit(f"{TRYCK_FIL.name}: udda antal sidor ({len(rader)})")
    kort = []
    for bild, text in zip(rader[0::2], rader[1::2]):
        mt = TEXT_MONSTER.fullmatch(text.strip())
        if bild.strip() != "KULTURAKTIVITET  GF" or not mt:
            sys.exit(f"Kunde inte tolka kortet: {bild!r} / {text!r}")
        varden = mt["varden"].split()
        kort.append({"ID": mt["id"], "Namn": mt["namn"], "Beskrivning": mt["besk"],
                     **{kod: v for (kod, _), v in zip(KOMPETENSER, varden)}})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for r, t in zip(csv_rader, tryck):
        for falt in ["ID", "Namn"] + [k for k, _ in KOMPETENSER]:
            if normalisera(t[falt]) != normalisera(r[falt]):
                avv.append((r["ID"], falt, t[falt], r[falt]))
        if jamforbar(t["Beskrivning"]) != jamforbar(r["Beskrivning"]):
            avv.append((r["ID"], "Beskrivning", t["Beskrivning"], r["Beskrivning"]))
    return avv


def main():
    rader = las_csv("3. Genomförande/GF_kultur.csv", "ID")
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="GF_kultur.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        langa_kolumner=("Beskrivning",),
        kalla=[
            ("Korttyp", "GF_kultur — kulturaktivitetskort (FÖRETAGSKULTUR), Skede 2.2 Genomförande"),
            ("Antal kort", f"{len(rader)} unika, 1 exemplar vardera per spel"),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — "
                       "_tryckeri_temp/GF_kultur_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/GF_kultur_tryckeri.pdf"),
            ("Tryckfilens text", f"arv/tryckt_text/GF_kultur_tryckeri.txt (utläst via OneDrive, "
                                 f"{2 * len(rader)} sidor)"),
            ("Datakälla", "arv/spelet2_v1/3. Genomförande/GF_kultur.csv"),
            ("CSV-datum", "2026-04-26 16:26 — före tryck"),
            ("Kontroll", "ID, Namn, Beskrivning (utjämnad för tryckets radbrytning/avstavning) och alla sex "
                         "kompetensvärden jämförda kort för kort mot tryckfilen: 0 avvikelser."),
            ("Ej tryckt", "Kolumnen @bild (kompetensikon per kort) styr bildsidans motiv; ingen text."),
            ("Byggd med", "verktyg/bygg_gf_kultur_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
