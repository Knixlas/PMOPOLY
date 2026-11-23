"""
docx_to_markdown.py
===================
Konverterar ÅKEPOL_Regelbok.docx (eller annan strukturerad docx) till ren
Markdown med extraherade bilder och callouts som blockquotes istället för
fula HTML-tabeller.

Pipeline:
1. pandoc → grov markdown + extraherade bilder
2. Post-processor → städar HTML-block, lägger bilder i bilder/

Användning:
    python docx_to_markdown.py "ÅKEPOL_Regelbok.docx"
    python docx_to_markdown.py "ÅKEPOL_Regelbok.docx" --output-dir ut/

Kräver:
    pandoc installerat (https://pandoc.org/installing.html)
    Python 3.10+
"""

from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Post-processor
# ---------------------------------------------------------------------------

def clean_text(s: str) -> str:
    """Normalisera HTML-formatering till markdown."""
    s = re.sub(r'<br\s*/?>', '', s).strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'<strong>(.*?)</strong>', r'**\1**', s)
    s = re.sub(r'<em>(.*?)</em>', r'*\1*', s)
    s = re.sub(r'<img\s+src="([^"]+)"[^>]*/?>', r'![](\1)', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s.strip()


def extract_lines_from_row(row: str) -> list[str]:
    """Plocka ut text/bild ur en <tr>. Hanterar både <p>-wrappade och rena <td>."""
    paras = re.findall(r'<p>(.*?)</p>', row, flags=re.DOTALL)
    if paras:
        return [t for t in (clean_text(p) for p in paras) if t]
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.DOTALL)
    out: list[str] = []
    for c in cells:
        for part in re.split(r'(<img[^>]+/?>)', c):
            t = clean_text(part)
            if t:
                out.append(t)
    return out


def html_table_to_blockquote(match: re.Match) -> str:
    block = match.group(0)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', block, flags=re.DOTALL)
    output = []
    for row in rows:
        lines = extract_lines_from_row(row)
        if lines:
            # Tom > -rad mellan stycken så markdown gör dem till separata <p>
            output.append('\n>\n'.join(f'> {ln}' for ln in lines))
    return ('\n\n'.join(output) + '\n') if output else ''


def md_imagecell_to_blockquote(match: re.Match) -> str:
    cell = match.group(1).strip()
    cell = re.sub(r'<img\s+src="([^"]+)"[^>]*/?>', r'![](\1)', cell)
    img_match = re.match(r'(!\[[^\]]*\]\([^)]+\))\s*(.*)', cell, flags=re.DOTALL)
    if img_match:
        return f'> {img_match.group(1)}\n> {img_match.group(2).strip()}\n'
    return f'> {cell}\n'


def post_process(text: str, media_prefix: str) -> str:
    """Konvertera grov pandoc-markdown till ren markdown."""
    text = re.sub(r'<table[^>]*>.*?</table>', html_table_to_blockquote, text, flags=re.DOTALL)
    text = re.sub(
        r'\|\s+\|\s*\n\|[-\s|]+\|\s*\n\|\s*(<img[^|]+)\|\s*\n',
        md_imagecell_to_blockquote,
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r'<img\s+src="([^"]+)"[^>]*/?>', r'![](\1)', text)
    text = re.sub(r'\*\*\s*\n\s*\*\*', '', text)
    text = re.sub(r'^##\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Bildvägar: ersätt vad pandoc än genererade (oavsett mappnamn)
    # Matchar bara INUTI markdown-bildsyntax ![](...) eller HTML-attribut
    text = re.sub(
        r'(\!\[[^\]]*\]\()[^\)]*?/media/(image[^\)]+\))',
        r'\1bilder/\2',
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# METADATA: HEADERTEXT OCH PRIMÄRFÄRG (per docx)
# ---------------------------------------------------------------------------

def derive_header_text(stem: str) -> str:
    """ÅKEPOL_Förvaltningsplan → 'ÅKEPOL · Förvaltningsplan'."""
    if '_' in stem:
        prefix, rest = stem.split('_', 1)
        return f"{prefix} · {rest.replace('_', ' ')}"
    return stem


def extract_primary_color(docx_path: Path) -> str | None:
    """Hämta primärfärgen från rubriknivå 1 i docx, eller None.

    Letar efter den stil som har <w:outlineLvl w:val="0"/> (= H1 oavsett
    språk i Word: 'Heading1' på engelska, 'Rubrik1' på svenska, etc.).
    """
    try:
        with zipfile.ZipFile(docx_path) as z:
            styles = z.read('word/styles.xml').decode('utf-8')
    except (KeyError, FileNotFoundError, zipfile.BadZipFile):
        return None

    # Iterera över alla stilar och hitta den med outlineLvl=0
    for m in re.finditer(
        r'<w:style[^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>',
        styles,
        flags=re.DOTALL,
    ):
        body = m.group(2)
        if '<w:outlineLvl w:val="0"' not in body:
            continue
        color_m = re.search(r'<w:color w:val="([A-Fa-f0-9]{6})"', body)
        if color_m:
            return f'#{color_m.group(1).upper()}'

    # Fallback: leta direkt efter typiska H1-stilnamn
    for sid in ('Heading1', 'Rubrik1', 'Heading 1', 'Rubrik 1', 'berskrift1'):
        m = re.search(
            rf'<w:style[^>]*w:styleId="{re.escape(sid)}"[^>]*>(.*?)</w:style>',
            styles,
            flags=re.DOTALL,
        )
        if m:
            color_m = re.search(r'<w:color w:val="([A-Fa-f0-9]{6})"', m.group(1))
            if color_m:
                return f'#{color_m.group(1).upper()}'
    return None


def derive_color_palette(primary_hex: str, cream_hex: str = '#FAF0DD') -> dict[str, str]:
    """Räkna fram (primary, soft, tint) ur primärfärgen och cremebakgrunden."""
    def hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip('#')
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
        r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
        return f'#{r:02X}{g:02X}{b:02X}'

    def mix(a: tuple, b: tuple, t: float) -> tuple:
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

    p = hex_to_rgb(primary_hex)
    c = hex_to_rgb(cream_hex)
    return {
        'primary': rgb_to_hex(p),
        'soft':    rgb_to_hex(mix(p, c, 0.50)),  # 50/50 mix → tabellramar/tabellheader
        'tint':    rgb_to_hex(mix(p, c, 0.85)),  # 15% primary → callout-bakgrund
    }


def build_front_matter(docx_path: Path) -> str:
    """Bygg YAML-frontmatter med headertext + färgpalett."""
    header = derive_header_text(docx_path.stem)
    primary = extract_primary_color(docx_path) or '#8B2920'
    palette = derive_color_palette(primary)
    return (
        '---\n'
        f'header: {header}\n'
        f'color_primary: {palette["primary"]}\n'
        f'color_soft: {palette["soft"]}\n'
        f'color_tint: {palette["tint"]}\n'
        '---\n\n'
    )


# ---------------------------------------------------------------------------
def run_pandoc(docx: Path, work_dir: Path) -> Path:
    """Kör pandoc → markdown + extraherad media."""
    work_dir.mkdir(parents=True, exist_ok=True)
    md_file = work_dir / 'raw.md'
    cmd = [
        'pandoc',
        str(docx),
        '--to', 'gfm',
        '--wrap=preserve',
        f'--extract-media={work_dir}',
        '-o', str(md_file),
    ]
    subprocess.run(cmd, check=True)
    return md_file


def safe_rmtree(path: Path, max_retries: int = 6) -> None:
    """Robust rmtree för Windows där AV/indexerare kan hålla filer låsta kort.

    Försöker upp till max_retries gånger med exponentiellt växande väntan.
    Varnar och fortsätter om slutgiltigt misslyckande — work_dir är temporärt
    och kan tas bort manuellt senare utan konsekvenser.
    """
    delay = 0.2
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return
        except (PermissionError, OSError) as exc:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 1.6  # 0.2, 0.32, 0.51, 0.82, 1.31, totalt ~3.2s
            else:
                print(f'  [VARNING] Kunde inte rensa {path}: {exc}')
                print(f'  [VARNING] Filen kan tas bort manuellt senare.')


# ---------------------------------------------------------------------------
# BILDROTATION (Word lagrar bilder med rot-transform i XML, som pandoc tappar)
# ---------------------------------------------------------------------------

_OOXML_NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}
_REL_NS = '{http://schemas.openxmlformats.org/package/2006/relationships}'
_EMBED_ATTR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'


def find_image_rotations(docx_path: Path) -> dict[str, float]:
    """Returnera {filnamn: vinkel_grader} för alla bilder i docx med rotation.

    OOXML lagrar rotationen i 60000-delar av en grad och positiv = medurs.
    """
    rotations: dict[str, float] = {}
    try:
        with zipfile.ZipFile(docx_path) as z:
            # rId → filnamn
            rels = ET.fromstring(z.read('word/_rels/document.xml.rels'))
            rel_map = {}
            for r in rels.findall(f'{_REL_NS}Relationship'):
                target = r.get('Target', '')
                if 'media/' in target:
                    rel_map[r.get('Id')] = target.rsplit('/', 1)[-1]

            doc = ET.fromstring(z.read('word/document.xml'))
            for pic in doc.iter(f'{{{_OOXML_NS["pic"]}}}pic'):
                xfrm = pic.find('.//a:xfrm[@rot]', _OOXML_NS)
                if xfrm is None:
                    continue
                try:
                    rot_deg = int(xfrm.get('rot', '0')) / 60000
                except ValueError:
                    continue
                if rot_deg == 0:
                    continue
                blip = pic.find('.//a:blip', _OOXML_NS)
                if blip is None:
                    continue
                embed = blip.get(_EMBED_ATTR)
                if embed and embed in rel_map:
                    rotations[rel_map[embed]] = rot_deg
    except (KeyError, ET.ParseError):
        pass
    return rotations


def apply_rotations(rotations: dict[str, float], bilder_dir: Path) -> None:
    """Rotera filer i bilder_dir enligt {filnamn: vinkel_grader}."""
    if not rotations:
        return
    try:
        from PIL import Image  # noqa: WPS433
    except ImportError:
        print('  [!] Pillow (PIL) saknas — kan inte korrigera bildrotationer.')
        print('      Installera med: pip install Pillow')
        return

    for filename, degrees in rotations.items():
        img_path = bilder_dir / filename
        if not img_path.exists():
            continue
        try:
            # Context manager säkerställer att filhandtaget släpps direkt
            with Image.open(img_path) as img:
                # Tvinga ladda hela bilden i minne (annars är filen kvar låst)
                img.load()
                rotated = img.rotate(-degrees, expand=True, resample=Image.BICUBIC)
            # Spara först efter att filen är stängd
            save_kwargs = {'quality': 95} if img_path.suffix.lower() in ('.jpg', '.jpeg') else {}
            rotated.save(img_path, **save_kwargs)
            print(f'  Roterade {filename}: {degrees:g}°')
        except Exception as exc:  # noqa: BLE001
            print(f'  [!] Kunde inte rotera {filename}: {exc}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Konvertera docx till ren markdown.')
    parser.add_argument('docx', type=Path, help='Indata, .docx-fil')
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=None,
        help='Outputmapp (default: <docx-stem>_md/)',
    )
    args = parser.parse_args()

    if not args.docx.exists():
        print(f'Fel: hittar inte {args.docx}', file=sys.stderr)
        return 1

    if shutil.which('pandoc') is None:
        print('Fel: pandoc är inte installerat. Se https://pandoc.org/installing.html', file=sys.stderr)
        return 1

    output_dir = args.output_dir or args.docx.parent / f'{args.docx.stem}_md'
    output_dir.mkdir(parents=True, exist_ok=True)
    bilder_dir = output_dir / 'bilder'
    bilder_dir.mkdir(exist_ok=True)

    # 1. pandoc till temporärt arbetsutrymme
    work_dir = output_dir / '_work'
    work_dir.mkdir(exist_ok=True)
    raw_md = run_pandoc(args.docx, work_dir)

    # 2. flytta media → bilder/
    media_src = work_dir / 'media'
    if media_src.exists():
        for img in media_src.iterdir():
            shutil.copy(img, bilder_dir / img.name)

    # 2b. korrigera ev. roterade bilder (Word-XML säger "rot", men pandoc
    #     tappar transformen så pixeldata ligger fel)
    rotations = find_image_rotations(args.docx)
    if rotations:
        apply_rotations(rotations, bilder_dir)

    # 3. post-process
    raw_text = raw_md.read_text(encoding='utf-8')
    media_prefix = f'{work_dir.name}/media/'
    cleaned = post_process(raw_text, media_prefix)

    # Lägg till YAML-frontmatter (header + färgpalett från docx)
    front_matter = build_front_matter(args.docx)
    cleaned = front_matter + cleaned

    out_md = output_dir / f'{args.docx.stem}.md'
    out_md.write_text(cleaned, encoding='utf-8')

    # 4. städa work_dir (med retry-logik mot Windows-AV som kan låsa filer kort)
    safe_rmtree(work_dir)

    # 5. rapport
    print(f'\nKlart. Output i: {output_dir}')
    print(f'  Markdown:  {out_md.name}')
    print(f'  Bilder:    {len(list(bilder_dir.iterdir()))} st i bilder/')
    print(f'  Storlek:   {out_md.stat().st_size:,} tecken, '
          f'{cleaned.count(chr(10))} rader')
    print(f'  Tabeller:  {cleaned.count(chr(10) + "|")} markdownrader')
    print(f'  Callouts:  {len(re.findall(r"^>", cleaned, re.MULTILINE))} blockquoterader')
    return 0


if __name__ == '__main__':
    sys.exit(main())

