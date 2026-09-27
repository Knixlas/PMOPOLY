"""
Genererar PNG-former för Husbyggspelet.

Hanterar två källfiler:
  1. PU_projekt.csv       → projektformer (BTA/250 ger antal rutor)
  2. PU_markexpansion.csv → markexpansionsformer (Antal rutor direkt)

Logik:
  - Enfärgad rektangel i fill_color, kant i line_color (inga mönster/streckning)
  - Formfaktor (1–8) styr hur oregelbunden/utspridd formen är
    (markexpansion har ingen FF-kolumn → defaultvärde används)
  - Seedat slumptal per projekts namn+index → reproducerbart
  - Varje unik form används bara en gång (försöker med nya seeds)

Output: en PNG per rad i angiven mapp.
"""

import csv
import os
import random
import hashlib
from PIL import Image, ImageDraw

# --- Destinationsmapp ---
OUTPUT_DIR = r"C:\Users\niklas.sviden\OneDrive - Åke Sundvalls Byggnads AB\SPELET 2\Bilder\Former"

# --- Grid-dimensioner ---
COLS = 4
ROWS = 5

# --- Bildstorlek ---
CELL_SIZE   = 60
PADDING     = 14
LINE_WIDTH  = 2
IMG_W = COLS * CELL_SIZE + 2 * PADDING
IMG_H = ROWS * CELL_SIZE + 2 * PADDING

DEFAULT_COLORS = ("#888888", "#333333")

# --- Default formfaktor för markexpansion (ingen FF-kolumn i CSV) ---
MARKEXPANSION_FF = 4

# --- CSV-kodning (samma som andra spel-filer) ---
CSV_ENCODING = "cp1252"


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def name_seed(name):
    """Stabilt seed baserat på projektnamnet → reproducerbart."""
    return int(hashlib.md5(name.encode()).hexdigest(), 16) % (2**32)


def generate_shape(n_cells, formfaktor, seed):
    """
    Genererar en sammanhängande form med n_cells fyllda rutor på 4×5-gridet.

    Formfaktor 1–2 : kompakta, rektangelliknande former
    Formfaktor 3–5 : måttlig oregelbundenhet (L, T, Z-liknande)
    Formfaktor 6–8 : utspridda, komplexa former
    """
    rng = random.Random(seed)
    n_cells = max(1, min(n_cells, COLS * ROWS))

    # Startpunkt: kompakta former börjar centralt, komplexa i ett hörn
    if formfaktor <= 2:
        start = (1, 1)
    elif formfaktor <= 4:
        start = (rng.randint(0, 1), rng.randint(0, 1))
    else:
        start = rng.choice([(0, 0), (0, COLS-1), (ROWS-1, 0), (ROWS-1, COLS-1)])

    filled = {start}

    for _ in range(n_cells - 1):
        candidates = set()
        for (r, c) in filled:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS and (nr, nc) not in filled:
                    candidates.add((nr, nc))
        if not candidates:
            break

        def score(cell):
            r, c = cell
            neighbors_filled = sum(
                1 for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if (r + dr, c + dc) in filled
            )
            dist_center = abs(r - ROWS / 2) + abs(c - COLS / 2)

            if formfaktor <= 2:
                return neighbors_filled * 3 + rng.random() * 0.3
            elif formfaktor <= 4:
                return neighbors_filled * 1.5 - dist_center * 0.3 + rng.random()
            elif formfaktor <= 6:
                return -neighbors_filled * 0.5 + dist_center * 0.5 + rng.random() * 1.5
            else:
                return -neighbors_filled * 2 + dist_center + rng.random() * 2

        scored = sorted(candidates, key=score, reverse=True)
        top = scored[:min(2, len(scored))]
        chosen = rng.choice(top)
        filled.add(chosen)

    grid = [0] * (COLS * ROWS)
    for (r, c) in filled:
        grid[r * COLS + c] = 1
    return grid


def draw_image(grid, fill_color, line_color):
    """Enfärgad form: fyllning i fill_color, kant i line_color."""
    img = Image.new("RGBA", (IMG_W, IMG_H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    fill_rgb = hex_to_rgb(fill_color)
    line_rgb = hex_to_rgb(line_color)

    for idx, filled in enumerate(grid):
        if not filled:
            continue
        row = idx // COLS
        col = idx % COLS
        x0 = PADDING + col * CELL_SIZE
        y0 = PADDING + row * CELL_SIZE
        x1 = x0 + CELL_SIZE
        y1 = y0 + CELL_SIZE
        draw.rectangle([x0, y0, x1, y1], fill=fill_rgb, outline=line_rgb, width=LINE_WIDTH)

    return img


def process_rows(rows, row_to_params, out_dir, used_shapes, label):
    """
    rows           : list of dict från CSV
    row_to_params  : function(row, idx) -> (filnamn, n_cells, formfaktor, fill, line) eller None
    """
    print(f"\n=== {label} ({len(rows)} rader) ===")
    for idx, row in enumerate(rows):
        params = row_to_params(row, idx)
        if params is None:
            continue
        filnamn, n_cells, ff, fill, line = params

        base_seed = name_seed(filnamn)

        attempt = 0
        while True:
            grid = generate_shape(n_cells, ff, base_seed + attempt)
            key = tuple(grid)
            if key not in used_shapes:
                used_shapes.add(key)
                break
            attempt += 1
            if attempt > 500:  # säkerhetsbrytare
                break

        suffix = f" (försök {attempt+1})" if attempt > 0 else ""
        img = draw_image(grid, fill, line)

        out_path = os.path.join(out_dir, f"{filnamn}.png")
        img.save(out_path)
        print(f"  {filnamn:30}  rutor={n_cells:2}  FF={ff}  → {filnamn}.png{suffix}")


def params_for_projekt(row, idx):
    namn = row.get("Namn", "").strip()
    typ  = row.get("Typ", "").strip()
    bta_raw = row.get("BTA", "").strip()
    ff_raw  = row.get("Formfaktor", "").strip()

    if not namn or not bta_raw or not ff_raw:
        return None

    try:
        bta = int(bta_raw)
        ff  = int(ff_raw)
    except ValueError:
        return None

    n_cells = max(1, bta // 250)
    fill = row.get("fill_color", "").strip() or DEFAULT_COLORS[0]
    line = row.get("line_color", "").strip() or DEFAULT_COLORS[1]
    return (namn, n_cells, ff, fill, line)


def params_for_markexpansion(row, idx):
    namn = row.get("Namn", "").strip()
    rutor_raw = row.get("Antal rutor", "").strip()

    if not namn or not rutor_raw:
        return None

    try:
        n_cells = int(rutor_raw)
    except ValueError:
        return None

    # Filnamn behöver vara unikt (alla heter "Markexpansion") → lägg till index
    filnamn = f"{namn}_{idx+1:02d}_{n_cells}rutor"
    fill = row.get("fill_color", "").strip() or DEFAULT_COLORS[0]
    line = row.get("line_color", "").strip() or DEFAULT_COLORS[1]
    return (filnamn, n_cells, MARKEXPANSION_FF, fill, line)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    running_local = os.name == "nt"
    out_dir = OUTPUT_DIR if running_local else "/home/claude/output_v2"
    os.makedirs(out_dir, exist_ok=True)

    used_shapes = set()

    # 1) Projektformer
    projekt_csv = os.path.join(script_dir, "PU_projekt.csv")
    if os.path.exists(projekt_csv):
        with open(projekt_csv, encoding=CSV_ENCODING, newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = [r for r in reader if r.get("Namn", "").strip()]
        process_rows(rows, params_for_projekt, out_dir, used_shapes, "Projektformer")
    else:
        print(f"Hittar inte {projekt_csv} – hoppar projektformer")

    # 2) Markexpansionsformer
    markexp_csv = os.path.join(script_dir, "PU_markexpansion.csv")
    if os.path.exists(markexp_csv):
        with open(markexp_csv, encoding=CSV_ENCODING, newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = [r for r in reader if r.get("Namn", "").strip()]
        process_rows(rows, params_for_markexpansion, out_dir, used_shapes, "Markexpansioner")
    else:
        print(f"Hittar inte {markexp_csv} – hoppar markexpansioner")

    print(f"\nKlart! Bilder sparade i:\n  {out_dir}")


if __name__ == "__main__":
    main()

