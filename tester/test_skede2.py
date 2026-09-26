"""Skede 2 (Planering, Genomförande, skedesavslut): determinism och regler som alltid ska hålla."""
import unittest

from motor.pu import PUData, PUMotor
from motor.pu_strategi import PU_STRATEGIER
from motor.skede2 import KOMPETENSER, S2Data, Skede2, kompetenser, krav, mu
from motor.skede2_strategi import S2_STRATEGIER
from motor.slump import DigitalSlump

PU, S2 = PUData(), S2Data()


def parti(fro):
    s = DigitalSlump(fro)
    pu = PUMotor([k() for k in PU_STRATEGIER.values()], slump=s, data=PU).spela()
    m = Skede2(pu, [k() for k in list(S2_STRATEGIER.values()) + [S2_STRATEGIER["balanserad"]]], slump=s, data=S2)
    return m, m.spela()


class TestSkede2(unittest.TestCase):
    def test_samma_fro_ger_samma_parti(self):
        self.assertEqual([r["tb"] for r in parti(2)[1]], [r["tb"] for r in parti(2)[1]])

    def test_tolkning(self):
        self.assertEqual(krav("KOM 2, SAM 5, INN 3"), {"KOM": 2, "SAM": 5, "INN": 3})
        self.assertEqual(krav("—"), {})
        self.assertIsNone(krav(None))
        self.assertEqual(mu(0), 1.0)
        self.assertEqual(mu(4), 0.70)
        self.assertEqual(mu(15), 0.45)
        for k in S2.leverantorer + S2.organisation + S2.kultur:
            self.assertTrue(set(kompetenser(k)) <= set(KOMPETENSER))

    def test_alla_effekter_tolkas(self):
        m, _ = parti(1)
        b = m.bolag[0]
        for lek, kol in ((S2.handelse, ["Konsekvens 1–5", "Konsekvens 6–17", "Konsekvens 18–20", "Konsekvens 21+"]),
                         (S2.fas, ["Effekt negativt", "Effekt neutralt", "Effekt positivt", "Effekt bonus"]),
                         (S2.konsekvens, ["Utfall D20+ER 1-9", "Utfall D20+ER 10-17", "Utfall D20+ER 18-24",
                                          "Utfall D20+ER 25+"])):
            for k in lek:
                for c in kol:
                    m.effekt(b, k[c])            # kastar ValueError vid okänd text

    def test_invarianter(self):
        for fro in range(10):
            m, res = parti(fro)
            for b, r in zip(m.bolag, res):
                self.assertGreaterEqual(min(b.q, b.h, b.riskbuffert), 0)
                self.assertGreaterEqual(b.t, 8)
                self.assertLessEqual(b.erfarenhet, 12)
                self.assertGreaterEqual(b.kvar, 0)          # moderbolagslånen täcker underskott
                self.assertAlmostEqual(r["tb"], b.abt - b.kostnad)


if __name__ == "__main__":
    unittest.main()
