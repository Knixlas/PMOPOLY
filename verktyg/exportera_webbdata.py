"""Exportera speldata och testfall till webbklienten (spel/webb).

- spel/webb/src/data/pussel.json   projekt (namn, typ, form, BTA), markexpansioner och bitarnas färger,
                                   ur kortdata/*.xlsx (källan)
- spel/webb/public/bilder/*.jpg    projektens bilder, nedskalade (ur tryck/bilder)
- spel/webb/public/brade/pu.jpg     PU-brädet med klistermärkena (ur tryck/ut, byggs av tryck/bygg_klistermarken.py)
- spel/webb/src/data/regler.json   regelbokens avsnitt (k3-1 …) för spelledaren, ur regler/regelbok.html
- tester/pussel_fall.json          gemensamma testfall: webbklientens regler och lösare ska ge
                                   samma svar som motor/pussel.py

    python verktyg/exportera_webbdata.py
"""
import json
import random
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

import openpyxl  # noqa: E402
from PIL import Image  # noqa: E402

from motor.data import las_lek  # noqa: E402
from motor.pussel import GRUNDMARK, Bit, granska, lagen, losa, placera  # noqa: E402

WEBB = ROT / "spel" / "webb"
BILDPREFIX = {"FÖRSKOLA": "FÖRSKOLOR", "KONTOR": "KONTOR", "LOKAL": "LOKAL", "HYRESRÄTT": "Hyresrätt", "BRF": "BRF"}
MARKFARG = "#91B542"            # markbitarnas gröna (formbilderna, G-skedets färg)


def form(k):
    return [list(c) for c in json.loads(k["Form (rutor)"])]


def fargar():
    """Bitarnas färger per typ: fill_color på Produktion-fliken i PU_projekt.xlsx."""
    ws = openpyxl.load_workbook(ROT / "kortdata" / "PU_projekt.xlsx", read_only=True)["Produktion"]
    rader = ws.iter_rows(values_only=True)
    rubrik = next(rader)
    typ_for = {p["Kort-id"]: p["Typ"] for p in las_lek("PU_projekt.xlsx")}
    ut = {"MARK": {"fyllning": MARKFARG, "ljus": "#e8f0d6"}}
    for r in rader:
        d = dict(zip(rubrik, r))
        typ = typ_for.get(d["Kort-id"])
        if typ and typ not in ut:
            ut[typ] = {"fyllning": d["fill_color"], "ljus": d["bakgrund_color"]}
    return ut


def bildnamn(p):
    return f'{BILDPREFIX[p["Typ"]]} {p["Namn"].split(" ", 1)[1]}.jpg'


def exportera_data():
    projekt = []
    (WEBB / "public" / "bilder").mkdir(parents=True, exist_ok=True)
    for p in las_lek("PU_projekt.xlsx"):
        kalla = ROT / "tryck" / "bilder" / bildnamn(p)
        bild = None
        if kalla.exists():
            bild = f"bilder/{p['Kort-id']}.jpg"
            im = Image.open(kalla).convert("RGB")
            im.thumbnail((240, 240))
            im.save(WEBB / "public" / bild, quality=82)
        projekt.append({"id": f"P{p['Kort-id']}", "namn": p["Namn"], "typ": p["Typ"], "form": form(p),
                        "bta": int(p["BTA (kvm)"]), "bild": bild})
    mark = [{"id": f"M{k['Kort-id']}", "namn": "Markexpansion", "typ": "MARK", "form": form(k),
             "bya": int(k["BYA (kvm)"])} for k in las_lek("PU_markexpansion.xlsx")]
    data = {"tomt": 16, "grundmark": sorted(list(c) for c in GRUNDMARK), "fargar": fargar(),
            "projekt": projekt, "markexpansioner": mark}
    ut = WEBB / "src" / "data" / "pussel.json"
    ut.parent.mkdir(parents=True, exist_ok=True)
    ut.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def exportera_brade():
    kalla = ROT / "tryck" / "ut" / "PU_brade_med_klistermarken.png"
    if not kalla.exists():
        return None
    ut = WEBB / "public" / "brade" / "pu.jpg"
    ut.parent.mkdir(parents=True, exist_ok=True)
    Image.open(kalla).convert("RGB").save(ut, quality=80, optimize=True, progressive=True)
    return ut


def exportera_regler():
    """Regelbokens numrerade avsnitt (<h2 id="k…">) som {id: {rubrik, html}}; bilder och figurer tas bort."""
    import re
    kalla = (ROT / "regler" / "regelbok.html").read_text(encoding="utf-8")
    kropp = kalla[kalla.index("<body"):]
    delar = re.split(r'(?=<h[12] id="k)', kropp)
    ut = {}
    for d in delar:
        m = re.match(r'<h2 id="(k\d+-\d+)"[^>]*>(.*?)</h2>', d, re.S)
        if not m:
            continue
        html = d[m.end():]
        html = re.split(r"<h1|<footer|</main", html)[0]
        html = re.sub(r"<figure.*?</figure>|<img[^>]*>", "", html, flags=re.S)
        rubrik = re.sub(r"<[^>]+>", "", m.group(2))
        rubrik = re.sub(r"(Ändrat|Nytt) i \d+(\.\d+)*", "", rubrik).strip()
        ut[m.group(1)] = {"rubrik": re.sub(r"\s+", " ", rubrik), "html": html.strip()}
    mal = WEBB / "src" / "data" / "regler.json"
    mal.write_text(json.dumps(ut, ensure_ascii=False), encoding="utf-8")
    return ut


def testfall(data, antal=40):
    """Slumpade kvarter med facit från motor/pussel.py."""
    R = random.Random(2026)
    fall = {"lagen": {p["id"]: [list(map(list, l)) for l in lagen([tuple(c) for c in p["form"]])]
                      for p in data["projekt"] + data["markexpansioner"]},
            "granska": [], "losa": []}
    for _ in range(antal):
        bitar = []
        for e in R.sample(data["markexpansioner"], R.randint(0, 2)):
            c = placera([tuple(x) for x in e["form"]], R.randrange(8), R.randrange(4, 12), R.randrange(4, 12))
            bitar.append(Bit(e["id"], "MARK", c, 0))
        for p in R.sample(data["projekt"], R.randint(2, 6)):
            c = placera([tuple(x) for x in p["form"]], R.randrange(8), R.randrange(5, 10), R.randrange(5, 10))
            bitar.append(Bit(p["id"], p["typ"], c, R.choice([1, 1, 2])))
        g = granska(bitar)
        fall["granska"].append({"bitar": [b.till() for b in bitar], "fel": sorted(g.fel), "mark": sorted(map(list, g.mark))})
    for _ in range(antal):
        mark = set(GRUNDMARK)
        for e in R.sample(data["markexpansioner"], R.randint(0, 2)):
            for _ in range(300):
                c = placera([tuple(x) for x in e["form"]], R.randrange(8), R.randrange(16), R.randrange(16))
                if not granska([Bit("x", "MARK", frozenset(mark - GRUNDMARK), 0), Bit("y", "MARK", c, 0)]).fel:
                    mark |= c
                    break
        valda = R.sample(data["projekt"], R.randint(3, 7))
        proj = [(p["id"], p["typ"], [tuple(c) for c in p["form"]]) for p in valda]
        plac, full = losa(mark, proj)
        _, full2 = alla_svar = losa(mark, proj, alla=True)
        if not (full and full2):
            continue
        typ = {p["id"]: p["typ"] for p in valda}
        exp = Bit("expansioner", "MARK", frozenset(mark - GRUNDMARK), 0)
        losning = [exp] + [Bit(i, typ[i], c, l) for i, (c, l) in plac.items()]
        fall["granska"].append({"bitar": [b.till() for b in losning], "fel": [], "mark": sorted(map(list, mark))})
        uppe = [b for b in losning if b.lager == 2]
        if uppe:                                   # samma bostad med en ruta utanför underlaget: "hål"
            b = uppe[0]
            under = set().union(*(x.celler for x in losning if x.lager == 1))
            flytt = next((frozenset((r + dr, k + dk) for r, k in b.celler) for dr, dk in ((0, 1), (1, 0), (0, -1), (-1, 0))
                          if not {(r + dr, k + dk) for r, k in b.celler} <= under), None)
            if flytt:
                hal = [x if x is not b else Bit(b.id, b.typ, flytt, 2) for x in losning]
                g = granska(hal)
                fall["granska"].append({"bitar": [x.till() for x in hal], "fel": sorted(g.fel),
                                        "mark": sorted(map(list, g.mark))})
        fall["losa"].append({"mark": sorted(map(list, mark)), "projekt": [p["id"] for p in valda],
                             "antal": len(plac), "yta": sum(len(c) for c, _ in plac.values()),
                             "alla": bool(alla_svar[0])})
    (ROT / "tester" / "pussel_fall.json").write_text(json.dumps(fall, ensure_ascii=False), encoding="utf-8")
    return fall


if __name__ == "__main__":
    d = exportera_data()
    f = testfall(d)
    print("brädet →", exportera_brade())
    print(f"{len(exportera_regler())} regelavsnitt → spel/webb/src/data/regler.json")
    print(f"{len(d['projekt'])} projekt, {len(d['markexpansioner'])} markexpansioner → spel/webb/src/data/pussel.json")
    print(f"{len(f['granska'])} granskningsfall, {len(f['losa'])} lösarfall → tester/pussel_fall.json")
