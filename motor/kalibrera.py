"""Rutnätssökning över kalibreringsreglage. Kör: python -m motor.kalibrera"""
import itertools
import statistics

from .motor import Parametrar
from .simulera import kor

VOLATIL = ("LOKAL", "KONTOR")


def matt(parametrar, partier, fro):
    vinst, deltog, s3, stat, drift = kor(partier, parametrar, fro)
    andel = {n: vinst["strategi"][n] / deltog["strategi"][n] for n in deltog["strategi"]}
    m = lambda k: statistics.mean(stat[k])
    return {
        "bank": m("bank_tar"), "sanering": m("sanering_tagen"), "kop": m("kop"), "tvang": m("tvangsbud"),
        "uppgr": m("uppgradering"), "spridning": max(andel.values()) - min(andel.values()),
        "bast": max(andel, key=andel.get), "s3": statistics.median(s3["alla"]),
    }


def main(partier=1200, fro=3):
    print("kostnad tröskel extra-minus | bank sanering köp tvång uppgr | strategispridning (bäst) | S3")
    for kost, grans, extra in itertools.product((3, 5, 8), (10, 12), (0, 2, 4)):
        ex = {t: {"direkt_dn_minus": extra} for t in VOLATIL} if extra else {}
        r = matt(Parametrar(uppgradering_kostnad=kost, uppgradering_troskel=grans, extra_handelse=ex), partier, fro)
        print(f"{kost:5} {grans:6} {extra:6}      | {r['bank']:4.2f} {r['sanering']:5.2f} {r['kop']:5.2f} {r['tvang']:4.2f} "
              f"{r['uppgr']:5.1f} | {100 * r['spridning']:4.1f} pp ({r['bast']}) | {r['s3']:.0f}")


if __name__ == "__main__":
    main()
