"""
provkort_ark.py
Skapar PROVKORT_alla.pdf – en översikt där ETT slumpmässigt kortpar
(bildsida + textsida bredvid varandra) visas per korttyp, i rutnät
på A4 liggande. Används för att snabbt se hur alla korttyper skiljer
sig åt visuellt.

Efter översiktssidorna läggs hela _bildsida.pdf och _textsida.pdf till
för varje korttyp (i samma PU → PL → GF → F-ordning), så man kan se
varje fram- och baksida i full storlek.

Källa: alla PDF-par *_bildsida.pdf / *_textsida.pdf i PDF-mappen.
Målfil: PDF\\Kombinerade\\PROVKORT_alla.pdf

Anrop: python provkort_ark.py "C:\\väg\\till\\PDF-mapp"
Kräver: pip install pypdf reportlab
"""

import sys
import os
import re
import random
import io
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
from reportlab.pdfgen import canvas


# ── Inställningar ────────────────────────────────────────────────────────
# A4 liggande: 842 x 595 pt (1 pt = 1/72 tum)
SIDA_BREDD = 842.0
SIDA_HOJD  = 595.0

# Marginaler kring hela sidan
MARGINAL   = 30.0

# Rutnät: 2 par per rad × 3 rader = 6 kortpar per A4
KOLUMNER   = 2
RADER      = 3

# Hur mycket utrymme etiketten under varje par tar
ETIKETT_HOJD = 18.0

# Mellanrum mellan bild- och textsida inom samma par
PAR_MELLANRUM = 6.0

# Mellanrum runt varje kortpar i cellen
CELL_PADDING = 6.0

# Frö för slumpval. Sätt till ett heltal (t.ex. 42) för att få samma
# urval varje körning. None = nytt urval varje gång.
SLUMPFRO = None


# ── Sortering: PU → PL → GF → F ─────────────────────────────────────────
FAS_ORDNING = {"L_": 0, "PU": 1, "PL": 2, "GF": 3, "F_": 4}

def fas_sort_key(basnamn):
    upper = basnamn.upper()
    for prefix, prio in FAS_ORDNING.items():
        if upper.startswith(prefix):
            return (prio, upper)
    return (9, upper)


def skapa_etikett_och_ram_pdf(kortpar_info):
    """
    Skapa ett reportlab-genererat PDF-ark där etiketterna och ev.
    ram-linjer är utritade på rätt position. Kortens faktiska innehåll
    fogas in senare via pypdf:s merge_transformed_page.

    kortpar_info = [{
        "basnamn": "GF_garantibesiktning",
        "index_etikett": "1/6",
        "cell_x": 30, "cell_y_bottom": 300,
        "cell_bredd": 391, "cell_hojd": 178,
    }, ...]

    Returnerar: PdfReader med en sida per A4-ark
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(SIDA_BREDD, SIDA_HOJD))

    sida_nr = 0
    cells_pa_sida = 0

    for info in kortpar_info:
        if cells_pa_sida == 0 and sida_nr > 0:
            c.showPage()
        elif cells_pa_sida >= KOLUMNER * RADER:
            c.showPage()
            cells_pa_sida = 0
            sida_nr += 1

        if cells_pa_sida == 0:
            # Ny sida – vi ritar inget i bakgrunden
            pass

        # Etikett under paret
        etikett = f"{info['basnamn']}  (kort {info['index_etikett']})"
        c.setFont("Helvetica", 9)
        c.setFillGray(0.4)
        etikett_x = info["cell_x"] + info["cell_bredd"] / 2
        etikett_y = info["cell_y_bottom"] + ETIKETT_HOJD / 2 - 3
        c.drawCentredString(etikett_x, etikett_y, etikett)

        cells_pa_sida += 1

    c.save()
    buf.seek(0)
    return PdfReader(buf)


def placera_sida_pa_ark(ark, kalla_sida, x, y, max_bredd, max_hojd):
    """
    Skala och positionera en källsida inom rutan (x, y, max_bredd, max_hojd)
    på ark-sidan. Bevarar proportioner (fit inside).
    """
    kalla_bredd = float(kalla_sida.mediabox.width)
    kalla_hojd  = float(kalla_sida.mediabox.height)

    if kalla_bredd <= 0 or kalla_hojd <= 0:
        return

    skala = min(max_bredd / kalla_bredd, max_hojd / kalla_hojd)

    faktisk_bredd = kalla_bredd * skala
    faktisk_hojd  = kalla_hojd * skala
    offset_x = x + (max_bredd - faktisk_bredd) / 2
    offset_y = y + (max_hojd - faktisk_hojd) / 2

    transform = Transformation().scale(skala).translate(offset_x, offset_y)
    ark.merge_transformed_page(kalla_sida, transform)


def berakna_cell_position(cell_index_pa_sida):
    """
    Räkna ut var en cell ska placeras på en A4 liggande.
    Returnerar (cell_x, cell_y_bottom, cell_bredd, cell_hojd).
    Rad 0 = överst på sidan.
    """
    yta_bredd = SIDA_BREDD - 2 * MARGINAL
    yta_hojd  = SIDA_HOJD  - 2 * MARGINAL

    cell_bredd = yta_bredd / KOLUMNER
    cell_hojd  = yta_hojd  / RADER

    rad = cell_index_pa_sida // KOLUMNER
    kol = cell_index_pa_sida % KOLUMNER

    cell_x = MARGINAL + kol * cell_bredd
    # rad 0 ska vara överst: y_top = SIDA_HOJD - MARGINAL - rad * cell_hojd
    cell_y_top    = SIDA_HOJD - MARGINAL - rad * cell_hojd
    cell_y_bottom = cell_y_top - cell_hojd

    return cell_x, cell_y_bottom, cell_bredd, cell_hojd


def bygg_provkortark(pdf_mapp):
    pdf_mapp = pdf_mapp.rstrip("\\/")
    if not os.path.isdir(pdf_mapp):
        print(f"FEL: Mappen finns inte: {pdf_mapp}")
        sys.exit(1)

    ut_mapp = os.path.join(pdf_mapp, "Kombinerade")
    os.makedirs(ut_mapp, exist_ok=True)

    if SLUMPFRO is not None:
        random.seed(SLUMPFRO)
        print(f"Slumpfrö: {SLUMPFRO} (reproducerbart urval)")
    else:
        print("Slumpfrö: inget (nytt urval varje körning)")

    # Hitta alla bildsida-PDF:er (även multi-exemplar som _1, _2, ...)
    filer = os.listdir(pdf_mapp)
    bildsidor = sorted(
        f for f in filer
        if re.search(r"_bildsida(?:_\d+)?\.pdf$", f, re.IGNORECASE)
    )

    if not bildsidor:
        print("Inga *_bildsida.pdf hittades.")
        return

    # Samla par: (basnamn, bild_path, text_path). För multi-exemplar
    # (_1, _2, ...) tas bara FÖRSTA exemplaret — alla är kopior av
    # samma korttyp så ett räcker i översikten.
    sedda_basnamn = set()
    par = []
    for bildfil in bildsidor:
        m = re.match(r"^(.+)_bildsida(_\d+)?\.pdf$", bildfil, re.IGNORECASE)
        if not m:
            continue
        bas = m.group(1)
        suffix = m.group(2) or ""  # "_1", "_2" eller ""
        if bas in sedda_basnamn:
            continue
        sedda_basnamn.add(bas)
        textfil = f"{bas}_textsida{suffix}.pdf"
        if textfil not in filer:
            print(f"HOPPAR: {bas} (saknar textsida)")
            continue
        par.append((
            bas,
            os.path.join(pdf_mapp, bildfil),
            os.path.join(pdf_mapp, textfil),
        ))

    if not par:
        print("Inga kompletta par hittades.")
        return

    # Sortera i PU → PL → GF → F-ordning
    par.sort(key=lambda p: fas_sort_key(p[0]))
    print(f"Hittade {len(par)} korttyper")

    per_sida = KOLUMNER * RADER
    antal_sidor = (len(par) + per_sida - 1) // per_sida
    print(f"Layout: {KOLUMNER}x{RADER} = {per_sida} kortpar/sida, "
          f"{antal_sidor} sidor totalt")

    # ── Steg 1: välj slumpmässigt kortindex per korttyp ──────────────────
    valda = []
    for basnamn, bild_path, text_path in par:
        try:
            bild_reader = PdfReader(bild_path)
            text_reader = PdfReader(text_path)
        except Exception as e:
            print(f"FEL vid läsning av {basnamn}: {e}")
            continue

        n_sidor = min(len(bild_reader.pages), len(text_reader.pages))
        if n_sidor == 0:
            print(f"HOPPAR: {basnamn} (tom PDF)")
            continue

        valt_index = random.randint(0, n_sidor - 1)
        valda.append({
            "basnamn": basnamn,
            "bild_sida": bild_reader.pages[valt_index],
            "text_sida": text_reader.pages[valt_index],
            "index_etikett": f"{valt_index + 1}/{n_sidor}",
        })
        print(f"  {basnamn}: valde kort {valt_index + 1}/{n_sidor}")

    # ── Steg 2: generera etikett-PDF med reportlab ────────────────────────
    # Vi bygger en PDF med en sida per ark där etiketterna ligger rätt
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(SIDA_BREDD, SIDA_HOJD))
    c.setFont("Helvetica", 9)

    for i, vald in enumerate(valda):
        idx_pa_sida = i % per_sida
        if i > 0 and idx_pa_sida == 0:
            c.showPage()
            c.setFont("Helvetica", 9)

        cell_x, cell_y_bottom, cell_bredd, cell_hojd = berakna_cell_position(idx_pa_sida)

        # Etikett under paret
        etikett = f"{vald['basnamn']}  (kort {vald['index_etikett']})"
        c.setFillGray(0.4)
        c.drawCentredString(cell_x + cell_bredd / 2,
                            cell_y_bottom + ETIKETT_HOJD / 2 - 3,
                            etikett)

    c.save()
    buf.seek(0)
    etikett_reader = PdfReader(buf)

    # ── Steg 3: bygg slutlig PDF genom att MERGE:a kortsidor på etikett-PDF:n ──
    writer = PdfWriter()

    for sida_index in range(antal_sidor):
        # Börja från etikett-arket som har etiketterna redan inritade
        ark = etikett_reader.pages[sida_index]

        # Lägg kortpar på ark-sidan
        for i_i_grupp in range(per_sida):
            global_index = sida_index * per_sida + i_i_grupp
            if global_index >= len(valda):
                break

            vald = valda[global_index]
            cell_x, cell_y_bottom, cell_bredd, cell_hojd = berakna_cell_position(i_i_grupp)

            # Utrymme för korten (över etiketten)
            kort_y = cell_y_bottom + ETIKETT_HOJD + CELL_PADDING
            kort_hojd = cell_hojd - ETIKETT_HOJD - 2 * CELL_PADDING
            kort_bredd = (cell_bredd - 2 * CELL_PADDING - PAR_MELLANRUM) / 2

            bild_x = cell_x + CELL_PADDING
            text_x = cell_x + CELL_PADDING + kort_bredd + PAR_MELLANRUM

            placera_sida_pa_ark(ark, vald["bild_sida"],
                                bild_x, kort_y, kort_bredd, kort_hojd)
            placera_sida_pa_ark(ark, vald["text_sida"],
                                text_x, kort_y, kort_bredd, kort_hojd)

        writer.add_page(ark)

    # ── Steg 4: lägg till första sidan av _bildsida.pdf + _textsida.pdf ──
    # Översikten är bra för att jämföra typer; men man vill ofta också
    # se ett fram-/baksideark i originalstorlek. Vi lägger därför till
    # första sidan av bildsida.pdf följt av första sidan av textsida.pdf
    # per korttyp (i samma PU → PL → GF → F-ordning).
    print(f"\nLägger till ett fram- och ett baksidesark per korttyp...")
    extra_sidor = 0
    for basnamn, bild_path, text_path in par:
        try:
            bild_reader = PdfReader(bild_path)
            text_reader = PdfReader(text_path)
            if len(bild_reader.pages) > 0:
                writer.add_page(bild_reader.pages[0])
                extra_sidor += 1
            if len(text_reader.pages) > 0:
                writer.add_page(text_reader.pages[0])
                extra_sidor += 1
            print(f"  {basnamn}: +1 bild + 1 text")
        except Exception as e:
            print(f"  FEL vid {basnamn}: {e}")

    # Skriv ut
    ut_path = os.path.join(ut_mapp, "PROVKORT_alla.pdf")
    with open(ut_path, "wb") as f:
        writer.write(f)

    total_sidor = antal_sidor + extra_sidor
    print(f"\nKlart: {ut_path}")
    print(f"  {len(valda)} korttyper på {antal_sidor} översiktssidor "
          f"+ {extra_sidor} fram-/baksidor = {total_sidor} sidor totalt")


if __name__ == "__main__":
    mapp = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    bygg_provkortark(mapp)

