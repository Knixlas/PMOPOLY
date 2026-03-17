"""Extract polyomino shape coordinates from project PNG images.

Uses the outline color (fill_color from CSV) to detect cell grid lines,
then checks which grid cells have content.
"""
import os
import json
import csv
import sys
from PIL import Image
import numpy as np

DIR_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMBILD_DIR = os.path.join(
    os.path.expanduser("~"),
    "OneDrive - Åke Sundvalls Byggnads AB",
    "SPELET 2", "1. Projektutveckling", "IC", "former", "temp"
)
CSV_PATH = os.path.join(DIR_BASE, "data", "1_projektutveckling", "PU_3_projekt.csv")
OUTPUT_PATH = os.path.join(DIR_BASE, "data", "shapes.json")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def load_projects():
    """Load project names and fill colors from CSV."""
    projects = {}
    with open(CSV_PATH, "r", encoding="latin-1") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        for row in reader:
            namn = row[0].strip()
            if not namn:
                continue
            fc = row[42].strip() if len(row) > 42 else ""
            projects[namn] = fc
    return projects


def smooth(arr, window=5):
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def find_borders(profile, threshold):
    """Find centers of runs above threshold."""
    borders = []
    in_peak = False
    start = 0
    for i, v in enumerate(profile):
        if v > threshold:
            if not in_peak:
                start = i
                in_peak = True
        else:
            if in_peak:
                borders.append((start + (i - 1)) // 2)
                in_peak = False
    if in_peak:
        borders.append((start + len(profile) - 1) // 2)
    return borders


def extract_shape(img_path, fill_color_hex):
    """Extract polyomino cells using outline color detection."""
    img = Image.open(img_path).convert("RGBA")
    pixels = np.array(img)

    oc = hex_to_rgb(fill_color_hex)
    tol = 15

    # Find pixels matching outline color
    is_outline = (
        (np.abs(pixels[:, :, 0].astype(int) - oc[0]) < tol) &
        (np.abs(pixels[:, :, 1].astype(int) - oc[1]) < tol) &
        (np.abs(pixels[:, :, 2].astype(int) - oc[2]) < tol) &
        (pixels[:, :, 3] > 200)
    )

    if not np.any(is_outline):
        return []

    # Per-row and per-column outline density
    row_density = smooth(np.mean(is_outline, axis=1), 5)
    col_density = smooth(np.mean(is_outline, axis=0), 5)

    # Adaptive threshold: border lines have higher density than pattern dots
    r_mean = np.mean(row_density[row_density > 0.001]) if np.any(row_density > 0.001) else 0.01
    c_mean = np.mean(col_density[col_density > 0.001]) if np.any(col_density > 0.001) else 0.01

    row_borders = find_borders(row_density, r_mean * 1.5)
    col_borders = find_borders(col_density, c_mean * 1.5)

    if len(row_borders) < 2 or len(col_borders) < 2:
        return []

    # Number of cell rows/cols = borders - 1
    nr = len(row_borders) - 1
    nc = len(col_borders) - 1

    # Check which cells have content (alpha > 0 or outline pixels)
    cells = []
    for r in range(nr):
        r_start = row_borders[r]
        r_end = row_borders[r + 1]
        for c in range(nc):
            c_start = col_borders[c]
            c_end = col_borders[c + 1]

            # Check alpha channel: any non-transparent pixels in this region?
            region_alpha = pixels[r_start:r_end + 1, c_start:c_end + 1, 3]
            alpha_ratio = np.mean(region_alpha > 0)

            if alpha_ratio > 0.5:  # More than half the region has content
                cells.append([r, c])

    # Normalize to origin
    if cells:
        min_r = min(c[0] for c in cells)
        min_c = min(c[1] for c in cells)
        cells = sorted([[c[0] - min_r, c[1] - min_c] for c in cells])

    return cells


def visualize(cells):
    if not cells:
        return "(empty)"
    max_r = max(c[0] for c in cells)
    max_c = max(c[1] for c in cells)
    cell_set = {(c[0], c[1]) for c in cells}
    lines = []
    for r in range(max_r + 1):
        line = ""
        for c in range(max_c + 1):
            line += "X" if (r, c) in cell_set else "."
        lines.append(line)
    return " ".join(lines)


def main():
    projects = load_projects()
    print(f"Loaded {len(projects)} projects")

    shapes = {}
    errors = []

    for namn, fill_color in sorted(projects.items()):
        png_path = os.path.join(FORMBILD_DIR, f"{namn}.png")
        if not os.path.exists(png_path):
            errors.append(f"MISSING: {namn}")
            continue

        if not fill_color:
            errors.append(f"NO COLOR: {namn}")
            continue

        cells = extract_shape(png_path, fill_color)
        shapes[namn] = cells

        vis = visualize(cells)
        print(f"  {namn}: {len(cells)} cells -> {vis}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(shapes, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(shapes)} shapes to {OUTPUT_PATH}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

    # Summary
    counts = {}
    for cells in shapes.values():
        n = len(cells)
        counts[n] = counts.get(n, 0) + 1
    print(f"\nCell count distribution: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
