"""Placeringspusslet (regelboken 4.3) och de gemensamma testfallen för webbklienten."""
import json
import unittest
from pathlib import Path

from motor.pussel import GRUNDMARK, Bit, granska, lagen, lager_for, las_marklayout, losa

FALL = json.loads((Path(__file__).parent / "pussel_fall.json").read_text(encoding="utf-8"))
DATA = json.loads((Path(__file__).parent.parent / "spel" / "webb" / "src" / "data" / "pussel.json").read_text(encoding="utf-8"))
FORM = {p["id"]: [tuple(c) for c in p["form"]] for p in DATA["projekt"] + DATA["markexpansioner"]}
TYP = {p["id"]: p["typ"] for p in DATA["projekt"]}


def bit(id_, typ, celler, lager):
    return Bit(id_, typ, frozenset(celler), lager)


class TestRegler(unittest.TestCase):
    def test_bostad_ovanpa_utan_hal(self):
        kontor = bit("K", "KONTOR", [(6, 6), (6, 7), (7, 6), (7, 7)], 1)
        hel = bit("B", "BRF", [(6, 6), (6, 7)], 2)
        self.assertTrue(granska([kontor, hel]).giltigt)
        hal = bit("B", "BRF", [(6, 7), (6, 8)], 2)            # (6, 8) är mark men inget projekt under
        self.assertEqual(granska([kontor, hal]).fel, {"B": "vilar inte helt på andra projekt"})

    def test_bara_bostader_ovanpa(self):
        kontor = bit("K", "KONTOR", [(6, 6), (6, 7)], 1)
        lokal = bit("L", "LOKAL", [(6, 6), (6, 7)], 2)
        self.assertIn("L", granska([kontor, lokal]).fel)

    def test_bostad_direkt_pa_marken(self):
        self.assertTrue(granska([bit("H", "HYRESRÄTT", [(9, 9), (9, 8)], 1)]).giltigt)

    def test_markexpansion_kant_i_kant(self):
        self.assertTrue(granska([bit("M", "MARK", [(10, 6), (11, 6)], 0)]).giltigt)
        self.assertIn("M", granska([bit("M", "MARK", [(11, 6), (12, 6)], 0)]).fel)      # en rad glapp
        self.assertIn("M", granska([bit("M", "MARK", [(10, 10), (11, 10)], 0)]).fel)    # bara hörn mot hörn
        # expansion som når marken via en annan expansion
        self.assertTrue(granska([bit("M1", "MARK", [(10, 6)], 0), bit("M2", "MARK", [(11, 6)], 0)]).giltigt)

    def test_projekt_pa_expansionen(self):
        exp = bit("M", "MARK", [(10, 6), (11, 6)], 0)
        self.assertTrue(granska([exp, bit("F", "FÖRSKOLA", [(9, 6), (10, 6), (11, 6)], 1)]).giltigt)

    def test_lager_for_slapp(self):
        mark, under = frozenset(GRUNDMARK), frozenset({(6, 6), (6, 7)})
        self.assertEqual(lager_for("BRF", frozenset({(8, 8)}), mark, under), 1)
        self.assertEqual(lager_for("BRF", frozenset({(6, 6)}), mark, under), 2)
        self.assertIsNone(lager_for("BRF", frozenset({(6, 7), (6, 8)}), mark, under))   # halvt ovanpå
        self.assertIsNone(lager_for("KONTOR", frozenset({(6, 6)}), mark, under))

    def test_lagen(self):
        self.assertEqual(len(lagen([(0, 0), (0, 1), (1, 0), (1, 1)])), 1)
        self.assertEqual(len(lagen([(0, 0), (1, 0)])), 2)
        self.assertEqual(len(lagen([(0, 0), (0, 1), (0, 2), (1, 0)])), 8)


class TestMarklayout(unittest.TestCase):
    """Markexpansioner får flyttas: en hel ny marklayout granskas som helhet."""
    FORMER = {"A": [(0, 0), (1, 0)], "B": [(0, 0), (0, 1), (0, 2)]}

    def test_giltig_och_kedjad(self):
        # A kant i kant med grundmarken, B kant i kant med A (inte med grundmarken)
        svar = [["A", [[4, 6], [5, 6]]], ["B", [[3, 6], [3, 7], [3, 8]]]]
        self.assertEqual(las_marklayout(svar, self.FORMER)["B"], frozenset({(3, 6), (3, 7), (3, 8)}))

    def test_vriden_form_godtas(self):
        svar = [["A", [[5, 6], [5, 5]]], ["B", [[6, 5], [7, 5], [8, 5]]]]
        self.assertIsInstance(las_marklayout(svar, self.FORMER), dict)

    def test_fel(self):
        self.assertIn("form", las_marklayout([["A", [[5, 6], [5, 7]]], ["B", [[4, 6], [4, 7], [3, 7]]]], self.FORMER))
        self.assertIn("kant i kant", las_marklayout([["A", [[0, 0], [1, 0]]], ["B", [[5, 6], [5, 7], [5, 8]]]], self.FORMER))
        self.assertIn("alla", las_marklayout([["A", [[5, 6], [4, 6]]]], self.FORMER))
        self.assertIn("överlappar", las_marklayout([["A", [[6, 6], [5, 6]]], ["B", [[5, 7], [5, 8], [5, 9]]]], self.FORMER))


class TestGemensammaFall(unittest.TestCase):
    """Samma fall körs av webbklientens tester (spel/webb/src/pussel/regler.test.ts)."""

    def test_lagen(self):
        for id_, facit in FALL["lagen"].items():
            self.assertEqual([list(map(list, l)) for l in lagen(FORM[id_])], facit, id_)

    def test_granska(self):
        for f in FALL["granska"]:
            g = granska([Bit.fran(b) for b in f["bitar"]])
            self.assertEqual(sorted(g.fel), f["fel"])

    def test_losa(self):
        for f in FALL["losa"][:15]:
            proj = [(i, TYP[i], FORM[i]) for i in f["projekt"]]
            mark = {tuple(c) for c in f["mark"]}
            plac, full = losa(mark, proj)
            self.assertTrue(full)
            self.assertEqual((len(plac), sum(len(c) for c, _ in plac.values())), (f["antal"], f["yta"]))
            kvarter = [Bit("mark", "MARK", frozenset(mark - GRUNDMARK), 0)]
            kvarter += [Bit(i, TYP[i], c, l) for i, (c, l) in plac.items()]
            self.assertTrue(granska(kvarter).giltigt)
            self.assertEqual(bool(losa(mark, proj, alla=True)[0]), f["alla"])


class TestMotornsPlacering(unittest.TestCase):
    """Skede 1 i motorn lägger pusslet på riktigt: markexpansioner kant i kant, projekt enligt 4.3."""

    def test_layouter_foljer_reglerna(self):
        from motor.pu import PUData, PUMotor, PUParametrar
        from motor.pu_strategi import PU_STRATEGIER
        from motor.pussel import form_av
        from motor.slump import DigitalSlump
        data, slump = PUData(), DigitalSlump(5)
        for _ in range(6):
            m = PUMotor([k() for k in PU_STRATEGIER.values()], PUParametrar(), slump, data)
            for kv, r in zip(m.kvarter, m.spela()):
                self.assertEqual(len(kv.mark), 16 + sum(len(form_av(e)) for e in kv.expansioner))
                typ = {p["Namn"]: p["Typ"] for p in kv.godkanda}
                bitar = [Bit("mark", "MARK", kv.mark - GRUNDMARK, 0)]
                bitar += [Bit(n, typ[n], c, l) for n, (c, l) in kv.layout.items()]
                self.assertTrue(granska(bitar).giltigt, kv.namn)
                self.assertEqual(r["projekt"] + r["oplacerade"], len(kv.godkanda))
                self.assertEqual(r["bya"], 250 * sum(len(c) for c, l in kv.layout.values() if l == 1))


if __name__ == "__main__":
    unittest.main()
