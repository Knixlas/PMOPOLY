"""Bygg provark och tryckfiler ur kortdata/*.xlsx.

    python tryck/bygg_tryck.py prov         # provark (A4) för granskning -> tryck/ut/provark.pdf + .png
Tryckeri-PDF:er (ett kort per sida, 3 mm utfall, skärmärken) byggs när provarket är godkänt.
"""
import asyncio
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
    if sys.argv[1:2] == ["prov"]:
        asyncio.run(skriv(provark(), UT / "provark.pdf", UT / "provark.png"))
        print("Skrev", UT / "provark.pdf")
