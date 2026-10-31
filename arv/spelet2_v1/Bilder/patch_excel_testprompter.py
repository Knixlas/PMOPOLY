"""
patch_excel_testprompter.py

Byter ut Prompt v6 för fem testkort enligt den nya picture-book-stilen,
backupar originalvärdena i en ny kolumn, och aktiverar testläge.

Körning:
    python patch_excel_testprompter.py sökväg/till/bilder.xlsx

Om ingen sökväg anges letas filen i samma mapp som skriptet.
Originalfilen kopieras till bilder_FÖRE_patch.xlsx innan något skrivs.
"""

import sys
import shutil
from pathlib import Path

import openpyxl


# ─────────────────────────────────────────────────────────────────────────────
# DE FEM NYA PROMPTERNA
# ─────────────────────────────────────────────────────────────────────────────

NYA_PROMPTER = {
    "brf_solrosen": (
        "A warm Scandinavian picture-book illustration of a single large sunflower "
        "in full bloom, seen from slightly below, its head tilted toward the light. "
        "Hand-painted gouache texture with visible brushstrokes, layered washes "
        "and subtle paper grain. Confident ink linework with varied weight — "
        "thicker at the flower's base and stem, finer on the petal edges and seed pattern. "
        "Soft directional light from upper left, gentle form shadows give the petals "
        "real volume. Palette built on deep forest green #1A4D24 and warm leaf green #2D7A3A, "
        "with muted golden yellow and soft ochre for the bloom. "
        "Centered composition on an off-white textured background with a soft natural vignette. "
        "Characterful, slightly imperfect, alive. "
        "Style references: Beatrix Potter botanicals, Carl Larsson, Lena Anderson. "
        "Not a flat vector icon, not clipart, not a pictogram, no hard geometric shapes, "
        "no solid color blocks, no thick uniform outlines, no text, no photorealism."
    ),

    "förskolor_nyckelpigan": (
        "A warm Scandinavian picture-book illustration of a single plump ladybug "
        "seen from above, resting on a curling green leaf, her wing-case slightly open "
        "as if about to take flight. Hand-painted gouache with visible brushstrokes "
        "and layered washes, the red of the shell built from several warm reds "
        "rather than one flat color. Varied ink linework — confident around the silhouette, "
        "softer inside. Soft top-left light gives the dome of her back a real curve. "
        "Palette anchored in deep preschool blue #0F3D5C and bright playful blue #1A6B9A "
        "as supporting tones, with warm vermillion and black for the ladybug, fresh "
        "leaf green for the perch. Centered on a cream textured background with gentle vignette. "
        "Charming, slightly imperfect, full of life. "
        "Style references: Elsa Beskow, Lena Anderson, classic Nordic children's books. "
        "Not a flat icon, not clipart, not a pictogram, no hard geometric shapes, "
        "no solid color blocks, no uniform outlines, no text, no 3d render."
    ),

    "kontor_fyrtornet": (
        "A warm Scandinavian picture-book illustration of a classic red-and-white "
        "striped lighthouse standing on a weathered rocky outcrop, its warm lamp "
        "glowing against a deep twilight sky, a soft beam of light sweeping out "
        "to the right. Hand-painted gouache texture — the stripes built from "
        "imperfect brushstrokes, the rock layered in greys and cool browns, "
        "the sky a graded wash from deep violet to navy. Confident ink linework, "
        "thicker at the base, finer toward the lantern. Warm lamp-light creates "
        "real atmospheric glow around the top. Palette anchored in deep cosmic "
        "purple #321F50 and rich violet #5B3A8A, with warm lamp-yellow as the "
        "single bright accent. Centered composition on soft textured dark background "
        "with a gentle luminous vignette around the beacon. "
        "Atmospheric, characterful, romantic. "
        "Style references: classic Nordic maritime illustration, Jon Klassen, "
        "evening light in Carl Larsson's watercolors. "
        "Not a flat icon, not clipart, not a pictogram, no geometric simplification, "
        "no solid color blocks, no uniform outlines, no photorealism, no text."
    ),

    "hyresförhandling": (
        "A warm Scandinavian picture-book illustration of two hands meeting "
        "over a wooden table across an open document — one hand offering a pen, "
        "the other resting thoughtfully on the paper. Seen from a slight three-quarter "
        "angle, cropped at the wrists. Hand-painted gouache with visible brushwork, "
        "the wood grain of the table suggested in loose warm strokes, the paper "
        "slightly creased and worn. Confident varied ink line — strong around the hands, "
        "softer on the document. Warm directional light from upper left casts "
        "soft shadows that ground the hands in real space. Muted earthy palette with "
        "warm cream paper, honey-toned wood, and a single deep blue accent on the pen. "
        "Centered composition on a soft textured neutral background, subtle vignette. "
        "Human, warm, quietly serious — a moment of negotiation, not a transaction icon. "
        "Style references: Carl Larsson interiors, classic Swedish editorial illustration, "
        "hand-drawn picture book warmth. "
        "Not a flat icon, not clipart, not a pictogram, no geometric simplification, "
        "no solid color blocks, no uniform outlines, no faces shown, no text, no 3d render."
    ),

    "fastighetschef_bostader": (
        "A warm Scandinavian picture-book illustration of a property manager "
        "standing confidently in three-quarter view, holding a worn leather folder "
        "under one arm, a small brass key visible clipped to its cover. Dressed "
        "in a simple practical jacket and work trousers, sleeves slightly rolled. "
        "Hand-painted gouache with visible brushwork — the folder's leather built "
        "from several warm browns, the fabric of the clothes with soft variation "
        "and gentle wrinkle shadows. Face suggested with minimal, gentle features — "
        "no sharp realism, but a real person with warmth and presence. Confident "
        "varied ink linework, stronger around the silhouette, softer inside. "
        "Soft directional light from upper left gives the figure real dimensional volume. "
        "Palette anchored in soft cream #F2EFE9 and dusty slate blue-grey #5D737E, "
        "with warm honey-leather accents and a small touch of terracotta on a detail. "
        "Centered composition on a gently textured off-white background with soft vignette. "
        "Characterful, slightly imperfect, human — a person, not a symbol of one. "
        "Style references: Carl Larsson portraits, modern Nordic editorial illustration, "
        "warm picture-book figure work. "
        "Not a flat icon, not clipart, not a pictogram, no geometric body, no solid "
        "color blocks, no uniform outlines, no photorealism, no 3d render, no text."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# HJÄLPFUNKTIONER
# ─────────────────────────────────────────────────────────────────────────────

def hitta_xlsx():
    """Leta reda på Excel-filen. Antingen från argv eller i skriptets mapp."""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1]).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Hittar inte filen: {p}")
        return p

    here = Path(__file__).resolve().parent
    kandidater = [
        here / "bilder.xlsx",
        here / "bilder_v5_finjusterad_merged_v6.xlsx",
    ]
    for c in kandidater:
        if c.exists():
            return c
    # fallback: första .xlsx i mappen som inte börjar på ~$
    xlsxar = sorted(p for p in here.glob("*.xlsx") if not p.name.startswith("~$"))
    if xlsxar:
        return xlsxar[0]
    raise FileNotFoundError(
        "Hittar ingen Excel-fil. Ange sökvägen: python patch_excel_testprompter.py <fil.xlsx>"
    )


def skapa_backup(path: Path) -> Path:
    """Kopiera original till <filnamn>_FÖRE_patch.xlsx bredvid originalet."""
    backup = path.with_name(path.stem + "_FÖRE_patch" + path.suffix)
    shutil.copy2(path, backup)
    return backup


def säkerställ_backupkolumn(ws, rubrik_radnummer=1, källkolumn_rubrik="Prompt v6",
                            backupkolumn_rubrik="Prompt v6 (original backup)"):
    """
    Ser till att det finns en kolumn 'Prompt v6 (original backup)' direkt efter
    'Prompt v6'. Returnerar (källkolumn_index_1baserat, backupkolumn_index_1baserat).
    Om backupkolumnen redan finns lämnas den orörd.
    """
    headers = [c.value for c in ws[rubrik_radnummer]]
    try:
        src_idx = headers.index(källkolumn_rubrik) + 1  # 1-baserat
    except ValueError:
        raise RuntimeError(f"Kolumnen '{källkolumn_rubrik}' saknas i bladet.")

    if backupkolumn_rubrik in headers:
        bak_idx = headers.index(backupkolumn_rubrik) + 1
        return src_idx, bak_idx

    # Sätt in ny kolumn direkt efter källkolumnen
    bak_idx = src_idx + 1
    ws.insert_cols(bak_idx)
    ws.cell(row=rubrik_radnummer, column=bak_idx, value=backupkolumn_rubrik)
    return src_idx, bak_idx


def hitta_radindex(ws, id_kolumn_1baserat: int, mål_ids: set) -> dict:
    """Mappa id → radnummer för rader där Unikt ID matchar något i mål_ids."""
    träffar = {}
    for row_num in range(2, ws.max_row + 1):
        rid = ws.cell(row=row_num, column=id_kolumn_1baserat).value
        if rid and str(rid).strip() in mål_ids:
            träffar[str(rid).strip()] = row_num
    return träffar


def uppdatera_inställningar(wb, test_ids: list):
    """
    Sätt test_läge=TRUE och test_id till första test-id:t.
    (Skriptet kan bara köra ett test_id i taget i generate_images_v5.py,
     så vi sätter det första och skriver ut de andra som kommentar.)
    """
    ws = wb["Inställningar"]
    radkarta = {}
    for row_num in range(2, ws.max_row + 1):
        nyckel = ws.cell(row=row_num, column=1).value
        if nyckel:
            radkarta[str(nyckel).strip()] = row_num

    if "test_läge" in radkarta:
        ws.cell(row=radkarta["test_läge"], column=2, value="TRUE")
    if "test_id" in radkarta:
        ws.cell(row=radkarta["test_id"], column=2, value=test_ids[0])


# ─────────────────────────────────────────────────────────────────────────────
# HUVUDPROGRAM
# ─────────────────────────────────────────────────────────────────────────────

def main():
    xlsx_path = hitta_xlsx()
    print(f"Excel-fil: {xlsx_path}")

    backup_path = skapa_backup(xlsx_path)
    print(f"Backup skapad: {backup_path.name}")

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["Bilder"]

    # Hitta kolumnerna vi behöver
    headers = [c.value for c in ws[1]]
    id_kol = headers.index("Unikt ID") + 1

    src_kol, bak_kol = säkerställ_backupkolumn(ws)
    print(f"Prompt v6-kolumn: {src_kol}, backupkolumn: {bak_kol}")

    # Hitta raderna för de fem korten
    mål_ids = set(NYA_PROMPTER.keys())
    radkarta = hitta_radindex(ws, id_kol, mål_ids)

    saknade = mål_ids - set(radkarta.keys())
    if saknade:
        print(f"\n⚠ Varning – dessa id hittades inte i bladet: {saknade}")
        print("  Skriptet fortsätter med de som hittades.")

    # Skriv in nya prompter, med backup av tidigare värde
    print("\nUppdaterar rader:")
    for rid, row_num in radkarta.items():
        gammal = ws.cell(row=row_num, column=src_kol).value
        nuvarande_backup = ws.cell(row=row_num, column=bak_kol).value

        # Skriv bara backup första gången så vi inte skriver över originalet
        # om skriptet körs flera gånger.
        if not nuvarande_backup and gammal:
            ws.cell(row=row_num, column=bak_kol, value=gammal)

        ws.cell(row=row_num, column=src_kol, value=NYA_PROMPTER[rid])
        print(f"  rad {row_num:3}  {rid}")

    # Aktivera testläge med första id:t
    test_ids = list(radkarta.keys())
    if test_ids:
        uppdatera_inställningar(wb, test_ids)
        print(f"\nInställningar: test_läge=TRUE, test_id={test_ids[0]}")

    wb.save(xlsx_path)
    print(f"\n✓ Sparat: {xlsx_path.name}")

    # Instruktioner
    print("\n" + "─" * 72)
    print("NÄSTA STEG")
    print("─" * 72)
    print("Kör en bild i taget genom att ändra test_id i Inställningar och köra:")
    print("    python generate_images_v5.py")
    print("\nTest-id att köra (ett i taget):")
    for rid in test_ids:
        print(f"    {rid}")
    print("\nNär du är nöjd med en prompt: ångra genom att kopiera tillbaka värdet")
    print("från kolumnen 'Prompt v6 (original backup)' till 'Prompt v6'.")
    print("\nOm allt ska rullas tillbaka: återställ från backupfilen")
    print(f"    {backup_path.name}")


if __name__ == "__main__":
    main()

