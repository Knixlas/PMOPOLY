"""Grundtester för motorn (Skede 3). Kör: python -m unittest discover tester"""
import unittest

from motor.data import Kortdata
from motor.modell import KLASSER
from motor.motor import Motor, Parametrar
from motor.slump import DigitalSlump
from motor.strategi import STRATEGIER, Strategi

DATA = Kortdata()


def parti(fro, **p):
    m = Motor([k() for k in STRATEGIER.values()][:4], Parametrar(**p), DigitalSlump(fro), DATA)
    return m, m.spela()


class TestMotor(unittest.TestCase):
    def test_samma_fro_ger_samma_parti(self):
        _, a = parti(7)
        _, b = parti(7)
        self.assertEqual(a, b)

    def test_invarianter_efter_parti(self):
        for fro in range(30):
            m, res = parti(fro)
            for sp in m.spel.spelare:
                self.assertLessEqual(len(sp.hand), m.p.handgrans)
                self.assertGreaterEqual(sp.riskbuffert, 0)
                for f in sp.fastigheter:
                    self.assertIn(f.ek, KLASSER)
                    self.assertGreater(f.dn_brickor, -3)   # netto -3 visas alltid
            for y, niva in m.spel.yieldniva.items():
                lo, hi = {"bostäder": (2, 6), "kommersiellt": (3, 7)}[y]
                self.assertTrue(lo <= niva <= hi)

    def test_plus_valfritt_gar_att_spela(self):
        _, res = parti(3, plus_visning="val")
        self.assertEqual(len(res), 4)

    def test_lan_ar_70_procent_av_start_mv(self):
        m = Motor([Strategi()] * 2, Parametrar(), DigitalSlump(1), DATA)
        f = m.ny_fastighet(DATA.projekt[0])
        self.assertLessEqual(f.lan, f.eff_dn() / 0.05 + 5)
        self.assertEqual(f.lan % 10, 0)

    def test_alla_effektkoder_hanteras(self):
        """Varje effekt i lekarna ska motorn känna till (annars tyst ignorerad)."""
        import re
        kanda = set(re.findall(r'"([a-z_]+)"', open("motor/motor.py", encoding="utf-8").read()))
        for lek in (DATA.handelse, DATA.kvartal, DATA.person, DATA.omvarld, DATA.dd):
            for k in lek:
                if k["Effekt"] in ("kika", "stopp", "forkop", "forhandling_mod", "forhandling_auto", "energi_mod"):
                    continue   # används via strategin (handkort)
                self.assertTrue(k["Effekt"] in kanda, f"{k['ID']}: {k['Effekt']} hanteras inte")


if __name__ == "__main__":
    unittest.main()
