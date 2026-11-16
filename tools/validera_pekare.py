"""Kontrollera spelens pekare till Åkepedia mot en utcheckad kopia av Åkepedias standard.

Spelen innehåller ingen text ur Åkepedia, bara pekare: dokumentnamn, version, nummer och
rubrik (data/kampanj_texter.json → pa_riktigt, blixt.AKEPEDIA, staden.KUNSKAP). När
standarden får en ny version kan ett nummer flytta eller försvinna. Det här skriptet
läser Åkepedias standardfiler (bara läser) och säger till om en pekare inte längre stämmer.

Kör:  python tools/validera_pekare.py <sökväg till akepedia/standard>
"""
import glob
import json
import os
import sys

ROT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROT, "backend"))


def las_standard(mapp: str) -> dict:
    """typ → {titel, version, kapitel: {nr: rubrik}, avsnitt: {nr: rubrik}, pastaenden: {nr}}, senaste versionen."""
    ut = {}
    for typ in sorted(os.listdir(mapp)):
        filer = sorted(glob.glob(os.path.join(mapp, typ, "*.json")))
        if not filer:
            continue
        d = json.load(open(filer[-1], encoding="utf-8"))
        post = {"titel": d["titel"], "version": d["version"], "kapitel": {}, "avsnitt": {}, "pastaenden": set()}
        for k in d["kapitel"]:
            post["kapitel"][k.get("nr")] = k.get("rubrik")
            for a in k.get("avsnitt", []):
                post["avsnitt"][a.get("nr")] = a.get("rubrik")
                post["pastaenden"].update(p["nr"] for p in a.get("pastaenden", []))
        ut[typ] = post
    return ut


def kontrollera(pekare: dict, std: dict, var: str) -> list:
    fel = []
    s = std.get(pekare.get("typ"))
    if not s:
        return [f"{var}: dokumenttypen {pekare.get('typ')!r} finns inte i Åkepedia."]
    if pekare.get("version") and pekare["version"] != s["version"]:
        fel.append(f"{var}: {pekare['typ']} är nu version {s['version']} (pekaren säger {pekare['version']}).")
    if "kapitel" in pekare:
        rubrik = s["kapitel"].get(pekare["kapitel"])
        if rubrik is None:
            fel.append(f"{var}: {pekare['typ']} har inget kapitel {pekare['kapitel']}.")
        elif pekare.get("rubrik") and rubrik != pekare["rubrik"]:
            fel.append(f"{var}: kapitel {pekare['kapitel']} heter nu {rubrik!r}.")
    elif pekare.get("nr"):
        nr = pekare["nr"]
        if nr in s["avsnitt"]:
            if pekare.get("rubrik") and s["avsnitt"][nr] != pekare["rubrik"]:
                fel.append(f"{var}: {nr} heter nu {s['avsnitt'][nr]!r}.")
        elif nr not in s["pastaenden"]:
            fel.append(f"{var}: {nr} finns inte i {pekare['typ']} {s['version']}.")
    return fel


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit(__doc__)
    std = las_standard(sys.argv[1])
    fel, antal = [], 0
    texter = json.load(open(os.path.join(ROT, "data", "kampanj_texter.json"), encoding="utf-8"))
    for steg, lista in texter.get("pa_riktigt", {}).items():
        for p in lista:
            antal += 1
            fel += kontrollera(p, std, f"kampanj {steg}")
    import blixt
    import staden
    for nyckel, p in blixt.AKEPEDIA.items():
        antal += 1
        fel += kontrollera(p, std, f"blixt {nyckel}")
    for gren, g in staden.KUNSKAP.items():
        for p in g.get("akepedia", []):
            antal += 1
            fel += kontrollera(p, std, f"staden {gren}")
    for rad in fel:
        print("FEL  " + rad)
    print(f"{antal} pekare kontrollerade, {len(fel)} fel.")
    sys.exit(1 if fel else 0)


if __name__ == "__main__":
    main()
