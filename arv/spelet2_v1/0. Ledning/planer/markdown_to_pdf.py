"""
markdown_to_pdf.py
==================
Konverterar ren Markdown (output från docx_to_markdown.py) till en stylad PDF
som matchar plan-templatens cremebakgrund, burgundy-serif och italic-callouts.

Pipeline:
    1. Markdown → HTML (markdown-bibliotek + extensions)
    2. Post-processera HTML (cover-page, del-divider, tomma table-headers)
    3. HTML + CSS → PDF (WeasyPrint)

Användning:
    python markdown_to_pdf.py akepol_regelbok.md
    python markdown_to_pdf.py akepol_regelbok.md --output regelbok.pdf

Kräver:
    pip install markdown weasyprint
    Ett "template/regelbok.css" och "template/regelbok.html" i samma mapp som
    skriptet.
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import markdown as md_lib
from weasyprint import HTML, CSS


# ---------------------------------------------------------------------------
# YAML FRONT MATTER (headertext + färg från docx)
# ---------------------------------------------------------------------------

def parse_front_matter(md_text: str) -> tuple[dict[str, str], str]:
    """Plocka ut YAML-frontmatter och returnera (metadata, rest av md)."""
    if not md_text.startswith('---\n'):
        return {}, md_text
    end = md_text.find('\n---\n', 4)
    if end == -1:
        return {}, md_text
    block = md_text[4:end]
    body = md_text[end + 5:].lstrip('\n')
    metadata: dict[str, str] = {}
    for line in block.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            metadata[k.strip()] = v.strip()
    return metadata, body


def build_override_css(metadata: dict[str, str]) -> str:
    """Bygg CSS som overridar header och färgpalett baserat på metadata."""
    parts: list[str] = []
    header = metadata.get('header')
    if header:
        # CSS-escape: dubbla citattecken och bakåtsneck
        h = header.replace('\\', '\\\\').replace('"', '\\"')
        parts.append(f'@page {{ @top-left {{ content: "{h}"; }} }}')
    primary = metadata.get('color_primary')
    soft = metadata.get('color_soft')
    tint = metadata.get('color_tint')
    if primary or soft or tint:
        root_decls = []
        if primary:
            root_decls.append(f'--burgundy: {primary};')
        if soft:
            root_decls.append(f'--burgundy-soft: {soft};')
        if tint:
            root_decls.append(f'--burgundy-tint: {tint};')
        parts.append(':root { ' + ' '.join(root_decls) + ' }')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# COVER-DETEKTION
# ---------------------------------------------------------------------------

def split_cover(md_text: str) -> tuple[dict, str]:
    """
    Plocka ut cover-sidans innehåll (allt innan första H1).

    Markdown-källan börjar typiskt:
        **ÅKEPOL**
        Regelhäfte
        *Ett utbildningsspel om ...*
        Åke Sundvalls Byggnads AB
        1–4 kvarter · Utbildningsspel
        **DEL I INTRODUKTION**
        # 1. Välkommen till Åkepol  ← split här

    Returnerar (cover_dict, body_md).
    """
    # Hitta första H1
    m = re.search(r'^# .+$', md_text, re.MULTILINE)
    if not m:
        return {}, md_text

    cover_raw = md_text[:m.start()].strip()
    body = md_text[m.start():]

    lines = [ln.strip() for ln in cover_raw.splitlines() if ln.strip()]
    if not lines:
        return {}, body

    cover: dict[str, str] = {}
    # Heuristik på rader
    for i, line in enumerate(lines):
        clean = line.strip()
        # Strippa **/*-paret
        bare = re.sub(r'^\*+|\*+$', '', clean).strip()

        if i == 0 and clean.startswith('**'):
            cover['title'] = bare
        elif 'subtitle' not in cover and i == 1:
            cover['subtitle'] = bare
        elif clean.startswith('*') and 'tagline' not in cover:
            cover['tagline'] = bare
        elif ' AB' in clean and 'org' not in cover:
            cover['org'] = bare
        elif '·' in clean and 'meta' not in cover:
            cover['meta'] = bare
        elif clean.upper().startswith('**DEL'):
            # första del-rubrik — hör till body, men just denna rad slängs
            # eftersom body börjar vid första H1 ändå
            pass

    return cover, body


# ---------------------------------------------------------------------------
# MARKDOWN → HTML
# ---------------------------------------------------------------------------

def markdown_to_html(md_text: str) -> str:
    """Konvertera markdown till HTML med utvalda extensions."""
    extensions = [
        'tables',          # pipe-tabeller
        'sane_lists',      # bättre listhantering
        'attr_list',       # {.class}-stöd om det skulle behövas
    ]
    return md_lib.markdown(md_text, extensions=extensions)


def post_process_html(html: str) -> str:
    """
    Städa HTML från markdown-konvertering:
    - Markera tomma <thead>-rader så de kan döljas via CSS
    - Lägg klass på definition-tabeller (utan header)
    - Lyft fram **DEL I/II/III**-rader som part-dividers
    - Wrappa varje rubrik med sitt första efterföljande stycke i en
      keep-together-div så de inte separeras över sidbrytningar
    """
    # Tomma <th></th>-headers (definition-tabeller)
    html = re.sub(
        r'<thead>\s*<tr>\s*((?:<th[^>]*>\s*</th>\s*)+)</tr>\s*</thead>',
        r'<thead><tr class="empty-header">\1</tr></thead>',
        html,
    )
    # Tabeller med tom thead → markera som no-header
    html = re.sub(
        r'<table>(\s*<thead><tr class="empty-header">)',
        r'<table class="no-header">\1',
        html,
    )

    # Del-rubriker: rader som bara är "<p><strong>DEL I INTRODUKTION</strong></p>"
    html = re.sub(
        r'<p><strong>(DEL [IVX]+ +[A-ZÅÄÖ\s]+)</strong></p>',
        r'<div class="part-divider">\1</div>',
        html,
    )

    # Håll ihop rubrik + första stycke (+ ev. tabell/lista) över sidbrytningar.
    # Mönster: rubrik, sedan VALFRITT första stycke, sedan VALFRITT
    # tabell/ul/ol/blockquote. Wrappar i keep-together-div om något följer.
    keep_together_pattern = re.compile(
        r'(?P<heading><h[1-6][^>]*>.*?</h[1-6]>)'
        r'(?:\s*(?P<para><p(?![^>]*\bclass=)[^>]*>.*?</p>))?'
        r'(?:\s*(?P<block><(?P<bt>table|ul|ol|blockquote)[^>]*>.*?</(?P=bt)>))?',
        flags=re.DOTALL,
    )

    def _wrap_keep_together(m: re.Match) -> str:
        heading = m.group('heading')
        para = m.group('para') or ''
        block = m.group('block') or ''
        if not para and not block:
            return heading  # ingenting att hålla ihop med
        return f'<div class="keep-together">{heading}{para}{block}</div>'

    html = keep_together_pattern.sub(_wrap_keep_together, html)

    # Ta bort tomma rubriker (t.ex. "<h1></h1>" från " #  "-rader i källan)
    html = re.sub(
        r'<(h[1-6])[^>]*>\s*</\1>',
        '',
        html,
    )

    # Sätt in en sidbrytare före varje H1 utom den första.
    # Hanterar både wrappad <div class="keep-together"><h1>… och bar <h1>.
    h1_anchor = re.compile(
        r'(<div class="keep-together"[^>]*>\s*)?<h1[^>]*>',
        flags=re.DOTALL,
    )
    matches = list(h1_anchor.finditer(html))
    if len(matches) > 1:
        # Bygg om strängen från slutet så vi inte rubbar offsets
        parts: list[str] = []
        last_end = len(html)
        for m in reversed(matches[1:]):
            parts.append(html[m.start():last_end])
            parts.append('<div class="h1-pagebreak"></div>')
            last_end = m.start()
        parts.append(html[:last_end])
        html = ''.join(reversed(parts))

    return html


# ---------------------------------------------------------------------------
# HTML-MALL
# ---------------------------------------------------------------------------

def build_full_html(cover: dict, body_html: str) -> str:
    """Bygg komplett HTML med cover-sida + body."""
    cover_html = ''
    if cover:
        cover_html = f"""
<div class="cover">
    <div class="cover-band-top">
        <div class="left">{cover.get('title', '')} · {cover.get('subtitle', '')}</div>
        <div class="right">{cover.get('org', '')}<br>KONFIDENTIELL</div>
    </div>
    <div class="cover-title">{cover.get('title', '')}</div>
    <div class="cover-subtitle">{cover.get('subtitle', '')}</div>
    <div class="cover-tagline">{cover.get('tagline', '')}</div>
    <div class="cover-org">{cover.get('org', '')}</div>
    <div class="cover-meta">{cover.get('meta', '')}</div>
    <div class="cover-bottom-line"></div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>{cover.get('title', 'Regelhäfte')}</title>
</head>
<body>
{cover_html}
<main>
{body_html}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HUVUDFLÖDE
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description='Konvertera markdown till stylad PDF.')
    parser.add_argument('markdown', type=Path, help='Indata, .md-fil')
    parser.add_argument('--output', '-o', type=Path, default=None,
                        help='Output-PDF (default: <stem>.pdf)')
    parser.add_argument('--css', type=Path, default=None,
                        help='CSS-fil (default: template/regelbok.css)')
    parser.add_argument('--with-cover', action='store_true',
                        help='Generera coversida från markdown-källans titelblock '
                             '(default: ingen cover — för plansamfogning där '
                             'coversidan kommer från extern PDF per bolag)')
    parser.add_argument('--keep-html', action='store_true',
                        help='Spara även HTML för felsökning')
    args = parser.parse_args()

    if not args.markdown.exists():
        print(f'Fel: hittar inte {args.markdown}', file=sys.stderr)
        return 1

    script_dir = Path(__file__).parent
    css_path = args.css or (script_dir / 'template' / 'regelbok.css')
    if not css_path.exists():
        print(f'Fel: hittar inte CSS-mall {css_path}', file=sys.stderr)
        return 1

    md_text = args.markdown.read_text(encoding='utf-8')

    # Plocka ut YAML-frontmatter (header + färg) först
    metadata, md_text = parse_front_matter(md_text)

    if args.with_cover:
        cover, body_md = split_cover(md_text)
    else:
        # Hoppa över titelblocket helt (allt innan första H1)
        cover = {}
        m = re.search(r'^# .+$', md_text, re.MULTILINE)
        body_md = md_text[m.start():] if m else md_text

    body_html = markdown_to_html(body_md)
    body_html = post_process_html(body_html)
    full_html = build_full_html(cover, body_html)

    base_url = str(args.markdown.parent.resolve()) + '/'
    out = args.output or args.markdown.with_suffix('.pdf')

    if args.keep_html:
        html_out = out.with_suffix('.html')
        html_out.write_text(full_html, encoding='utf-8')
        print(f'  HTML:     {html_out.name}')

    print(f'  Renderar PDF{"  (med cover)" if args.with_cover else "  (utan cover)"}...')

    # Bygg stylesheet-listan: huvud-CSS först, sedan override för
    # headertext + primärfärg från front matter (kommer SENARE i kaskaden).
    stylesheets = [CSS(filename=str(css_path))]
    override = build_override_css(metadata)
    if override:
        stylesheets.append(CSS(string=override))

    HTML(string=full_html, base_url=base_url).write_pdf(
        str(out),
        stylesheets=stylesheets,
    )

    print(f'\nKlart: {out}')
    print(f'  Storlek: {out.stat().st_size / 1024:.1f} KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())

