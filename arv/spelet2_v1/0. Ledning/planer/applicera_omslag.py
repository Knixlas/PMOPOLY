"""
applicera_omslag.py
===================
For varje befintlig PDF i en mapp som matchar moenstret "* - .pdf":
behaall sida 1 (omslaget) och ersaett allt oevrigt med innehallet fran en
nygenererad kropps-PDF.

Resultat: PDFen pa plats far cover (originalets sida 1) + nytt innehall.
Ursprungs-omslaget (sida 1) overlever varje koerning eftersom det alltid
tas fran filen som finns dar just nu.

Anvaending (anropas av bygg_pdf.bat efter markdown_to_pdf.py).

Krav:
    pip install pypdf
"""

from __future__ import annotations
import argparse
import sys
from io import BytesIO
from pathlib import Path


def _make_cream_page(width_pt: float, height_pt: float,
                     color: str = '#FAF0DD'):
    """Skapa en PDF-sida i given storlek med given bakgrundsfärg.

    Anvaender WeasyPrint for att generera sidan, sen pypdf for att
    laesa in den. Storleken matchar omslagets matt.
    """
    from io import BytesIO
    from weasyprint import HTML, CSS
    from pypdf import PdfReader

    # Konvertera punkter till millimeter (1 pt = 0.352778 mm)
    w_mm = width_pt * 0.3527778
    h_mm = height_pt * 0.3527778

    css = f"""
    @page {{
        size: {w_mm:.4f}mm {h_mm:.4f}mm;
        margin: 0;
        background: {color};
    }}
    body {{ margin: 0; padding: 0; }}
    """
    pdf_bytes = HTML(string='').write_pdf(
        stylesheets=[CSS(string=css)],
    )
    return PdfReader(BytesIO(pdf_bytes)).pages[0]


def replace_content(target_pdf: Path, body_pdf: Path,
                    blank_color: str = '#FAF0DD') -> tuple[bool, int]:
    """Behaall sida 1 i target_pdf, ersaett resten med body_pdf.

    Layout efter koerning:
      sida 1: omslag (originalets sida 1)
      sida 2: blank i cremefarg (saa omslaget star ensamt)
      sida 3+: kropps-innehallet
      sista sidor: blanka i cremefarg sa att totalen ar delbar med 4

    Returnerar (ok, antal_sidor_i_resultat).
    """
    from pypdf import PdfReader, PdfWriter

    buf = BytesIO()
    with open(target_pdf, 'rb') as f:
        cover_reader = PdfReader(f)
        if not cover_reader.pages:
            return False, 0

        cover_page = cover_reader.pages[0]
        cover_w = float(cover_page.mediabox.width)
        cover_h = float(cover_page.mediabox.height)

        body_reader = PdfReader(str(body_pdf))
        body_pages = list(body_reader.pages)

        # Raekna ut hur manga blanksidor som behovs:
        # 1 (sida 2) + N padding for att summan ska bli delbar med 4
        pages_excluding_padding = 2 + len(body_pages)  # cover + blank + body
        padding = (-pages_excluding_padding) % 4
        total_blanks = 1 + padding

        # Generera blanksidor i creme-fearg (en gang, atervaends)
        # Notera: pypdf kopierar sidan vid add_page, sa atervaendning ar saekert
        cream_blank = _make_cream_page(cover_w, cover_h, blank_color)

        # Bygg den slutliga PDFen
        writer = PdfWriter()
        writer.add_page(cover_page)            # 1: omslag
        writer.add_page(cream_blank)           # 2: blank
        for p in body_pages:                   # 3-N: kropp
            writer.add_page(p)
        for _ in range(padding):               # ev. extra blanksidor
            writer.add_page(cream_blank)

        total = len(writer.pages)
        writer.write(buf)
        writer.close()

    with open(target_pdf, 'wb') as f:
        f.write(buf.getvalue())

    return True, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('body_pdf', type=Path,
                        help='Den genererade kropps-PDF:en')
    parser.add_argument('--plantyp', required=True,
                        help='Plantyp att matcha, t.ex. "Forvaltningsplan"')
    parser.add_argument('--search-dir', type=Path, default=Path('.'),
                        help='Mapp att soka i (default: aktuell mapp)')
    args = parser.parse_args()

    if not args.body_pdf.exists():
        print(f'  [FEL] Hittar inte kropps-PDF: {args.body_pdf}', file=sys.stderr)
        return 1

    try:
        import pypdf  # noqa: F401
    except ImportError:
        print('  [VARNING] pypdf saknas - kan inte applicera omslag.')
        print('            Installera med: pip install pypdf')
        return 0  # ej fatalt - kropps-PDF finns aendaa

    # Hitta cover-PDFer enligt moenstret "* - .pdf"
    pattern = f'* - {args.plantyp}.pdf'
    targets = sorted(args.search_dir.glob(pattern))

    if not targets:
        print(f'  Inga PDFer matchade "{pattern}"')
        return 0

    print(f'  Hittade {len(targets)} matchande PDFer:')

    success = 0
    for target in targets:
        try:
            ok, total = replace_content(target, args.body_pdf)
            if ok:
                print(f'    {target.name}  ({total} sidor)')
                success += 1
            else:
                print(f'    [SKIP] {target.name}: tom PDF')
        except Exception as exc:
            print(f'    [FEL] {target.name}: {exc}', file=sys.stderr)

    return 0 if success > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
