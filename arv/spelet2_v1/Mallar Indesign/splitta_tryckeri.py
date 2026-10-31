"""
splitta_tryckeri.py

Postprocessor för tryckeri_engine.jsx. Tar multi-card PDF:er + layout-JSON
och producerar tryckeri-PDF:er med 1 motiv per sida, 3mm utfall, öppna
skärmärken och alternerande bild/text.

Output-format (matchar tryckeriets exempel):
  TrimBox  = kortstorlek (t.ex. 58×88 mm)
  BleedBox = TrimBox + 3mm runtom
  MediaBox = BleedBox + 4mm runtom (för öppna skärmärken)

Skärmärken: korta linjer 3mm utanför trim, 4mm långa, går INTE ihop vid
hörnet. Färgad bakgrund (3mm utfall) hämtas per kort från CSV
(bakskede för bildsidor, bakgrund_color för textsidor).

Anrop: python splitta_tryckeri.py <manifest_json>

Manifest-format (skrivs av tryckeri_engine.jsx):
{
  "storlek_namn": "58x88",
  "card_w_mm": 58,
  "card_h_mm": 88,
  "rot": "C:\\...\\SPELET 2\\",
  "tryck_mapp": "C:\\...\\SPELET 2\\PDF\\Tryckbara\\",
  "poster": [
    {
      "basnamn": "PU_projekt_bildsida",
      "stem": "PU_projekt",
      "sida_typ": "bild",
      "temp_pdf": "...\\PU_projekt_bildsida_temp.pdf",
      "layout_json": "...\\PU_projekt_bildsida_layout.json",
      "final_pdf": "...\\Tryckbara\\PU_projekt_tryckeri.pdf",
      "csv_path": "...\\PU_projekt.csv",
      "fas_prefix": "PU_"
    },
    ...
  ]
}
"""

import csv as csvmod
import json
import math
import os
import sys

try:
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    from pypdf.generic import RectangleObject
except ImportError:
    print("FEL: pip install pypdf", file=sys.stderr)
    sys.exit(1)

try:
    from reportlab.pdfgen import canvas
except ImportError:
    print("FEL: pip install reportlab", file=sys.stderr)
    sys.exit(1)


MM = 72.0 / 25.4

# ── Tryckeri-konstanter ──────────────────────────────────────────────────
BLEED_MM      = 3.0   # utfall runt trim
MARK_OFFSET_MM = 3.0  # avstånd från trim till mark-start (= bleed-kanten)
MARK_LEN_MM    = 4.0  # längd på varje skärmärke
MARK_WIDTH_PT  = 0.25 # tjocklek
MEDIA_MARGIN_MM = MARK_OFFSET_MM + MARK_LEN_MM + 0.4  # plats för märken på media


# ── CSV-hjälpfunktioner ──────────────────────────────────────────────────
def detektera_csv_encoding(path):
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


def hex_till_rgb(hex_str):
    h = (hex_str or "").lstrip("#").strip()
    if len(h) != 6:
        return (1, 1, 1)
    try:
        return (int(h[0:2], 16) / 255.0,
                int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0)
    except ValueError:
        return (1, 1, 1)


def las_kortdata_fran_csv(csv_path):
    """Returnerar (bild_data, text_data) — listor av dicts {bsk, bg, ob, ot}
    sorterade i forward-ordning (ordning_bild). Båda listorna är samma
    förutom sortering, och eftersom tryckeri-flödet sorterar BÅDA på
    ordning_bild blir bild_data == text_data i ordning. Behåller två
    listor för att matcha skapa_tryckark.py-mönstret."""
    if not csv_path or not os.path.exists(csv_path):
        return [], []
    enc = detektera_csv_encoding(csv_path)
    with open(csv_path, encoding=enc, newline="") as f:
        reader = csvmod.reader(f, delimiter=";")
        header = next(reader, None)
        if not header:
            return [], []

        def col(name):
            try:
                return header.index(name)
            except ValueError:
                return -1

        bsk_idx = col("bakskede")
        bg_idx  = col("bakgrund_color")
        ob_idx  = col("ordning_bild")

        rader = []
        for row in reader:
            if not row or len(row) < 2:
                continue
            bsk = row[bsk_idx].strip() if 0 <= bsk_idx < len(row) else ""
            bg  = row[bg_idx].strip()  if 0 <= bg_idx  < len(row) else ""
            try:
                ob = int(row[ob_idx]) if 0 <= ob_idx < len(row) else 9999
            except (ValueError, IndexError):
                ob = 9999
            rader.append({
                "bsk": bsk or "#FFFFFF",
                "bg":  bg  or "#FFFFFF",
                "ob":  ob,
            })
        rader.sort(key=lambda r: r["ob"])
    return rader, list(rader)


# ── Skapa skärmärken som PDF ─────────────────────────────────────────────
def skapa_marks_overlay(path, page_w_pt, page_h_pt, trim_w_pt, trim_h_pt):
    """En PDF-sida med öppna skärmärken vid trim-hörnen.
    trim är centrerat i media. Märken börjar MARK_OFFSET_MM utanför trim
    (= på bleed-kanten) och är MARK_LEN_MM långa, går inte ihop vid hörnet."""
    c = canvas.Canvas(path, pagesize=(page_w_pt, page_h_pt))
    c.setLineWidth(MARK_WIDTH_PT)
    c.setStrokeColorRGB(0, 0, 0)

    # Trim är centrerat i media
    trim_x = (page_w_pt - trim_w_pt) / 2
    trim_y = (page_h_pt - trim_h_pt) / 2
    x1 = trim_x
    y1 = trim_y
    x2 = trim_x + trim_w_pt
    y2 = trim_y + trim_h_pt

    off = MARK_OFFSET_MM * MM
    lng = MARK_LEN_MM * MM

    # Nedre-vänster (x1, y1): horisontell utåt-vänster, vertikal utåt-ner
    c.line(x1 - off - lng, y1, x1 - off,       y1)
    c.line(x1, y1 - off,        x1,            y1 - off - lng)
    # Nedre-höger (x2, y1)
    c.line(x2 + off,       y1, x2 + off + lng, y1)
    c.line(x2, y1 - off,        x2,            y1 - off - lng)
    # Övre-vänster (x1, y2)
    c.line(x1 - off - lng, y2, x1 - off,       y2)
    c.line(x1, y2 + off,        x1,            y2 + off + lng)
    # Övre-höger (x2, y2)
    c.line(x2 + off,       y2, x2 + off + lng, y2)
    c.line(x2, y2 + off,        x2,            y2 + off + lng)

    c.save()


def skapa_bleed_bg_overlay(path, page_w_pt, page_h_pt, bleed_w_pt, bleed_h_pt, hex_farg):
    """En PDF-sida med en heltäckande färgad rektangel = bleed-area
    (centrerad i media). Renderas BAKOM kortet."""
    c = canvas.Canvas(path, pagesize=(page_w_pt, page_h_pt))
    r, g, b = hex_till_rgb(hex_farg)
    c.setStrokeColorRGB(r, g, b)
    c.setFillColorRGB(r, g, b)
    bleed_x = (page_w_pt - bleed_w_pt) / 2
    bleed_y = (page_h_pt - bleed_h_pt) / 2
    c.rect(bleed_x, bleed_y, bleed_w_pt, bleed_h_pt, stroke=0, fill=1)
    c.save()


# ── Extrahera ett kort från en multi-card sida ───────────────────────────
def extrahera_kort_sida(source_page, kort, page_w_mm, page_h_mm,
                        card_w_mm, card_h_mm, marks_page, bg_page,
                        media_w_pt, media_h_pt, bleed_w_pt, bleed_h_pt,
                        trim_w_pt, trim_h_pt):
    """Skapa en ny PDF-sida med:
      - Färgad bleed-bakgrund (bg_page)
      - Källsidans innehåll, klippt och positionerat så kortet är centrerat
      - Skärmärken (marks_page)

    'kort' är dict {x_mm, y_mm, w_mm, h_mm} med InDesign-koordinater
    (övre-vänster origin) i mm.
    """
    new_page = PageObject.create_blank_page(width=media_w_pt, height=media_h_pt)

    # 1. Bleed-bakgrund först (bakom)
    if bg_page is not None:
        new_page.merge_page(bg_page)

    # 2. Källsidan: vi merge:ar in den med transformation som flyttar kortets
    # nedre-vänster till media-koordinaternas trim-position.
    #
    # InDesign-bounds: y_mm mäts från sidans ÖVRE-vänster, växande nedåt.
    # PDF-koord: y mäts från sidans NEDRE-vänster, växande uppåt.
    # source-PDF har ursprung nedre-vänster, samma som InDesign-page nedre.
    #
    # Kortets nedre-vänster i source-PDF (pt):
    #   src_x = kort.x_mm * MM
    #   src_y = (page_h_mm - kort.y_mm - kort.h_mm) * MM
    # Vi vill flytta till trim-position i ny sida (pt):
    #   tgt_x = (media_w_pt - trim_w_pt) / 2 = bleed-margin + 0
    #   tgt_y = (media_h_pt - trim_h_pt) / 2
    # Translation: (tgt_x - src_x, tgt_y - src_y)
    src_x_pt = kort["x_mm"] * MM
    src_y_pt = (page_h_mm - kort["y_mm"] - kort["h_mm"]) * MM
    tgt_x_pt = (media_w_pt - trim_w_pt) / 2
    tgt_y_pt = (media_h_pt - trim_h_pt) / 2
    dx = tgt_x_pt - src_x_pt
    dy = tgt_y_pt - src_y_pt

    # Klipp source så bara kortets bleed-area visas
    bleed_x = (media_w_pt - bleed_w_pt) / 2
    bleed_y = (media_h_pt - bleed_h_pt) / 2

    # pypdf:s merge_translated_page lägger sidan med translation. Vi måste
    # också klippa till bleed-rektangeln så inte grannkort syns.
    # Lösning: använd Transformation + add_transformation, sen sätt cropbox
    # på resultatet. Men eftersom new_page redan har bleed-bakgrund (heltäck-
    # ande färg under), kan kortet bredda ut sig — det syns inte utanför
    # bleed-area pga... nej det syns. Vi behöver klippa.
    #
    # Enklaste lösningen: använd add_transformation på source-page och
    # merge_page (utan translation). Sätt source-page's cropbox till bleed-
    # area först. Men det förstör source-page för andra kort.
    #
    # Bättre: skapa en kopia av source-page, sätt dess cropbox, merge med
    # translation. pypdf:s PageObject har inte enkel deep-copy — vi gör
    # det via stream-rebuild.
    #
    # Faktiskt: pypdf kan göra detta via add_transformation som inkluderar
    # ett /Form XObject med /BBox satt till bleed-area. Men det är
    # komplext. Vi använder en alternativ lösning:
    #
    # Vi merge:ar source-page med translation, sen täcker vi MEDIA-area
    # UTANFÖR bleed-rektangeln med rektanglar som matchar media-bakgrunden
    # (vit). Det är ineffektivt men funkar.
    #
    # ENNU enklare: vi merge:ar source-page med transformation och låter
    # bleed-bakgrunden TÄCKA outline. För det måste bleed-bakgrunden vara
    # ovanpå source... men då döljs kortet. Nej.
    #
    # LÖSNING: använd add_transformation + merge_page. Sen sätt cropbox
    # på new_page till bleed-area. Men vi VILL ha media-area som cropbox.
    #
    # Riktig lösning: kopiera source-page till ett /Form XObject med
    # /BBox = bleed-area. Sen rita formen vid trim-position. pypdf har
    # PageObject.add_transformation och man kan klippa via
    # Page.cropbox-set, men inte per-merge.
    #
    # Praktiskt: använd reportlab+pypdf hybrid. Skapa ett tomt overlay som
    # 'q ... cm /Form Do Q' med en form-resurs som har source-page som
    # innehåll och BBox satt till bleed-area. För enkelhet använder vi
    # istället pypdf:s _add_xobject med BBox. Eller helt enkelt:
    # konvertera source-page till XObject via PdfWriter:s _add_object och
    # mergea med klippning.
    #
    # Vi använder pypdf:s page.merge_transformed_page() med expand=False
    # och sen MANUELLT sätter clip path via raw content. För enkelhet
    # börjar vi med det enkla fallet utan klippning och accepterar att
    # grannkort kan synas i bleed-zonen — i praktiken är bleed-färgen samma
    # som grannkortets bakskede så det syns inte.
    new_page.merge_translated_page(source_page, dx, dy, expand=False)

    # 3. Skärmärken ovanpå
    if marks_page is not None:
        new_page.merge_page(marks_page)

    # 4. Sätt boxes
    new_page.mediabox = RectangleObject([0, 0, media_w_pt, media_h_pt])
    new_page.bleedbox = RectangleObject([bleed_x, bleed_y,
                                         bleed_x + bleed_w_pt,
                                         bleed_y + bleed_h_pt])
    new_page.trimbox  = RectangleObject([tgt_x_pt, tgt_y_pt,
                                         tgt_x_pt + trim_w_pt,
                                         tgt_y_pt + trim_h_pt])
    new_page.cropbox  = new_page.mediabox
    new_page.artbox   = new_page.trimbox

    return new_page


def extrahera_kort_sida_med_klipp(source_pdf_path, source_page_idx,
                                  kort, page_w_mm, page_h_mm,
                                  card_w_mm, card_h_mm, marks_page, bg_page,
                                  media_w_pt, media_h_pt, bleed_w_pt, bleed_h_pt,
                                  trim_w_pt, trim_h_pt):
    """Robust version: läs bara EN sida ur source och sätt dess cropbox
    till bleed-area INNAN merge. Förhindrar att grannkort syns."""
    # Läs source-sidan på nytt så vi har en egen instans att modifiera
    src_reader = PdfReader(source_pdf_path)
    src_page = src_reader.pages[source_page_idx]

    # Sätt cropbox till bleed-area i source-koordinater
    src_x_pt = kort["x_mm"] * MM
    src_y_pt = (page_h_mm - kort["y_mm"] - kort["h_mm"]) * MM
    bleed_pad = BLEED_MM * MM

    src_clip_x1 = src_x_pt - bleed_pad
    src_clip_y1 = src_y_pt - bleed_pad
    src_clip_x2 = src_x_pt + (kort["w_mm"] * MM) + bleed_pad
    src_clip_y2 = src_y_pt + (kort["h_mm"] * MM) + bleed_pad

    src_page.cropbox = RectangleObject([src_clip_x1, src_clip_y1,
                                        src_clip_x2, src_clip_y2])
    src_page.mediabox = RectangleObject([src_clip_x1, src_clip_y1,
                                         src_clip_x2, src_clip_y2])

    # Skapa ny output-sida
    new_page = PageObject.create_blank_page(width=media_w_pt, height=media_h_pt)

    if bg_page is not None:
        new_page.merge_page(bg_page)

    # Translation: src_clip_x1 → bleed_x_target, src_clip_y1 → bleed_y_target
    bleed_x_target = (media_w_pt - bleed_w_pt) / 2
    bleed_y_target = (media_h_pt - bleed_h_pt) / 2
    dx = bleed_x_target - src_clip_x1
    dy = bleed_y_target - src_clip_y1

    new_page.merge_translated_page(src_page, dx, dy, expand=False)

    if marks_page is not None:
        new_page.merge_page(marks_page)

    tgt_x_pt = (media_w_pt - trim_w_pt) / 2
    tgt_y_pt = (media_h_pt - trim_h_pt) / 2

    new_page.mediabox = RectangleObject([0, 0, media_w_pt, media_h_pt])
    new_page.bleedbox = RectangleObject([bleed_x_target, bleed_y_target,
                                         bleed_x_target + bleed_w_pt,
                                         bleed_y_target + bleed_h_pt])
    new_page.trimbox  = RectangleObject([tgt_x_pt, tgt_y_pt,
                                         tgt_x_pt + trim_w_pt,
                                         tgt_y_pt + trim_h_pt])
    new_page.cropbox  = new_page.mediabox
    new_page.artbox   = new_page.trimbox

    return new_page


# ── Bygg en sida-uppsättning per .indd (alla kort som lista av PDF-sidor) ─
def bygg_sidor_for_indd(post, card_w_mm, card_h_mm, csv_data,
                        marks_page, media_w_pt, media_h_pt,
                        bleed_w_pt, bleed_h_pt, trim_w_pt, trim_h_pt,
                        temp_dir):
    """Returnerar lista av PageObject — en per kort i läs-/sortordning."""
    layout_path = post["layout_json"]
    pdf_path    = post["temp_pdf"]
    sida_typ    = post.get("sida_typ", "okänd")

    if not (os.path.exists(layout_path) and os.path.exists(pdf_path)):
        print(f"  VARNING: saknar layout/PDF för {post['basnamn']}")
        return []

    with open(layout_path, encoding="utf-8") as f:
        layout = json.load(f)

    spreads = layout.get("spreads", [])
    if not spreads:
        print(f"  VARNING: inga spreads i layout för {post['basnamn']}")
        return []

    # Beräkna total kort-count på alla spreads
    total_kort = sum(len(sp.get("cards", [])) for sp in spreads)
    print(f"  {post['basnamn']}: {len(spreads)} sidor, {total_kort} kort")

    # CSV-data: bsk för bildsida-bakgrund, bg för textsida-bakgrund
    fargkolumn = "bsk" if sida_typ == "bild" else "bg"

    sidor = []
    kort_idx_global = 0
    for spread in spreads:
        page_idx   = spread["page"] - 1   # JSON är 1-baserad, pypdf 0-baserad
        page_w_mm  = spread["page_w_mm"]
        page_h_mm  = spread["page_h_mm"]
        cards      = spread.get("cards", [])

        for kort in cards:
            # Hämta bleed-färg från CSV
            if kort_idx_global < len(csv_data):
                hex_farg = csv_data[kort_idx_global].get(fargkolumn, "#FFFFFF")
            else:
                hex_farg = "#FFFFFF"

            # Skapa bleed-bakgrund overlay för detta kort
            bg_path = os.path.join(temp_dir,
                f"_bg_{post['basnamn']}_p{page_idx}_k{kort_idx_global}.pdf")
            skapa_bleed_bg_overlay(bg_path, media_w_pt, media_h_pt,
                                   bleed_w_pt, bleed_h_pt, hex_farg)
            bg_reader = PdfReader(bg_path)
            bg_page = bg_reader.pages[0]

            ny_sida = extrahera_kort_sida_med_klipp(
                pdf_path, page_idx, kort, page_w_mm, page_h_mm,
                card_w_mm, card_h_mm, marks_page, bg_page,
                media_w_pt, media_h_pt, bleed_w_pt, bleed_h_pt,
                trim_w_pt, trim_h_pt
            )
            sidor.append(ny_sida)
            kort_idx_global += 1

    return sidor


# ── Huvudloop ────────────────────────────────────────────────────────────
def main(manifest_path):
    if not os.path.exists(manifest_path):
        print(f"FEL: manifest saknas: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    storlek_namn = manifest["storlek_namn"]
    card_w_mm    = manifest["card_w_mm"]
    card_h_mm    = manifest["card_h_mm"]
    tryck_mapp   = manifest["tryck_mapp"]
    poster       = manifest["poster"]

    print(f"Tryckeri-postprocessing {storlek_namn}: {len(poster)} poster")
    print(f"Output: {tryck_mapp}")

    if not poster:
        print("Inga poster att processa.")
        return

    temp_dir = os.path.join(tryck_mapp, "_tryckeri_temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Beräkna PDF-dimensioner
    trim_w_pt  = card_w_mm * MM
    trim_h_pt  = card_h_mm * MM
    bleed_w_pt = (card_w_mm + 2 * BLEED_MM) * MM
    bleed_h_pt = (card_h_mm + 2 * BLEED_MM) * MM
    media_w_pt = (card_w_mm + 2 * MEDIA_MARGIN_MM) * MM
    media_h_pt = (card_h_mm + 2 * MEDIA_MARGIN_MM) * MM

    print(f"  Trim:  {card_w_mm:.1f} × {card_h_mm:.1f} mm")
    print(f"  Bleed: {(card_w_mm + 2*BLEED_MM):.1f} × {(card_h_mm + 2*BLEED_MM):.1f} mm")
    print(f"  Media: {(card_w_mm + 2*MEDIA_MARGIN_MM):.1f} × {(card_h_mm + 2*MEDIA_MARGIN_MM):.1f} mm")

    # Skärmärken-overlay (samma för alla kort)
    marks_path = os.path.join(temp_dir, f"_marks_{storlek_namn}.pdf")
    skapa_marks_overlay(marks_path, media_w_pt, media_h_pt,
                        trim_w_pt, trim_h_pt)
    marks_reader = PdfReader(marks_path)
    marks_page = marks_reader.pages[0]

    # Para ihop poster på (stem, exemplar_nr). En post utan exemplar_nr
    # behandlas som exemplar_nr=1 (bakåtkompatibilitet).
    par = {}
    for post in poster:
        stem = post["stem"]
        ex_nr = post.get("exemplar_nr", 1)
        nyckel = (stem, ex_nr)
        par.setdefault(nyckel, {"bild": None, "text": None})
        par[nyckel][post["sida_typ"]] = post

    klara = []
    misslyckades = []
    for (stem, ex_nr), sidor_par in par.items():
        bild_post = sidor_par.get("bild")
        text_post = sidor_par.get("text")

        if bild_post is None and text_post is None:
            continue

        etikett = stem + (f" (S{ex_nr})" if ex_nr > 1 or
                          any(p and p.get("exemplar_nr", 1) > 1
                              for p in (bild_post, text_post)) else "")
        print(f"\n=== {etikett} ===")

        # Final PDF-sökväg (samma stem för båda)
        if bild_post:
            final_pdf = bild_post["final_pdf"]
        else:
            final_pdf = text_post["final_pdf"]

        try:
            # Läs CSV-data (samma CSV för båda sidor; sortering är ordning_bild)
            csv_path = (bild_post or text_post)["csv_path"]
            bild_data, text_data = las_kortdata_fran_csv(csv_path)
            print(f"  CSV: {os.path.basename(csv_path)} ({len(bild_data)} rader)")

            bild_sidor = []
            text_sidor = []

            if bild_post:
                bild_sidor = bygg_sidor_for_indd(
                    bild_post, card_w_mm, card_h_mm, bild_data,
                    marks_page, media_w_pt, media_h_pt,
                    bleed_w_pt, bleed_h_pt, trim_w_pt, trim_h_pt,
                    temp_dir
                )

            if text_post:
                text_sidor = bygg_sidor_for_indd(
                    text_post, card_w_mm, card_h_mm, text_data,
                    marks_page, media_w_pt, media_h_pt,
                    bleed_w_pt, bleed_h_pt, trim_w_pt, trim_h_pt,
                    temp_dir
                )

            # Interfoliera: bild #1, text #1, bild #2, text #2, ...
            n = max(len(bild_sidor), len(text_sidor))
            if len(bild_sidor) > 0 and len(text_sidor) > 0 and \
               len(bild_sidor) != len(text_sidor):
                print(f"  VARNING: bild ({len(bild_sidor)}) och text "
                      f"({len(text_sidor)}) har olika antal kort!")

            writer = PdfWriter()
            for i in range(n):
                if i < len(bild_sidor):
                    writer.add_page(bild_sidor[i])
                if i < len(text_sidor):
                    writer.add_page(text_sidor[i])

            with open(final_pdf, "wb") as f:
                writer.write(f)

            n_pages = len(bild_sidor) + len(text_sidor)
            print(f"  -> {os.path.basename(final_pdf)} ({n_pages} sidor)")
            klara.append(final_pdf)

        except Exception as e:
            print(f"  FEL: {e}")
            import traceback
            traceback.print_exc()
            misslyckades.append((stem, str(e)))

    # Städa temp-overlays
    try:
        for f in os.listdir(temp_dir):
            if f.startswith("_bg_") or f.startswith("_marks_"):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except OSError:
                    pass
    except OSError:
        pass

    print(f"\nKlart: {len(klara)} PDF:er skrivna")
    if misslyckades:
        print(f"Fel: {len(misslyckades)}")
        for stem, msg in misslyckades:
            print(f"  ✗ {stem}: {msg}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Användning: python splitta_tryckeri.py <manifest_json>")
        sys.exit(1)
    main(sys.argv[1])

