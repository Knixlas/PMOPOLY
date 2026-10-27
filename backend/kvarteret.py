"""Åkepol Kvarteret – kortversion av Åkepol, helt digital och utan spelplaner.

Tre huvuddelar à ca 10 minuter (Före / Under / Efter). Alla spelare beslutar
samtidigt, servern avslöjar och räknar. Använder bara befintliga komponenter
(projekt, PC/AC, dialog- och politikkort, markexpansioner, leverantörer,
organisationer, händelsekort, faskort, kulturkort, konsekvens- och garantikort) via
GameData. Förvaltningen följer Förvaltning 2.1 med lekarna i data/forvaltning_2-1/,
och slutpoängen räknas med economics.calc_final_score.

Kvarteret skriver bara i sina egna data: data/kvarteret_logs/ (fylls bara på).
"""
import asyncio
import json
import os
import random
import re
import string
import time
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional

from fastapi import WebSocket

import models
from config import (
    DATA_DIR, D20_THRESHOLDS, MARK_TOMT_KOSTNAD, EXPANSION_KOSTNAD, TOMT_CELLS,
    START_Q_KRAV, START_H_KRAV, MIN_T, MAX_PROJECTS, PHASE_COST,
    YIELD_START_BOSTADER, YIELD_START_KOMMERSIELLT, ENERGY_CLASSES, SLOT_TO_CARD_IDS,
    EK_DN_MODIFIER, EFFECTIVE_DN_ABS_MAX, LOAN_RATIO,
)
from data_loader import read_csv
from economics import calc_final_score
from engine import _mv_lookup

LOG_DIR = os.path.join(DATA_DIR, "kvarteret_logs")
CELL_KVM = 250                 # 16 rutor = 4 000 kvm BYA
BOSTAD_TYPER = ("BRF", "HYRESRÄTT")
KOMP_KEYS = ["STA", "KOM", "SAM", "NOG", "INN", "ABM"]
COLORS = ["#E4572E", "#2E86AB", "#7BB661", "#F2A541", "#9B5DE5", "#00B8A9"]
MAX_PLAYERS = 6

# Sekunder per beslut. Info-skärmar har egen klocka.
TIMER = {"pc": 45, "p1": 45, "ac": 45, "upph": 60, "fas": 50, "f_setup": 50,
         "kvartal": 70, "info": 40, "intro": 60}

UPPHANDLINGAR = [
    ("Organisation", ["OPERATIVT TEAM", "STÖDFUNKTIONER", "MARKNADSTEAM", "DIGITALISERING"]),
    ("Mark, grund och klimatskal", ["MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER"]),
    ("Inredning och installationer", ["STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"]),
]
ORG_SLOTS = set(UPPHANDLINGAR[0][1])

# Kortversionen: spelaren gör de viktiga valen, resten slumpas – lika för alla bolag
# och utan att straffa någon
START_PROJEKT_ANTAL = 4    # fyra startprojekt av olika typ
START_PROJEKT_RUTOR = 12   # på högst 12 av tomtens 16 rutor mark (bostäder staplas)
P1_ROUNDS = 2              # rundor för att ta 1–2 projekt till
MAX_EGNA_UPPH = 3          # upphandlingar man gör själv; resten får gemensam slumpad nivå 2–3
FAS_RUNDOR = 2             # byggfaser man spelar; övriga godkänns automatiskt
QUARTERS = 1               # kvartal i förvaltningen
ALLA_SLOTS = [s for _, slots in UPPHANDLINGAR for s in slots]

# Förvaltning 2.1 (FORVALTNING_DESIGN_2-1.md) – lekarna läses ur data/forvaltning_2-1/
F21_DIR = os.path.join(DATA_DIR, "forvaltning_2-1")
ENERGI_MAX = {1: 3, 2: 2, 3: 1}           # energiuppgraderingar per kvartal
ENERGI_KOSTNAD = 3                       # Mkr per slagrunda
YIELD_SPANN = {"b": (2.0, 6.0), "k": (3.0, 7.0)}
_F21: Dict[str, list] = {}


def f21(namn: str) -> list:
    if namn not in _F21:
        _F21[namn] = read_csv(os.path.join(F21_DIR, f"F2-1_{namn}.csv"))
    return _F21[namn]


def typ_namn(typ: str) -> str:
    return {"HYRESRÄTT": "hyresrätt", "FÖRSKOLA": "förskola", "LOKAL": "lokal", "KONTOR": "kontor"}.get(typ, typ.lower())


# ── Hjälpfunktioner ──

def d(sides: int, rng: random.Random) -> int:
    return rng.randint(1, sides)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_effekt(text: str, bta_klass: str = "C") -> dict:
    """Tolka korttext som '-6 Mkr, +1 mån, -1 Q' till siffror."""
    out = {"mkr": 0.0, "man": 0, "q": 0, "h": 0, "rb": 0}
    if not text or text.strip().lower() in ("ingen effekt", "—", "-"):
        return out
    if "//" in text:
        parts = [p.strip() for p in text.split("//")]
        chosen = parts[0]
        for p in parts:
            if bta_klass in ("A", "B") and "A-B" in p or bta_klass in ("C", "D") and "C-D" in p:
                chosen = p
        text = chosen
    m = re.search(r"\(B\)ÄTA\s*\+(\d+)/\+(\d+)/\+(\d+)", text)
    if m:
        idx = {"A": 0, "B": 0, "C": 1, "D": 2}.get(bta_klass, 1)
        out["mkr"] += int(m.group(idx + 1))
        return out
    if ":" in text:
        text = text.split(":", 1)[1]
    num = r"([+-]?\d+(?:[.,]\d+)?)"
    for v in re.findall(num + r"\s*Mkr", text):
        out["mkr"] += _num(v)
    for v in re.findall(num + r"\s*mån", text):
        out["man"] += int(_num(v))
    for v in re.findall(num + r"\s*T\b", text):
        out["man"] += int(_num(v))
    for v in re.findall(num + r"\s*Q\b", text):
        out["q"] += int(_num(v))
    for v in re.findall(num + r"\s*H\b", text):
        out["h"] += int(_num(v))
    for v in re.findall(num + r"\s*Rb\b", text):
        out["rb"] += int(_num(v))
    return out


def parse_krav(text: str) -> Dict[str, int]:
    """'SAM 3, INN 1' → {'SAM': 3, 'INN': 1}."""
    out = {}
    for k, v in re.findall(r"([A-ZÅÄÖ]{3})\s*(\d+)", text or ""):
        out[k] = out.get(k, 0) + int(v)
    return out


def markbehov(projects: List[dict]) -> int:
    """Rutor mark som projekten kräver. Bostäder (BRF, hyresrätt) får läggas i ett övre
    lager ovanpå andra projekt, så marken blir den största av kommersiella och bostadsrutor."""
    bostad = sum(x["rutor"] for x in projects if x["typ"] in BOSTAD_TYPER)
    ovrigt = sum(x["rutor"] for x in projects if x["typ"] not in BOSTAD_TYPER)
    return max(bostad, ovrigt)


def proj_dict(p) -> dict:
    return {
        "id": p.id, "namn": p.namn, "typ": p.typ, "kostnad": p.kostnad,
        "rutor": max(1, p.bta // CELL_KVM), "bta": p.bta, "anskaffning": p.anskaffning,
        "marknadsvarde": p.marknadsvarde, "rorlig": p.rorlig_intakt,
        "q": p.kvalitet, "h": p.hallbarhet, "tid": p.tid, "namnd": p.namndbeslut,
        "energiklass": p.energiklass or "C", "driftnetto": p.driftnetto,
        "beskrivning": p.beskrivning,
        "bas_dn": p.bas_dn if p.bas_dn is not None else int(p.driftnetto or 0),
        "lanebelopp": p.lanebelopp,
        "krav_lev": {k: int(v.split()[-1]) for k, v in p.supplier_reqs.items()
                     if v and v.startswith("nivå")},
    }


# ── Modell ──

@dataclass
class KPlayer:
    id: str
    name: str
    color: str
    is_bot: bool = False
    is_host: bool = False
    # Ledning och personal
    pc: Optional[dict] = None
    ac: Optional[dict] = None
    fc: Optional[dict] = None
    fs: List[dict] = field(default_factory=list)
    # Skede 1
    projects: List[dict] = field(default_factory=list)
    returned: List[dict] = field(default_factory=list)
    rutor: int = TOMT_CELLS
    expansions: int = 0
    rb: int = 0
    t_pu: int = 0              # tid från dialog-/politikkort i skede 1
    q_krav: int = START_Q_KRAV
    h_krav: int = START_H_KRAV
    ekonomi1: dict = field(default_factory=dict)
    # Skede 2
    abt_start: float = 0.0
    abt: float = 0.0
    q: int = 0
    h: int = 0
    t: int = 12
    t_mal: int = 12
    erf: int = 0
    komp: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in KOMP_KEYS})
    lev: Dict[str, dict] = field(default_factory=dict)
    n_q: int = 0
    n_h: int = 0
    n_t: int = 0
    tb: float = 0.0
    # Skede 3
    ek: float = 0.0            # eget kapital; kassan i förvaltningen
    props: List[dict] = field(default_factory=list)
    hand: List[dict] = field(default_factory=list)   # personkort
    forkop: List[str] = field(default_factory=list)  # förköp per fastighetstyp
    extra_ansk: float = 0.0    # anskaffning för fastigheter köpta i förvaltningen
    # Runtime
    offer: dict = field(default_factory=dict)
    choice: Optional[dict] = None
    ready: bool = False
    log: List[dict] = field(default_factory=list)
    result: dict = field(default_factory=dict)

    @property
    def rutor_kvar(self) -> int:
        return self.rutor - markbehov(self.projects)

    def passar(self, proj: dict) -> bool:
        return markbehov(self.projects + [proj]) <= self.rutor

    @property
    def bta(self) -> int:
        return sum(p["bta"] for p in self.projects)

    @property
    def bya(self) -> int:
        return markbehov(self.projects) * CELL_KVM

    @property
    def bta_klass(self) -> str:
        return models.classify(self.bta, models.BTA_CLASSES) if self.bta else "A"

    @property
    def bya_klass(self) -> str:
        return models.classify(self.bya, models.BYA_CLASSES) if self.bya else "A"

    def public(self) -> dict:
        return {
            "id": self.id, "name": self.name, "color": self.color, "is_bot": self.is_bot,
            "is_host": self.is_host, "submitted": self.choice is not None, "ready": self.ready,
            "pc": self.pc["namn"] if self.pc else None,
            "ac": self.ac["namn"] if self.ac else None,
            "fc": self.fc["namn"] if self.fc else None,
            "n_projects": len(self.projects), "bta": self.bta,
            "n_props": len(self.props), "rb": self.rb,
            "abt": round(self.abt, 1), "ek": round(self.ek, 1),
        }

    def private(self) -> dict:
        return {
            **self.public(),
            "pc_full": self.pc, "ac_full": self.ac, "fc_full": self.fc, "fs_full": self.fs,
            "projects": self.projects, "returned": self.returned,
            "rutor": self.rutor, "rutor_kvar": self.rutor_kvar, "expansions": self.expansions,
            "rutor_bostad": sum(x["rutor"] for x in self.projects if x["typ"] in BOSTAD_TYPER),
            "rutor_ovrigt": sum(x["rutor"] for x in self.projects if x["typ"] not in BOSTAD_TYPER),
            "q_krav": self.q_krav, "h_krav": self.h_krav,
            "bya": self.bya, "bta_klass": self.bta_klass, "bya_klass": self.bya_klass,
            "ekonomi1": self.ekonomi1, "abt_start": round(self.abt_start, 1),
            "q": self.q, "h": self.h, "t": self.t, "t_mal": self.t_mal, "erf": self.erf,
            "komp": self.komp, "lev": self.lev,
            "n_q": self.n_q, "n_h": self.n_h, "n_t": self.n_t, "tb": round(self.tb, 1),
            "props": self.props, "hand": self.hand, "forkop": self.forkop,
            "offer": self.offer, "choice": self.choice, "result": self.result,
        }


class KRoom:
    def __init__(self, code: str, gd):
        self.code = code
        self.gd = gd
        self.rng = random.Random()
        self.players: Dict[str, KPlayer] = {}
        self.created = time.time()
        self.touched = time.time()
        self.flow: List[tuple] = []
        self.idx = -1
        self.step = "lobby"
        self.round = 0
        self.kind = "lobby"         # lobby | decision | info | final
        self.deadline: Optional[float] = None
        self.shared: dict = {}      # gemensamt läge för aktuellt steg
        self.reveal: dict = {}      # {title, shared, rows: {pid: [rad]}}
        self.yield_b = YIELD_START_BOSTADER
        self.yield_k = YIELD_START_KOMMERSIELLT
        self.fas_steg: List[int] = []
        self.log_path = os.path.join(
            LOG_DIR, f"{datetime.now():%Y%m%d-%H%M%S}-{code}.jsonl")
        self._build_decks()

    # ── Lekar ──
    def _deck(self, items):
        items = list(items)
        self.rng.shuffle(items)
        return items

    def _build_decks(self):
        gd = self.gd
        # Korten finns i flera exemplar med samma id; varje exemplar får ett eget
        self.proj_piles = {typ: self._deck(dict(proj_dict(p), id=f"{p.id}-{i}") for i, p in enumerate(ps))
                           for typ, ps in gd.projects.items()}
        self.dialog_deck = self._deck(c for c in gd.dialog if c.nr.startswith("D"))
        self.politik_deck = self._deck(c for c in gd.dialog if c.nr.startswith("P"))
        self.exp_deck = self._deck(gd.mark_expansion_deck)
        self.kultur_deck = self._deck(gd.external_support)
        self.penalty = {k: self._deck(v) for k, v in gd.penalty_cards.items()}
        self.garanti = {k: self._deck(v) for k, v in gd.garanti_cards.items()}
        self.personkort = self._deck(f21("personkort"))
        self.dd = self._deck(f21("DD"))
        self.omvarld = self._deck(f21("omvärldskort"))
        self.kvartalskort = self._deck(f21("kvartalskort"))
        self.banken: List[dict] = []  # projektbanken / bankens fastigheter

    def _draw(self, deck: list, refill=None):
        if not deck and refill is not None:
            deck.extend(self._deck(refill))
        return deck.pop() if deck else None

    # ── Logg (Vakten §3: fylls bara på) ──
    def log(self, player: Optional[str], what: str, data: dict):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now().isoformat(timespec="seconds"), "rum": self.code,
                    "steg": self.step, "runda": self.round, "spelare": player,
                    "vad": what, "data": data}, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            print(f"KVARTERET: kunde inte logga: {e}")

    def note(self, p: KPlayer, text: str, mkr: float = 0.0, plan: bool = False, privat: bool = False):
        """En rad i spelarens reveal. Oplanerade belopp hamnar också i lärdomsloggen.
        privat = dolt kort som bara ägaren får läsa."""
        self.reveal.setdefault("rows", {}).setdefault(p.id, []).append(
            {"text": text, "mkr": round(mkr, 1) if mkr else 0, "privat": privat})
        if mkr and not plan:
            p.log.append({"del": self._del(), "text": text, "mkr": round(mkr, 1)})

    def _del(self) -> int:
        s = self.step
        if s in ("pc", "p1", "namnd", "slut1", "intro1"):
            return 1
        if s in ("ac", "upph", "fas", "slut2", "intro2"):
            return 2
        return 3

    # ── Spelare ──
    def add_player(self, name: str, is_bot=False) -> KPlayer:
        pid = "".join(self.rng.choices(string.ascii_lowercase + string.digits, k=8))
        p = KPlayer(id=pid, name=name[:24] or "Bolag", color=COLORS[len(self.players) % len(COLORS)],
                    is_bot=is_bot, is_host=not self.players)
        self.players[pid] = p
        return p

    def humans(self):
        return [p for p in self.players.values() if not p.is_bot]

    # ── Flöde ──
    def start(self):
        self.flow = ([("intro1", 0), ("pc", 0)] +
                     [x for r in range(1, P1_ROUNDS + 1) for x in (("p1", r), ("p1_res", r))] +
                     [("namnd", 0), ("namnd_res", 0), ("slut1", 0), ("intro2", 0), ("ac", 0)] +
                     [("upph", 1), ("upph_res", 1)] +
                     [x for r in range(1, FAS_RUNDOR + 1) for x in (("fas", r), ("fas_res", r))] +
                     [("slut2", 0), ("intro3", 0), ("f_setup", 0)] +
                     [x for q in range(1, QUARTERS + 1) for x in (("kvartal", q), ("kvartal_res", q))] +
                     [("final", 0)])
        self.fas_steg = [self.rng.choice([1, 2, 3, 4]), self.rng.choice([5, 6, 7, 8])]
        # Automatiska upphandlingsnivåer: samma för alla bolag
        self.auto_niva = {slot: self.rng.choice([2, 3]) for slot in ALLA_SLOTS}
        self.log(None, "start", {"spelare": [p.name for p in self.players.values()]})
        self.advance()

    def advance(self):
        self.idx += 1
        self.step, self.round = self.flow[self.idx]
        self.shared = {}
        if not self.step.endswith("_res"):  # _res-stegen visar utfallet som just räknades fram
            self.reveal = {}
        for p in self.players.values():
            p.choice, p.ready, p.offer = None, p.is_bot, {}
        enter = getattr(self, f"_enter_{self.step}")
        kind = enter()
        self.kind = kind
        if kind == "decision":
            self.deadline = time.time() + TIMER.get(self.step, 60)
            for p in self.players.values():
                if p.is_bot:
                    p.choice = self._bot_choice(p)
            self._maybe_resolve()
        elif kind == "info":
            t = TIMER["intro"] if self.step.startswith("intro") else TIMER["info"]
            self.deadline = time.time() + t
            self._maybe_continue()
        else:
            self.deadline = None

    def submit(self, pid: str, data: dict) -> Optional[str]:
        p = self.players.get(pid)
        if not p or self.kind != "decision":
            return "Inget beslut att fatta just nu."
        err = getattr(self, f"_validate_{self.step}")(p, data)
        if err:
            return err
        p.choice = data
        self.log(pid, "beslut", data)
        self._maybe_resolve()
        return None

    def set_ready(self, pid: str):
        p = self.players.get(pid)
        if p and self.kind == "info":
            p.ready = True
            self._maybe_continue()

    def force(self):
        """Klockan slut eller värden trycker vidare."""
        if self.kind == "decision":
            for p in self.players.values():
                if p.choice is None:
                    p.choice = self._bot_choice(p)
                    self.log(p.id, "beslut_auto", p.choice)
            self._maybe_resolve()
        elif self.kind == "info":
            for p in self.players.values():
                p.ready = True
            self._maybe_continue()

    def _maybe_resolve(self):
        if all(p.choice is not None for p in self.players.values()):
            getattr(self, f"_resolve_{self.step}")()
            self.advance()

    def _maybe_continue(self):
        if all(p.ready for p in self.players.values()):
            self.advance()

    # ════════════════ SKEDE 1 – PROJEKTUTVECKLING ════════════════

    def _enter_intro1(self):
        """Fyra startprojekt per bolag av olika typ, på högst START_PROJEKT_RUTOR rutor mark.
        Uppsättningarna väljs så att intäkt, kostnad, ytor och krav blir så lika som möjligt
        mellan bolagen. Startprojekten är redan förankrade och går inte till nämnden."""
        piles = [pile for pile in self.proj_piles.values() if pile]
        kandidater = []
        for _ in range(3000):
            kand = [self.rng.choice(pile) for pile in self.rng.sample(piles, START_PROJEKT_ANTAL)]
            if markbehov(kand) <= START_PROJEKT_RUTOR:
                kandidater.append(kand)
        if not kandidater:
            kandidater = [[min(pile, key=lambda x: x["rutor"]) for pile in piles]]
            # (bara om inga slumpade uppsättningar får plats)
        nycklar = ("anskaffning", "kostnad", "bta", "rutor", "q", "h", "bas_dn")
        vek = lambda kand: [sum(x[k] for x in kand) for k in nycklar]
        vektorer = [vek(k) for k in kandidater]
        median = [sorted(v[i] for v in vektorer)[len(vektorer) // 2] for i in range(len(nycklar))]
        skala = [max(1, max(v[i] for v in vektorer) - min(v[i] for v in vektorer)) for i in range(len(nycklar))]
        avst = lambda v: sum(((a - b) / c) ** 2 for a, b, c in zip(v, median, skala))
        ordning = sorted(range(len(kandidater)), key=lambda i: avst(vektorer[i]))
        anvanda = set()
        for p in self.players.values():
            val = next((kandidater[i] for i in ordning
                        if not any(id(x) in anvanda for x in kandidater[i])), kandidater[ordning[0]])
            for proj in val:
                anvanda.add(id(proj))
                self.proj_piles[proj["typ"]].remove(proj)
                proj = dict(proj, start=True)
                p.projects.append(proj)
                p.q_krav += proj["q"]
                p.h_krav += proj["h"]
            self.log(p.id, "startprojekt", {"projekt": [x["namn"] for x in val],
                                            **dict(zip(nycklar, vek(val)))})
        return "info"

    def _enter_pc(self):
        pool = self._deck(self.gd.pc_staff)
        for i, p in enumerate(self.players.values()):
            p.offer = {"pc": [pool[(i * 3 + k) % len(pool)] for k in range(3)]}
        return "decision"

    def _validate_pc(self, p, data):
        if data.get("id") not in [c["id"] for c in p.offer["pc"]]:
            return "Välj en av projektcheferna."

    def _resolve_pc(self):
        for p in self.players.values():
            p.pc = next(c for c in p.offer["pc"] if c["id"] == p.choice["id"])
            p.rb += p.pc.get("rb", 0)

    def _market(self) -> Dict[str, dict]:
        return {typ: pile[-1] for typ, pile in self.proj_piles.items() if pile}

    def _enter_p1(self):
        self.shared = {"market": self._market(), "runda": self.round, "av": P1_ROUNDS}
        for p in self.players.values():
            p.offer = {"passar": {t: p.passar(x) for t, x in self.shared["market"].items()}}
        return "decision"

    def _validate_p1(self, p, data):
        val = data.get("val")
        if val == "projekt":
            proj = self.shared["market"].get(data.get("typ"))
            if not proj:
                return "Högen är tom."
            if not p.passar(proj):
                return "Projektet får inte plats på din mark."
            if len(p.projects) >= MAX_PROJECTS:
                return f"Max {MAX_PROJECTS} projekt."
        elif val not in ("dialog", "riskbuffert", "markexpansion"):
            return "Okänt val."

    def _resolve_p1(self):
        self.reveal = {"title": f"Runda {self.round} av {P1_ROUNDS}", "rows": {}}
        # Projekt: krockar avgörs med D6, förloraren får nästa kort i samma hög
        by_typ: Dict[str, List[KPlayer]] = {}
        for p in self.players.values():
            if p.choice["val"] == "projekt":
                by_typ.setdefault(p.choice["typ"], []).append(p)
        for typ, ps in by_typ.items():
            rolls = {p.id: d(6, self.rng) + self.rng.random() / 10 for p in ps}
            ps.sort(key=lambda p: rolls[p.id], reverse=True)
            for p in ps:
                pile = self.proj_piles[typ]
                if len(ps) > 1:
                    self.note(p, f"Krock om {typ.lower()}! Du slog D6 = {int(rolls[p.id])}.")
                proj = pile[-1] if pile else None
                if proj and p.passar(proj):
                    pile.pop()
                    p.projects.append(proj)
                    p.q_krav += proj["q"]
                    p.h_krav += proj["h"]
                    self.note(p, f"Du tog {proj['namn']} ({proj['bta']} kvm BTA). "
                                 f"Kvalitetskrav +{proj['q']}, hållbarhetskrav +{proj['h']}.")
                else:
                    self.note(p, "Projektet du fick på krocken får inte plats – ingenting den här rundan.")
        for p in self.players.values():
            val = p.choice["val"]
            if val == "dialog":
                card = self._draw(self.dialog_deck, [c for c in self.gd.dialog if c.nr.startswith("D")])
                self._spela_kort(p, card, "Dialogkort")
            elif val == "riskbuffert":
                p.rb += 1
                self.note(p, "Du tog en riskbuffert.")
            elif val == "markexpansion":
                exp = self._draw(self.exp_deck, self.gd.mark_expansion_deck)
                p.rutor += exp["cell_count"]
                p.expansions += 1
                self.note(p, f"Markexpansion: +{exp['cell_count']} rutor "
                             f"({exp['cell_count'] * CELL_KVM} kvm). Kostar {EXPANSION_KOSTNAD} Mkr.")
        # Stadshuset: D6 = 1 → politikkort
        for p in self.players.values():
            roll = d(6, self.rng)
            if roll != 1:
                continue
            card = self._draw(self.politik_deck, [c for c in self.gd.dialog if c.nr.startswith("P")])
            self._spela_kort(p, card, "Politikkort")
        self.log(None, "runda_p1", {pid: [r["text"] for r in rows]
                                    for pid, rows in self.reveal["rows"].items()})

    def _spela_kort(self, p: KPlayer, card, slag: str):
        """Dialog-/politikkort: D20 (+ projektchefens lindring) på kortets skala, som engine.py."""
        roll = d(20, self.rng)
        lindring = 0
        if p.pc and slag.lower() in p.pc.get("handelsemotstand", "").lower():
            lindring = p.pc.get("lindring", 0)
        tot = min(20, roll + lindring)
        key = "1" if tot <= 1 else "2-10" if tot <= 10 else "11-15" if tot <= 15 else "16-19" if tot <= 19 else "20"
        eff = card.effects.get(key) or "Ingen effekt"
        bonus = f" + lindring {lindring} ({p.pc['namn']})" if lindring else ""
        self.note(p, f"{slag}: {card.rubrik}. D20 = {roll}{bonus} → {eff}.")
        self._apply_kort(p, eff)

    def _apply_kort(self, p: KPlayer, eff: str):
        e = eff.lower()
        if e == "ingen effekt":
            return
        tal = lambda ord_: sum(int(n) for n in re.findall(r"([+-]\d+)\s*" + ord_, e))
        if "kvalitetskrav" in e or "hållbarhetskrav" in e or re.search(r"[+-]\d+\s*tid", e):
            p.q_krav = max(0, p.q_krav + tal("kvalitetskrav"))
            p.h_krav = max(0, p.h_krav + tal("hållbarhetskrav"))
            p.t_pu += tal("tid")
            return
        if "riskbuffert" in e:
            n = int((re.search(r"(\d+)", e) or [0, 1])[1])
            p.rb = max(0, p.rb - n) if "förlora" in e else p.rb + n
            return
        if "markanvisning" in e:  # valfritt – i kortversionen tar man den
            exp = self._draw(self.exp_deck, self.gd.mark_expansion_deck)
            p.rutor += exp["cell_count"]
            p.expansions += 1
            self.note(p, f"Du tar markanvisningen: +{exp['cell_count']} rutor ({EXPANSION_KOSTNAD} Mkr).")
            return
        if "ta projekt" in e:  # valfritt – största projektet som får plats
            fits = [x for x in self._market().values() if p.passar(x)]
            if fits and len(p.projects) < MAX_PROJECTS:
                proj = max(fits, key=lambda x: x["bta"])
                self.proj_piles[proj["typ"]].pop()
                p.projects.append(proj)
                p.q_krav += proj["q"]
                p.h_krav += proj["h"]
                self.note(p, f"Du tar {proj['namn']} ({proj['bta']} kvm BTA).")
            return
        if "byt projekt" in e:
            self.note(p, "Byte av projekt är valfritt och hoppas över i kortversionen.")
            return
        if not p.projects:
            self.note(p, "Du har inga projekt än – kortet slår inte.")
            return
        if "högst intäkt" in e:
            proj = max(p.projects, key=lambda x: x["anskaffning"])
        elif "högst bta" in e:
            proj = max(p.projects, key=lambda x: x["bta"])
        elif "lägst anskaffning" in e:
            proj = min(p.projects, key=lambda x: x["anskaffning"])
        else:
            return
        self._return_project(p, proj)
        self.note(p, f"{proj['namn']} lämnas tillbaka. Utvecklingskostnaden "
                     f"({proj['kostnad']} Mkr) är redan lagd.", -proj["kostnad"])

    def _return_project(self, p: KPlayer, proj: dict):
        p.projects.remove(proj)
        p.returned.append(proj)
        p.q_krav = max(0, p.q_krav - proj["q"])
        p.h_krav = max(0, p.h_krav - proj["h"])

    def _enter_p1_res(self):
        return "info"

    def _namnd_summa(self, p: KPlayer) -> int:
        return sum(x["namnd"] for x in p.projects)

    def _enter_namnd(self):
        """Nämnden prövar hela portföljen: D20 + projektchefens nämndbonus ska bli högre
        än summan av projektens nämndkrav. Varje miss höjer Q- eller H-kravet ett steg
        (spelaren väljer vilket) och man slår om tills det går igenom."""
        for p in self.players.values():
            bonus = p.pc.get("namnd_bonus", 0) if p.pc else 0
            p.offer = {"summa": self._namnd_summa(p), "bonus": bonus,
                       "q_krav": p.q_krav, "h_krav": p.h_krav}
        return "decision"

    def _validate_namnd(self, p, data):
        if data.get("hoj") not in ("q", "h"):
            return "Välj vilket krav som höjs vid en miss."

    def _resolve_namnd(self):
        self.reveal = {"title": "Nämndbeslut", "rows": {}}
        for p in self.players.values():
            summa, bonus = p.offer["summa"], p.offer["bonus"]
            krav = "kvalitetskravet" if p.choice["hoj"] == "q" else "hållbarhetskravet"
            slag = []
            for _ in range(30):
                r = d(20, self.rng)
                slag.append(r)
                if r == 20 or r + bonus > summa:
                    break
                if p.choice["hoj"] == "q":
                    p.q_krav += 1
                else:
                    p.h_krav += 1
            missar = len(slag) - 1
            txt = " → ".join(f"{r}{f'+{bonus}' if bonus else ''}" for r in slag)
            self.note(p, f"Summa nämndkrav {summa}. D20: {txt}. Godkänt"
                         + (f" efter {missar} miss{'ar' if missar > 1 else ''}: {krav} +{missar}." if missar else " direkt!"))
            self.log(p.id, "namnd", {"summa": summa, "slag": slag, "hoj": p.choice["hoj"]})

    def _enter_namnd_res(self):
        return "info"

    def _enter_slut1(self):
        """Ekonomi enligt economics.calc_phase1_economics."""
        self.reveal = {"title": "Skede 1 klart", "rows": {}}
        for p in self.players.values():
            intakt = sum(x["anskaffning"] for x in p.projects)
            mark = MARK_TOMT_KOSTNAD
            exp = p.expansions * EXPANSION_KOSTNAD
            dev = sum(x["kostnad"] for x in p.projects + p.returned)
            p.abt = p.abt_start = intakt - mark - exp - dev
            p.ek = 0.0
            p.ekonomi1 = {"intakt": intakt, "mark": mark, "expansion": exp,
                          "utveckling": dev, "abt": p.abt}
            self.log(p.id, "ekonomi_skede1", p.ekonomi1)
        return "info"

    # ════════════════ SKEDE 2 – PLANERING OCH GENOMFÖRANDE ════════════════

    def _enter_intro2(self):
        return "info"

    def _enter_ac(self):
        pool = self._deck(self.gd.ac_staff)
        for i, p in enumerate(self.players.values()):
            p.offer = {"ac": [pool[(i * 3 + k) % len(pool)] for k in range(3)]}
        return "decision"

    def _validate_ac(self, p, data):
        if data.get("id") not in [c["id"] for c in p.offer["ac"]]:
            return "Välj en av arbetscheferna."

    def _resolve_ac(self):
        for p in self.players.values():
            p.ac = ac = next(c for c in p.offer["ac"] if c["id"] == p.choice["id"])
            p.rb += ac.get("rb", 0)
            p.q, p.h = ac.get("q_bonus", 0), ac.get("h_bonus", 0)
            p.t_mal = 12 + max([x["tid"] for x in p.projects] or [0])
            p.t = 12 - ac.get("t_bonus", 0) + p.t_pu
            p.erf = ac.get("erfarenhet", 0)
            p.komp = {k: 0 for k in KOMP_KEYS}
            for src in (p.pc or {}, ac):
                for k, v in src.get("kompetenser", {}).items():
                    if k in p.komp:
                        p.komp[k] += v

    def _offers_for_slot(self, p: KPlayer, slot: str) -> dict:
        min_niva = max([x["krav_lev"].get(slot, 1) for x in p.projects] or [1])
        if slot in ORG_SLOTS:
            items = sorted(self.gd.organisations.get(slot, []), key=lambda o: o.niva)
            levels = [{"niva": o.niva, "namn": o.namn.title(), "kostnad": o.kostnad_mkr,
                       "q": o.q, "h": o.h, "t": o.t, "erf": o.erfarenhet, "rb": o.riskbuffert,
                       "komp": o.kompetenser} for o in items]
        else:
            items = sorted(self.gd.suppliers.get(slot, []), key=lambda s: s.niva)
            levels = []
            for s in items:
                klass = p.bya_klass if s.beror_av == "BYA" else p.bta_klass
                levels.append({"niva": s.niva, "namn": s.beskrivning, "kostnad": s.kostnad(klass),
                               "q": s.q, "h": s.h, "t": s.t, "erf": s.erfarenhet, "rb": 0,
                               "komp": s.kompetenser})
        return {"slot": slot, "min": min_niva, "levels": levels}

    def _enter_upph(self):
        self.shared = {"max": MAX_EGNA_UPPH, "grupper": [[namn, slots] for namn, slots in UPPHANDLINGAR]}
        for p in self.players.values():
            p.offer = {"slots": [dict(self._offers_for_slot(p, s), auto=max(self._offers_for_slot(p, s)["min"],
                                                                          self.auto_niva[s]))
                                 for s in ALLA_SLOTS]}
        return "decision"

    def _validate_upph(self, p, data):
        val = data.get("val") or {}
        if len(val) > MAX_EGNA_UPPH:
            return f"Du upphandlar högst {MAX_EGNA_UPPH} poster själv."
        slots = {s["slot"]: s for s in p.offer["slots"]}
        for slot, n in val.items():
            s = slots.get(slot)
            if not s or not isinstance(n, int) or not any(l["niva"] == n for l in s["levels"]):
                return f"Välj nivå för {slot.lower()}."
            if n < s["min"]:
                return f"Dina projekt kräver minst nivå {s['min']} på {slot.lower()}."

    def _resolve_upph(self):
        """Egna val kostar och ger effekt som vanligt och följs av sitt händelsekort.
        Övriga poster får den gemensamma slumpade nivån (2–3, minst projektens krav) och
        ger varken händelse- eller garantikort, så att det automatiska inte straffar någon."""
        self.reveal = {"title": "Upphandling", "rows": {},
                       "val": {pid: p.choice["val"] for pid, p in self.players.items()}}
        for p in self.players.values():
            egna, auto = 0, 0
            for s in p.offer["slots"]:
                eget = s["slot"] in p.choice["val"]
                n = p.choice["val"][s["slot"]] if eget else s["auto"]
                lvl = next(l for l in s["levels"] if l["niva"] == n)
                p.lev[s["slot"]] = {**lvl, "slot": s["slot"], "auto": not eget}
                if eget:
                    egna += lvl["kostnad"]
                else:
                    auto += lvl["kostnad"]
                p.q += lvl["q"]
                p.h += lvl["h"]
                p.t = max(MIN_T, p.t + lvl["t"])
                p.erf += lvl["erf"]
                p.rb += lvl.get("rb", 0)
                for k, v in lvl["komp"].items():
                    if k in p.komp:
                        p.komp[k] += v
            p.abt -= egna + auto
            if egna:
                self.note(p, f"Egna upphandlingar för {egna} Mkr.", -egna, plan=True)
            self.note(p, f"Övriga {len(ALLA_SLOTS) - len(p.choice['val'])} poster upphandlades automatiskt "
                         f"för {auto} Mkr.", -auto, plan=True)
            for slot in p.choice["val"]:
                self._planning_event(p, slot)

    def _planning_event(self, p: KPlayer, slot: str):
        card_id = slot if slot in ORG_SLOTS else SLOT_TO_CARD_IDS.get(slot, [slot])[0]
        deck = self.gd.planning_events.get(card_id, [])
        if not deck:
            return
        card = self.rng.choice(deck)
        roll = d(20, self.rng)
        effect = card.get_effect(roll + p.erf)
        txt = f"Händelse ({slot.lower()}): {card.namn}. D20 = {roll} + erfarenhet {p.erf} → {effect}"
        if effect == card.effects[0] and p.rb > 0 and len(card.effects) > 1:
            p.rb -= 1
            roll2 = d(20, self.rng)
            effect2 = card.get_effect(roll2 + p.erf)
            txt += f". Riskbuffert används, omslag: D20 = {roll2} → {effect2}"
            effect = effect2
        e = parse_effekt(effect, p.bta_klass)
        self._apply_bygg(p, e)
        self.note(p, txt + ".", e["mkr"])

    def _apply_bygg(self, p: KPlayer, e: dict):
        p.abt += e["mkr"]
        p.t = max(MIN_T, p.t + e["man"])
        p.q += e["q"]
        p.h += e["h"]
        p.rb = max(0, p.rb + e["rb"])

    def _enter_upph_res(self):
        return "info"

    def _krav_key(self, p: KPlayer) -> str:
        return "req_k" if len(p.projects) >= 7 else "req_b"

    def _enter_fas(self):
        steg = self.fas_steg[self.round - 1]
        card = self.rng.choice(self.gd.phase_cards[steg])
        self.shared = {"steg": steg, "runda": self.round, "av": FAS_RUNDOR, "kort": card.to_dict(),
                       "kulturpris": PHASE_COST[steg - 1]}
        for p in self.players.values():
            key = self._krav_key(p)
            nivaer = [{"name": l["name"], "krav": parse_krav(l[key]), "effect": l["effect"] or "Ingen effekt"}
                      for l in card.levels]
            kultur = [self._draw(self.kultur_deck, self.gd.external_support) for _ in range(2)]
            p.offer = {"nivaer": nivaer, "kultur": [k.to_dict() for k in kultur if k],
                       "kolumn": {"req_b": "Standard", "req_k": "Komplext (5+ projekt)"}[key]}
        return "decision"

    def _komp_after(self, p: KPlayer, data: dict) -> Dict[str, int]:
        komp = dict(p.komp)
        for k in p.offer["kultur"]:
            if k["id"] in (data.get("kultur") or []):
                for kk, v in k["kompetenser"].items():
                    komp[kk] = komp.get(kk, 0) + v
        return komp

    def _validate_fas(self, p, data):
        i = data.get("niva")
        if not isinstance(i, int) or not 0 <= i < len(p.offer["nivaer"]):
            return "Välj nivå."
        komp = self._komp_after(p, data)
        for k, v in p.offer["nivaer"][i]["krav"].items():
            if komp.get(k, 0) < v:
                return f"Du har inte {v} {k}."

    def _resolve_fas(self):
        s = self.shared
        self.reveal = {"title": f"Fas {s['steg']}: {s['kort']['namn']}", "rows": {},
                       "val": {pid: p.offer["nivaer"][p.choice["niva"]]["name"]
                               for pid, p in self.players.items()}}
        for p in self.players.values():
            kultur = [k for k in p.offer["kultur"] if k["id"] in (p.choice.get("kultur") or [])]
            if kultur:
                cost = s["kulturpris"] * len(kultur)
                p.abt -= cost
                p.komp = self._komp_after(p, p.choice)
                self.note(p, f"Köpte kulturkort: {', '.join(k['namn'] for k in kultur)}.", -cost, plan=True)
            niva = p.offer["nivaer"][p.choice["niva"]]
            for k, v in niva["krav"].items():
                p.komp[k] -= v
            e = parse_effekt(niva["effect"], p.bta_klass)
            self._apply_bygg(p, e)
            spent = ", ".join(f"{v} {k}" for k, v in niva["krav"].items()) or "inga kompetenser"
            self.note(p, f"{niva['name']} (lade {spent}) → {niva['effect']}.", e["mkr"])

    def _enter_fas_res(self):
        return "info"

    def _enter_slut2(self):
        self.reveal = {"title": "Skede 2 klart", "rows": {}}
        ovriga = [str(x) for x in range(1, 9) if x not in self.fas_steg]
        for p in self.players.values():
            self.note(p, f"Byggfas {', '.join(ovriga)} godkändes automatiskt utan anmärkning.")
            p.n_t = max(0, p.t - p.t_mal)
            p.n_q = max(0, p.q_krav - p.q)
            p.n_h = max(0, p.h_krav - p.h)
            self.note(p, f"Tid {p.t} mån (mål {p.t_mal}), kvalitet {p.q} (krav {p.q_krav}), "
                         f"hållbarhet {p.h} (krav {p.h_krav}).")
            garanti = []  # (lek, orsak)
            for typ, n, gtyp in (("TID", p.n_t, "KVALITETSBRIST"),
                                 ("KVALITET", p.n_q, "KVALITETSBRIST"),
                                 ("HÅLLBARHET", p.n_h, "HÅLLBARHETSAVVIKELSE")):
                for _ in range(n):
                    card = self._draw(self.penalty[typ], self.gd.penalty_cards[typ])
                    e = parse_effekt(card.effects[0])
                    p.abt += e["mkr"]
                    garanti.append((gtyp, f"efter missad {typ.lower()}"))
                    self.note(p, f"Konsekvenskort {typ.lower()}: {card.namn} → {e['mkr']:+.0f} Mkr.", e["mkr"])
            for lev in p.lev.values():
                if lev["slot"] not in ORG_SLOTS and lev["niva"] <= 2 and not lev.get("auto"):
                    garanti.append(("KVALITETSBRIST", f"{lev['slot'].lower()} nivå {lev['niva']}"))
            for gtyp, orsak in garanti:
                card = self._draw(self.garanti[gtyp], self.gd.garanti_cards[gtyp])
                e = parse_effekt(card.effects[0])
                p.abt += e["mkr"]
                self.note(p, f"Garantibesiktning ({orsak}): {card.namn} → {e['mkr']:+.0f} Mkr.", e["mkr"])
            p.tb = p.abt
            self.note(p, f"Täckningsbidrag (TB): {p.tb:.0f} Mkr "
                         f"({(p.tb / p.abt_start * 100) if p.abt_start > 0 else 0:.0f} % av ABT).")
            # BRF:er säljs
            for brf in [x for x in p.projects if x["typ"] == "BRF"]:
                m = re.search(r"D(\d+)", brf["rorlig"] or "")
                extra = d(int(m.group(1)), self.rng) if m else 0
                vinst = brf["marknadsvarde"] - brf["anskaffning"] + extra
                p.ek += vinst
                self.note(p, f"{brf['namn']} säljs: {brf['marknadsvarde']} − {brf['anskaffning']}"
                             f"{f' + D{m.group(1)} ({extra})' if m else ''} = {vinst:+.0f} Mkr till eget kapital.",
                          vinst)
            # Förvaltning 2.1: TB förs till kassan; fastigheterna får sin energiklass,
            # ett steg sämre om hållbarhetskravet missades (H-poängen i kortversionen)
            p.ek += p.tb
            ek_skift = 1 if p.n_h > 0 else 0
            p.props = [self._fastighet(x, "byggd", self._ek_steg(x["energiklass"], ek_skift))
                       for x in p.projects if x["typ"] != "BRF"]
            for prop in p.props:  # §4: lånet är 70 % av MV vid inträdet i förvaltningen
                prop["lan"] = self._nytt_lan(self._mv(prop))
            self.note(p, f"TB {p.tb:.0f} Mkr förs till kassan. Kassa inför förvaltningen: {p.ek:.0f} Mkr.")
            self.log(p.id, "skede2_slut", {"t": p.t, "q": p.q, "h": p.h, "tb": p.tb, "ek": p.ek})
        return "info"

    # ════════════════ SKEDE 3 – FÖRVALTNING (2.1) ════════════════
    # Smal version av FORVALTNING_DESIGN_2-1.md: lånemodellen, MV = effektiv DN ÷ yield,
    # inga löner, händelsebrickor, personkort och eskalerande energislag. Tvångsbud,
    # saneringsuppdrag och stoppkort ingår inte i kortversionen.

    def _enter_intro3(self):
        return "info"

    def _yield(self, prop: dict) -> float:
        return self.yield_b if prop["typ"] in BOSTAD_TYPER else self.yield_k

    @staticmethod
    def _eff_dn(prop: dict) -> int:
        """Som engine._eff_dn: bas-DN + energiklassens modifier, cap bas × 2."""
        bas = prop["bas_dn"]
        eff = bas + EK_DN_MODIFIER.get(prop["energiklass"], 0)
        if bas > 0:
            eff = min(eff, bas * 2)
        return max(0, min(eff, EFFECTIVE_DN_ABS_MAX))

    def _mv(self, prop: dict) -> int:
        return _mv_lookup(self._eff_dn(prop), self._yield(prop))

    @staticmethod
    def _nytt_lan(mv: int) -> int:
        """Lån = 70 % av MV vid förvärvet, avrundat till närmaste 10 Mkr, capat ≤ MV."""
        return min(mv, int(round(mv * LOAN_RATIO / 10.0) * 10))

    def _lan(self, prop: dict) -> int:
        return prop["lan"] if prop.get("lan") is not None else self._nytt_lan(self._mv(prop))

    @staticmethod
    def _fastighet(proj: dict, agd: str, energiklass: Optional[str] = None) -> dict:
        prop = {k: proj[k] for k in ("id", "namn", "typ", "bta", "anskaffning", "bas_dn")}
        prop.update(energiklass=energiklass or proj["energiklass"], agd=agd,
                    lan=proj.get("lan", proj.get("lanebelopp")), dn_net=0, varn=0, en_net=0)
        return prop

    def _prop_view(self, prop: dict, egen: bool = True) -> dict:
        mv = self._mv(prop)
        lan = self._lan(prop)
        v = {**prop, "eff_dn": self._eff_dn(prop), "mv": mv, "lan": lan, "pris": mv - lan,
             "yield": self._yield(prop)}
        if not egen:  # dolda brickor ser bara ägaren
            v.pop("dn_net", None)
            v.pop("en_net", None)
        return v

    def _personkort(self, p: KPlayer, n: int = 1):
        for _ in range(n):
            p.hand.append(dict(self._draw(self.personkort, f21("personkort"))))

    def _enter_f_setup(self):
        fcs = [c for c in f21("FC") if "konsekvenskort" not in c["Styrka"]]
        fss = [c for c in f21("FS") if "ta bort" in c["Egenskap"] or "dolt DN" in c["Egenskap"]]
        for p in self.players.values():
            p.offer = {"fc": self.rng.sample(fcs, min(3, len(fcs))), "fs": fss}
        # Projektbanken: tre fastigheter ur de kvarvarande högarna
        pool = [x for t, pile in self.proj_piles.items() if t != "BRF" for x in pile]
        self.rng.shuffle(pool)
        for proj in pool[:3]:
            self.proj_piles[proj["typ"]].remove(proj)
            self.banken.append(self._fastighet({**proj, "lanebelopp": None}, "bank"))
        return "decision"

    def _validate_f_setup(self, p, data):
        if data.get("fc") not in [c["ID"] for c in p.offer["fc"]]:
            return "Välj en fastighetschef."
        if data.get("fs") not in [c["ID"] for c in p.offer["fs"]]:
            return "Välj en fastighetsskötare."

    def _resolve_f_setup(self):
        for p in self.players.values():
            fc = next(c for c in p.offer["fc"] if c["ID"] == p.choice["fc"])
            mods = {"forh": 0, "energi": 0}
            for text in (fc["Styrka"], fc["Svaghet"]):
                for v, typ in re.findall(r"([+-]\d+)\s*(?:på\s*)?(förhandling|energi)", text):
                    mods["forh" if typ == "förhandling" else "energi"] += int(v)
            p.fc = {"id": fc["ID"], "namn": fc["Namn"], "styrka": fc["Styrka"], "svaghet": fc["Svaghet"],
                    **mods, "extra_pk": int("personkort" in fc["Styrka"]),
                    "rb_q": int("riskbuffert" in fc["Styrka"])}
            fs = next(c for c in p.offer["fs"] if c["ID"] == p.choice["fs"])
            p.fs = [{"id": fs["ID"], "namn": fs["Namn"], "egenskap": fs["Egenskap"]}]
            self._personkort(p, 3)

    # ── Kort och brickor ──

    def _bricka(self, p: KPlayer, prop: dict, falt: str, delta: int) -> str:
        """Plus/minus- och energibrickor: 3 i netto → ±1 bas-DN resp. ±1 energiklass."""
        prop[falt] += delta
        if abs(prop[falt]) < 3:
            return ""
        steg = 1 if prop[falt] > 0 else -1
        prop[falt] = 0
        if falt == "dn_net":
            prop["bas_dn"] = max(0, prop["bas_dn"] + steg)
            return f" Tre brickor i netto → bas-DN {'+' if steg > 0 else '−'}1 (nu {prop['bas_dn']})."
        prop["energiklass"] = self._ek_steg(prop["energiklass"], -steg)
        return f" Tre energibrickor → energiklass {prop['energiklass']}."

    def _handelse(self, p: KPlayer, prop: dict, kalla: str = "Händelse"):
        lek = [c for c in f21("händelsekort") if c["Typ"] == prop["typ"]]
        if not lek:
            return
        kort = self.rng.choice(lek)
        e, dolt = kort["Effekt"], kort["Synlig"] == "nej"
        v = int(kort["Värde"] or 0)
        mkr, extra = 0.0, ""
        if e == "dolt_plus_dn":
            extra = " +1-bricka." + self._bricka(p, prop, "dn_net", 1)
        elif e == "dolt_minus_dn":
            extra = " −1-bricka." + self._bricka(p, prop, "dn_net", -1)
        elif e == "underhallsvarning":
            prop["varn"] += 1
            extra = f" Varning {prop['varn']} av 3."
            if prop["varn"] >= 3:
                prop["varn"] = 0
                prop["bas_dn"] = max(0, prop["bas_dn"] - 1)
                extra += f" Tre varningar → bas-DN −1 (nu {prop['bas_dn']})."
        elif e == "energi_plus":
            extra = " +1 energibricka." + self._bricka(p, prop, "en_net", 1)
        elif e == "energivarning":
            extra = " Energivarning." + self._bricka(p, prop, "en_net", -1)
        elif e in ("direkt_dn_plus", "direkt_dn_minus"):
            steg = 1 if e.endswith("plus") else -1
            prop["bas_dn"] = max(0, prop["bas_dn"] + steg)
            extra = f" Bas-DN {'+' if steg > 0 else '−'}1 direkt (nu {prop['bas_dn']})."
        elif e in ("engangskassa_plus", "engangskassa_minus"):
            mkr = v if e.endswith("plus") else -v
            p.ek += mkr
            extra = f" {mkr:+.0f} Mkr i kassan."
        elif e == "villkorskort":
            extra = " " + self._villkor(p, kort["Beskrivning"], prop)
        elif e == "forkop":
            p.forkop.append(prop["typ"])
            extra = f" Förköp sparas: du vinner nästa förhandling om en {typ_namn(prop['typ'])}."
        self.note(p, f"{kalla}, {prop['namn']}: {kort['Rubrik']}.{extra}", mkr, privat=dolt)

    def _villkor(self, p: KPlayer, text: str, prop: Optional[dict] = None, typ: Optional[str] = None) -> str:
        """Villkorskort: 'energiklass D eller sämre ger −1 DN' och 'äger du N eller fler X'."""
        t = text.lower()
        if re.search(r"energiklass\w*\s+(?:på\s+)?d eller sämre", t):
            traffade = [x for x in ([prop] if prop else p.props)
                        if (typ is None or x["typ"] == typ) and x["energiklass"] in ("D", "E")]
            for x in traffade:
                x["bas_dn"] = max(0, x["bas_dn"] - 1)
            return f"Villkor: energiklass D eller sämre → −1 DN på {len(traffade)} fastighet(er)."
        m = re.search(r"äger du (\d+) eller fler (\w+)", t)
        if m:
            n, ord_ = int(m.group(1)), m.group(2)
            ftyp = next((k for k in ("HYRESRÄTT", "FÖRSKOLA", "LOKAL", "KONTOR") if k.lower()[:5] in ord_), None)
            hit = [x for x in p.props if x["typ"] == ftyp]
            if len(hit) >= n:
                for x in hit:
                    x["bas_dn"] = max(0, x["bas_dn"] - 1)
                return f"Villkor uppfyllt: −1 DN på {len(hit)} fastigheter."
            return "Villkoret uppfylls inte."
        return "Villkoret gäller inte i kortversionen."

    # ── Kvartalen ──

    def _enter_kvartal(self):
        q = self.round
        self.reveal = {"rows": {}}
        for p in self.players.values():
            if q == 1:  # Kvartal 0: ett händelsekort per fastighet
                for prop in p.props:
                    self._handelse(p, prop, "Uppställning")
            if p.fc and p.fc.get("rb_q"):
                p.rb += 1
                self.note(p, f"{p.fc['namn']} ger +1 riskbuffert.")
            # a) Balanskrav: MV ≥ lån, annars tar banken fastigheten
            for prop in list(p.props):
                mv, lan = self._mv(prop), self._lan(prop)
                if mv < lan:
                    p.props.remove(prop)
                    self.banken.append({**prop, "lan": self._nytt_lan(mv), "agd": "bank", "fynd": True})
                    self.note(p, f"{prop['namn']}: MV {mv} < lån {lan}. Banken tar fastigheten utan "
                                 f"ersättning och listar den som fynd.", -float(prop.get("ek_vid_kop", 0)))
        self.shared = {"kvartal": q, "info": self.reveal["rows"], "yield_b": self.yield_b,
                       "yield_k": self.yield_k, "energi_max": ENERGI_MAX.get(q, 0),
                       "market": [self._prop_view(x, egen=False) for x in self.banken]}
        self.reveal = {}
        for p in self.players.values():
            p.offer = {"props": [self._prop_view(x) for x in p.props],
                       "motstandare": [{"id": o.id, "name": o.name,
                                        "props": [{"id": x["id"], "namn": x["namn"]} for x in o.props]}
                                       for o in self.players.values() if o.id != p.id]}
        return "decision"

    def _validate_kvartal(self, p, data):
        market = {m["id"]: m for m in self.shared["market"]}
        egna = {x["id"]: x for x in p.props}
        kop, salj, energi = data.get("kop") or [], data.get("salj") or [], data.get("energi") or []
        if any(x not in market for x in kop):
            return "Okänd fastighet på marknaden."
        if any(x not in egna for x in salj + energi):
            return "Okänd egen fastighet."
        if set(salj) & set(energi):
            return "Du kan inte både sälja och energiuppgradera samma fastighet."
        if len(energi) > self.shared["energi_max"]:
            return f"Högst {self.shared['energi_max']} energiuppgraderingar det här kvartalet."
        if any(egna[x]["energiklass"] == "A" for x in energi):
            return "Energiklass A kan inte uppgraderas."
        inkomst = sum(self._mv(egna[x]) - self._lan(egna[x]) for x in salj)
        if sum(market[x]["pris"] for x in kop) > max(0.0, p.ek + inkomst):
            return f"Kassan ({p.ek:.0f} Mkr) räcker inte till köpen."
        kort = data.get("kort") or {}
        if kort:
            c = next((c for c in p.hand if c["ID"] == kort.get("id")), None)
            if not c:
                return "Kortet finns inte på din hand."
            mal = kort.get("mal")
            if c["Effekt"] in ("lagg_dn_plus_egen", "stada") and mal not in egna:
                return "Välj en av dina fastigheter för kortet."
            if c["Effekt"] == "sabotage_minus" and not any(
                    x["id"] == mal for o in self.players.values() if o.id != p.id for x in o.props):
                return "Välj en motståndares fastighet för kortet."
            if c["Effekt"] in ("kika", "sabotage_slang") and mal not in self.players:
                return "Välj en motståndare för kortet."
            if c["Effekt"] == "stopp":
                return "Stoppkort spelas bara mot tvångsbud, som inte finns i kortversionen."

    def _spela_personkort(self, p: KPlayer, kort: dict, mods: dict):
        c = next(c for c in p.hand if c["ID"] == kort["id"])
        p.hand.remove(c)
        e, mal = c["Effekt"], kort.get("mal")
        v = int((c["Värde"] or "0").replace("+", ""))
        text = f"Personkort: {c['Rubrik']}."
        if e == "forhandling_mod":
            mods["forh"] += v
            text += f" +{v} på förhandling det här kvartalet."
        elif e == "forhandling_auto":
            mods["auto"] = True
            text += " Du vinner nästa förhandling."
        elif e == "energi_mod":
            mods["energi"] += v
            text += f" +{v} på energislag det här kvartalet."
        elif e == "lagg_dn_plus_egen":
            prop = next(x for x in p.props if x["id"] == mal)
            text += f" Dold +1 på {prop['namn']}." + self._bricka(p, prop, "dn_net", 1)
        elif e == "stada":
            prop = next(x for x in p.props if x["id"] == mal)
            if prop["dn_net"] < 0:
                prop["dn_net"] += 1
            elif prop["varn"] > 0:
                prop["varn"] -= 1
            elif prop["en_net"] < 0:
                prop["en_net"] += 1
            text += f" En minus- eller varningsbricka bort från {prop['namn']}."
        elif e == "sabotage_minus":
            o, prop = next((o, x) for o in self.players.values() for x in o.props if x["id"] == mal)
            extra = self._bricka(o, prop, "dn_net", -1)
            text += f" Minusbricka på {o.name}s {prop['namn']}."
            self.note(o, f"{p.name} lade en minusbricka på {prop['namn']}.{extra}")
        elif e == "kika":
            o = self.players[mal]
            if o.props:
                prop = self.rng.choice(o.props)
                text += f" {o.name}s {prop['namn']} har {prop['dn_net']:+d} i dolda brickor."
            else:
                text += f" {o.name} äger inga fastigheter."
        elif e == "sabotage_slang":
            o = self.players[mal]
            if o.hand:
                o.hand.remove(self.rng.choice(o.hand))
                self.note(o, f"{p.name} tvingade dig att slänga ett personkort.")
            text += f" {o.name} slänger ett personkort."
        elif e == "riskbuffert":
            p.rb += 1
            text += " +1 riskbuffert."
        elif e == "dra_personkort":
            self._personkort(p)
            text += " Du drar ett personkort."
        self.note(p, text, privat=e == "kika")

    def _resolve_kvartal(self):
        q = self.round
        self.reveal = {"title": f"Kvartal {q}", "rows": {}, "kop": []}
        mods = {pid: {"forh": p.fc["forh"], "energi": p.fc["energi"], "auto": False}
                for pid, p in self.players.items()}
        # 1. Personkort
        for p in self.players.values():
            if p.choice.get("kort"):
                self._spela_personkort(p, p.choice["kort"], mods[p.id])
        # 2. Försäljning till banken för Normal-MV
        for p in self.players.values():
            for pid_ in p.choice.get("salj") or []:
                prop = next((x for x in p.props if x["id"] == pid_), None)
                if not prop:
                    continue
                mv, lan = self._mv(prop), self._lan(prop)
                p.props.remove(prop)
                p.ek += mv - lan
                self.banken.append({**prop, "lan": None, "agd": "bank", "dn_net": 0, "varn": 0, "en_net": 0})
                self.note(p, f"Sålde {prop['namn']} till banken: MV {mv} − lån {lan} = {mv - lan:+d} Mkr.",
                          mv - lan, plan=True)
        # 3. Köp med förhandling (D20 + modifierare, högst vinner, lika → färst fastigheter)
        for listing in list(self.banken):
            pris = self._mv(listing) - self._lan(listing)
            buyers = [p for p in self.players.values()
                      if listing["id"] in (p.choice.get("kop") or []) and p.ek >= pris]
            if not buyers:
                continue
            slag = []
            for p in buyers:
                if mods[p.id]["auto"] or listing["typ"] in p.forkop:
                    s, txt = 99, "vinner direkt"
                else:
                    r = d(20, self.rng)
                    s, txt = r + mods[p.id]["forh"], f"D20 {r}{mods[p.id]['forh']:+d}"
                slag.append((s, -len(p.props), self.rng.random(), p, txt))
            slag.sort(key=lambda x: x[:3], reverse=True)
            w = slag[0][3]
            if slag[0][0] == 99:
                if mods[w.id]["auto"]:
                    mods[w.id]["auto"] = False
                else:
                    w.forkop.remove(listing["typ"])
            lan = self._lan(listing)
            w.ek -= pris
            self.banken.remove(listing)
            prop = {**listing, "lan": lan, "agd": "köpt", "ek_vid_kop": pris}
            w.props.append(prop)
            w.extra_ansk += prop["anskaffning"]
            self.reveal["kop"].append({"namn": listing["namn"], "pris": pris, "vinnare": w.name,
                                       "slag": [{"name": x[3].name, "color": x[3].color, "txt": x[4]} for x in slag]})
            self.note(w, f"Du köpte {prop['namn']}: MV {pris + lan} − lån {lan} = {pris} Mkr ur kassan.",
                      -pris, plan=True)
            dd = self._draw(self.dd, f21("DD"))
            if dd["Effekt"] == "dd_ek":
                prop["energiklass"] = self._ek_steg(prop["energiklass"], 1 if "sämre" in dd["Rubrik"] else -1)
                self.note(w, f"DD-kort: {dd['Rubrik']}. Energiklass nu {prop['energiklass']}.", privat=True)
            else:
                extra = self._bricka(w, prop, "dn_net", 1 if dd["Effekt"] == "dd_plus" else -1)
                self.note(w, f"DD-kort: {dd['Rubrik']} ({'plus' if dd['Effekt'] == 'dd_plus' else 'minus'}"
                             f"bricka).{extra}", privat=True)
        # 4. Omvärldskort (träffar alla)
        w = self._draw(self.omvarld, f21("omvärldskort"))
        self.reveal["omvarld"] = {"rubrik": w["Rubrik"], "beskrivning": w["Beskrivning"]}
        self._apply_omvarld(w)
        # 5–7. Driftnetto, personkort, fastighetsskötare och händelser
        for p in self.players.values():
            dn = sum(self._eff_dn(x) for x in p.props) / 4
            p.ek += dn
            self.note(p, f"Driftnetto in: {dn:+.2f} Mkr (summa effektiv DN ÷ 4).", dn, plan=True)
            self._personkort(p, 2 + p.fc.get("extra_pk", 0))
            fs = p.fs[0] if p.fs else None
            if fs and p.props:
                if "ta bort" in fs["egenskap"]:
                    prop = min(p.props, key=lambda x: (x["dn_net"], -x["varn"]))
                    if prop["dn_net"] < 0 or prop["varn"] > 0:
                        if prop["dn_net"] < 0:
                            prop["dn_net"] += 1
                        else:
                            prop["varn"] -= 1
                        self.note(p, f"{fs['namn']} tar bort en minus- eller varningsbricka på {prop['namn']}.")
                else:
                    prop = max(p.props, key=lambda x: x["bas_dn"])
                    extra = self._bricka(p, prop, "dn_net", 1)
                    self.note(p, f"{fs['namn']}: dold +1 på {prop['namn']}.{extra}", privat=True)
            for prop in list(p.props):
                self._handelse(p, prop)
        # 8. Kvartalskort (tempo/resurs, aldrig yield)
        k = self._draw(self.kvartalskort, f21("kvartalskort"))
        self.reveal["kvartalskort"] = {"rubrik": k["Rubrik"], "beskrivning": k["Beskrivning"], "typ": k["Typ"]}
        self._apply_kvartalskort(k)
        # 9. Energiuppgraderingar
        for p in self.players.values():
            for pid_ in p.choice.get("energi") or []:
                prop = next((x for x in p.props if x["id"] == pid_), None)
                if prop:
                    self._energi(p, prop, mods[p.id]["energi"])
        self.log(None, "kvartal", {"kop": self.reveal["kop"], "omvarld": w["ID"], "kvartalskort": k["ID"],
                                   "yield": [self.yield_b, self.yield_k]})

    def _apply_omvarld(self, w: dict):
        e = w["Effekt"]
        if e in ("yield_rorelse", "yield_stor"):
            v = _num(w["Värde"])
            if "bost" in w["Påverkar"]:
                self.yield_b = min(YIELD_SPANN["b"][1], max(YIELD_SPANN["b"][0], self.yield_b + v))
            else:
                self.yield_k = min(YIELD_SPANN["k"][1], max(YIELD_SPANN["k"][0], self.yield_k + v))
        elif e == "bords_dn":
            # "Välj typ": i kortversionen den typ som finns flest av på bordet
            typer = [x["typ"] for p in self.players.values() for x in p.props]
            steg = -1 if "-1 DN" in w["Beskrivning"] or "−1 DN" in w["Beskrivning"] else 1
            if typer:
                typ = max(set(typer), key=lambda t: (typer.count(t), t))
                for p in self.players.values():
                    for x in p.props:
                        if x["typ"] == typ:
                            x["bas_dn"] = max(0, x["bas_dn"] + steg)
                self.reveal["omvarld"]["effekt"] = f"Typen med flest fastigheter, {typ_namn(typ)}: {steg:+d} DN."
        elif e == "resurs":
            for p in self.players.values():
                if "riskbuffert" in w["Beskrivning"]:
                    p.rb += 1
                if "personkort" in w["Beskrivning"]:
                    self._personkort(p)

    def _apply_kvartalskort(self, k: dict):
        e, typ = k["Effekt"], k["Typ"]
        for p in self.players.values():
            hit = [x for x in p.props if x["typ"] == typ]
            if not hit:
                continue
            if e in ("typbred_dn_plus", "typbred_dn_minus"):
                steg = 1 if e.endswith("plus") else -1
                for x in hit:
                    x["bas_dn"] = max(0, x["bas_dn"] + steg)
                self.note(p, f"Kvartalskort: {k['Rubrik']} → {steg:+d} DN på {len(hit)} fastighet(er).")
            elif e in ("typbred_ek_plus", "typbred_ek_minus"):
                steg = -1 if e.endswith("plus") else 1
                for x in hit:
                    x["energiklass"] = self._ek_steg(x["energiklass"], steg)
                self.note(p, f"Kvartalskort: {k['Rubrik']} → energiklass {'+' if steg < 0 else '−'}1 "
                             f"på {len(hit)} fastighet(er).")
            elif e == "spotlight":
                for x in hit:
                    self._handelse(p, x, "Extra händelse")
            elif e == "resurs":
                self._personkort(p)
                self.note(p, f"Kvartalskort: {k['Rubrik']} → du drar ett personkort.")
            elif e == "villkorat":
                self.note(p, f"Kvartalskort: {k['Rubrik']}. " + self._villkor(p, k["Beskrivning"], typ=typ))

    def _energi(self, p: KPlayer, prop: dict, mod: int):
        """Eskalerande slag: 1×D20, 2×D20 … för 3 Mkr per runda, en 20 gör rundan gratis.
        Över 10 (med modifierare) → +1 energiklass. Riskbufferten ger ett omslag."""
        if prop["energiklass"] == ENERGY_CLASSES[0]:
            return
        kostnad, omslag = 0, False
        for runda in range(1, 7):
            tarn = [d(20, self.rng) for _ in range(runda)]
            if 20 not in tarn:
                if p.ek < ENERGI_KOSTNAD:
                    self.note(p, f"{prop['namn']}: kassan räcker inte till fler energislag.")
                    break
                p.ek -= ENERGI_KOSTNAD
                kostnad += ENERGI_KOSTNAD
            if max(tarn) + mod <= 10 and p.rb > 0 and not omslag:
                p.rb -= 1
                omslag = True
                tarn = [d(20, self.rng) for _ in range(runda)]
            if max(tarn) + mod > 10:
                prop["energiklass"] = self._ek_steg(prop["energiklass"], -1)
                self.note(p, f"{prop['namn']}: energiuppgradering till {prop['energiklass']} "
                             f"{'på första slaget' if runda == 1 else f'efter {runda} slagrundor'}"
                             f"{' (med omslag)' if omslag else ''}, {kostnad} Mkr.",
                          -kostnad, plan=True)
                return
        self.note(p, f"{prop['namn']}: energiuppgraderingen misslyckades, {kostnad} Mkr.", -kostnad)

    @staticmethod
    def _ek_steg(klass: str, steg: int) -> str:
        """steg −1 = bättre klass (mot A), +1 = sämre (mot E)."""
        if klass not in ENERGY_CLASSES:
            klass = "C"
        i = min(len(ENERGY_CLASSES) - 1, max(0, ENERGY_CLASSES.index(klass) + steg))
        return ENERGY_CLASSES[i]

    def _enter_kvartal_res(self):
        return "info"

    # ════════════════ SLUTRESULTAT ════════════════

    def _enter_final(self):
        """Slutpoäng via economics.calc_final_score: (S1 + S2 + S3) × f(n)."""
        res = []
        for p in self.players.values():
            fv_obelan = sum(self._mv(x) - self._lan(x) for x in p.props)
            spelare = SimpleNamespace(
                projects=[SimpleNamespace(id=x["id"], anskaffning=x["anskaffning"]) for x in p.projects],
                placed_project_ids=[x["id"] for x in p.projects],
                abt_start=p.abt_start, abt_budget=p.tb, abt_loans_net=0.0, abt_borrowing_cost=0.0,
                eget_kapital=p.ek, q_krav=p.q_krav, h_krav=p.h_krav,
                snap_exec_q=p.q, snap_exec_h=p.h, snap_exec_t=p.t)
            r = calc_final_score(spelare, fv_obelan, extra_anskaffning=p.extra_ansk)
            p.result = {**r, "n_props": len(p.props),
                        "lardomar": sorted(p.log, key=lambda x: x["mkr"])[:3],
                        "basta": sorted(p.log, key=lambda x: -x["mkr"])[:2]}
            res.append((r["score"], p))
        res.sort(key=lambda x: -x[0])
        self.shared = {"ranking": [{"id": p.id, "name": p.name, "color": p.color, **p.result}
                                   for _, p in res],
                       "yield_b": self.yield_b, "yield_k": self.yield_k}
        self.log(None, "slut", {"ranking": [(p.name, p.result["score"]) for _, p in res]})
        return "final"

    # ════════════════ DATORBOLAG ════════════════

    def _bot_choice(self, p: KPlayer) -> dict:
        r = self.rng
        s = self.step
        if s == "pc":
            return {"id": r.choice(p.offer["pc"])["id"]}
        if s == "namnd":
            return {"hoj": r.choice(["q", "h"])}
        if s == "ac":
            return {"id": r.choice(p.offer["ac"])["id"]}
        if s == "p1":
            fits = [t for t, x in self.shared["market"].items() if p.passar(x)]
            if fits and len(p.projects) < MAX_PROJECTS and r.random() < 0.7:
                best = max(fits, key=lambda t: self.shared["market"][t]["bta"] / max(1, self.shared["market"][t]["rutor"]) + r.random() * 200)
                return {"val": "projekt", "typ": best}
            if not fits and p.expansions < 2:
                return {"val": "markexpansion"}
            return {"val": r.choice(["dialog", "riskbuffert"])}
        if s == "upph":
            return {"val": {o["slot"]: max(o["min"], r.choice([2, 3, 3, 4]))
                            for o in r.sample(p.offer["slots"], 2)}}
        if s == "fas":
            for i in range(len(p.offer["nivaer"]) - 1, -1, -1):
                if not self._validate_fas(p, {"niva": i, "kultur": []}):
                    return {"niva": i, "kultur": []}
            return {"niva": 0, "kultur": []}
        if s == "f_setup":
            return {"fc": r.choice(p.offer["fc"])["ID"], "fs": r.choice(p.offer["fs"])["ID"]}
        if s == "kvartal":
            kassa = p.ek
            kop = []
            for m in self.shared["market"]:
                if m["pris"] <= kassa * 0.6 and r.random() < 0.5:
                    kop.append(m["id"])
                    kassa -= m["pris"]
            energi = []
            if kassa > 8:
                cands = sorted((x for x in p.props if x["energiklass"] != "A"),
                               key=lambda x: -ENERGY_CLASSES.index(x["energiklass"]))
                energi = [x["id"] for x in cands[:self.shared["energi_max"]]]
            kort = None
            for c in p.hand:
                if c["Effekt"] in ("riskbuffert", "dra_personkort", "forhandling_mod", "energi_mod"):
                    kort = {"id": c["ID"]}
                elif c["Effekt"] in ("lagg_dn_plus_egen", "stada") and p.props:
                    kort = {"id": c["ID"], "mal": p.props[0]["id"]}
                if kort:
                    break
            return {"kop": kop, "salj": [], "energi": energi, "kort": kort}
        return {}

    # ════════════════ VY ════════════════

    @staticmethod
    def _dolj(rows: dict, pid: Optional[str]) -> dict:
        """Andra spelares dolda kort visas bara som 'Dolt kort'."""
        return {owner: [r if owner == pid or not r.get("privat") else {"text": "Dolt kort.", "mkr": 0}
                        for r in lines] for owner, lines in rows.items()}

    def view(self, pid: Optional[str]) -> dict:
        me = self.players.get(pid) if pid else None
        reveal = dict(self.reveal)
        if "rows" in reveal:
            reveal["rows"] = self._dolj(reveal["rows"], pid)
        shared = dict(self.shared)
        if "info" in shared:
            shared["info"] = self._dolj(shared["info"], pid)
        return {
            "code": self.code, "step": self.step, "round": self.round, "kind": self.kind,
            "deadline": self.deadline, "now": time.time(),
            "del": self._del() if self.step != "lobby" else 0,
            "players": [p.public() for p in self.players.values()],
            "me": me.private() if me else None,
            "shared": shared, "reveal": reveal,
            "fas_steg": self.fas_steg, "yield_b": self.yield_b, "yield_k": self.yield_k,
        }


# ── Manager + websocket ──

class KvarteretManager:
    def __init__(self):
        self.rooms: Dict[str, KRoom] = {}
        self.conns: Dict[str, Dict[str, WebSocket]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.gd = None

    def create(self, gd, name: str):
        self._cleanup()
        self.gd = gd
        code = "".join(random.choices(string.ascii_uppercase, k=4))
        while code in self.rooms:
            code = "".join(random.choices(string.ascii_uppercase, k=4))
        room = KRoom(code, gd)
        self.rooms[code] = room
        p = room.add_player(name)
        return room, p

    def join(self, code: str, name: str):
        room = self.rooms.get(code.upper())
        if not room:
            return None, None, "Rummet finns inte."
        if room.step != "lobby":
            return None, None, "Spelet har redan börjat."
        if len(room.players) >= MAX_PLAYERS:
            return None, None, "Rummet är fullt."
        return room, room.add_player(name), None

    def _cleanup(self):
        now = time.time()
        for code, room in list(self.rooms.items()):
            if now - room.touched > 6 * 3600:
                self.rooms.pop(code, None)
                t = self.tasks.pop(code, None)
                if t:
                    t.cancel()

    async def connect(self, code, pid, ws: WebSocket):
        await ws.accept()
        self.conns.setdefault(code, {})[pid] = ws

    def disconnect(self, code, pid, ws):
        if self.conns.get(code, {}).get(pid) is ws:
            del self.conns[code][pid]

    async def broadcast(self, code):
        room = self.rooms.get(code)
        if not room:
            return
        for pid, ws in list(self.conns.get(code, {}).items()):
            try:
                await ws.send_json({"type": "state", "state": room.view(pid)})
            except Exception:
                self.conns[code].pop(pid, None)

    async def _ticker(self, code):
        while code in self.rooms:
            await asyncio.sleep(1)
            room = self.rooms.get(code)
            if room and room.deadline and time.time() > room.deadline:
                room.force()
                await self.broadcast(code)
            if room and room.kind == "final":
                return

    async def handle(self, code, pid, msg: dict, ws: WebSocket):
        room = self.rooms.get(code)
        if not room:
            return
        room.touched = time.time()
        p = room.players.get(pid)
        t = msg.get("type")
        err = None
        if t == "add_bot" and p and p.is_host and room.step == "lobby":
            if len(room.players) < MAX_PLAYERS:
                n = sum(1 for x in room.players.values() if x.is_bot) + 1
                room.add_player(f"Datorbolag {n}", is_bot=True)
        elif t == "remove_bot" and p and p.is_host and room.step == "lobby":
            bot = room.players.get(msg.get("id"))
            if bot and bot.is_bot:
                del room.players[bot.id]
        elif t == "start" and p and p.is_host and room.step == "lobby":
            room.start()
            self.tasks[code] = asyncio.create_task(self._ticker(code))
        elif t == "submit":
            err = room.submit(pid, msg.get("data") or {})
        elif t == "ready":
            room.set_ready(pid)
        elif t == "skip" and p and p.is_host:
            room.force()
        if err:
            await ws.send_json({"type": "error", "message": err})
        await self.broadcast(code)


kvarteret_manager = KvarteretManager()
