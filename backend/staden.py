"""Åkepol Staden – den långa versionen. Hela staden, kvarter efter kvarter.

Staden är en beständig värld ovanpå Kvarterets motor (kvarteret.py). Den har tjugo kvarter
(dotterbolagen i data/0_ledning/L_dotterbolag.csv) och ett antal bolag, människor och
datorbolag. Spelet går i omgångar: varje bolag väljer ett ledigt kvarter på kartan, och
sedan spelas kvarteren samtidigt som ett vanligt parti (kort eller i kampanjlängd).
När partiet är slut förs resultatet tillbaka hit:

  * kvarteret står kvar på kartan i bolagets färg
  * kassan och fastigheterna följer med bolaget in i nästa omgång, och förvaltas vidare där
  * yielden fortsätter där den slutade
  * bolaget får lärdomar, som köper nivåer i kunskapsträdet

Reglerna för själva kvarteren är brädspelets. Det som är Stadens eget, och som är satt för
att kunna provspelas och justeras, är: poängräkningen över flera kvarter (i fora_resultat),
lärdomarna och kunskapsträdets effekter (i början av filen).

Staden skriver bara i sina egna data: data/staden/<kod>.json.
"""
import json
import os
import random
import re
import string
import time
from datetime import datetime
from typing import Optional

from config import DATA_DIR, YIELD_START_BOSTADER, YIELD_START_KOMMERSIELLT
from data_loader import read_csv
import kvarteret
from kvarteret import COLORS, KRoom

STAD_DIR = os.path.join(DATA_DIR, "staden")
DOTTERBOLAG = os.path.join(DATA_DIR, "0_ledning", "L_dotterbolag.csv")
MAX_BOLAG = 6

# ── Stadens egna regler ──
LARDOMAR_PER_KVARTER = 3
LARDOMAR_ALLA_KRAV = 2          # extra när inget steg på tid, kvalitet eller hållbarhet missades
KUNSKAP_MAX = 3
KUNSKAP_PRIS = 3                # lärdomar per nivå: nivå n kostar n × priset
# Vad varje nivå i en gren ger bolaget i alla kommande kvarter. "akepedia" pekar på de dokument
# i Åkepedia som grenen motsvarar (bara namn och version; upphandling har ingen motsvarighet där).
KUNSKAP = {
    "projektering": {"namn": "Projektering", "ger": "+1 hållbarhet från start", "arv": {"h": 1},
                     "akepedia": [{"dokument": "Projekteringsanvisningar PH", "typ": "projekteringsanvisning-ph", "version": "2026.01"}, {"dokument": "Projektera med omtanke", "typ": "projektera-med-omtanke", "version": "2023.01"}, {"dokument": "Handlingsutformning", "typ": "handlingsutformning", "version": "2026.02"}, {"dokument": "BIM Execution Plan (BEP)", "typ": "bep", "version": "2026.01"}]},
    "upphandling":  {"namn": "Upphandling", "ger": "+1 erfarenhet på alla slag", "arv": {"erf": 1}},
    "produktion":   {"namn": "Produktion", "ger": "+1 riskbuffert från start", "arv": {"rb": 1},
                     "akepedia": [{"dokument": "Svanen valda (P) poäng", "typ": "svanen", "version": "2025.01"}, {"dokument": "Anvisning – Märkning och skyltning av installationer", "typ": "anvisning-markning", "version": "2023.1"}]},
    "forvaltning":  {"namn": "Förvaltning", "ger": "+1 på förhandling och energislag", "arv": {"forh": 1, "energi": 1},
                     "akepedia": [{"dokument": "Projekteringsanvisning Mätning", "typ": "projekteringsanvisning-matning", "version": "2025.01"}]},
}

# Kartan: 6 × 5 platser. K = kvarter, v = vatten, p = park, s/S = befintlig stad (låg/hög)
KARTA = ("KKKpKv"
         "KKSKKv"
         "KpKKSK"
         "KKsKKp"
         "vKKSKK")
KOLUMNER = 6


def _kvartersnamn(bolagsnamn: str) -> str:
    """'Cornelia Stadsutveckling AB' → 'Cornelia'. Kvarteret heter som sitt dotterbolag."""
    n = bolagsnamn
    for _ in range(3):
        n = re.sub(r"\s+(AB|Stadsutveckling|Stadsbygg|Kvartersbolag|Utveckling|Stadsdel)$", "", n).strip()
    return re.sub(r"\s+Etapp \d+$", "", n).strip() or bolagsnamn


def _slump_id(n=8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


class Stad:
    def __init__(self):
        self.kod = ""
        self.skapad = datetime.now().isoformat(timespec="seconds")
        self.langd = "kort"             # längden på varje kvarter: "kort" eller "kampanj"
        self.omgang = 0                 # antal spelade omgångar
        self.klar = False
        self.rum: Optional[str] = None  # pågående partis rumskod
        self.yield_b = YIELD_START_BOSTADER
        self.yield_k = YIELD_START_KOMMERSIELLT
        self.bolag: list = []
        self.kvarter: list = []
        self.handelser: list = []       # stadens logg, nyast sist (fylls bara på)

    # ── Skapa, läsa, spara ──

    @classmethod
    def ny(cls, kod: str, gd, namn: str, antal_datorbolag: int = 3, langd: str = "kort") -> "Stad":
        s = cls()
        s.kod = kod
        s.langd = langd if langd in kvarteret.LAGEN else "kort"
        rader = [r for r in read_csv(DOTTERBOLAG) if (r.get("Namn") or "").strip()]
        for i, r in enumerate(rader[:KARTA.count("K")]):
            s.kvarter.append({
                "id": (r.get("ID") or f"DB-{i + 1}").strip(), "namn": _kvartersnamn(r["Namn"].strip()),
                "dotterbolag": r["Namn"].strip(), "stadsdel": (r.get("Stadsdel") or "").strip() or str(i % 5 + 1),
                "status": "ledig", "bolag": None, "omgang": None, "poang": None})
        s.lagg_till_bolag(namn or "Bolag 1")
        for n in range(1, max(0, min(MAX_BOLAG - 1, antal_datorbolag)) + 1):
            s.lagg_till_bolag(f"Datorbolag {n}", is_bot=True)
        s.logga(f"Staden grundas med {len(s.bolag)} bolag och {len(s.kvarter)} lediga kvarter.")
        s.spara()
        return s

    @classmethod
    def las(cls, kod: str) -> Optional["Stad"]:
        if not re.fullmatch(r"[A-Z]{4}", kod or ""):
            return None
        try:
            with open(os.path.join(STAD_DIR, f"{kod}.json"), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return None
        s = cls()
        s.__dict__.update(data)
        return s

    def spara(self):
        os.makedirs(STAD_DIR, exist_ok=True)
        tmp = os.path.join(STAD_DIR, f"{self.kod}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, ensure_ascii=False, default=str)
        os.replace(tmp, os.path.join(STAD_DIR, f"{self.kod}.json"))

    def logga(self, text: str):
        self.handelser.append({"ts": datetime.now().isoformat(timespec="seconds"),
                               "omgang": self.omgang, "text": text})

    # ── Bolag ──

    def lagg_till_bolag(self, namn: str, is_bot: bool = False) -> Optional[dict]:
        if len(self.bolag) >= MAX_BOLAG or self.rum:
            return None
        b = {"id": _slump_id(6), "nyckel": _slump_id(16), "namn": (namn or "Bolag")[:24], "is_bot": is_bot,
             "farg": COLORS[len(self.bolag) % len(COLORS)], "vard": not self.bolag,
             "s1": 0.0, "s2": 0.0, "s3": 0.0, "poang": 0.0, "bygg": [], "ek": 0.0, "props": [],
             "lardomar": 0, "kunskap": {g: 0 for g in KUNSKAP}, "val": None, "pid": None}
        self.bolag.append(b)
        return b

    def bolag_med_nyckel(self, nyckel: Optional[str]) -> Optional[dict]:
        return next((b for b in self.bolag if nyckel and b["nyckel"] == nyckel), None)

    def lediga(self) -> list:
        return [k for k in self.kvarter if k["status"] == "ledig"]

    @property
    def omgangar_totalt(self) -> int:
        return len(self.kvarter) // max(1, len(self.bolag))

    # ── Drag mellan omgångarna ──

    def valj(self, bolag: dict, kvarter_id: str) -> Optional[str]:
        if self.rum or self.klar:
            return "Det går inte att välja kvarter just nu."
        k = next((k for k in self.kvarter if k["id"] == kvarter_id), None)
        if not k or k["status"] != "ledig":
            return "Kvarteret är inte ledigt."
        if any(b["val"] == kvarter_id for b in self.bolag if b is not bolag):
            return "Ett annat bolag har redan valt det kvarteret."
        bolag["val"] = kvarter_id
        self.spara()
        return None

    def kop_kunskap(self, bolag: dict, gren: str) -> Optional[str]:
        if gren not in KUNSKAP:
            return "Okänd gren."
        if self.rum:
            return "Kunskap köps mellan omgångarna."
        niva = bolag["kunskap"][gren]
        if niva >= KUNSKAP_MAX:
            return "Grenen är fullt utbyggd."
        pris = (niva + 1) * KUNSKAP_PRIS
        if bolag["lardomar"] < pris:
            return f"Det kostar {pris} lärdomar."
        bolag["lardomar"] -= pris
        bolag["kunskap"][gren] = niva + 1
        self.logga(f"{bolag['namn']} bygger ut {KUNSKAP[gren]['namn'].lower()} till nivå {niva + 1}.")
        self.spara()
        return None

    def _datorbolagens_drag(self):
        for b in self.bolag:
            if not b["is_bot"]:
                continue
            for gren in random.sample(list(KUNSKAP), len(KUNSKAP)):
                if b["kunskap"][gren] < KUNSKAP_MAX and b["lardomar"] >= (b["kunskap"][gren] + 1) * KUNSKAP_PRIS:
                    self.kop_kunskap(b, gren)
                    break

    def _arv(self, b: dict) -> dict:
        arv = {"ek": b["ek"], "props": [dict(x) for x in b["props"]]}
        for gren, niva in b["kunskap"].items():
            for nyckel, v in KUNSKAP[gren]["arv"].items():
                arv[nyckel] = arv.get(nyckel, 0) + v * niva
        return arv

    # ── En omgång: alla bolag bygger var sitt kvarter i samma parti ──

    def starta_omgang(self, gd, manager=None) -> KRoom:
        if self.rum:
            raise ValueError("En omgång pågår redan.")
        if self.klar:
            raise ValueError("Staden är färdigbyggd.")
        self._datorbolagens_drag()
        tagna = {b["val"] for b in self.bolag if b["val"]}
        for b in self.bolag:        # den som inte har valt får ett ledigt kvarter
            lediga_ids = {k["id"] for k in self.lediga()}
            if b["val"] not in lediga_ids:
                b["val"] = None
            if not b["val"]:
                kvar = [k["id"] for k in self.lediga() if k["id"] not in tagna]
                b["val"] = random.choice(kvar)
                tagna.add(b["val"])
        kod = (manager.ny_kod() if manager else "".join(random.choices(string.ascii_uppercase, k=4)))
        room = KRoom(kod, gd, self.langd)
        room.stad_kod = self.kod
        room.yield_b, room.yield_k = self.yield_b, self.yield_k
        for b in self.bolag:
            p = room.add_player(b["namn"], is_bot=b["is_bot"])
            p.color = b["farg"]
            p.arv = self._arv(b)
            p.rb += p.arv.get("rb", 0)
            b["pid"] = p.id
            k = next(k for k in self.kvarter if k["id"] == b["val"])
            k.update(status="pagar", bolag=b["id"], omgang=self.omgang + 1)
        room.vid_slut = self.fora_resultat
        self.rum = room.code
        if manager:
            manager.rooms[room.code] = room
        self.logga(f"Omgång {self.omgang + 1} börjar: " + ", ".join(
            f"{b['namn']} tar {next(k['namn'] for k in self.kvarter if k['id'] == b['val'])}" for b in self.bolag) + ".")
        self.spara()
        return room

    def fora_resultat(self, room: KRoom):
        """Partiet är slut: för över poäng, kassa, fastigheter och lärdomar till staden."""
        for b in self.bolag:
            p = room.players.get(b["pid"])
            if not p:
                continue
            r = p.result
            # Utveckling är volym och växer för varje kvarter. Byggande är hur bra bolaget bygger:
            # snittet över dess kvarter. Förvaltning är bolagets samlade värde just nu.
            # Måluppfyllelsen f(n) räknas per kvarter, som i brädspelets slutformel.
            b["s1"] = round(b["s1"] + r["skede1"] * r["f_n"], 1)
            b.setdefault("bygg", []).append(round(r["skede2"] * r["f_n"], 1))
            b["s2"] = round(sum(b["bygg"]) / len(b["bygg"]), 1)
            b["s3"] = r["skede3"]
            b["poang"] = round(b["s1"] + b["s2"] + b["s3"], 1)
            b["ek"] = round(p.ek, 1)
            b["props"] = [dict(x) for x in p.props]
            for x in b["props"]:        # samma kort kan dyka upp i ett senare parti: gör id:t unikt i staden
                if not x["id"].startswith("o"):
                    x["id"] = f"o{self.omgang + 1}-{x['id']}"
            fick = LARDOMAR_PER_KVARTER + (LARDOMAR_ALLA_KRAV if r["n_total"] == 0 else 0)
            b["lardomar"] += fick
            k = next(k for k in self.kvarter if k["id"] == b["val"])
            k.update(status="klart", poang=r["score"], bta=p.bta,
                     typer=sorted({x["typ"] for x in p.projects}))
            self.logga(f"{b['namn']} är klart med {k['namn']}: {r['score']:.0f} poäng, {fick} lärdomar.")
            b["val"], b["pid"] = None, None
        self.yield_b, self.yield_k = room.yield_b, room.yield_k
        self.omgang += 1
        self.rum = None
        if len(self.lediga()) < len(self.bolag):
            self.klar = True
            vinnare = max(self.bolag, key=lambda b: b["poang"])
            self.logga(f"Staden är färdigbyggd. {vinnare['namn']} vinner med {vinnare['poang']:.0f} poäng.")
        self.spara()

    # ── Vy ──

    def vy(self, nyckel: Optional[str]) -> dict:
        jag = self.bolag_med_nyckel(nyckel)
        per_id = {b["id"]: b for b in self.bolag}
        vald_av = {b["val"]: b for b in self.bolag if b["val"]}
        hogsta = max([k["poang"] or 0 for k in self.kvarter] + [1])
        platser, i = [], 0
        for n, tecken in enumerate(KARTA):
            if tecken != "K" or i >= len(self.kvarter):
                platser.append({"id": f"f{n}", "sort": {"v": "vatten", "p": "park"}.get(tecken, "stad"),
                                "hog": tecken == "S"})
                continue
            k = self.kvarter[i]
            i += 1
            agare = per_id.get(k["bolag"]) or vald_av.get(k["id"])
            platser.append({
                "id": k["id"], "sort": "kvarter", "namn": k["namn"], "stadsdel": k["stadsdel"],
                "status": k["status"], "farg": agare["farg"] if agare else None,
                "agare": agare["namn"] if agare else None, "poang": k["poang"],
                "hojd": max(0.15, (k["poang"] or 0) / hogsta) if k["status"] == "klart" else None,
                "vald_av": vald_av[k["id"]]["id"] if k["id"] in vald_av and k["status"] == "ledig" else None})
        offentlig = lambda b: {k: b[k] for k in ("id", "namn", "farg", "is_bot", "vard", "s1", "s2", "s3", "poang")} | {
            "kvarter": sum(1 for k in self.kvarter if k["bolag"] == b["id"] and k["status"] == "klart"),
            "fastigheter": len(b["props"]), "har_valt": bool(b["val"])}
        ut = {
            "kod": self.kod, "langd": self.langd, "omgang": self.omgang, "omgangar": self.omgangar_totalt,
            "klar": self.klar, "pagar": bool(self.rum), "yield_b": self.yield_b, "yield_k": self.yield_k,
            "kolumner": KOLUMNER, "platser": platser,
            "stallning": sorted((offentlig(b) for b in self.bolag), key=lambda b: -b["poang"]),
            "handelser": self.handelser[-8:],
            "kunskap": {g: {"namn": v["namn"], "ger": v["ger"],
                            "akepedia": [p["dokument"] for p in v.get("akepedia", [])]} for g, v in KUNSKAP.items()},
            "kunskap_max": KUNSKAP_MAX, "kunskap_pris": KUNSKAP_PRIS,
            "jag": None,
        }
        if jag:
            ut["jag"] = {**offentlig(jag), "ek": jag["ek"], "props": jag["props"], "lardomar": jag["lardomar"],
                         "kunskap_niva": jag["kunskap"], "val": jag["val"],
                         "rum": {"kod": self.rum, "pid": jag["pid"],
                                 "sida": "/kampanj" if self.langd == "kampanj" else "/kvarteret"} if self.rum else None}
        return ut


class StadenManager:
    def __init__(self):
        self.stader: dict = {}

    def _ny_kod(self) -> str:
        while True:
            kod = "".join(random.choices(string.ascii_uppercase, k=4))
            if kod not in self.stader and not os.path.exists(os.path.join(STAD_DIR, f"{kod}.json")):
                return kod

    def skapa(self, gd, namn: str, antal_datorbolag: int, langd: str) -> Stad:
        s = Stad.ny(self._ny_kod(), gd, namn, antal_datorbolag, langd)
        self.stader[s.kod] = s
        return s

    def hamta(self, kod: str) -> Optional[Stad]:
        kod = (kod or "").upper()
        if kod not in self.stader:
            s = Stad.las(kod)
            if not s:
                return None
            if s.rum and s.rum not in kvarteret.kvarteret_manager.rooms and not kvarteret.kvarteret_manager.hamta(s.rum):
                # Partiet försvann (t.ex. vid omstart mitt i ett kort parti): lämna tillbaka kvarteren
                for k in s.kvarter:
                    if k["status"] == "pagar":
                        k.update(status="ledig", bolag=None, omgang=None)
                s.rum = None
                s.logga("Omgången avbröts och kvarteren är lediga igen.")
                s.spara()
            self.stader[kod] = s
        s = self.stader[kod]
        # Ett sparat kampanjrum som lästs in igen ska fortfarande rapportera hit
        if s.rum:
            room = kvarteret.kvarteret_manager.hamta(s.rum)
            if room and not room.vid_slut:
                room.vid_slut = s.fora_resultat
        return s


staden_manager = StadenManager()
