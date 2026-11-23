"""
Applicerar formmasker på bilder.

Stödda former (bildform-kolumn i CSV):
  rund       - cirkel
  romb       - 45°-roterad kvadrat
  hexagon    - sexhörning
  triangel   - uppåtpekande triangel
  kvadrat    - vanlig kvadrat (ingen mask, bara beskärning)
  pentagon   - femhörning
  stjärna    - femuddig stjärna
"""

import math
from PIL import Image, ImageDraw


def apply_mask(img: Image.Image, form: str) -> Image.Image:
    """
    Tar en kvadratisk RGBA-bild och returnerar en ny bild
    med transparent bakgrund utanför formen.
    """
    size = min(img.width, img.height)
    img = img.crop((
        (img.width  - size) // 2,
        (img.height - size) // 2,
        (img.width  + size) // 2,
        (img.height + size) // 2,
    )).convert("RGBA")

    form = form.strip().lower()

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    cx, cy = size / 2, size / 2
    r = size / 2 * 0.97  # lite innanför kanten

    if form in ("rund", "cirkel"):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)

    elif form in ("romb", "diamant"):
        pts = [
            (cx,     cy - r),
            (cx + r, cy    ),
            (cx,     cy + r),
            (cx - r, cy    ),
        ]
        draw.polygon(pts, fill=255)

    elif form == "hexagon":
        pts = _polygon_pts(cx, cy, r, 6, offset_angle=0)
        draw.polygon(pts, fill=255)

    elif form in ("triangel", "triangle"):
        pts = _polygon_pts(cx, cy, r, 3, offset_angle=-90)
        draw.polygon(pts, fill=255)

    elif form == "pentagon":
        pts = _polygon_pts(cx, cy, r, 5, offset_angle=-90)
        draw.polygon(pts, fill=255)

    elif form == "stjärna":
        pts = _star_pts(cx, cy, r, r * 0.45, 5, offset_angle=-90)
        draw.polygon(pts, fill=255)

    else:
        # kvadrat / okänd → ingen mask, returnera som den är
        return img

    # Kombinera alpha från bilden med formmasken (intersection, inte replace)
    result = img.copy()
    existing_alpha = result.getchannel("A")
    
    # Slutlig alpha = min(bildAlpha, maskAlpha) – transparent utanför formen OCH i bakgrunden
    from PIL import ImageChops
    combined_alpha = ImageChops.multiply(existing_alpha, mask.convert("L"))
    result.putalpha(combined_alpha)
    return result


def _polygon_pts(cx, cy, r, n, offset_angle=0):
    pts = []
    for i in range(n):
        angle = math.radians(offset_angle + i * 360 / n)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _star_pts(cx, cy, r_outer, r_inner, n, offset_angle=0):
    pts = []
    for i in range(n * 2):
        r = r_outer if i % 2 == 0 else r_inner
        angle = math.radians(offset_angle + i * 180 / n)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts

