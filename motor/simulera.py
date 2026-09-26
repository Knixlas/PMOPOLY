"""Låt bottarna spela många partier och sammanfatta balansen.

Kör:  python -m motor.simulera --partier 2000 [--plus val] [--fro 1]
"""
import argparse
import statistics
from collections import Counter, defaultdict

from .data import Kortdata
from .motor import Motor, Parametrar
from .slump import DigitalSlump
from .strategi import STRATEGIER


def kor(partier, parametrar, fro=1, spelare=4):
    data = Kortdata()
    slump = DigitalSlump(fro)
    vinst = defaultdict(Counter)     # kategori -> värde -> vinster
    deltog = defaultdict(Counter)
    s3 = defaultdict(list)
    stat = defaultdict(list)
    drift = defaultdict(list)
    for _ in range(partier):
        klasser = [slump.valj(list(STRATEGIER.values())) for _ in range(spelare)]
        m = Motor([k() for k in klasser], parametrar, slump, data)
        res = m.spela()
        bast = max(res, key=lambda r: r["F"])
        for r in res:
            for kat in ("strategi", "fc", "fs"):
                deltog[kat][r[kat]] += 1
                if r is bast:
                    vinst[kat][r[kat]] += 1
            s3[r["strategi"]].append(r["F"])
            s3["alla"].append(r["F"])
            s3["_startkassa"].append(r["startkassa"])
            s3["_fastigheter"].append(r["fastigheter"])
        for k, v in m.stat.items():
            if k == "dn_drift":
                for t, n in v.items():
                    drift[t].append(n)
            else:
                stat[k].append(v)
    return vinst, deltog, s3, stat, drift


def rapport(partier, parametrar, fro):
    vinst, deltog, s3, stat, drift = kor(partier, parametrar, fro)
    print(f"# {partier} partier, 4 spelare, plus_visning={parametrar.plus_visning}\n")
    for kat, rubrik in (("strategi", "Strategi"), ("fc", "FC"), ("fs", "FS")):
        print(f"## {rubrik}: vinstandel (förväntat 25 %)")
        for namn, n in sorted(deltog[kat].items(), key=lambda x: -vinst[kat][x[0]] / x[1]):
            extra = f", snitt F {statistics.mean(s3[namn]):.1f}" if kat == "strategi" else ""
            print(f"  {namn:32} {100 * vinst[kat][namn] / n:5.1f} %  ({n} deltagare{extra})")
        print()
    for nyckel, rubrik in (("alla", "F-poäng"), ("_startkassa", "Startkassa (TB + BRF)"), ("_fastigheter", "Fastigheter vid slut")):
        v = sorted(s3[nyckel])
        print(f"## {rubrik}: median {statistics.median(v):.1f}, 10–90 %: {v[len(v) // 10]:.1f}–{v[9 * len(v) // 10]:.1f}, "
              f"bästa 5 %: {v[95 * len(v) // 100]:.1f}")
    print()
    print("## Händelser per parti (snitt)")
    for k, v in stat.items():
        print(f"  {k:22} {statistics.mean(v):6.2f}")
    print("\n## DN-drift per typ och parti (summa bas-DN-ändring, alla spelare)")
    for t, v in drift.items():
        print(f"  {t:10} {statistics.mean(v):+6.2f}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--partier", type=int, default=1000)
    a.add_argument("--plus", default="direkt", choices=("direkt", "val"))
    a.add_argument("--fro", type=int, default=1)
    arg = a.parse_args()
    rapport(arg.partier, Parametrar(plus_visning=arg.plus), arg.fro)
