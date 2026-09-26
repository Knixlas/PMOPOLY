"""Skede 1 (Projektutveckling): determinism och regler som alltid ska hålla."""
import unittest

from motor.pu import BOSTAD, MARK_CELLER, PUData, PUMotor, tal
from motor.pu_strategi import PU_STRATEGIER
from motor.slump import DigitalSlump

DATA = PUData()


def parti(fro):
    s = DigitalSlump(fro)
    m = PUMotor([k() for k in PU_STRATEGIER.values()], slump=s, data=DATA)
    return m, m.spela()


class TestPU(unittest.TestCase):
    def test_samma_fro_ger_samma_parti(self):
        self.assertEqual([r["abt"] for r in parti(4)[1]], [r["abt"] for r in parti(4)[1]])

    def test_formerna_stammer_med_bta(self):
        for p in DATA.projekt:
            self.assertEqual(tal(p["Antal rutor"]) * 250, tal(p["BTA (kvm)"]), p["Namn"])

    def test_invarianter(self):
        for fro in range(20):
            m, res = parti(fro)
            namn = [p["Namn"] for kv in m.kvarter for p in kv.placerade]
            self.assertEqual(len(namn), len(set(namn)), "ett projekt i två kvarter")
            for kv in m.kvarter:
                mark = sum(tal(p["Antal rutor"]) for p in kv.placerade if p["Typ"] not in BOSTAD)
                bostad = sum(tal(p["Antal rutor"]) for p in kv.placerade if p["Typ"] in BOSTAD)
                self.assertLessEqual(max(mark, bostad), kv.markceller)
                self.assertGreaterEqual(kv.markceller, MARK_CELLER)
                self.assertGreaterEqual(min(kv.q_krav, kv.h_krav, kv.riskbuffert), 0)
                # 5.1: anskaffning − tomt − expansioner − utveckling (komplettering 3 ×)
                utv = sum(tal(p["Utvecklingskostnad (Mkr)"]) for p in kv.godkanda) \
                    + 2 * sum(tal(p["Utvecklingskostnad (Mkr)"]) for p in kv.kompletterade)
                abt = sum(tal(p["Anskaffning (Mkr)"]) for p in kv.placerade) - m.p.tomtkostnad \
                    - 5 * len(kv.expansioner) - utv
                self.assertAlmostEqual(kv.abt, abt)


if __name__ == "__main__":
    unittest.main()
