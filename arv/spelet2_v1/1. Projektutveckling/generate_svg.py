"""
Genererar en SVG med alla projektformer på ett ark.
Varje form visas som ren ytterkontur (skärlinje för Cricut).
Former läggs ut i ett rutnät.
"""

import csv
import os
import hashlib
import random

# --- Inställningar ---
COLS = 4
ROWS = 5
CELL   = 20        # mm per cell
GAP    = 8         # mm mellan former
MARGIN = 10        # mm runt hela arket
GRID_COLS = 9      # antal former per rad i layouten

CSV_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PU_projekt_textsida.csv")
OUTPUT_SVG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "former_cricut.svg")

# mm → SVG-enheter (1mm = 3.7795275591 px vid 96dpi, men vi kör i mm direkt)
def mm(v):
    return f"{v}mm"


# ── Samma form-logik som generate_forms_v2.py ──────────────────────────────

def name_seed(name):
    return int(hashlib.md5(name.encode()).hexdigest(), 16) % (2**32)


def generate_shape(n_cells, formfaktor, seed):
    rng = random.Random(seed)
    n_cells = max(1, min(n_cells, COLS * ROWS))
    if formfaktor <= 2:
        start = (1, 1)
    elif formfaktor <= 4:
        start = (rng.randint(0, 1), rng.randint(0, 1))
    else:
        start = rng.choice([(0,0),(0,COLS-1),(ROWS-1,0),(ROWS-1,COLS-1)])

    filled = {start}
    for _ in range(n_cells - 1):
        candidates = set()
        for (r, c) in filled:
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < ROWS and 0 <= nc < COLS and (nr,nc) not in filled:
                    candidates.add((nr,nc))
        if not candidates:
            break

        def score(cell):
            r, c = cell
            nb = sum(1 for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)] if (r+dr,c+dc) in filled)
            dist = abs(r - ROWS/2) + abs(c - COLS/2)
            if formfaktor <= 2:
                return nb * 3 + rng.random() * 0.3
            elif formfaktor <= 4:
                return nb * 1.5 - dist * 0.3 + rng.random()
            elif formfaktor <= 6:
                return -nb * 0.5 + dist * 0.5 + rng.random() * 1.5
            else:
                return -nb * 2 + dist + rng.random() * 2

        top = sorted(candidates, key=score, reverse=True)[:2]
        filled.add(rng.choice(top))

    grid = [0] * (COLS * ROWS)
    for (r, c) in filled:
        grid[r * COLS + c] = 1
    return grid


# ── Ytterkontur: samla alla yttre kanter ───────────────────────────────────

def outer_edges(grid):
    """
    Returnerar en lista av linjsegment [(x0,y0,x1,y1), ...] i cell-koordinater
    som utgör ytterkonturen av formen.
    """
    filled = set()
    for idx, v in enumerate(grid):
        if v:
            filled.add((idx // COLS, idx % COLS))

    edges = []
    for (r, c) in filled:
        # Topp
        if (r-1, c) not in filled:
            edges.append((c, r, c+1, r))
        # Botten
        if (r+1, c) not in filled:
            edges.append((c, r+1, c+1, r+1))
        # Vänster
        if (r, c-1) not in filled:
            edges.append((c, r, c, r+1))
        # Höger
        if (r, c+1) not in filled:
            edges.append((c+1, r, c+1, r+1))
    return edges


def edges_to_polylines(edges):
    """
    Kedjekopplar kanter till sammanhängande polylines.
    Returnerar lista av punktlistor [(x,y), ...].
    """
    # Bygg adjacenslista: punkt → lista av grannar
    from collections import defaultdict
    adj = defaultdict(list)
    for (x0, y0, x1, y1) in edges:
        adj[(x0,y0)].append((x1,y1))
        adj[(x1,y1)].append((x0,y0))

    visited_edges = set()
    polylines = []

    def edge_key(a, b):
        return (min(a,b), max(a,b))

    for start_edge in edges:
        x0,y0,x1,y1 = start_edge
        key = edge_key((x0,y0),(x1,y1))
        if key in visited_edges:
            continue

        # Starta en ny polyline
        path = [(x0,y0),(x1,y1)]
        visited_edges.add(key)

        while True:
            current = path[-1]
            prev    = path[-2]
            moved   = False
            for nxt in adj[current]:
                k = edge_key(current, nxt)
                if k not in visited_edges:
                    visited_edges.add(k)
                    path.append(nxt)
                    moved = True
                    break
            if not moved:
                break

        polylines.append(path)

    return polylines


# ── Bygg SVG ───────────────────────────────────────────────────────────────

def shape_width_cells(grid):
    cols_used = [idx % COLS for idx, v in enumerate(grid) if v]
    return (max(cols_used) - min(cols_used) + 1) if cols_used else COLS

def shape_height_cells(grid):
    rows_used = [idx // COLS for idx, v in enumerate(grid) if v]
    return (max(rows_used) - min(rows_used) + 1) if rows_used else ROWS


def generate_svg(shapes):
    """
    shapes: lista av dict med keys: namn, grid
    """
    n = len(shapes)
    layout_cols = GRID_COLS
    layout_rows = (n + layout_cols - 1) // layout_cols

    cell_box_w = COLS * CELL   # bredd per form-slot
    cell_box_h = ROWS * CELL   # höjd per form-slot

    total_w = MARGIN * 2 + layout_cols * cell_box_w + (layout_cols - 1) * GAP
    total_h = MARGIN * 2 + layout_rows * cell_box_h + (layout_rows - 1) * GAP

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg"')
    lines.append(f'     width="{total_w}mm" height="{total_h}mm"')
    lines.append(f'     viewBox="0 0 {total_w} {total_h}">')
    lines.append(f'  <rect width="{total_w}" height="{total_h}" fill="white"/>')

    for i, shape in enumerate(shapes):
        col_i = i % layout_cols
        row_i = i // layout_cols

        ox = MARGIN + col_i * (cell_box_w + GAP)
        oy = MARGIN + row_i * (cell_box_h + GAP)

        grid = shape["grid"]
        namn = shape["namn"]

        # Gruppera per form
        lines.append(f'  <g id="{namn}" transform="translate({ox},{oy})">')

        # Etiketttext under formen
        lines.append(f'    <text x="{cell_box_w/2}" y="{cell_box_h + 5}"')
        lines.append(f'          font-family="sans-serif" font-size="3"')
        lines.append(f'          text-anchor="middle" fill="#555">{namn}</text>')

        # Ytterkontur
        edges = outer_edges(grid)
        polylines = edges_to_polylines(edges)

        for pts in polylines:
            points_str = " ".join(f"{x*CELL},{y*CELL}" for x,y in pts)
            lines.append(f'    <polyline points="{points_str}"')
            lines.append(f'              fill="none" stroke="#000" stroke-width="0.5"')
            lines.append(f'              stroke-linejoin="round" stroke-linecap="round"/>')

        lines.append(f'  </g>')

    lines.append('</svg>')
    return "\n".join(lines)


def main():
    used_shapes = set()
    shapes = []

    with open(CSV_PATH, encoding="iso-8859-1", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = [r for r in reader if r.get("Namn","").strip()]

    for row in rows:
        namn    = row["Namn"].strip()
        bta_raw = row.get("BTA","").strip()
        ff_raw  = row.get("Formfaktor","").strip()
        if not bta_raw or not ff_raw:
            continue
        try:
            bta = int(bta_raw)
            ff  = int(ff_raw)
        except ValueError:
            continue

        n_cells   = max(1, bta // 250)
        base_seed = name_seed(namn)

        attempt = 0
        while True:
            grid = generate_shape(n_cells, ff, base_seed + attempt)
            key  = tuple(grid)
            if key not in used_shapes:
                used_shapes.add(key)
                break
            attempt += 1

        shapes.append({"namn": namn, "grid": grid})

    svg = generate_svg(shapes)

    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Sparade {len(shapes)} former → {OUTPUT_SVG}")


if __name__ == "__main__":
    main()

