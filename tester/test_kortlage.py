"""Kortversionen (motor/kortlage.py): kortare parti, samma regler, rättvist automatiskt."""
import unittest

from motor.kortlage import AUTOMAT, KORT
from motor.parti import Parti
from motor.pu import tal


def spela(fro, manniska=True):
    kvarter = [{"namn": "Norr", "styrning": "människa" if manniska else "bott"}, {"namn": "Söder"}, {"namn": "Öst"}]
    p = Parti(kvarter, fro=fro, langd="kort")
    fragor = []
    while (f := p.steg()) is not None:
        fragor.append(f)
        p.svara(f.forslag)
    return p, fragor


class TestKortlage(unittest.TestCase):
    def test_ett_kvartal_och_resultat(self):
        p, _ = spela(3)
        self.assertEqual(p.motor.spel.kvartal, KORT["kvartal"])
        self.assertEqual(len(p.resultat), 3)
        for r in p.resultat:
            self.assertIn("total", r)

    def test_automaten_tar_sina_beslut(self):
        _, fragor = spela(5)
        metoder = {f.metod for f in fragor}
        self.assertFalse(metoder & AUTOMAT)
        self.assertIn("valj_egna_upphandlingar", metoder)
        self.assertEqual(sum(1 for f in fragor if f.metod == "spela_fas"), KORT["spelade_faser"])
        self.assertLessEqual(sum(1 for f in fragor if f.metod == "valj_niva"), KORT["egna_upphandlingar"])

    def test_startportfoljerna_ar_lika(self):
        for fro in (1, 2, 3):
            p, _ = spela(fro, manniska=False)
            port = [sp.pu["startportfolj"] for sp in p.motor.spel.spelare]
            for nyckel in ("Anskaffning (Mkr)", "BTA (kvm)"):
                summor = [sum(tal(x[nyckel]) for x in pf) for pf in port]
                self.assertLessEqual(max(summor) - min(summor), 0.25 * max(summor), (fro, nyckel, summor))
            for pf in port:
                self.assertEqual(len(pf), KORT["start_portfolj"])

    def test_uppspelning(self):
        p, _ = spela(9)
        q = Parti.fran_sparat(p.uppstart(), p.logg)
        self.assertEqual([round(r["total"], 6) for r in q.spela_klart()], [round(r["total"], 6) for r in p.resultat])

    def test_hela_spelet_ar_standard(self):
        self.assertEqual(Parti([{"namn": "A"}], fro=1).langd, "hela")
        with self.assertRaises(ValueError):
            Parti([{"namn": "A"}], fro=1, langd="kort", slump="inmatad")


if __name__ == "__main__":
    unittest.main()
