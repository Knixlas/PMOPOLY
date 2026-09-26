"""Bygg provark och tryckfiler ur kortdata/*.xlsx.

    python tryck/bygg_tryck.py prov          # provark (A4) för granskning -> tryck/ut/provark.pdf + .png
    python tryck/bygg_tryck.py tryck [lek]   # tryckeri-PDF:er -> tryck/ut/<lek>_tryckeri.pdf

Tryckfilerna följer de gamla: ett motiv per sida, 3 mm utfall, skärmärken, bildsida och textsida
växelvis (sida 1 = kort 1 fram, sida 2 = kort 1 bak …), varje kort × "Antal exemplar".
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor.data import las_lek  # noqa: E402
import kortmallar as km  # noqa: E402

ROT = Path(__file__).resolve().parent
UT = ROT / "ut"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def sida(innehall, extra_css=""):
    css = (ROT / "kort.css").read_text(encoding="utf-8")
    return f"""<!doctype html><html lang="sv"><head><meta charset="utf-8"><base href="{ROT.as_uri()}/">
<style>{css}{extra_css}</style></head><body>{innehall}</body></html>"""


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
        b = await p.chromium.launch(executable_path=CHROME)
        s = await b.new_page()
        await s.goto(tmp.as_uri())
        await s.wait_for_timeout(500)
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
        b = await p.chromium.launch(executable_path=CHROME)
        s = await b.new_page()
        await s.goto(tmp.as_uri())
        await s.wait_for_timeout(300)
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
