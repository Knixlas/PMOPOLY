"""Spelservern (spel/server): rum, svar från rätt enhet, WebSocket och återskapning efter omstart."""
import os
import random
import tempfile
import unittest

os.environ.setdefault("SPEL_DATA", tempfile.mkdtemp(prefix="akepol-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from spel.server import app as appmodul  # noqa: E402
from spel.server.rum import Rum  # noqa: E402

KLIENT = TestClient(appmodul.app)


def skapa(**kw):
    kropp = {"kvarter": [{"namn": "Norr"}, {"namn": "Söder"}], "fro": 3, **kw}
    r = KLIENT.post("/api/rum", json=kropp)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def svar_for(vy, R):
    """Ett giltigt svar på en fråga, som en spelare skulle ge det."""
    if vy["typ"] == "janej":
        return {"svar": R.random() < 0.5}
    if vy["typ"] == "tal":
        return {"svar": R.randint(vy["min"], vy["max"])}
    if vy["typ"] in ("val", "markexpansion") and vy.get("alternativ"):
        return {"val": R.randrange(len(vy["alternativ"]))}
    return {"forslag": True}


class TestServer(unittest.TestCase):
    def test_halsa(self):
        self.assertEqual(KLIENT.get("/health").json()["status"], "ok")

    def test_helt_parti_via_api(self):
        id_ = skapa()
        R = random.Random(1)
        for _ in range(3000):
            lage = KLIENT.get(f"/api/rum/{id_}").json()
            self.assertIsNone(lage["fel"])
            if lage["klart"]:
                break
            f = lage["fraga"]
            svar = svar_for(f["vy"], R) if R.random() < 0.3 else {"forslag": True}
            r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"], "svar": svar})
            self.assertEqual(r.status_code, 200, r.text)
        lage = KLIENT.get(f"/api/rum/{id_}").json()
        self.assertTrue(lage["klart"])
        self.assertEqual({r["spelare"] for r in lage["resultat"]}, {"Norr", "Söder"})

    def test_fel_enhet_och_gammal_fraga(self):
        id_ = skapa()
        f = KLIENT.get(f"/api/rum/{id_}").json()["fraga"]
        annan = "Söder" if f["kvarter"] == "Norr" else "Norr"
        r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": annan, "nr": f["nr"], "svar": {"forslag": True}})
        self.assertEqual(r.status_code, 409)
        r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"] + 5, "svar": {"forslag": True}})
        self.assertEqual(r.status_code, 409)

    def test_websocket(self):
        id_ = skapa()
        with KLIENT.websocket_connect(f"/ws/{id_}/Norr") as ws:
            lage = ws.receive_json()
            self.assertEqual(lage["typ"], "lage")
            for _ in range(20):
                f = lage["fraga"]
                if f["kvarter"] != "Norr":
                    KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"], "svar": {"forslag": True}})
                else:
                    ws.send_json({"typ": "svar", "nr": f["nr"], "svar": {"forslag": True}})
                lage = ws.receive_json()
                self.assertEqual(lage["typ"], "lage")
                self.assertNotEqual(lage["fraga"]["nr"], f["nr"])

    def test_inmatad_slump_besvaras_vid_bordet(self):
        id_ = skapa(slump="inmatad")
        R = random.Random(2)
        slump = 0
        for _ in range(200):
            f = KLIENT.get(f"/api/rum/{id_}").json()["fraga"]
            if f["kanal"] == "slump":
                slump += 1
                kvarter = "bordet"
                svar = svar_for(f["vy"], R)
            else:
                kvarter, svar = f["kvarter"], {"forslag": True}
            r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": kvarter, "nr": f["nr"], "svar": svar})
            self.assertEqual(r.status_code, 200, r.text)
        self.assertGreater(slump, 20)

    def test_aterskapas_efter_omstart(self):
        id_ = skapa()
        for _ in range(60):
            f = KLIENT.get(f"/api/rum/{id_}").json()["fraga"]
            KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"], "svar": {"forslag": True}})
        fore = KLIENT.get(f"/api/rum/{id_}").json()
        rum = Rum.ladda(os.path.join(os.environ["SPEL_DATA"], f"{id_}.json"), appmodul.DATA)
        efter = rum.lage()
        self.assertEqual(efter["fraga"]["vy"], fore["fraga"]["vy"])
        self.assertEqual(efter["bild"], fore["bild"])

    def test_pusselsvar(self):
        id_ = skapa(kvarter=[{"namn": "Norr"}])
        for _ in range(3000):
            lage = KLIENT.get(f"/api/rum/{id_}").json()
            f = lage["fraga"]
            if f["vy"]["typ"] == "pussel":
                break
            KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"], "svar": {"forslag": True}})
        else:
            self.fail("kom aldrig till 4.3")
        vy = f["vy"]
        p = vy["projekt"][0]                                  # lägg det första projektet i markens övre vänstra hörn
        r0 = min(r for r, _ in vy["mark"])
        k0 = min(k for r, k in vy["mark"] if r == r0)
        celler = [[r0 + r, k0 + k] for r, k in p["form"]]
        r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": "Norr", "nr": f["nr"],
                                                      "svar": {"placering": [[p["namn"], celler, 1]]}})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(r.json()["fel"])

    def test_markexpansion_som_hel_layout(self):
        """Markexpansionen kan besvaras med hela marken ([[id, rutor], ...]); fel layout avvisas med skäl."""
        id_ = skapa(kvarter=[{"namn": "Norr"}], fro=5)
        for _ in range(3000):
            f = KLIENT.get(f"/api/rum/{id_}").json()["fraga"]
            if f["vy"]["typ"] == "markexpansion":
                break
            svar = {"svar": True} if f["vy"]["typ"] == "janej" and "markexpansion" in f["vy"]["rubrik"] else {"forslag": True}
            KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": f["kvarter"], "nr": f["nr"], "svar": svar})
        else:
            self.fail("ingen markexpansion")
        vy = f["vy"]
        lagda = [[b["id"], b["celler"]] for b in vy["markbitar"]]
        fel = [[vy["id"], [[r, k] for r, k in vy["form"]]]]    # i hörnet: inte kant i kant
        r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": "Norr", "nr": f["nr"], "svar": {"mark": lagda + fel}})
        self.assertNotEqual(r.status_code, 200)
        self.assertIn("marken", r.text)
        ratt = [[vy["id"], vy["platser"][0]]]
        r = KLIENT.post(f"/api/rum/{id_}/svar", json={"kvarter": "Norr", "nr": f["nr"], "svar": {"mark": lagda + ratt}})
        self.assertEqual(r.status_code, 200, r.text)
        mark = {tuple(c) for c in KLIENT.get(f"/api/rum/{id_}").json()["fraga"]["vy"].get("mark", [])} or None
        if mark:                                              # nästa fråga är en pusselfråga: marken syns där
            self.assertTrue({tuple(c) for c in vy["platser"][0]} <= mark)


if __name__ == "__main__":
    unittest.main()
