# -*- coding: utf-8 -*-
"""
konvertera_former_till_png.py

Konverterar PDF-filer (projektformer) till PNG:er med:
  - Transparent bakgrund (vita pixlar -> alpha=0)
  - Auto-detekterad rutstorlek (alla rutor blir lika stora pixel-massigt)
  - Kvadratisk transparent canvas pa N x N rutor (samma for alla bilder)
  - Formen centrerad pa canvasen
  - Hog upplosning (default 300 DPI)

Default-input:  Bilder/Former/
Default-output: Bilder/Former/png/

Anvandning:
    python konvertera_former_till_png.py
    python konvertera_former_till_png.py --canvas-grid 5
    python konvertera_former_till_png.py --dpi 600
    python konvertera_former_till_png.py --ruta-px 250

Kraver: pip install pymupdf pillow
"""

import argparse
import os
import sys

try:
    import fitz
except ImportError:
    print("FEL: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("FEL: pip install pillow", file=sys.stderr)
    sys.exit(1)


def rendera_och_croppa(pdf_path, dpi, vit_troskel):
    """Renderar PDF:ens forsta sida, gor vit transparent, croppar till bbox."""
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        doc.close()
        return None, None

    sida = doc[0]
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = sida.get_pixmap(matrix=matrix, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")

    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = pixels[x, y]
            if r >= vit_troskel and g >= vit_troskel and b >= vit_troskel:
                pixels[x, y] = (r, g, b, 0)

    bbox = img.getbbox()
    if not bbox:
        return None, None
    img = img.crop(bbox)
    return img, img.size


def main():
    skript_dir = os.path.dirname(os.path.abspath(__file__))
    default_indir = os.path.join(skript_dir, "Bilder", "Former")

    parser = argparse.ArgumentParser(description="Konvertera projektform-PDF till transparenta PNG")
    parser.add_argument("--indir", default=default_indir)
    parser.add_argument("--outdir", default=None)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--threshold", type=int, default=245)
    parser.add_argument("--canvas-grid", type=int, default=5)
    parser.add_argument("--ruta-px", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    indir = os.path.abspath(args.indir)
    if not os.path.isdir(indir):
        print("FEL: hittar inte mappen " + indir, file=sys.stderr)
        sys.exit(1)

    outdir = os.path.abspath(args.outdir) if args.outdir else os.path.join(indir, "png")
    os.makedirs(outdir, exist_ok=True)

    pdf_filer = sorted(f for f in os.listdir(indir) if f.lower().endswith(".pdf"))
    if not pdf_filer:
        print("Inga PDF-filer hittade i " + indir)
        return

    print("Input:       " + indir)
    print("Output:      " + outdir)
    print("DPI:         " + str(args.dpi))
    print("Troskel:     >=" + str(args.threshold) + " (R,G,B) -> transparent")
    print("Canvas:      " + str(args.canvas_grid) + "x" + str(args.canvas_grid) + " rutor")
    print("Antal PDF:   " + str(len(pdf_filer)))
    print("")

    print("Pass 1: renderar och croppar alla figurer...")
    figurer = {}
    fel_lista = []
    for fn in pdf_filer:
        pdf_path = os.path.join(indir, fn)
        try:
            img, size = rendera_och_croppa(pdf_path, args.dpi, args.threshold)
            if img is None:
                print("  [TOM] " + fn)
                fel_lista.append(fn)
                continue
            figurer[fn] = img
            print("  - " + fn + "  (" + str(size[0]) + "x" + str(size[1]) + " px)")
        except Exception as e:
            print("  [FEL] " + fn + ": " + str(e))
            fel_lista.append(fn)

    if not figurer:
        print("Inga figurer kunde renderas.")
        return

    if args.ruta_px is not None:
        ruta_px = args.ruta_px
        print("\nRutstorlek: " + str(ruta_px) + " px (manuellt satt)")
    else:
        ruta_px = min(min(img.size) for img in figurer.values())
        print("\nRutstorlek: " + str(ruta_px) + " px (auto-detekterad)")

    canvas_px = args.canvas_grid * ruta_px
    print("Canvas:     " + str(canvas_px) + "x" + str(canvas_px) + " px")
    print("")

    print("Pass 2: skriver PNG:er med centrerad figur...")
    ok = 0
    hoppat = 0
    overflow = []
    for fn, img in figurer.items():
        png_namn = os.path.splitext(fn)[0] + ".png"
        png_path = os.path.join(outdir, png_namn)

        if os.path.exists(png_path) and not args.overwrite:
            print("  - " + fn + "  (PNG finns redan, hoppar)")
            hoppat += 1
            continue

        canvas = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))
        fw, fh = img.size
        rutor_w = round(fw / float(ruta_px))
        rutor_h = round(fh / float(ruta_px))
        if fw > canvas_px or fh > canvas_px:
            overflow.append(fn + " (" + str(rutor_w) + "x" + str(rutor_h) + ")")

        x = (canvas_px - fw) // 2
        y = (canvas_px - fh) // 2
        canvas.paste(img, (x, y), img)
        canvas.save(png_path, "PNG", optimize=True)
        print("  [OK] " + png_namn + "  (" + str(rutor_w) + "x" + str(rutor_h) + " rutor)")
        ok += 1

    print("")
    print("Klart: " + str(ok) + " skrivna, " + str(hoppat) + " hoppade, " + str(len(fel_lista)) + " fel")
    if overflow:
        print("")
        print("Varning: " + str(len(overflow)) + " figurer storre an canvas:")
        for o in overflow:
            print("  - " + o)
        print("  Anvand --canvas-grid med hogre varde for storre canvas.")
    print("")
    print("PNG-filerna ligger i: " + outdir)


if __name__ == "__main__":
    main()

