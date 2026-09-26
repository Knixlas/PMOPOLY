"""Bygg provark och tryckfiler ur kortdata/*.xlsx.

    python tryck/bygg_tryck.py prov          # provark (A4) för granskning -> tryck/ut/provark.pdf + .png
    python tryck/bygg_tryck.py tryck [lek]   # tryckeri-PDF:er -> tryck/ut/<lek>_tryckeri.pdf
    python tryck/bygg_tryck.py kontroll      # hittar kortsidor där text krockar med foten

Tryckfilerna följer de gamla: ett motiv per sida, 3 mm utfall, skärmärken, bildsida och textsida
växelvis (sida 1 = kort 1 fram, sida 2 = kort 1 bak …), varje kort × "Antal exemplar".
"""
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor.data import las_lek  # noqa: E402
import kortmallar as km  # noqa: E402

ROT = Path(__file__).resolve().parent
UT = ROT / "ut"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# Bahnschrift hämtas från Niklas Adobe Fonts-licens via ett webbkit (Regular 400 och Bold 700).
# Typsnittet sparas aldrig på disk eller i repot: Chromiums anrop till Typekit hämtas av Python
# (verifierad TLS via miljöns CA) och lämnas direkt till sidan. Byt kit med miljövariabeln ADOBE_KIT.
ADOBE_KIT = os.environ.get("ADOBE_KIT", "rex1ldm")   # kitet "ÅKEPOL tryck" på fonts.adobe.com


def sida(innehall, extra_css=""):
    # Adobe-kitets teckenurval saknar minustecknet (U+2212): tankstreck som i trycket
    innehall = innehall.replace("\u2212", "\u2013")
    css = (ROT / "kort.css").read_text(encoding="utf-8")
    return f"""<!doctype html><html lang="sv"><head><meta charset="utf-8"><base href="{ROT.as_uri()}/">
<link rel="stylesheet" href="https://use.typekit.net/{ADOBE_KIT}.css">
<style>{css}{extra_css}</style></head><body>{innehall}</body></html>"""


async def _typekit(route, req):
    import requests
    h = {k: v for k, v in req.headers.items() if k.lower() in ("accept", "user-agent", "referer", "origin")}
    try:
        r = await asyncio.to_thread(requests.get, req.url, headers=h, timeout=30)
    except requests.RequestException:
        await route.abort()
        return
    await route.fulfill(status=r.status_code, body=r.content,
                        headers={"content-type": r.headers.get("content-type", "application/octet-stream"),
                                 "access-control-allow-origin": "*"})


async def ny_sida(p):
    """Starta Chromium med Typekit-hämtningen på plats. Returnerar (webbläsare, sida)."""
    b = await p.chromium.launch(executable_path=CHROME)
    s = await b.new_page()
    await s.route("https://*.typekit.net/**", _typekit)
    return b, s


VARNAT = []


async def ladda(s, uri):
    """Öppna sidan och vänta in typsnitten. Varnar en gång om Bahnschrift inte laddades."""
    await s.goto(uri)
    ok = await s.evaluate("""async () => {
        await document.fonts.ready;
        const f = await Promise.all(['400', '700'].map(w => document.fonts.load(w + ' 12px bahnschrift')));
        return f.every(l => l.some(x => x.family.toLowerCase() === 'bahnschrift'));
    }""")
    if not ok and not VARNAT:
        VARNAT.append(1)
        print("VARNING: Bahnschrift laddades inte (nät/kit) – ersättningstypsnittet används.", file=sys.stderr)
    return ok


def provark():
    hk = las_lek("F_händelsekort.xlsx")
    nk = las_lek("F_nätverkskort.xlsx")
    fc = las_lek("F_FC.xlsx")
    pu = las_lek("PU_projekt.xlsx")
    val = [next(k for k in hk if k["Effekt"] == eff and k["Typ"] == "HYRESRÄTT")
           for eff in ("dolt_plus_dn", "underhallsvarning", "inget")]
    sma = [km.handelsekort(val[0])[0]] + [km.handelsekort(k)[1] for k in val]
    sma += [km.natverkskort(nk[0])[0]] + [km.natverkskort(k)[1] for k in (nk[5], nk[70])]
    sma += [km.fc_kort(next(k for k in fc if k["Namn"] == "Bostadsveteranen")),
            km.fc_kort(next(k for k in fc if k["Namn"] == "Bostadsveteranen"), senior=True)]
    draklyan = next(p for p in pu if p["Namn"] == "Förskolan Draklyan")
    stora = [km.projekt_framsida(draklyan), km.projekt_textsida(draklyan)]
    css = """body { background: #fff; } .ark { width: 210mm; padding: 8mm; display: flex; flex-wrap: wrap; gap: 4mm; }
             .ark .kort { outline: .2mm solid #ccc; } h1 { font-size: 11pt; padding: 8mm 8mm 0; }"""
    return sida(f'<h1>ÅKEPOL · provark, Förvaltning och projektkort</h1><div class="ark">{"".join(sma)}</div>'
                f'<div class="ark">{"".join(stora)}</div>', css)


UTFALL, MARK = 3, 5          # mm: utfall och plats för skärmärken

LEKAR = {   # lek -> (Excel, format (b, h) mm, funktion kort -> [sidor])
    "F_händelsekort": ("F_händelsekort.xlsx", (58, 88), lambda k: list(km.handelsekort(k))),
    "F_nätverkskort": ("F_nätverkskort.xlsx", (58, 88), lambda k: list(km.natverkskort(k))),
    "F_kvartalskort": ("F_kvartalskort.xlsx", (58, 88), lambda k: list(km.kvartalskort(k))),
    "F_omvärldskort": ("F_omvärldskort.xlsx", (58, 88), lambda k: list(km.omvarldskort(k))),
    "F_DD": ("F_DD.xlsx", (58, 88), lambda k: list(km.ddkort(k))),
    "F_FC": ("F_FC.xlsx", (58, 88), lambda k: [km.fc_kort(k), km.fc_kort(k, senior=True)]),
    "F_FS": ("F_FS.xlsx", (58, 88), lambda k: [km.fs_kort(k), km.fs_kort(k, senior=True)]),
    "PU_projekt": ("PU_projekt.xlsx", (88, 146), lambda k: [km.projekt_framsida(k), km.projekt_textsida(k)]),
}


def skarmarken(b, h):
    """Öppna skärmärken i hörnen, utanför utfallet."""
    x0, y0, x1, y1 = MARK + UTFALL, MARK + UTFALL, MARK + UTFALL + b, MARK + UTFALL + h
    W, H = b + 2 * (MARK + UTFALL), h + 2 * (MARK + UTFALL)
    l = []
    for x in (x0, x1):
        l += [(x, 0, x, MARK), (x, H - MARK, x, H)]
    for y in (y0, y1):
        l += [(0, y, MARK, y), (W - MARK, y, W, y)]
    streck = "".join(f'<line x1="{a}" y1="{b_}" x2="{c}" y2="{d}"/>' for a, b_, c, d in l)
    return (f'<svg class="marken" viewBox="0 0 {W} {H}" style="width:{W}mm;height:{H}mm">'
            f'<g stroke="#000" stroke-width="0.12">{streck}</g></svg>')


def tryckark(lek):
    fil, (b, h), sidor = LEKAR[lek]
    W, H = b + 2 * (MARK + UTFALL), h + 2 * (MARK + UTFALL)
    delar = []
    for k in las_lek(fil):
        for _ in range(int(k.get("Antal exemplar") or 1)):
            for sida_ in sidor(k):
                bg = re.search(r"--bg:(#[0-9a-fA-F]{6})", sida_)
                delar.append(f'<div class="ark" style="width:{W}mm;height:{H}mm">{skarmarken(b, h)}'
                             f'<div class="utfall" style="left:{MARK}mm;top:{MARK}mm;width:{b + 2 * UTFALL}mm;'
                             f'height:{h + 2 * UTFALL}mm;background:{bg.group(1) if bg else "#fff"}"></div>'
                             f'<div class="plats" style="left:{MARK + UTFALL}mm;top:{MARK + UTFALL}mm">{sida_}</div></div>')
    css = (f"@page {{ size: {W}mm {H}mm; margin: 0; }} .ark {{ position: relative; overflow: hidden; break-after: page; }}"
           ".marken, .utfall, .plats { position: absolute; } .marken { left: 0; top: 0; }")
    return sida("".join(delar), css), (W, H), len(delar)


async def skriv_tryck(lek):
    from playwright.async_api import async_playwright
    html_, (W, H), antal = tryckark(lek)
    UT.mkdir(exist_ok=True)
    tmp = UT / f"{lek}_tryckeri.html"
    tmp.write_text(html_, encoding="utf-8")
    async with async_playwright() as p:
        b, s = await ny_sida(p)
        await ladda(s, tmp.as_uri())
        await s.pdf(path=str(UT / f"{lek}_tryckeri.pdf"), width=f"{W}mm", height=f"{H}mm", print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        await b.close()
    tmp.unlink()
    return antal


async def skriv(html_, pdf, png=None):
    from playwright.async_api import async_playwright
    UT.mkdir(exist_ok=True)
    tmp = UT / (pdf.stem + ".html")
    tmp.write_text(html_, encoding="utf-8")
    async with async_playwright() as p:
        b, s = await ny_sida(p)
        await ladda(s, tmp.as_uri())
        await s.pdf(path=str(pdf), format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        if png:
            await s.set_viewport_size({"width": 800, "height": 1100})
            await s.screenshot(path=str(png), full_page=True)
        await b.close()


if __name__ == "__main__":
    if sys.argv[1:2] == ["tryck"]:
        for lek in sys.argv[2:] or LEKAR:
            print(f"{lek}: {asyncio.run(skriv_tryck(lek))} sidor -> {UT / (lek + '_tryckeri.pdf')}")
    if sys.argv[1:2] == ["prov"]:
        asyncio.run(skriv(provark(), UT / "provark.pdf", UT / "provark.png"))
        print("Skrev", UT / "provark.pdf")


async def kontrollera():
    """Hitta kort där innehållet krockar med foten eller går utanför kortet."""
    from playwright.async_api import async_playwright
    fel = []
    async with async_playwright() as p:
        b, s = await ny_sida(p)
        for lek in LEKAR:
            html_, _, _ = tryckark(lek)
            tmp = UT / f"_kontroll_{lek}.html"
            tmp.write_text(html_, encoding="utf-8")
            await ladda(s, tmp.as_uri())
            res = await s.evaluate("""() => [...document.querySelectorAll('.kort')].map((k, i) => {
                const kr = k.getBoundingClientRect();
                const fot = k.querySelector('.fot'); const lista = k.querySelector('.list');
                const grans = fot ? fot.getBoundingClientRect().top : (lista ? lista.getBoundingClientRect().top : kr.bottom);
                const barn = [...k.querySelectorAll('.regel, .egenskap, .stamning, .p-tal, .p-regel, .p-besk, .f-under')];
                const over = barn.filter(e => e.getBoundingClientRect().bottom > grans - 1).map(e => e.className);
                // tabeller som blivit bredare än sin spalt (värden bryts inte längre, de sticker ut)
                k.querySelectorAll('.p-tal').forEach(t => { if (t.getBoundingClientRect().right > t.parentElement.getBoundingClientRect().right + 1) over.push('p-tal bred'); });
                return {i, over, text: (k.querySelector('.t-rubrik, .p-namn, .f-rubrik') || {}).textContent};
            }).filter(r => r.over.length)""")
            for r in res:
                fel.append((lek, r["i"], (r["text"] or "").strip(), r["over"]))
            tmp.unlink()
        await b.close()
    return fel


if __name__ == "__main__" and sys.argv[1:2] == ["kontroll"]:
    fel = asyncio.run(kontrollera())
    for f in fel:
        print("KROCK", f)
    print(f"{len(fel)} kortsidor med krock")
