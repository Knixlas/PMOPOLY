"""Ett rum är ett parti med de enheter som är anslutna till det.

Partiet (motor/parti.py) körs i sin egen tråd och stannar vid varje fråga. Rummet håller den aktuella
frågan, tar emot svar från rätt enhet, översätter enkla svar (valt alternativ, ja/nej, tal, en
pusselplacering) till motorns svarskoder och sparar partiet (uppstart + logg) efter varje svar.
Efter en omstart återskapas rummet ur det sparade: loggen spelas upp och partiet står där det stod.
"""
import json
import secrets
import threading
import time
from pathlib import Path

from motor.lage import bild
from motor.pussel import las_marklayout
from motor.spelledare import ledare
from motor.parti import Parti
from motor.styrning import koda


class SvarsFel(ValueError):
    """Svaret går inte att använda (fel fråga, fel enhet eller fel form)."""


def nytt_id():
    return secrets.token_urlsafe(5).replace("-", "x").replace("_", "y")


class Rum:
    def __init__(self, id_, uppstart, logg=None, katalog=None, data=None, skapad=None):
        self.id = id_
        self.uppstart = uppstart
        self.katalog = Path(katalog) if katalog else None
        self.skapad = skapad or time.time()
        self.parti = Parti.fran_sparat(uppstart, logg or [], data=data)
        self.las = threading.Lock()
        self.fraga = None
        self.klart = False
        self.fel = None
        self.svar = []                      # läsbar historik: vem svarade vad
        self.bild = self.ledare = None
        self._ga_vidare()

    # ------------------------------------------------------------------ partiet
    def _ga_vidare(self):
        try:
            self.fraga = self.parti.steg()
            self.klart = self.fraga is None
            self.bild = bild(self.parti)             # läses medan motorn står still
            self.ledare = ledare(self.parti, self.fraga)
        except Exception as e:              # noqa: BLE001 — visas i rummet i stället för att krascha servern
            self.fel = f"{type(e).__name__}: {e}"
            self.fraga = None
        self.spara()

    def spara(self):
        if not self.katalog:
            return
        self.katalog.mkdir(parents=True, exist_ok=True)
        tmp = self.katalog / f"{self.id}.json.tmp"
        tmp.write_text(json.dumps({"id": self.id, "skapad": self.skapad, "uppstart": self.uppstart,
                                   "logg": self.parti.logg, "svar": self.svar[-200:]},
                                  ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.katalog / f"{self.id}.json")

    @classmethod
    def ladda(cls, fil, data=None):
        d = json.loads(Path(fil).read_text(encoding="utf-8"))
        rum = cls(d["id"], d["uppstart"], d["logg"], Path(fil).parent, data, d.get("skapad"))
        rum.svar = d.get("svar", [])
        return rum

    # ------------------------------------------------------------------ svar
    def far_svara(self, kvarter):
        """Beslut besvaras av sitt kvarter; slumpfrågor (fysiskt spel) av vilken enhet som helst."""
        f = self.fraga
        return f is not None and (f.kanal == "slump" or f.kvarter == kvarter or kvarter == "bordet")

    def oversatt(self, svar):
        """Enhetens svar → motorns svarskod, utifrån frågans vy."""
        f = self.fraga
        vy = f.vy
        if "forslag" in svar:                              # "gör som förslaget"
            return f.forslag
        typ = vy.get("typ")
        mark = self._mark(svar, vy) if "mark" in svar else None
        if typ == "markexpansion" and mark is not None:
            return koda(mark, [])
        if typ in ("val", "markexpansion"):
            i = svar.get("val")
            alt = vy.get("alternativ", [])
            if not isinstance(i, int) or not 0 <= i < len(alt):
                raise SvarsFel("välj ett av alternativen")
            return alt[i]["kod"]
        if typ == "flerval":
            valda = svar.get("flera", [])
            alt = vy.get("alternativ", [])
            if not all(isinstance(i, int) and 0 <= i < len(alt) for i in valda) or len(set(valda)) != len(valda):
                raise SvarsFel("välj bland alternativen")
            if "max" in vy and len(valda) > vy["max"]:
                raise SvarsFel(f"högst {vy['max']}")
            return {"lista": [alt[i]["kod"] for i in valda]}
        if typ == "janej":
            if not isinstance(svar.get("svar"), bool):
                raise SvarsFel("svara ja eller nej")
            return svar["svar"]
        if typ == "tal":
            v = svar.get("svar")
            if not isinstance(v, int) or isinstance(v, bool) or not vy["min"] <= v <= vy["max"]:
                raise SvarsFel(f"ett heltal {vy['min']}–{vy['max']}")
            return v
        if typ == "pussel":
            plac = svar.get("placering")
            namn = {p["namn"] for p in vy["projekt"]}
            try:
                rent = [[str(n), [[int(r), int(k)] for r, k in celler], int(lager)] for n, celler, lager in plac]
            except (TypeError, ValueError):
                raise SvarsFel("placeringen ska vara [[namn, [[rad, kol], ...], lager], ...]") from None
            if not all(n in namn for n, _, _ in rent):
                raise SvarsFel("okänt projekt i placeringen")
            return koda([[n, c, 0] for n, c in mark or []] + rent, [])
        raise SvarsFel("frågan kan bara besvaras med förslaget")

    @staticmethod
    def _mark(svar, vy):
        """En flyttad marklayout ([[id, rutor], ...]) — granskas här så att spelaren får veta varför."""
        former = {b["id"]: [tuple(c) for c in b["form"]] for b in vy.get("markbitar", [])}
        if vy.get("typ") == "markexpansion":
            former[vy["id"]] = [tuple(c) for c in vy["form"]]
        bitar = las_marklayout(svar["mark"], former)
        if isinstance(bitar, str):
            raise SvarsFel(f"marken: {bitar}")
        return [[i, sorted(list(c) for c in celler)] for i, celler in sorted(bitar.items())]

    def svara(self, kvarter, nr, svar):
        with self.las:
            if self.fraga is None:
                raise SvarsFel("ingen fråga väntar")
            if nr != self.fraga.nr:
                raise SvarsFel("frågan är redan besvarad")
            if not self.far_svara(kvarter):
                raise SvarsFel("det är inte er fråga")
            kod = self.oversatt(svar)
            self.svar.append({"nr": nr, "kvarter": self.fraga.kvarter or kvarter, "rubrik": self.fraga.vy.get("rubrik"),
                              "svar": _lasbart(self.fraga.vy, svar), "tid": time.time()})
            self.parti.svara(kod)
            self._ga_vidare()

    # ------------------------------------------------------------------ vad enheterna ser
    def lage(self, kvarter=None):
        f = self.fraga
        return {
            "rum": self.id,
            "slump": self.uppstart.get("slump", "digital"),
            "kvarter": [{"namn": k["namn"], "styrning": k["styrning"]} for k in self.uppstart["kvarter"]],
            "bild": self.bild,
            "ledare": self.ledare,
            "fraga": None if f is None else {"nr": f.nr, "kanal": f.kanal, "kvarter": f.kvarter, "skede": f.skede,
                                             "vy": f.vy, "min": self.far_svara(kvarter) if kvarter else False},
            "svar": self.svar[-30:],
            "drag": [e["visa"] for e in self.parti.logg[-400:] if e.get("visa")][-15:],
            "bordet": self.parti.visningar[-12:],
            "klart": self.klart,
            "resultat": self.parti.resultat if self.klart else None,
            "fel": self.fel,
        }


def _lasbart(vy, svar):
    if "forslag" in svar:
        return f"förslaget: {vy.get('forslag_text', '')}"
    if "val" in svar and vy.get("alternativ"):
        return vy["alternativ"][svar["val"]]["text"]
    if "flera" in svar:
        return ", ".join(vy["alternativ"][i]["text"] for i in svar["flera"]) or "inga"
    if "svar" in svar:
        return {True: "ja", False: "nej"}.get(svar["svar"], str(svar["svar"]))
    if "placering" in svar:
        return f"{len(svar['placering'])} projekt placerade"
    if "mark" in svar:
        return "markexpansionen lagd"
    return ""
