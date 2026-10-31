"""Bygg kortdata/PU_markexpansion.xlsx ur det tryckta spelet.

Källor:
  - arv/spelet2_v1/1. Projektutveckling/PU_markexpansion.csv  (datan som InDesign-mallen fylldes med)
  - arv/tryckt_text/PU_markexpansion_tryckeri.txt             (text utläst ur tryckfilen, 2 rader per kort:
                                                               rad 1 = bildsida, rad 2 = textsida)

Skriptet kontrollerar varje kort mot tryckfilen och avbryter om något skiljer.
Kör:  python3 verktyg/bygg_pu_markexpansion_excel.py
"""
import re
import sys

from kortexcel import TRYCKT_TEXT, bygg_arbetsbok, las_csv, normalisera

TRYCK_FIL = TRYCKT_TEXT / "PU_markexpansion_tryckeri.txt"

KORT_KOLUMNER = [
    ("Kort-id", None, False, "Löpnummer 1–16 i tryckordning (= formbildens nummer 01–16)"),
    ("Korttyp", "Namn", True, "Står på bild- och textsidan: MARKEXPANSION"),
    ("BYA (kvm)", "kvm BYA", True, "Byggnadsarea som kortet tillför, tryckt som '<n> kvm BYA'"),
    ("Antal rutor", "Antal rutor", False, "Ej tryckt som text — antal rutor i markbiten (formbilden); "
                                          "= BYA / 250"),
    ("Antal exemplar", None, False, "Antal tryckta kort per spel (utskrift_config: 1)"),
]

PRODUKTION_KOLUMNER = ["@formbild", "@bildsida", "fill_color", "line_color", "skede_color",
                       "bakskede", "bakgrund_color"]

MALLTEXT = [
    ("Bildsida", "Etiketter", "MARKEXPANSION (från CSV 'Namn') · PU"),
    ("Textsida", "Etiketter", "kvm BYA (efter värdet) · MARKEXPANSION (från CSV 'Namn') · PU · PROJEKTUTVECKLING"),
    ("Textsida", "Regel", "PLACERA PÅ TOMT, KASTA KORTET"),
]


def las_tryck():
    rader = [r for r in TRYCK_FIL.read_text(encoding="utf-8").splitlines() if r.strip()]
    kort = []
    for bild, text in zip(rader[0::2], rader[1::2]):
        mb = re.fullmatch(r"(.+?)\s+PU", bild.strip())
        mt = re.fullmatch(r"(\d+) kvm BYA\s+(.+?)\s+PU\s+PROJEKTUTVECKLING\s+PLACERA PÅ TOMT, KASTA KORTET",
                          text.strip())
        if not (mb and mt):
            sys.exit(f"Kunde inte tolka kort: {bild!r} / {text!r}")
        kort.append({"Namn": mb.group(1), "_namn_text": mt.group(2), "kvm BYA": mt.group(1)})
    return kort


def jamfor(csv_rader, tryck):
    if len(csv_rader) != len(tryck):
        sys.exit(f"Antal kort skiljer: CSV {len(csv_rader)}, tryck {len(tryck)}")
    avv = []
    for i, (r, t) in enumerate(zip(csv_rader, tryck), 1):
        if t["_namn_text"] != t["Namn"]:
            avv.append((i, "Namn (textsida)", t["_namn_text"], r["Namn"]))
        for falt in ("Namn", "kvm BYA"):
            if normalisera(t[falt]) != normalisera(r[falt]):
                avv.append((i, falt, t[falt], r[falt]))
        # Rimlighetskontroll av ej tryckt speldata: 250 kvm per ruta, och formbildens namn.
        if int(r["kvm BYA"]) != 250 * int(r["Antal rutor"]):
            avv.append((i, "Antal rutor", r["Antal rutor"], f"BYA {r['kvm BYA']} ≠ 250 × rutor"))
        if not r["@formbild"].endswith(f"_{i:02d}_{r['Antal rutor']}rutor.png"):
            avv.append((i, "@formbild", r["@formbild"], f"förväntat _{i:02d}_{r['Antal rutor']}rutor.png"))
    return avv


def main():
    rader = las_csv("1. Projektutveckling/PU_markexpansion.csv", "Namn")
    avvikelser = jamfor(rader, las_tryck())
    if avvikelser:
        for a in avvikelser:
            print("AVVIKELSE", a)
        sys.exit("CSV och tryck skiljer — åtgärda innan Excel byggs.")

    ut = bygg_arbetsbok(
        filnamn="PU_markexpansion.xlsx",
        kort_kolumner=KORT_KOLUMNER,
        rader=rader,
        namn_kolumn="Namn",
        malltext=MALLTEXT,
        produktion_kolumner=PRODUKTION_KOLUMNER,
        format_mm="58 × 88",
        exemplar=1,
        kalla=[
            ("Korttyp", "PU_markexpansion — markexpansionskort, Skede 1 Projektutveckling"),
            ("Antal kort", f"{len(rader)} kort, 1 exemplar vardera per spel (utskrift_config "
                           "'PU_markexpansion _kombinerad': 1; exemplar_map: 1). Alla heter MARKEXPANSION; "
                           "de skiljer sig i formbild och BYA (2 × 500, 6 × 750, 6 × 1000, 2 × 1250 kvm)."),
            ("Format", "58 × 88 mm, dubbelsidigt (bildsida + textsida) — PU_markexpansion_bildsida_layout.json"),
            ("Tryckfil", "OneDrive: SPELET 2/PDF/Tryckbara/PU_markexpansion_tryckeri.pdf "
                         "(senast ändrad 2026-04-27 20:34 UTC, 32 sidor)"),
            ("Tryckfilens text", "arv/tryckt_text/PU_markexpansion_tryckeri.txt (utläst via OneDrive, 32 sidor, "
                                 "rad 1 = bildsida, rad 2 = textsida per kort)"),
            ("Datakälla", "arv/spelet2_v1/1. Projektutveckling/PU_markexpansion.csv"),
            ("CSV-datum", "2026-04-26 13:31 — före tryck"),
            ("Kontroll", "Namn och kvm BYA jämförda kort för kort mot tryckfilen: 0 avvikelser. "
                         "Antal rutor (ej tryckt som text) kontrollerat mot BYA (250 kvm/ruta) och formbildens "
                         "filnamn: stämmer för alla kort."),
            ("Byggd med", "verktyg/bygg_pu_markexpansion_excel.py"),
        ],
    )
    print(f"Skrev {ut}: {len(rader)} kort, 0 avvikelser")


if __name__ == "__main__":
    main()
