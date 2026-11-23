"""
skapa_tryckark.py

Tar PDF\\Kombinerade\\*_kombinerad(_N).pdf och skapar tryckbara ark där
flera kort monteras per A3-sida, med skärmärken och korrekt front/bak-
alignering för duplex-tryck.

Output: PDF\\Tryckbara\\<korttyp>_tryck(_N).pdf + MASTER_tryck.pdf

Antaganden:
  - Input-PDF:er har alternerande sidor: bild, text, bild, text ...
    (vilket interfoliera_pdf.py redan producerar)
  - Alla bildsidor och textsidor har samma dimensioner
  - Önskad arkstorlek: A3 (297×420 mm)
  - Utfall: 0 mm (mallarna har inget) — skärmärken sätts 2 mm utanför
    kortkant. Om du lägger till utfall i mallarna, öka CROP_OFFSET_MM.

Kör: python skapa_tryckark.py "C:\\...\\SPELET 2\\PDF"
Kräver: pip install pypdf reportlab
"""

import os
import re
import sys
import math

try:
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
except ImportError:
    print("FEL: pip install pypdf")
    sys.exit(1)

try:
    from reportlab.pdfgen import canvas
except ImportError:
    print("FEL: pip install reportlab")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# INSTÄLLNINGAR — justera här vid behov
# ═══════════════════════════════════════════════════════════════════════

MM = 72.0 / 25.4  # konvertera mm till PDF-punkter (points)

# Arkstorlek (A4 liggande default)
SHEET_WIDTH_MM  = 297
SHEET_HEIGHT_MM = 210

# Marginal runt arket (från papperskant till närmaste kort)
MARGIN_MM = 8

# Avstånd mellan kort på arket (påverkar utrymme för skärmärken)
GUTTER_MM = 8

# Utfall (bleed) — bakgrundsrektangel-metod (v2):
# Istället för att skala upp kortets innehåll (vilket distorderade text)
# ritar vi en heltäckande färgad rektangel BAKOM varje kort på arket
# som sträcker sig BLEED_MM utanför trim. Färgen läses per kort-typ från
# CSV: bakskede för bildsidor, bakgrund_color för textsidor.
# Antagandet är att alla kort i samma PDF har samma bakskede/bakgrund.
BLEED_MM = 5

# Sökväg till SPELET 2-rotmappen för att kunna läsa CSV-filer.
# Sätts automatiskt i main() utifrån PDF-mappens placering.
SPELET2_ROT = ""

# Mappning från fas-prefix till mapp där CSV-filerna ligger.
FAS_MAPPAR = {
    "L_":  "0. Ledning",
    "PU_": "1. Projektutveckling",
    "PL_": "2. Planering",
    "GF_": "3. Genomförande",
    "F_":  "4. Förvaltning",
}

# Alias-mappning för PDF-filnamn som inte enkelt mappar till en CSV via
# fuzzy-matching. Nyckel = normaliserat PDF-stam (lower, utan _-).
# Värde = relativ sökväg till CSV från SPELET 2-roten.
CSV_ALIAS = {
    "fkortmoderbolagslån":  "4. Förvaltning/F_moderbolagslån.csv",
    "puplpersonal":         "1. Projektutveckling/PU_personal.csv",
}

# Skärmärken (vid TRIM-linjen, inte bleed-kanten)
CROP_OFFSET_MM = 3   # avstånd från trim-kant till mark-start (>= BLEED_MM)
CROP_LEN_MM    = 4   # längd på varje skärmärke
CROP_WIDTH_PT  = 0.25  # linjebredd för märken

# Ska fram- och bak-sidor spegelvändas för duplex? (flip på långsida)
SPEGELVAND_BAK = True

# Stäng av imposition om kortet är för stort — då görs bara crop marks
MIN_CARDS_PER_SHEET = 1


# ═══════════════════════════════════════════════════════════════════════
# Hjälpfunktioner
# ═══════════════════════════════════════════════════════════════════════

def berakna_layout(card_w, card_h):
    """Räkna ut hur många kort som får plats på ett ark, och positionerna."""
    sheet_w = SHEET_WIDTH_MM * MM
    sheet_h = SHEET_HEIGHT_MM * MM
    margin  = MARGIN_MM * MM
    gutter  = GUTTER_MM * MM

    cols = int((sheet_w - 2*margin + gutter) / (card_w + gutter))
    rows = int((sheet_h - 2*margin + gutter) / (card_h + gutter))
    cols = max(cols, 0)
    rows = max(rows, 0)

    if cols < 1 or rows < 1:
        return None

    # Centrera kort-blocket på arket
    total_w = cols * card_w + (cols - 1) * gutter
    total_h = rows * card_h + (rows - 1) * gutter
    start_x = (sheet_w - total_w) / 2
    start_y = (sheet_h - total_h) / 2

    # Positioner från övre-vänster → nedre-höger (läsriktning)
    # PDF origin = nedre-vänster, så rad 0 är TOPP = högsta y
    positions_fram = []
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (card_w + gutter)
            y = start_y + (rows - 1 - r) * (card_h + gutter)
            positions_fram.append((x, y))

    # Bak-sidor speglas i x-led (flip på långsida/vertikal axel)
    if SPEGELVAND_BAK:
        positions_bak = []
        for r in range(rows):
            for c in range(cols):
                mirror_c = cols - 1 - c
                x = start_x + mirror_c * (card_w + gutter)
                y = start_y + (rows - 1 - r) * (card_h + gutter)
                positions_bak.append((x, y))
    else:
        positions_bak = list(positions_fram)

    return {
        "cols": cols,
        "rows": rows,
        "sheet_w": sheet_w,
        "sheet_h": sheet_h,
        "positions_fram": positions_fram,
        "positions_bak": positions_bak,
    }


def skapa_skarmarken_pdf(ut_path, positions, card_w, card_h, sheet_w, sheet_h):
    """Skapa en PDF med bara skärmärken vid varje kort-hörn."""
    c = canvas.Canvas(ut_path, pagesize=(sheet_w, sheet_h))
    c.setLineWidth(CROP_WIDTH_PT)
    c.setStrokeColorRGB(0, 0, 0)

    off = CROP_OFFSET_MM * MM
    lng = CROP_LEN_MM * MM

    for (x, y) in positions:
        # Fyra hörn: nedre-vänster, nedre-höger, övre-vänster, övre-höger
        hörn = [
            (x,          y),            # nedre-vänster
            (x + card_w, y),            # nedre-höger
            (x,          y + card_h),   # övre-vänster
            (x + card_w, y + card_h),   # övre-höger
        ]
        # Nedre-vänster hörn (x, y): märken till vänster om x och under y
        c.line(x - off - lng, y,          x - off,       y)         # horisontell
        c.line(x,             y - off,    x,             y - off - lng)  # vertikal
        # Nedre-höger (x+w, y)
        c.line(x + card_w + off, y,       x + card_w + off + lng, y)
        c.line(x + card_w,       y - off, x + card_w,   y - off - lng)
        # Övre-vänster (x, y+h)
        c.line(x - off - lng, y + card_h, x - off,       y + card_h)
        c.line(x,             y + card_h + off, x,       y + card_h + off + lng)
        # Övre-höger (x+w, y+h)
        c.line(x + card_w + off, y + card_h, x + card_w + off + lng, y + card_h)
        c.line(x + card_w,       y + card_h + off, x + card_w,       y + card_h + off + lng)

    c.save()


def hex_till_rgb(hex_str):
    """#RRGGBB -> (r, g, b) som 0..1 för reportlab."""
    h = (hex_str or "").lstrip("#").strip()
    if len(h) != 6:
        return (1, 1, 1)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return (1, 1, 1)


def detektera_csv_encoding(path):
    """Försök läsa fil med vanliga encodings; returnerar första som funkar."""
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "cp1252"


def _normalisera_namn(s):
    """Normalisera filnamn för fuzzy matching: lower, strip space/underscore/bindestreck."""
    return re.sub(r"[\s_\-]+", "", s.lower())


def hitta_csv_for_kombinerad(kombinerad_path):
    """Givet en *_kombinerad(_N).pdf, hitta motsvarande bas-CSV.
    Strategi: exakt match -> case-insensitiv -> fuzzy prefix-match.
    Hanterar varianter som 'PU_BYA_klass _kombinerad' -> PU_BYA.csv
    och 'PU_PolDia-speckort _kombinerad' -> PU_poldia_spec.csv."""
    if not SPELET2_ROT:
        return None
    basnamn = os.path.basename(kombinerad_path)
    stam = re.sub(r"\s*_kombinerad(?:_\d+)?\.pdf$", "", basnamn, flags=re.IGNORECASE)
    stam = stam.strip()
    stam_norm = _normalisera_namn(stam)

    # 0. Kolla alias-mappning först (för specialfall som F_kort_moderbolagslån)
    if stam_norm in CSV_ALIAS:
        alias_path = os.path.join(SPELET2_ROT, CSV_ALIAS[stam_norm])
        if os.path.exists(alias_path):
            return alias_path

    for prefix, mapp in FAS_MAPPAR.items():
        if not stam.upper().startswith(prefix.upper()):
            continue
        mapp_path = os.path.join(SPELET2_ROT, mapp)
        if not os.path.isdir(mapp_path):
            continue

        # 1. Exakt match
        kandidat = os.path.join(mapp_path, stam.replace(" ", "") + ".csv")
        if os.path.exists(kandidat):
            return kandidat

        # 2-3. Case-insensitiv eller fuzzy prefix-match
        try:
            csv_filer = [f for f in os.listdir(mapp_path) if f.lower().endswith(".csv")]
        except OSError:
            csv_filer = []

        # Case-insensitiv exakt match
        for f in csv_filer:
            if f.lower() == (stam.replace(" ", "") + ".csv").lower():
                return os.path.join(mapp_path, f)

        # Fuzzy: hitta längsta CSV-stam som är prefix till PDF-stam (efter normalisering)
        bästa = None
        for f in csv_filer:
            f_stam = f[:-4]
            f_norm = _normalisera_namn(f_stam)
            if len(f_norm) < 4:
                continue
            if stam_norm.startswith(f_norm):
                if bästa is None or len(f_norm) > len(_normalisera_namn(bästa[:-4])):
                    bästa = f
        if bästa:
            return os.path.join(mapp_path, bästa)

    return None


def las_kortdata_fran_csv(csv_path):
    """Returnerar (bild_data, text_data) - två listor med dicts {bsk, bg}
    sorterade efter ordning_bild respektive ordning_text. Detta gör att
    radernas ordning matchar PDF-sidornas ordning per sida-typ."""
    if not csv_path or not os.path.exists(csv_path):
        return [], []
    try:
        import csv as csvmod
        enc = detektera_csv_encoding(csv_path)
        with open(csv_path, encoding=enc, newline="") as f:
            reader = csvmod.reader(f, delimiter=";")
            header = next(reader, None)
            if not header:
                return [], []

            def col_idx(name):
                try:
                    return header.index(name)
                except ValueError:
                    return -1

            bsk_idx = col_idx("bakskede")
            bg_idx = col_idx("bakgrund_color")
            ob_idx = col_idx("ordning_bild")
            ot_idx = col_idx("ordning_text")

            all_rows = []
            for row in reader:
                if not row or len(row) < 2:
                    continue
                bsk = row[bsk_idx].strip() if 0 <= bsk_idx < len(row) else ""
                bg = row[bg_idx].strip() if 0 <= bg_idx < len(row) else ""
                try:
                    ob = int(row[ob_idx]) if 0 <= ob_idx < len(row) else 9999
                except (ValueError, IndexError):
                    ob = 9999
                try:
                    ot = int(row[ot_idx]) if 0 <= ot_idx < len(row) else 9999
                except (ValueError, IndexError):
                    ot = 9999
                all_rows.append({
                    "bsk": bsk or "#FFFFFF",
                    "bg": bg or "#FFFFFF",
                    "ob": ob,
                    "ot": ot,
                })

            bild_sorted = sorted(all_rows, key=lambda r: r["ob"])
            text_sorted = sorted(all_rows, key=lambda r: r["ot"])
            return bild_sorted, text_sorted
    except Exception as e:
        print(f"  FEL las_kortdata_fran_csv: {e}")
        return [], []


def las_bakgrundsfarger_fran_csv(csv_path):
    """Returnerar (bakskede_hex, bakgrund_color_hex) från första raden i CSV.
    Faller tillbaka till vit om kolumnerna saknas."""
    if not csv_path or not os.path.exists(csv_path):
        return ("#FFFFFF", "#FFFFFF")
    try:
        import csv as csvmod
        enc = detektera_csv_encoding(csv_path)
        with open(csv_path, encoding=enc, newline="") as f:
            reader = csvmod.reader(f, delimiter=";")
            header = next(reader, None)
            if not header:
                return ("#FFFFFF", "#FFFFFF")
            try:
                bsk_idx = header.index("bakskede")
            except ValueError:
                bsk_idx = -1
            try:
                bg_idx = header.index("bakgrund_color")
            except ValueError:
                bg_idx = -1
            for row in reader:
                if not row or len(row) < 2:
                    continue
                bsk = row[bsk_idx].strip() if bsk_idx >= 0 and bsk_idx < len(row) else ""
                bg = row[bg_idx].strip() if bg_idx >= 0 and bg_idx < len(row) else ""
                if bsk or bg:
                    return (bsk or "#FFFFFF", bg or "#FFFFFF")
        return ("#FFFFFF", "#FFFFFF")
    except Exception:
        return ("#FFFFFF", "#FFFFFF")


def skapa_bleed_bakgrund_pdf(ut_path, positions, card_w, card_h, sheet_w, sheet_h, farger):
    """Ritar en heltäckande färgad rektangel BAKOM varje kort som sträcker
    sig BLEED_MM utanför trim.

    'farger' kan vara:
      - en hex-sträng (samma färg för alla positioner)
      - en lista av hex-strängar (en färg per position, samma längd som positions)
    """
    bleed = BLEED_MM * MM
    if bleed <= 0:
        return None
    c = canvas.Canvas(ut_path, pagesize=(sheet_w, sheet_h))

    if isinstance(farger, str):
        farglista = [farger] * len(positions)
    else:
        farglista = list(farger)
        # Komplettera med vit om listan är kortare än positions
        while len(farglista) < len(positions):
            farglista.append("#FFFFFF")

    for (x, y), hex_farg in zip(positions, farglista):
        r, g, b = hex_till_rgb(hex_farg)
        c.setStrokeColorRGB(r, g, b)
        c.setFillColorRGB(r, g, b)
        c.rect(x - bleed, y - bleed,
               card_w + 2 * bleed, card_h + 2 * bleed,
               stroke=0, fill=1)
    c.save()


def imponera_sida(kort_sidor, positions, sheet_w, sheet_h, marks_page,
                  bg_pages=None, ar_textsida=False):
    """Skapa en ark-sida: bakgrundsruta (bleed) → kort → skärmärken.

    bg_pages är en tupel (bg_bild, bg_text) av PDF-sidor som har de
    färgade bakgrundsrektanglarna ritade. Använd bg_text för textsidor
    (ringer in med bakgrund_color) och bg_bild för bildsidor (bakskede).
    """
    sheet = PageObject.create_blank_page(width=sheet_w, height=sheet_h)

    # Lägg bakgrunden FÖRST så kort hamnar ovanpå
    if bg_pages:
        bg = bg_pages[1] if ar_textsida else bg_pages[0]
        if bg is not None:
            sheet.merge_page(bg)

    # Placera kort exakt på trim — ingen skalning, ingen text-distorsion
    for kort_page, (x, y) in zip(kort_sidor, positions):
        sheet.merge_translated_page(kort_page, x, y)

    if marks_page is not None:
        sheet.merge_page(marks_page)
    return sheet


def behandla_fil(kombinerad_path, ut_mapp, marks_cache):
    """Producera tryckark för en kombinerad PDF. Returnerar lista av ark-sidor."""
    filnamn = os.path.basename(kombinerad_path)
    print(f"\n{filnamn}")

    reader = PdfReader(kombinerad_path)
    sidor = list(reader.pages)

    if len(sidor) == 0:
        print("  (tom, hoppar)")
        return []

    if len(sidor) % 2 != 0:
        print(f"  VARNING: {len(sidor)} sidor (ojämnt), förväntat bild+text-par")
        return []

    bildsidor = sidor[0::2]
    textsidor = sidor[1::2]

    # Läs kortdimensioner från första bildsidan
    p0 = bildsidor[0]
    card_w = float(p0.mediabox.width)
    card_h = float(p0.mediabox.height)
    print(f"  Kortstorlek: {card_w/MM:.1f}×{card_h/MM:.1f} mm")

    layout = berakna_layout(card_w, card_h)
    if layout is None:
        print(f"  FEL: kortet är för stort för {SHEET_WIDTH_MM}×{SHEET_HEIGHT_MM} mm")
        return []

    kort_per_ark = layout["cols"] * layout["rows"]
    n_ark = math.ceil(len(bildsidor) / kort_per_ark)
    print(f"  Layout: {layout['cols']}×{layout['rows']} = {kort_per_ark} kort/ark, {n_ark} ark")

    # Skärmärken (cachas per kortstorlek)
    cache_nyckel = (card_w, card_h)
    if cache_nyckel not in marks_cache:
        marks_tmp = os.path.join(ut_mapp, f"_temp_crop_{int(card_w)}x{int(card_h)}.pdf")
        skapa_skarmarken_pdf(
            marks_tmp,
            layout["positions_fram"],
            card_w, card_h,
            layout["sheet_w"], layout["sheet_h"]
        )
        marks_reader = PdfReader(marks_tmp)
        marks_cache[cache_nyckel] = (marks_reader.pages[0], marks_tmp)
    marks_page, marks_tmp = marks_cache[cache_nyckel]

    # Läs per-kort-bakgrunder från CSV. För kort med samma bakgrundsfärg
    # blir alla färglista-element identiska. För PU_projekt (olika färg per
    # fastighetstyp) får varje kort sin egen färg.
    csv_path = hitta_csv_for_kombinerad(kombinerad_path)
    bild_data, text_data = las_kortdata_fran_csv(csv_path)
    if csv_path:
        print(f"  CSV: {os.path.basename(csv_path)} ({len(bild_data)} rader)")
    else:
        print(f"  CSV: saknas — ingen bleed-bakgrund kommer ritas")

    # Bygg ark-sidor — bakgrund per ark beräknas dynamiskt baserat på
    # vilka CSV-rader (= kort) som ligger på just det arket.
    ark_sidor = []
    for s in range(n_ark):
        start = s * kort_per_ark
        slut  = min(start + kort_per_ark, len(bildsidor))

        bg_pages = (None, None)
        if BLEED_MM > 0:
            # Hämta bakskede per kort på framsidan, bakgrund_color per kort på textsidan
            bsk_lista = [bild_data[start + i]["bsk"] if start + i < len(bild_data) else "#FFFFFF"
                         for i in range(slut - start)]
            bg_lista  = [text_data[start + i]["bg"] if start + i < len(text_data) else "#FFFFFF"
                         for i in range(slut - start)]

            bg_bild_path = os.path.join(ut_mapp, f"_temp_bg_bild_{int(card_w)}x{int(card_h)}_s{s}.pdf")
            bg_text_path = os.path.join(ut_mapp, f"_temp_bg_text_{int(card_w)}x{int(card_h)}_s{s}.pdf")
            skapa_bleed_bakgrund_pdf(
                bg_bild_path, layout["positions_fram"][:slut - start],
                card_w, card_h, layout["sheet_w"], layout["sheet_h"],
                bsk_lista
            )
            skapa_bleed_bakgrund_pdf(
                bg_text_path, layout["positions_bak"][:slut - start],
                card_w, card_h, layout["sheet_w"], layout["sheet_h"],
                bg_lista
            )
            bg_bild = PdfReader(bg_bild_path).pages[0]
            bg_text = PdfReader(bg_text_path).pages[0]
            bg_pages = (bg_bild, bg_text)

        fram = imponera_sida(
            bildsidor[start:slut],
            layout["positions_fram"][:slut - start],
            layout["sheet_w"], layout["sheet_h"],
            marks_page,
            bg_pages=bg_pages,
            ar_textsida=False,
        )
        bak = imponera_sida(
            textsidor[start:slut],
            layout["positions_bak"][:slut - start],
            layout["sheet_w"], layout["sheet_h"],
            marks_page,
            bg_pages=bg_pages,
            ar_textsida=True,
        )
        ark_sidor.append(fram)
        ark_sidor.append(bak)

    ut_namn = filnamn.replace("_kombinerad", "_tryck")
    ut_path = os.path.join(ut_mapp, ut_namn)
    w = PdfWriter()
    for p in ark_sidor:
        w.add_page(p)
    with open(ut_path, "wb") as f:
        w.write(f)
    print(f"  -> {ut_namn} ({len(ark_sidor)} sidor)")

    return ark_sidor


def fas_sort_key(filnamn):
    fn = os.path.basename(filnamn).upper()
    ordning = ["L_", "PU_", "PL_", "GF_", "F_"]
    for i, p in enumerate(ordning):
        if fn.startswith(p):
            return (i, fn)
    return (len(ordning), fn)


def main(pdf_mapp):
    global SPELET2_ROT
    pdf_mapp = os.path.abspath(pdf_mapp).rstrip("\\/")
    SPELET2_ROT = os.path.dirname(pdf_mapp)
    print(f"PDF-mapp: {pdf_mapp}")
    print(f"SPELET2-rot: {SPELET2_ROT}")
    print(f"Bleed (bakgrundsruta): {BLEED_MM} mm")

    in_mapp = os.path.join(pdf_mapp, "Kombinerade")
    ut_mapp = os.path.join(pdf_mapp, "Tryckbara")
    if not os.path.isdir(in_mapp):
        print(f"FEL: hittar inte {in_mapp}")
        return
    os.makedirs(ut_mapp, exist_ok=True)

    alla_filer = [os.path.join(in_mapp, f) for f in os.listdir(in_mapp)
                  if f.lower().endswith(".pdf") and "_kombinerad" in f.lower()]
    alla_filer.sort(key=fas_sort_key)

    if not alla_filer:
        print(f"Inga _kombinerad-PDF:er i {in_mapp}")
        return

    print(f"\nHittade {len(alla_filer)} kombinerade PDF:er")

    marks_cache = {}
    master_writer = PdfWriter()
    for fil in alla_filer:
        ark_sidor = behandla_fil(fil, ut_mapp, marks_cache)
        for p in ark_sidor:
            master_writer.add_page(p)

    master_path = os.path.join(ut_mapp, "MASTER_tryck.pdf")
    with open(master_path, "wb") as f:
        master_writer.write(f)
    print(f"\nKlart! MASTER: {master_path} ({len(master_writer.pages)} sidor)")

    for v in marks_cache.values():
        try:
            os.remove(v[1])
        except OSError:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        skript_mapp = os.path.dirname(os.path.abspath(__file__))
        pdf_default = os.path.join(skript_mapp, "PDF")
        if os.path.isdir(pdf_default):
            main(pdf_default)
        else:
            print("Ange PDF-mappen som argument")
            sys.exit(1)
    else:
        main(sys.argv[1])

