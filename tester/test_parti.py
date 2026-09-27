"""Partiet och styrningen: samma parti oavsett vem som svarar, och ett parti kan spelas upp ur sin logg."""
import json
import unittest

from motor.data import Kortdata
from motor.motor import Motor, Parametrar
from motor.parti import BOTTAR, Parti
from motor.slump import DigitalSlump
from motor.styrning import LoggFel

DATA = Kortdata()
KVARTER = [{"namn": "Norr", "bottar": {"PU": "expansiv", "S2": "kvalitet", "F": "aggressiv"}},
           {"namn": "Söder"},
           {"namn": "Öster", "bottar": {"F": "energi"}}]


def utan_strateginamn(resultat):
    return [{k: v for k, v in r.items() if "strategi" not in k} for r in resultat]


def json_kopia(v):
    return json.loads(json.dumps(v, ensure_ascii=False))


class TestParti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parti = Parti(KVARTER, fro=11, data=DATA)
        cls.resultat = utan_strateginamn(cls.parti.spela_klart())

    def test_samma_som_motorn_direkt(self):
        kv = self.parti.kvarter
        m = Motor([BOTTAR["F"][k["bottar"]["F"]]() for k in kv], Parametrar(), DigitalSlump(11), DATA,
                  pu_strategier=[BOTTAR["PU"][k["bottar"]["PU"]]() for k in kv],
                  s2_strategier=[BOTTAR["S2"][k["bottar"]["S2"]]() for k in kv], namn=[k["namn"] for k in kv])
        self.assertEqual(utan_strateginamn(m.spela()), self.resultat)

    def test_uppspelning_ur_sparad_logg(self):
        p = Parti.fran_sparat(json_kopia(self.parti.uppstart()), json_kopia(self.parti.logg), data=DATA)
        self.assertEqual(utan_strateginamn(p.spela_klart()), self.resultat)

    def test_ateruppta_mitt_i(self):
        halva = json_kopia(self.parti.logg[:len(self.parti.logg) // 2])
        p = Parti.fran_sparat(json_kopia(self.parti.uppstart()), halva, data=DATA)
        self.assertEqual(utan_strateginamn(p.spela_klart()), self.resultat)

    def test_manniska_som_svarar_som_botten(self):
        kv = [dict(k, styrning="människa") if k["namn"] == "Norr" else k for k in KVARTER]
        p = Parti(kv, fro=11, data=DATA)
        fragor = 0
        while (f := p.steg()) is not None:
            self.assertEqual(f.kvarter, "Norr")
            fragor += 1
            p.svara(f.forslag)
        self.assertGreater(fragor, 20)
        self.assertEqual(utan_strateginamn(p.resultat), self.resultat)

    def test_fel_logg_upptacks(self):
        logg = json_kopia(self.parti.logg)
        i = next(i for i, e in enumerate(logg) if e["kanal"] == "slump" and e["metod"] == "d20")
        logg[i]["varde"] = 21 - logg[i]["varde"] or 1          # ett annat tärningsslag
        p = Parti.fran_sparat(json_kopia(self.parti.uppstart()), logg, data=DATA)
        with self.assertRaises(LoggFel):
            p.spela_klart()

    def test_svarighet_satter_startkraven(self):
        """Svårighetsgraden är Detaljplanens startkrav (3.1) och följer med när partiet sparas."""
        p = Parti([{"namn": "Norr"}, {"namn": "Söder"}], fro=3, data=DATA, svarighet="svår")
        self.assertEqual(p.parametrar.start_krav, 6)
        self.assertEqual(p.uppstart()["svarighet"], "svår")
        with self.assertRaises(ValueError):
            Parti([{"namn": "Norr"}], data=DATA, svarighet="omöjlig")
        p.spela_klart()
        self.assertEqual(utan_strateginamn(Parti.fran_sparat(json_kopia(p.uppstart()), json_kopia(p.logg), data=DATA)
                                           .spela_klart()), utan_strateginamn(p.resultat))

    def test_fysiskt_spel_med_inmatad_slump(self):
        """Läge 2: spelarna anger tärningar och dragna kort; partiet går klart och kan spelas upp."""
        import random
        R = random.Random(4)
        p = Parti([{"namn": "Norr", "styrning": "människa"}, {"namn": "Söder", "styrning": "människa"}],
                  fro=4, data=DATA, slump="inmatad")
        slumpfragor = 0
        while (f := p.steg()) is not None:
            if f.kanal == "beslut":
                p.svara(f.forslag)
                continue
            slumpfragor += 1
            if f.metod in ("d20", "tarning", "heltal", "index"):
                self.assertLessEqual(f.argument[0], f.argument[1])
                p.svara(R.randint(f.argument[0], f.argument[1]))
            elif f.metod == "dra":                       # [högens namn, [kort-id kvar i högen]]
                self.assertTrue(f.argument[1])
                p.svara(R.randrange(len(f.argument[1])))
            else:
                p.svara(R.randrange(len(f.argument)))
        self.assertGreater(slumpfragor, 100)
        uppspelad = Parti.fran_sparat(json_kopia(p.uppstart()), json_kopia(p.logg), data=DATA).spela_klart()
        self.assertEqual(utan_strateginamn(uppspelad), utan_strateginamn(p.resultat))

    def test_varje_fraga_ar_lasbar(self):
        """Varje fråga har en vy med rubrik, och bottens förslag finns bland alternativen."""
        p = Parti([{"namn": n, "styrning": "människa"} for n in ("Norr", "Söder")], fro=8, data=DATA)
        typer = set()
        while (f := p.steg()) is not None:
            v = f.vy
            json.dumps(v)
            self.assertTrue(v.get("rubrik"), f.metod)
            self.assertNotEqual(v["typ"], "forslag", f"{f.metod} saknar beskrivning i motor/fragor.py")
            koder = [a["kod"] for a in v.get("alternativ", [])]
            if v["typ"] == "val":
                self.assertIn(f.forslag, koder, f.metod)
            if v["typ"] == "flerval":
                self.assertTrue(all(x in koder for x in f.forslag["lista"]), f.metod)
            typer.add(v["typ"])
            p.svara(f.forslag)
        self.assertTrue({"val", "janej", "pussel"} <= typer)

    def test_ensam_i_partiet(self):
        self.assertEqual(len(Parti([{"namn": "Ensam"}], fro=73, data=DATA).spela_klart()), 1)


if __name__ == "__main__":
    unittest.main()
