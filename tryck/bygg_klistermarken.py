"""Klistermärken till de tryckta brädorna: PU (Skede 1) och F (Förvaltning).

PU: rättar de tre grafiska felen på PU_spelbrade2.pdf (se OMSTART.md 5e):
  1. Stadshuset: "TA BY ÅTERLÄMNA PROJEKT" → "BYT".
  2. Lokal-rutan före Skönhetsrådet saknar bild → samma bild som den nedre lokal-rutan, vänd 180°.
  3. Högplatsen "Lokal" finns två gånger, "Förskola" saknas → en förskoleplats (88×146 mm)
     att klistra på den nedre vänstra lokal-platsen.

F: bygger om F_spelbrade2.pdf med märken, dvs. texter enligt regelboken 9.4 och högplatser
för DD-kort och nätverkskort (se F_TEXTER och F_PLATSER längre ned).

Märkena ritas från brädets egen grafik (vektor + originalbilder) och med brädets inbäddade
Bahnschrift-subset, så de ser ut som trycket. Utdata: tryck/ut/klistermarken_PU.pdf och
klistermarken_F.pdf, ett märke per sida i skala 1:1 med 3 mm utfall och skärmärken, plus
kontrollbilder av brädorna med märkena på plats (tryck/ut/*_brade_med_klistermarken.png).

    python tryck/bygg_klistermarken.py
"""
import io
import math
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


class Bahnschrift:
    """Brädornas inbäddade Bahnschrift-subset. Varje subset har bara tecknen från sitt bräde:
    fet = PU-brädets versaler (rubriker), regular = F-brädets brödtext (DHCODI: gemener, å/ä/ö,
    siffror, skiljetecken, men bara versalerna D och U). Märkenas texter är skrivna inom det.
    Byts mot hela typsnittet när det finns."""
    REGULAR = set("DUabdefghijklmnoprstuvyåäö0123456789-/().: ")

    def __init__(self):
        self.buf = {"V": fitz.open(BRADE).extract_font(FONT_XREF)[3],
                    "G": fitz.open(HAR / "brada" / "F_spelbrade2.pdf").extract_font(187)[3]}
        self.font = {k: fitz.Font(fontbuffer=b) for k, b in self.buf.items()}

    def _bitar(self, text, fet):
        if not fet and set(text) - self.REGULAR:
            raise ValueError(f"tecken saknas i regular-subsetet: {set(text) - self.REGULAR} i {text!r}")
        bitar = []
        for c in text:
            k = "V" if fet and c.isupper() else ("G" if c != " " or not bitar else bitar[-1][0])
            if bitar and bitar[-1][0] == k:
                bitar[-1][1] += c
            else:
                bitar.append([k, c])
        return bitar

    def bredd(self, text, storlek, fet=False):
        return sum(self.font[k].text_length(t, storlek) for k, t in self._bitar(text, fet))

    def skriv(self, sida, punkt, text, storlek, farg, vinkel=0, fet=False):
        """Som insert_text, med valfri vridning kring startpunkten (grader, medurs i sidled)."""
        for k in self.buf:
            sida.insert_font(fontname="bahn" + k, fontbuffer=self.buf[k])
        p = fitz.Point(punkt)
        rad = math.radians(-vinkel)
        riktning = fitz.Point(math.cos(rad), -math.sin(rad)) if vinkel else fitz.Point(1, 0)
        for k, t in self._bitar(text, fet):
            sida.insert_text(p, t, fontname="bahn" + k, fontsize=storlek, color=farg,
                             morph=(p, fitz.Matrix(vinkel)) if vinkel else None)
            p = p + riktning * self.font[k].text_length(t, storlek)


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


def ratta_stadshuset(sida, typ):
    """BY → BYT, centrerat på samma punkt och i samma 45°-riktning."""
    (s,) = spann_med(sida, "BY", fitz.Rect(100, 1740, 260, 1900))
    ox, oy = s["origin"]
    dx, dy = s["dir"]
    storlek = s["size"]
    forskj = (typ.bredd("BYT", storlek, fet=True) - typ.bredd("BY", storlek, fet=True)) / 2
    start = fitz.Point(ox - forskj * dx, oy - forskj * dy)
    ta_bort_text(sida, [s])
    typ.skriv(sida, start, "BYT", storlek, TEXTFARG, vinkel=-45 if dy > 0 else 45, fet=True)


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


def bygg_pu(typ):
    dok = fitz.open(BRADE)
    sida = dok[0]

    ratta_stadshuset(sida, typ)
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
        skala = h3 / ph
        typ.skriv(s, (inne.x0 + 40 * skala, inne.y0 + 214 * skala), "FÖRSKOLA", 66 * skala / 0.7,
                  tuple(c / 255 for c in FORSKOLA_MORK), fet=True)
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


# ---------------------------------------------------------------- F-brädet (Förvaltning)
# F-brädet byggs om med klistermärken: rättade texter enligt regelboken 9.4 och platser för
# de korttyper som saknar plats.

F_BRADE = HAR / "brada" / "F_spelbrade2.pdf"
F_TEXTFARG = (0x55 / 255, 0x53 / 255, 0x4E / 255)
F_ROD = (234, 85, 87)                  # rubrikfärg på F-brädets högplatser
F_MALL = 1050                          # omvärldskortets plats: mall för nya högplatser
KORT_PT = (58 * MM, 88 * MM)

# (märke, gamla rader, nya rader) — regelboken 9.4 steg 1, 3–4 och 7
F_TEXTER = [
    ("F 1 · MARKNAD (steg 1): yieldbanan läggs vid start och flyttar yielden, inga kort dras.",
     ["Dra yieldkort"], ["Uppdatera yielden"]),
    ("F 2 · EKONOMI (steg 3–4): lönekostnaden utgår, personalsteget drar nätverkskort.",
     ["- betala", "lönekostnader"], ["- dra två", "nätverkskort"]),
    ("F 3 · ENERGIUPPGRADERING: språkfel.",
     ["1 fastigheter i kvartal 3"], ["1 fastighet i kvartal 3"]),
]

# (märke, rubrik, underrubrik, bild, plats på brädet (x, y) i pt)
F_PLATSER = [
    ("F 4 · Högplats DD-KORT, 58 × 88 mm. Vänsterkanten under FASTIGHETER.",
     "DD-KORT", "Dras vid köp", "Due Diligence.jpg", (33, 610)),
    ("F 5 · Högplats NÄTVERKSKORT, 58 × 88 mm. Vänsterkanten under DD-korten.",
     "NÄTVERKSKORT", "Dras två per kvartal", None, (33, 925)),
]


def rad_matt(s):
    """Glyfernas vågräta utsträckning (utan mellanslag) och baslinje för ett spann."""
    cs = [c for c in s["chars"] if c["c"].strip()]
    return cs[0]["bbox"][0], cs[-1]["bbox"][2], s["origin"][1], s["size"]


def natverksbild(sida_px):
    """Nätverkskortens sexkant (samma symbol som på kortens framsida), ritad i 4× och nedskalad."""
    k = 4
    W = sida_px * k
    H = round(W * 30 / 34)
    bild = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(bild)
    y0 = (W - H) / 2
    d.polygon([(W * .25, y0), (W * .75, y0), (W, y0 + H / 2), (W * .75, y0 + H), (W * .25, y0 + H),
               (0, y0 + H / 2)], fill=F_ROD + (255,))
    # SVG-rutan 100×100 skalad till 70 % × 80 % av sexkanten, centrerad
    sx, sy = W * .7 / 100, H * .8 / 100
    ox, oy = W * .15, y0 + H * .1
    P = lambda x, y: (ox + x * sx, oy + y * sy)  # noqa: E731
    ljus = (252, 246, 239, 255)
    for a, b in [((30, 35), (70, 30)), ((30, 35), (45, 70)), ((70, 30), (45, 70)), ((70, 30), (78, 65)),
                 ((45, 70), (78, 65))]:
        d.line([P(*a), P(*b)], fill=ljus, width=round(3 * sx))
    for x, y, r in [(30, 35, 7), (70, 30, 8), (45, 70, 9), (78, 65, 6)]:
        cx, cy = P(x, y)
        d.ellipse([cx - r * sx, cy - r * sx, cx + r * sx, cy + r * sx], fill=ljus)
    return bild.resize((sida_px, sida_px), Image.LANCZOS)


def f_hogplats(dok, bildfil):
    """Högplats i F-brädets stil: omvärldsplatsens bild utan rubrik och bild, med ny bild."""
    mall = Image.open(io.BytesIO(dok.extract_image(F_MALL)["image"])).convert("RGB")
    bg = Image.new("RGB", (1, 1), mall.getpixel((20, 600)))
    mall.paste(bg.resize((560, 70)), (110, 185))            # rubrik bort
    mall.paste(bg.resize((460, 460)), (114, 290))           # bild bort
    ram = 439                                                # bildrutan: 439 px i (124, 301)
    if bildfil:
        b = Image.open(HAR / "bilder" / bildfil).convert("RGB")
        m = min(b.size)
        b = b.crop(((b.width - m) // 2, (b.height - m) // 2, (b.width + m) // 2, (b.height + m) // 2))
        mall.paste(b.resize((ram, ram), Image.LANCZOS), (124, 301))
    else:
        n = natverksbild(ram)
        mall.paste(n, (124, 301), n)
    buf = io.BytesIO()
    mall.save(buf, "JPEG", quality=95)
    return buf.getvalue(), mall.size


def bygg_f(typ):
    dok = fitz.open(F_BRADE)
    sida = dok[0]

    # Textbyten: mät, ta bort allt på en gång, skriv nytt centrerat på samma rader
    byten = []
    for markes, gamla, nya in F_TEXTER:
        spann = [spann_med(sida, g)[0] for g in gamla]
        byten.append((markes, spann, nya))
    ta_bort_text(sida, [s for _, sp, _ in byten for s in sp])
    klipp = []
    for markes, spann, nya in byten:
        x0s, x1s, ys = [], [], []
        for s, ny in zip(spann, nya):
            gx0, gx1, bas, storlek = rad_matt(s)
            mitt = (gx0 + gx1) / 2
            bredd = typ.bredd(ny, storlek)
            typ.skriv(sida, (mitt - bredd / 2, bas), ny, storlek, F_TEXTFARG)
            x0s += [gx0, mitt - bredd / 2]
            x1s += [gx1, mitt + bredd / 2]
            ys.append(bas)
        klipp.append((markes, fitz.Rect(min(x0s) - 8, min(ys) - 0.78 * storlek,
                                        max(x1s) + 8, max(ys) + 0.26 * storlek)))

    ut = fitz.open()
    for markes, r in klipp:
        s = markessida(ut, r.width, r.height,
                       lambda s_, rr, r=r: s_.show_pdf_page(rr, dok, 0, clip=r + (-UTFALL, -UTFALL, UTFALL, UTFALL)))
        text(s, markes)

    kb, kh = KORT_PT
    platser = []
    for markes, rubrik, under, bildfil, (x, y) in F_PLATSER:
        jpg, (pw, ph) = f_hogplats(dok, bildfil)
        skala = kb / pw
        bg = Image.open(io.BytesIO(jpg)).getpixel((20, 600))

        def rita(s_, r, jpg=jpg, rubrik=rubrik, under=under, skala=skala, bg=bg, ph=ph):
            s_.draw_rect(r, color=None, fill=tuple(c / 255 for c in bg))
            inne = fitz.Rect(r.x0 + UTFALL, r.y0 + UTFALL, r.x1 - UTFALL, r.y1 - UTFALL)
            s_.draw_rect(fitz.Rect(r.x0, inne.y1 - 10 * skala, r.x1, r.y1), color=None,
                         fill=tuple(c / 255 for c in F_ROD))   # röd list i nederkant som på brädets platser
            s_.insert_image(inne, stream=jpg)
            rod = tuple(c / 255 for c in F_ROD)
            typ.skriv(s_, (inne.x0 + 126 * skala, inne.y0 + 238 * skala), rubrik, 36 * skala / 0.71, rod, fet=True)
            us = 30 * skala / 0.71
            typ.skriv(s_, (inne.x0 + 343 * skala - typ.bredd(under, us) / 2, inne.y0 + 838 * skala), under, us, rod)
        s = markessida(ut, kb, kh, rita)
        text(s, markes)
        platser.append((len(ut) - 1, fitz.Rect(x, y, x + kb, y + kh)))

    # Kontrollbräde med alla F-märken på plats
    kontroll = fitz.open()
    kontroll.insert_pdf(dok, from_page=0, to_page=0)
    for nr, r in platser:
        kontroll[0].show_pdf_page(r, ut, nr, clip=fitz.Rect(MARK + UTFALL, MARK + UTFALL,
                                                             MARK + UTFALL + kb, MARK + UTFALL + kh))
    kontroll[0].get_pixmap(dpi=40).save(UT / "F_brade_med_klistermarken.png")

    ut.save(UT / "klistermarken_F.pdf", garbage=4, deflate=True)
    print(f"{len(ut)} märken → {UT / 'klistermarken_F.pdf'}")


def main():
    UT.mkdir(exist_ok=True)
    typ = Bahnschrift()
    bygg_pu(typ)
    bygg_f(typ)


if __name__ == "__main__":
    main()
