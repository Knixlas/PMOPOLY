"""
splitta_planer.py
=================
Splittrar en flersidig PDF där varje sida är en separat plan.
Varje sida sparas som "<Företagsnamn> - <Plantyp>.pdf" i samma mapp som källan.

Företagsnamn: läses från övre vänstra headern (raden som innehåller "AB").
Plantyp:      läses från övre högra headern (första raden, t.ex. "Verksamhetsplan").

Användning:
    python splitta_planer.py
        → letar efter en PDF i BASE_DIR och splittrar den.

    python splitta_planer.py "min_pdf.pdf"
        → splittrar angiven fil (relativ till BASE_DIR eller absolut sökväg).

Kräver:
    pip install pdfplumber pypdf
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter


# === KONFIGURATION =====================================================
BASE_DIR = Path(
    r"C:\Users\niklas.sviden\OneDrive - Åke Sundvalls Byggnads AB"
    r"\SPELET 2\0. Ledning\planer"
)

# Headerzonens position (andelar av sidan, 0–1).
# Justera om extraktionen missar — t.ex. öka HEADER_HEIGHT till 0.15.
HEADER_HEIGHT = 0.10
LEFT_ZONE_WIDTH = 0.55
RIGHT_ZONE_START = 0.45
# =======================================================================


# Tecken som inte får finnas i Windows-filnamn
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def rensa_filnamn(text: str) -> str:
    """Plocka bort otillåtna tecken och kollapsa mellanslag."""
    text = _INVALID_FILENAME_CHARS.sub("", text).strip()
    return re.sub(r"\s+", " ", text)


def extrahera_header(page) -> tuple[str, str]:
    """
    Returnera (företagsnamn, plantyp) från sidans header.

    Strategin:
    - Vänsterzonen (top-left): leta rad som innehåller " AB" men inte "HOLDING".
    - Högerzonen (top-right): första raden som inte är "UTGÅVA …" eller "KONFIDENTIELL".
    """
    w, h = page.width, page.height

    vanster_text = (
        page.crop((0, 0, w * LEFT_ZONE_WIDTH, h * HEADER_HEIGHT)).extract_text() or ""
    )
    hoger_text = (
        page.crop((w * RIGHT_ZONE_START, 0, w, h * HEADER_HEIGHT)).extract_text() or ""
    )

    # --- Företagsnamn ---
    foretagsnamn = ""
    for rad in vanster_text.splitlines():
        rad_strippad = rad.strip()
        if not rad_strippad:
            continue
        if " AB" in rad_strippad and "HOLDING" not in rad_strippad.upper():
            foretagsnamn = rad_strippad
            break
    # Fallback: ta sista icke-tomma raden
    if not foretagsnamn:
        rader = [r.strip() for r in vanster_text.splitlines() if r.strip()]
        if rader:
            foretagsnamn = rader[-1]

    # --- Plantyp ---
    plantyp = ""
    for rad in hoger_text.splitlines():
        rad_strippad = rad.strip()
        if not rad_strippad:
            continue
        if "UTGÅVA" in rad_strippad.upper():
            continue
        if "KONFIDENTIELL" in rad_strippad.upper():
            continue
        plantyp = rad_strippad
        break

    return rensa_filnamn(foretagsnamn), rensa_filnamn(plantyp)


def hitta_kalla() -> Path:
    """Försök hitta källfilen automatiskt om ingen anges."""
    pdfs = list(BASE_DIR.glob("*.pdf"))

    # Filtrera bort filer som ser ut som redan splittrade ("namn - plantyp.pdf")
    kandidater = [p for p in pdfs if " - " not in p.stem]

    if len(kandidater) == 1:
        return kandidater[0]
    if len(kandidater) == 0:
        print(f"Hittade ingen PDF i {BASE_DIR}")
        sys.exit(1)

    print("Flera PDF-kandidater hittades. Ange filnamn som argument:")
    for p in kandidater:
        print(f"   python splitta_planer.py \"{p.name}\"")
    sys.exit(1)


def main():
    # --- Hitta källfil ---
    if len(sys.argv) > 1:
        arg = Path(sys.argv[1])
        kalla = arg if arg.is_absolute() else (BASE_DIR / arg)
    else:
        kalla = hitta_kalla()

    if not kalla.exists():
        print(f"Hittar inte filen: {kalla}")
        sys.exit(1)

    print(f"Källa: {kalla.name}")
    print(f"Mapp:  {kalla.parent}\n")

    reader = PdfReader(str(kalla))
    antal_sidor = len(reader.pages)
    print(f"Antal sidor: {antal_sidor}\n")

    skapade = 0
    misslyckade = []
    anvanda_namn: set[str] = set()

    with pdfplumber.open(str(kalla)) as pdf:
        for i, ppage in enumerate(pdf.pages, start=1):
            foretagsnamn, plantyp = extrahera_header(ppage)

            if foretagsnamn and plantyp:
                filnamn = f"{foretagsnamn} - {plantyp}.pdf"
            else:
                filnamn = f"sida_{i:02d}_okand.pdf"
                misslyckade.append(
                    (i, foretagsnamn or "(tomt)", plantyp or "(tomt)")
                )

            # Hantera kollisioner (t.ex. om två sidor ger samma namn)
            stem = Path(filnamn).stem
            suffix_nr = 2
            unik = filnamn
            while unik.lower() in anvanda_namn or (kalla.parent / unik).exists():
                # Rör inte källfilen!
                if (kalla.parent / unik).resolve() == kalla.resolve():
                    unik = f"{stem} ({suffix_nr}).pdf"
                    suffix_nr += 1
                    continue
                unik = f"{stem} ({suffix_nr}).pdf"
                suffix_nr += 1
            anvanda_namn.add(unik.lower())

            mal = kalla.parent / unik

            writer = PdfWriter()
            writer.add_page(reader.pages[i - 1])
            with open(mal, "wb") as f:
                writer.write(f)

            print(f"  [{i:>3}/{antal_sidor}]  {unik}")
            skapade += 1

    # --- Sammanfattning ---
    print(f"\nKlart. {skapade} filer skapade i:")
    print(f"   {kalla.parent}")

    if misslyckade:
        print(f"\n[!] {len(misslyckade)} sidor fick fallback-namn (extraktion misslyckades):")
        for sida, foretag, plan in misslyckade:
            print(f"     Sida {sida}: företag={foretag!r}, plantyp={plan!r}")
        print("\nTips: öka HEADER_HEIGHT i konfigurationen om texten ligger längre ned.")


if __name__ == "__main__":
    main()

