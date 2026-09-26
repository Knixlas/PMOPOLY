"""Klistermärken till det tryckta PU-brädet (Skede 1).

Rättar de tre grafiska felen på PU_spelbrade2.pdf (se OMSTART.md 5e):
  1. Stadshuset: "TA BY ÅTERLÄMNA PROJEKT" → "BYT".
  2. Lokal-rutan före Skönhetsrådet saknar bild → samma bild som den nedre lokal-rutan, vänd 180°.
  3. Högplatsen "Lokal" finns två gånger, "Förskola" saknas → en förskoleplats (88×146 mm)
     att klistra på den nedre vänstra lokal-platsen.

Märkena ritas från brädets egen grafik (vektor + originalbilder) och med brädets inbäddade
Bahnschrift-subset, så de ser ut som trycket. Utdata: tryck/ut/klistermarken_PU.pdf, ett
märke per sida i skala 1:1 med 3 mm utfall och skärmärken, plus en kontrollbild av brädet
med märkena på plats (tryck/ut/PU_brade_med_klistermarken.png).

    python tryck/bygg_klistermarken.py
"""
import io
from pathlib import Path

import numpy as np
import pymupdf as fitz
from PIL import Image

HAR = Path(__file__).parent
BRADE = HAR / "brada" / "PU_spelbrade2.pdf"
UT = HAR / "ut"

MM = 72 / 25.4
UTFALL, MARK = 3 * MM, 5 * MM          # samma som bygg_tryck.py
FONT_XREF = 154                        # GIFOMG+Bahnschrift i PU-brädet
TEXTFARG = (0x2F / 255, 0x3D / 255, 0x44 / 255)

# Bilder i brädet (xref): kvadratrutornas hexagonbilder och högplatsernas bilder.
BILD_LOKAL, BILD_FORSKOLA, HOG_LOKAL = 277, 264, 272
FORSKOLA_BG = (235, 236, 213)          # förskolerutans bakgrund
FORSKOLA_MORK = (63, 74, 31)           # förskolerutans namnlist
LIST_Y = 1712                          # högplatsbildens bruna list börjar på denna pixelrad (av 1725)


def ta_bort_text(sida, spann):
    """Ta bort enskilda textspann utan att röra bilder och grafik under."""
    for s in spann:
        for c in s["chars"]:
            x0, y0, x1, y1 = c["bbox"]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            sida.add_redact_annot(fitz.Rect(mx - 0.5, my - 0.5, mx + 0.5, my + 0.5), fill=False)
    sida.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)


def spann_med(sida, text, klipp=None):
    ut = []
    for b in sida.get_text("rawdict", clip=klipp)["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if "".join(c["c"] for c in s["chars"]).strip() == text:
                    s["dir"] = l["dir"]
                    ut.append(s)
    return ut


def ratta_stadshuset(sida, font, fontbuf):
    """BY → BYT, centrerat på samma punkt och i samma 45°-riktning."""
    (s,) = spann_med(sida, "BY", fitz.Rect(100, 1740, 260, 1900))
    ox, oy = s["origin"]
    dx, dy = s["dir"]
    storlek = s["size"]
    forskj = (font.text_length("BYT", storlek) - font.text_length("BY", storlek)) / 2
    start = fitz.Point(ox - forskj * dx, oy - forskj * dy)
    ta_bort_text(sida, [s])
    sida.insert_font(fontname="bahn", fontbuffer=fontbuf)   # efter redigeringen
    vinkel = -45 if dy > 0 else 45
    sida.insert_text(start, "BYT", fontname="bahn", fontsize=storlek, color=TEXTFARG,
                     morph=(start, fitz.Matrix(vinkel)))


def lagg_lokalbild(sida):
    """Den övre lokal-rutan (rad 1, före Skönhetsrådet) får lokalbilden vänd 180°, som grannarna."""
    sida.insert_image(fitz.Rect(1437.24, 98.26, 1588.24, 249.26), xref=BILD_LOKAL, rotate=180)


def forskola_hog(dok):
    """Förskoleplatsen byggd av lokal-platsens bild: ny färg, förskolebild, rubrik läggs som text."""
    org = np.asarray(Image.open(io.BytesIO(dok.extract_image(HOG_LOKAL)["image"])).convert("RGB")).astype(int)
    lokal_bg = np.array([241, 227, 198])
    ny = org + (np.array(FORSKOLA_BG) - lokal_bg)          # flytta bakgrundstonen
    ny[LIST_Y:] = org[LIST_Y:]                               # brun list i nederkant som på alla platser
    k = 5                                                    # originalet har en vit kant på 1–4 px
    ny[:k], ny[-k:] = ny[k], ny[-k - 1]
    ny[:, :k], ny[:, -k:] = ny[:, k:k + 1], ny[:, -k - 1:-k]
    ny = np.clip(ny, 0, 255).astype(np.uint8)
    bild = Image.fromarray(ny)
    bg = Image.new("RGB", (1, 1), FORSKOLA_BG)
    bild.paste(bg.resize((300, 110)), (25, 130))            # gammal rubrik bort
    bild.paste(bg.resize((620, 520)), (210, 505))           # gammal hexagon bort
    # förskolebilden i samma skala och läge som lokalbilden (masken 611×529 → 560×485 px)
    hex_ = Image.open(io.BytesIO(dok.extract_image(BILD_FORSKOLA)["image"])).convert("RGB")
    mask = fitz.Pixmap(dok, dok.extract_image(BILD_FORSKOLA)["smask"])
    mask = Image.frombytes("L", (mask.w, mask.h), mask.samples)
    skala = 560 / 611
    s = round(630 * skala)
    x, y = round(240 - 9 * skala), round(525 - 50 * skala)
    bild.paste(hex_.resize((s, s), Image.LANCZOS), (x, y), mask.resize((s, s), Image.LANCZOS))
    buf = io.BytesIO()
    bild.save(buf, "JPEG", quality=95)
    return buf.getvalue(), bild.size


def markessida(ut, b, h, rita):
    """En sida: märket b×h pt med utfall och skärmärken. rita(sida, rect_med_utfall)."""
    W, H = b + 2 * (MARK + UTFALL), h + 2 * (MARK + UTFALL)
    sida = ut.new_page(width=W, height=H)
    rita(sida, fitz.Rect(MARK, MARK, W - MARK, H - MARK))
    x0, y0, x1, y1 = MARK + UTFALL, MARK + UTFALL, W - MARK - UTFALL, H - MARK - UTFALL
    for x in (x0, x1):
        sida.draw_line((x, 0), (x, MARK), width=0.35)
        sida.draw_line((x, H - MARK), (x, H), width=0.35)
    for y in (y0, y1):
        sida.draw_line((0, y), (MARK, y), width=0.35)
        sida.draw_line((W - MARK, y), (W, y), width=0.35)
    return sida


def text(sida, rad):
    """Etikett i marginalen (utanför skärmärket), radbruten vid behov."""
    sida.insert_textbox(fitz.Rect(MARK + UTFALL + 2, 1, sida.rect.width - MARK, MARK + UTFALL - 1), rad,
                        fontsize=4.5, color=(0, 0, 0))


def main():
    UT.mkdir(exist_ok=True)
    dok = fitz.open(BRADE)
    sida = dok[0]
    fontbuf = dok.extract_font(FONT_XREF)[3]
    font = fitz.Font(fontbuffer=fontbuf)

    ratta_stadshuset(sida, font, fontbuf)
    lagg_lokalbild(sida)
    fsk, (pw, ph) = forskola_hog(dok)

    # Rättat bräde (inte för tryck, som mall och kontroll)
    ut = fitz.open()
    # 1. Stadshuset: textblocket, vridet så att texten ligger vågrätt; märket klistras i 45°.
    blockmitt = fitz.Point(170, 1812)
    k = 60                                             # halv sida av källrutan
    mellan = fitz.open()
    m = mellan.new_page(width=2 * k * 1.4142, height=2 * k * 1.4142)
    m.show_pdf_page(m.rect, dok, 0, clip=fitz.Rect(blockmitt.x - k, blockmitt.y - k,
                                                    blockmitt.x + k, blockmitt.y + k), rotate=45)
    mm_ = m.rect.width / 2
    b1, h1 = 78, 62                                    # märkets storlek i pt (≈ 27,5 × 22 mm)

    def rita1(s, r):
        s.show_pdf_page(r, mellan, 0, clip=fitz.Rect(mm_ - b1 / 2 - UTFALL, mm_ - h1 / 2 - UTFALL,
                                                     mm_ + b1 / 2 + UTFALL, mm_ + h1 / 2 + UTFALL))
    s1 = markessida(ut, b1, h1, rita1)
    text(s1, "PU 1 · Stadshuset, BYT. Klistras i 45° över textblocket.")

    # 2. Lokal-rutans bildyta (rad 1, före Skönhetsrådet)
    ruta = fitz.Rect(1384.24, 88, 1643.97, 256.49)     # hela rutans bildyta, kant i kant

    def rita2(s, r):
        s.show_pdf_page(r, dok, 0, clip=ruta + (-UTFALL, -UTFALL, UTFALL, UTFALL))
    s2 = markessida(ut, ruta.width, ruta.height, rita2)
    text(s2, "PU 2 · Lokal-rutan före Skönhetsrådet: hela bildytan, kant i kant mot namnlisten.")

    # 3. Förskoleplatsen, 88 × 146 mm (stående; klistras på den liggande nedre vänstra lokal-platsen)
    b3, h3 = 249.48, 413.88

    def rita3(s, r):
        # bilden sträcks inte: utfallet fylls med kantfärgen
        s.draw_rect(r, color=None, fill=tuple(c / 255 for c in FORSKOLA_BG))
        inne = fitz.Rect(r.x0 + UTFALL, r.y0 + UTFALL, r.x1 - UTFALL, r.y1 - UTFALL)
        s.draw_rect(fitz.Rect(r.x0, inne.y1 - (ph - LIST_Y) / ph * h3, r.x1, r.y1), color=None,
                    fill=(123 / 255, 79 / 255, 32 / 255))
        s.insert_image(inne, stream=fsk)
        s.insert_font(fontname="bahn", fontbuffer=fontbuf)
        skala = h3 / ph
        s.insert_text((inne.x0 + 40 * skala, inne.y0 + 214 * skala), "FÖRSKOLA", fontname="bahn",
                      fontsize=66 * skala / 0.7, color=tuple(c / 255 for c in FORSKOLA_MORK))
    s3 = markessida(ut, b3, h3, rita3)
    text(s3, "PU 3 · Högplats FÖRSKOLA, 88 × 146 mm. Över den nedre vänstra LOKAL-platsen.")

    # Kontrollbräde: förskoleplatsen på plats (vriden som den ursprungliga platsen)
    kontroll = fitz.open()
    kontroll.insert_pdf(dok)
    kp = kontroll[0]
    kp.show_pdf_page(fitz.Rect(422.09, 1343.37, 835.97, 1592.85), ut, 2,
                     clip=fitz.Rect(MARK + UTFALL, MARK + UTFALL, MARK + UTFALL + b3, MARK + UTFALL + h3),
                     rotate=90)
    kp.get_pixmap(dpi=40).save(UT / "PU_brade_med_klistermarken.png")

    ut.save(UT / "klistermarken_PU.pdf", garbage=4, deflate=True)
    print(f"{len(ut)} märken → {UT / 'klistermarken_PU.pdf'}")


if __name__ == "__main__":
    main()
