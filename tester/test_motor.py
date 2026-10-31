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
                self.assertLessEqual(len(sp.hand), m.handgrans(sp))
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
        self.assertLessEqual(f.lan, f.eff_noi() / 0.05 + 5)
        self.assertEqual(f.lan % 5, 0)

    def test_projektkortens_forvaltningsvarden_hanger_ihop(self):
        """MV = (DN + ränta) ÷ startyield, lån = 70 % av anskaffningen, ränta = 2 % av lånet (minst 1)."""
        from motor.modell import START_YIELD, SPAR, avrunda
        for p in DATA.projekt:
            noi = p["Driftnetto (Mkr/år)"] + p["Räntekostnad (Mkr/år)"]
            mv = avrunda(noi / (START_YIELD[SPAR[p["Typ"]]] / 100), 5)
            self.assertEqual(p["Marknadsvärde (Mkr)"], mv, p["Namn"])
            self.assertEqual(p["Lån (Mkr)"], int(0.7 * p["Anskaffning (Mkr)"] / 5 + 0.5) * 5, p["Namn"])
            self.assertLessEqual(p["Lån (Mkr)"], mv, p["Namn"])
            self.assertEqual(p["Räntekostnad (Mkr/år)"], max(1, int(0.02 * p["Lån (Mkr)"] + 0.5)), p["Namn"])
            self.assertGreaterEqual(p["Driftnetto (Mkr/år)"], 0, p["Namn"])

    def test_uppgradering_flera_steg_tarningarna_borjar_om(self):
        """9.11: D → C lyckas på andra försöket (2 D20); nästa steg C → B slås ändå med 1 D20."""
        fragor = []

        class EttSteg(Strategi):
            def uppgradera(self, m, sp, antal):
                return [sp.fastigheter[0]]

            def fortsatt_uppgradera(self, m, sp, f, tarningar):
                fragor.append((f.ek, tarningar))
                return f.ek != "B"                           # sluta när B är nådd

        m = Motor([EttSteg(), Strategi()], Parametrar(), DigitalSlump(1), DATA)
        m.starta()
        m.spel.kvartal = 1
        sp = m.spel.spelare[0]
        f = sp.fastigheter[0]
        f.ek, f.uppgraderingsstopp, sp.kassa, sp.lan, sp.riskbuffert, sp.fc, sp.fs = "D", False, 100, 0, 0, None, None
        sp.hand = []
        m.spel.spelare[1].fastigheter = []
        slag = iter([2, 3, 15, 11, 1])                       # miss (1 D20), träff (2 D20), träff C → B (1 D20)
        m.s.d20 = lambda: next(slag)
        kast = []
        m.kast = lambda sp_, syfte, grupp=None: kast.append(syfte)
        m.energiuppgraderingar()
        self.assertEqual(f.ek, "B")
        self.assertEqual(fragor, [("D", 2), ("C", 1), ("B", 1)])
        self.assertIn("1 D20", kast[-1])
        self.assertEqual(sp.kassa, 100 - 3 * m.p.uppgradering_kostnad)

    def test_konsekvenskort_blir_varningar_storst_forst(self):
        """9.2: varje konsekvenskort från Skede 2 blir en varning, störst driftnetto först, varvet runt."""
        traffar = {}
        orig = Motor.varning

        def varning(self_, f, sp, kostnad):
            if sp.fc is None:                                # uppstarten, före personalvalet
                if sp.namn not in traffar:                   # första varningen: på den med störst driftnetto
                    self.assertEqual(f.eff_dn(), max(x.eff_dn() for x in sp.fastigheter))
                traffar.setdefault(sp.namn, []).append(f)
            orig(self_, f, sp, kostnad)

        Motor.varning = varning
        try:
            prov = 0
            for fro in range(12):
                traffar.clear()
                m = Motor([k() for k in STRATEGIER.values()][:4], Parametrar(), DigitalSlump(fro), DATA)
                m.starta()
                for sp in m.spel.spelare:
                    k = sp.pu["konsekvenskort"] if sp.fastigheter else 0
                    lista = traffar.get(sp.namn, [])
                    self.assertEqual(len(lista), k, sp.namn)
                    if k:
                        prov += 1
                        n = len(sp.fastigheter)
                        self.assertEqual(len(set(map(id, lista[:n]))), min(k, n))     # en per fastighet först
            self.assertGreater(prov, 0)
        finally:
            Motor.varning = orig

    def test_alla_effektkoder_hanteras(self):
        """Varje effekt i lekarna ska motorn känna till (annars tyst ignorerad)."""
        import re
        kanda = set(re.findall(r'"([a-z_]+)"', open("motor/motor.py", encoding="utf-8").read()))
        for lek in (DATA.handelse, DATA.kvartal, DATA.natverk, DATA.omvarld, DATA.dd):
            for k in lek:
                if k["Effekt"] in ("kika", "stopp", "forkop", "forhandling_mod", "forhandling_auto", "energi_mod"):
                    continue   # används via strategin (handkort)
                self.assertTrue(k["Effekt"] in kanda, f"{k['ID']}: {k['Effekt']} hanteras inte")


if __name__ == "__main__":
    unittest.main()
