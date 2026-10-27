"""Åkepol Kvarteret – kortversion av Åkepol, helt digital och utan spelplaner.

Tre huvuddelar à ca 10 minuter (Före / Under / Efter). Alla spelare beslutar
samtidigt, servern avslöjar och räknar. Använder bara befintliga komponenter
(projekt, PC/AC/FC/FS, dialog- och politikkort, markexpansioner, leverantörer,
organisationer, händelsekort, faskort, kulturkort, konsekvens- och garantikort,
omvärldskort, yield, DD-kort, budgivning och slutformeln) – läses via GameData.

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
from typing import Dict, List, Optional

from fastapi import WebSocket

import models
from config import (
    DATA_DIR, D20_THRESHOLDS, MARK_TOMT_KOSTNAD, EXPANSION_KOSTNAD, TOMT_CELLS,
    START_Q_KRAV, START_H_KRAV, MIN_T, MAX_PROJECTS, PHASE_COST, EK_FV_MODIFIER,
    YIELD_START_BOSTADER, YIELD_START_KOMMERSIELLT, QUARTER_NEW_PROPS,
    ENERGY_CLASSES, ENERGY_UPGRADE_COST_PER_STEP, SLOT_TO_CARD_IDS,
)
from economics import deviation_factor

LOG_DIR = os.path.join(DATA_DIR, "kvarteret_logs")
CELL_KVM = 250                 # 16 rutor = 4 000 kvm BYA
BOSTAD_TYPER = ("BRF", "HYRESRÄTT")
KOMP_KEYS = ["STA", "KOM", "SAM", "NOG", "INN", "ABM"]
COLORS = ["#E4572E", "#2E86AB", "#7BB661", "#F2A541", "#9B5DE5", "#00B8A9"]
MAX_PLAYERS = 6

# Sekunder per beslut. Info-skärmar har egen klocka.
TIMER = {"pc": 45, "p1": 45, "ac": 45, "upph": 60, "fas": 50, "fc": 60,
         "kvartal": 70, "info": 40, "intro": 60}

UPPHANDLINGAR = [
    ("Organisation", ["OPERATIVT TEAM", "STÖDFUNKTIONER", "MARKNADSTEAM", "DIGITALISERING"]),
    ("Mark, grund och klimatskal", ["MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER"]),
    ("Inredning och installationer", ["STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"]),
]
ORG_SLOTS = set(UPPHANDLINGAR[0][1])

P1_ROUNDS = 5
QUARTERS = 4


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


def proj_dict(p) -> dict:
    return {
        "id": p.id, "namn": p.namn, "typ": p.typ, "kostnad": p.kostnad,
        "rutor": p.formfaktor, "bta": p.bta, "anskaffning": p.anskaffning,
        "marknadsvarde": p.marknadsvarde, "rorlig": p.rorlig_intakt,
        "q": p.kvalitet, "h": p.hallbarhet, "tid": p.tid, "namnd": p.namndbeslut,
        "energiklass": p.energiklass or "C", "driftnetto": p.driftnetto,
        "beskrivning": p.beskrivning,
        "krav_lev": {k: int(v.split()[-1]) for k, v in p.supplier_reqs.items()
                     if v and v.startswith("nivå")},
    }


def fv(prop: dict, yield_pct: float) -> float:
    """Fastighetsvärde: årligt driftnetto / yield × energibonus (som engine.py)."""
    if yield_pct <= 0:
        return 0.0
    base = prop["driftnetto"] * 4 / (yield_pct / 100.0)
    return base * EK_FV_MODIFIER.get(prop["energiklass"], 1.0)


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
    ek: float = 0.0
    props: List[dict] = field(default_factory=list)
    # Runtime
    offer: dict = field(default_factory=dict)
    choice: Optional[dict] = None
    ready: bool = False
    log: List[dict] = field(default_factory=list)
    result: dict = field(default_factory=dict)

    @property
    def rutor_kvar(self) -> int:
        return self.rutor - sum(p["rutor"] for p in self.projects)

    @property
    def bta(self) -> int:
        return sum(p["bta"] for p in self.projects)

    @property
    def bya(self) -> int:
        return sum(p["rutor"] for p in self.projects) * CELL_KVM

    @property
    def bta_klass(self) -> str:
        return models.classify(self.bta, models.BTA_CLASSES) if self.bta else "A"

    @property
    def bya_klass(self) -> str:
        return models.classify(self.bya, models.BYA_CLASSES) if self.bya else "A"

    @property
    def kapacitet(self) -> int:
        return (self.fc["kapacitet"] if self.fc else 0) + sum(f["kapacitet"] for f in self.fs)

    @property
    def lon(self) -> float:
        return (self.fc["lon"] if self.fc else 0) + sum(f["lon"] for f in self.fs)

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
            "q_krav": self.q_krav, "h_krav": self.h_krav,
            "bya": self.bya, "bta_klass": self.bta_klass, "bya_klass": self.bya_klass,
            "ekonomi1": self.ekonomi1, "abt_start": round(self.abt_start, 1),
            "q": self.q, "h": self.h, "t": self.t, "t_mal": self.t_mal, "erf": self.erf,
            "komp": self.komp, "lev": self.lev,
            "n_q": self.n_q, "n_h": self.n_h, "n_t": self.n_t, "tb": round(self.tb, 1),
            "props": self.props, "kapacitet": self.kapacitet, "lon": round(self.lon, 2),
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
        self.proj_piles = {typ: self._deck(proj_dict(p) for p in ps)
                           for typ, ps in gd.projects.items()}
        self.dialog_deck = self._deck(c for c in gd.dialog if c.nr.startswith("D"))
        self.politik_deck = self._deck(c for c in gd.dialog if c.nr.startswith("P"))
        self.exp_deck = self._deck(gd.mark_expansion_deck)
        self.kultur_deck = self._deck(gd.external_support)
        self.penalty = {k: self._deck(v) for k, v in gd.penalty_cards.items()}
        self.garanti = {k: self._deck(v) for k, v in gd.garanti_cards.items()}
        self.world_deck = self._deck(gd.world_events)
        self.dd_deck = self._deck(gd.dd_cards)
        self.mgmt = {k: self._deck(v) for k, v in gd.mgmt_events.items()}
        self.yield_deck = {k: self._deck(v) for k, v in gd.yield_cards.items()}

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

    def note(self, p: KPlayer, text: str, mkr: float = 0.0, plan: bool = False):
        """En rad i spelarens reveal. Oplanerade belopp hamnar också i lärdomsloggen."""
        self.reveal.setdefault("rows", {}).setdefault(p.id, []).append(
            {"text": text, "mkr": round(mkr, 1) if mkr else 0})
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
                     [("namnd", 0), ("slut1", 0), ("intro2", 0), ("ac", 0)] +
                     [x for r in range(1, 4) for x in (("upph", r), ("upph_res", r))] +
                     [x for r in range(1, 4) for x in (("fas", r), ("fas_res", r))] +
                     [("slut2", 0), ("intro3", 0), ("fc", 0)] +
                     [x for q in range(1, QUARTERS + 1) for x in (("kvartal", q), ("kvartal_res", q))] +
                     [("final", 0)])
        steg = list(range(1, 9))
        self.fas_steg = sorted([self.rng.choice(steg[0:3]), self.rng.choice(steg[3:6]),
                                self.rng.choice(steg[6:8])])
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
        return "decision"

    def _validate_p1(self, p, data):
        val = data.get("val")
        if val == "projekt":
            proj = self.shared["market"].get(data.get("typ"))
            if not proj:
                return "Högen är tom."
            if proj["rutor"] > p.rutor_kvar:
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
                if proj and proj["rutor"] <= p.rutor_kvar:
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
                eff = list(card.effects.values())[0] if card else "Ingen effekt"
                if "kvalitetskrav" in eff:
                    p.q_krav = max(0, p.q_krav - 1)
                if "hållbarhetskrav" in eff:
                    p.h_krav = max(0, p.h_krav - 1)
                self.note(p, f"Dialogkort: {card.rubrik} → {eff}.")
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
            eff = list(card.effects.values())[0]
            if p.pc and "politik" in p.pc.get("handelsemotstand", "").lower():
                self.note(p, f"Politikkort: {card.rubrik}. Din projektchef {p.pc['namn']} "
                             f"avvärjde det ({eff.lower()}).")
                continue
            self.note(p, f"Politikkort: {card.rubrik} → {eff}.")
            self._apply_politik(p, eff)
        self.log(None, "runda_p1", {pid: [r["text"] for r in rows]
                                    for pid, rows in self.reveal["rows"].items()})

    def _apply_politik(self, p: KPlayer, eff: str):
        e = eff.lower()
        if "riskbuffert" in e:
            p.rb = max(0, p.rb - 2)
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

    def _enter_namnd(self):
        self.reveal = {"title": "Nämndbeslut", "rows": {}}
        for p in self.players.values():
            bonus = p.pc.get("namnd_bonus", 0) if p.pc else 0
            for proj in list(p.projects):
                if proj["namnd"] <= 1:
                    continue
                roll = d(20, self.rng)
                if roll + bonus >= proj["namnd"]:
                    self.note(p, f"{proj['namn']}: D20 = {roll}{f' + {bonus}' if bonus else ''} "
                                 f"(behövde {proj['namnd']}). Godkänt!")
                else:
                    self._return_project(p, proj)
                    self.note(p, f"{proj['namn']}: D20 = {roll}{f' + {bonus}' if bonus else ''} "
                                 f"(behövde {proj['namnd']}). Avslag – projektet går tillbaka.",
                              -proj["kostnad"])
            if not self.reveal["rows"].get(p.id):
                self.note(p, "Inga projekt behövde gå till nämnden. Allt godkänt.")
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
            p.t = 12 - ac.get("t_bonus", 0)
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
        namn, slots = UPPHANDLINGAR[self.round - 1]
        self.shared = {"namn": namn, "runda": self.round, "av": len(UPPHANDLINGAR)}
        for p in self.players.values():
            p.offer = {"slots": [self._offers_for_slot(p, s) for s in slots]}
        return "decision"

    def _validate_upph(self, p, data):
        val = data.get("val") or {}
        for s in p.offer["slots"]:
            n = val.get(s["slot"])
            if not isinstance(n, int) or not any(l["niva"] == n for l in s["levels"]):
                return f"Välj nivå för {s['slot'].lower()}."
            if n < s["min"]:
                return f"Dina projekt kräver minst nivå {s['min']} på {s['slot'].lower()}."

    def _resolve_upph(self):
        namn, slots = UPPHANDLINGAR[self.round - 1]
        self.reveal = {"title": f"Upphandling: {namn}", "rows": {},
                       "val": {pid: p.choice["val"] for pid, p in self.players.items()}}
        for p in self.players.values():
            kost = 0
            for s in p.offer["slots"]:
                lvl = next(l for l in s["levels"] if l["niva"] == p.choice["val"][s["slot"]])
                p.lev[s["slot"]] = {**lvl, "slot": s["slot"]}
                kost += lvl["kostnad"]
                p.q += lvl["q"]
                p.h += lvl["h"]
                p.t = max(MIN_T, p.t + lvl["t"])
                p.erf += lvl["erf"]
                p.rb += lvl.get("rb", 0)
                for k, v in lvl["komp"].items():
                    if k in p.komp:
                        p.komp[k] += v
            p.abt -= kost
            self.note(p, f"Upphandlat för {kost} Mkr.", -kost, plan=True)
            self._planning_event(p, self.rng.choice(slots))

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
        return "req_k" if len(p.projects) >= 5 else "req_b"

    def _enter_fas(self):
        steg = self.fas_steg[self.round - 1]
        card = self.rng.choice(self.gd.phase_cards[steg])
        self.shared = {"steg": steg, "runda": self.round, "av": 3, "kort": card.to_dict(),
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
        for p in self.players.values():
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
                if lev["slot"] not in ORG_SLOTS and lev["niva"] <= 2:
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
            p.props = [{**x, "agd": "byggd"} for x in p.projects if x["typ"] != "BRF"]
            self.log(p.id, "skede2_slut", {"t": p.t, "q": p.q, "h": p.h, "tb": p.tb, "ek": p.ek})
        return "info"

    # ════════════════ SKEDE 3 – FÖRVALTNING ════════════════

    def _enter_intro3(self):
        return "info"

    def _yield(self, prop: dict) -> float:
        return self.yield_b if prop["typ"] in BOSTAD_TYPER else self.yield_k

    def _prop_view(self, prop: dict) -> dict:
        return {**prop, "fv": round(fv(prop, self._yield(prop)), 1)}

    def _enter_fc(self):
        fcs = self._deck([s.to_dict() | {"kapacitet": s.kapacitet} for s in self.gd.staff if s.roll == "FC"])
        fss = self._deck([s.to_dict() | {"kapacitet": s.kapacitet} for s in self.gd.staff if s.roll == "FS"])
        for i, p in enumerate(self.players.values()):
            p.offer = {"fc": [fcs[(i * 3 + k) % len(fcs)] for k in range(3)],
                       "fs": [fss[(i * 3 + k) % len(fss)] for k in range(3)]}
        return "decision"

    def _validate_fc(self, p, data):
        if data.get("fc") not in [c["id"] for c in p.offer["fc"]]:
            return "Välj en fastighetschef."
        fs = data.get("fs") or []
        if any(f not in [c["id"] for c in p.offer["fs"]] for f in fs):
            return "Okänd fastighetsskötare."
        kap = next(c for c in p.offer["fc"] if c["id"] == data["fc"])["kapacitet"] + \
            sum(c["kapacitet"] for c in p.offer["fs"] if c["id"] in fs)
        if kap < len(p.props):
            return f"Personalen räcker till {kap} fastigheter, du äger {len(p.props)}."

    def _resolve_fc(self):
        for p in self.players.values():
            p.fc = next(c for c in p.offer["fc"] if c["id"] == p.choice["fc"])
            p.fs = [c for c in p.offer["fs"] if c["id"] in (p.choice.get("fs") or [])]

    def _enter_kvartal(self):
        q = self.round
        self.reveal = {"title": f"Kvartal {q}", "rows": {}}
        world = self._draw(self.world_deck, self.gd.world_events)
        extra_market = 1 if world.effekt_typ == "auktion" else 0
        for p in self.players.values():
            self._apply_world(p, world)
            dn = sum(x["driftnetto"] for x in p.props)
            p.ek += dn
            self.note(p, f"Driftnetto in: {dn:+.1f} Mkr.", dn, plan=True)
            if p.lon:
                p.ek -= p.lon
                self.note(p, f"Löner till personalen: {-p.lon:.1f} Mkr.", -p.lon, plan=True)
            for prop in p.props:
                deck = self.mgmt.get(prop["typ"])
                if not deck and prop["typ"] in self.gd.mgmt_events:
                    deck = self.mgmt[prop["typ"]] = self._deck(self.gd.mgmt_events[prop["typ"]])
                if not deck:
                    continue
                ev = deck.pop()
                belopp, txt = ev.effekt_mkr, ""
                if ev.mildring_roll and self._har_mildring(p, ev):
                    belopp = ev.mildring_effekt_mkr
                    txt = f" Din {ev.mildring_roll.lower()} lindrar: {belopp:+.1f} Mkr."
                p.ek += belopp
                self.note(p, f"{prop['namn']}: {ev.rubrik} ({ev.effekt_mkr:+.1f} Mkr).{txt}", belopp)
        # Yield ändras i kvartal 1–3
        yb = yk = 0.0
        if q <= 3:
            yb = self._draw(self.yield_deck["bostader"], self.gd.yield_cards["bostader"])
            yk = self._draw(self.yield_deck["kommersiellt"], self.gd.yield_cards["kommersiellt"])
            self.yield_b = max(2.0, self.yield_b + yb)
            self.yield_k = max(2.0, self.yield_k + yk)
        # Marknaden
        pool = [x for t, pile in self.proj_piles.items() if t != "BRF" for x in pile]
        self.rng.shuffle(pool)
        market = []
        for prop in pool[:QUARTER_NEW_PROPS.get(q, 0) + extra_market]:
            self.proj_piles[prop["typ"]].remove(prop)
            market.append(self._prop_view(prop))
        self.shared = {"kvartal": q, "omvarld": world.to_dict(), "yield_b": self.yield_b,
                       "yield_k": self.yield_k, "yield_andring": {"b": yb, "k": yk}, "market": market,
                       "info": self.reveal["rows"]}
        self.reveal = {}
        for p in self.players.values():
            p.offer = {"props": [self._prop_view(x) for x in p.props],
                       "fs": [s.to_dict() | {"kapacitet": s.kapacitet}
                              for s in self.gd.staff if s.roll == "FS"
                              and s.id not in [f["id"] for f in p.fs]][:4]}
        return "decision"

    def _har_mildring(self, p: KPlayer, ev) -> bool:
        folk = ([p.fc] if p.fc and "chef" in ev.mildring_roll.lower() else []) + \
               (p.fs if "skötare" in ev.mildring_roll.lower() else [])
        return any(f["specialisering"] == ev.mildring_spec for f in folk)

    def _apply_world(self, p: KPlayer, w):
        typ, mkr = w.effekt_typ, w.effekt_mkr
        if typ in ("kostnad_alla", "intäkt_alla"):
            hit = p.props
        elif typ in ("kostnad_per_ek", "intäkt_per_ek"):
            klasser = re.findall(r"\b([A-F])\b", w.poverkar.replace("+", " "))
            hit = [x for x in p.props if x["energiklass"] in klasser]
        elif typ == "kostnad_kommersiellt":
            hit = [x for x in p.props if x["typ"] not in BOSTAD_TYPER]
        elif typ == "kostnad_kon":
            hit = [x for x in p.props if x["typ"] == "KONTOR"]
        elif typ == "intäkt_hr":
            hit = [x for x in p.props if x["typ"] == "HYRESRÄTT"]
        elif typ == "energi_sänkning_alla":
            for x in p.props:
                x["energiklass"] = self._ek_steg(x["energiklass"], +1)
            self.note(p, f"Omvärld: {w.rubrik}. Alla dina fastigheter tappar en energiklass.")
            return
        elif typ == "energi_höjning_val" and p.props:
            worst = max(p.props, key=lambda x: ENERGY_CLASSES.index(x["energiklass"])
                        if x["energiklass"] in ENERGY_CLASSES else 2)
            worst["energiklass"] = self._ek_steg(worst["energiklass"], -1)
            p.ek += mkr
            self.note(p, f"Omvärld: {w.rubrik}. {worst['namn']} lyfts till klass "
                         f"{worst['energiklass']} ({mkr:+.1f} Mkr).", mkr)
            return
        else:
            self.note(p, f"Omvärld: {w.rubrik}.")
            return
        total = mkr * len(hit)
        p.ek += total
        self.note(p, f"Omvärld: {w.rubrik} → {mkr:+.1f} Mkr × {len(hit)} fastigheter.", total)

    @staticmethod
    def _ek_steg(klass: str, steg: int) -> str:
        if klass not in ENERGY_CLASSES:
            klass = "C"
        i = min(len(ENERGY_CLASSES) - 1, max(0, ENERGY_CLASSES.index(klass) + steg))
        return ENERGY_CLASSES[i]

    def _validate_kvartal(self, p, data):
        market = {m["id"]: m for m in self.shared["market"]}
        bud = {k: float(v) for k, v in (data.get("bud") or {}).items() if v}
        for pid_, b in bud.items():
            if pid_ not in market:
                return "Okänd fastighet."
            if b < market[pid_]["fv"]:
                return f"Budet på {market[pid_]['namn']} måste vara minst {market[pid_]['fv']:.0f} Mkr."
        if 0.3 * sum(bud.values()) > max(0.0, p.ek):
            return f"Du har {p.ek:.1f} Mkr i eget kapital. 30 % av buden får inte överstiga det."
        salj = data.get("salj")
        if salj and salj not in [x["id"] for x in p.props]:
            return "Okänd fastighet att sälja."
        if salj and self.round == QUARTERS and len(p.props) <= 1:
            return "Du måste äga minst en fastighet när året är slut."
        upp = data.get("uppgradera")
        if upp:
            prop = next((x for x in p.props if x["id"] == upp), None)
            if not prop or prop["energiklass"] == ENERGY_CLASSES[0]:
                return "Fastigheten kan inte uppgraderas."
        fs = data.get("fs")
        if fs and fs not in [f["id"] for f in p.offer["fs"]]:
            return "Okänd fastighetsskötare."
        kap = p.kapacitet + (next(f["kapacitet"] for f in p.offer["fs"] if f["id"] == fs) if fs else 0)
        if len(p.props) - (1 if salj else 0) + len(bud) > kap:
            return f"Personalen räcker till {kap} fastigheter. Anställ en fastighetsskötare eller bjud på färre."

    def _resolve_kvartal(self):
        self.reveal = {"title": f"Kvartal {self.round}: marknaden", "rows": {}, "bud": {}}
        for p in self.players.values():
            c = p.choice
            if c.get("fs"):
                fs = next(f for f in p.offer["fs"] if f["id"] == c["fs"])
                p.fs.append(fs)
                self.note(p, f"Anställde fastighetsskötare {fs['namn']} (lön {fs['lon']} Mkr/kvartal).")
            if c.get("salj"):
                prop = next(x for x in p.props if x["id"] == c["salj"])
                varde = 0.8 * fv(prop, self._yield(prop))
                p.props.remove(prop)
                self.proj_piles[prop["typ"]].insert(0, {k: v for k, v in prop.items() if k != "agd"})
                p.ek += 0.3 * varde
                self.note(p, f"Sålde {prop['namn']} till banken för 80 % ({varde:.0f} Mkr). "
                             f"Din andel 30 % → {0.3 * varde:+.1f} Mkr.", 0.3 * varde, plan=True)
            if c.get("uppgradera"):
                prop = next(x for x in p.props if x["id"] == c["uppgradera"])
                prop["energiklass"] = self._ek_steg(prop["energiklass"], -1)
                p.ek -= ENERGY_UPGRADE_COST_PER_STEP
                self.note(p, f"Energiuppgraderade {prop['namn']} till klass {prop['energiklass']}.",
                          -ENERGY_UPGRADE_COST_PER_STEP, plan=True)
        for m in self.shared["market"]:
            bids = [(float(p.choice.get("bud", {}).get(m["id"]) or 0), d(6, self.rng), p)
                    for p in self.players.values()]
            bids = [b for b in bids if b[0] >= m["fv"]]
            self.reveal["bud"][m["id"]] = {
                "namn": m["namn"], "fv": m["fv"],
                "bud": [{"name": p.name, "color": p.color, "bud": b} for b, _, p in bids]}
            if not bids:
                self.proj_piles[m["typ"]].insert(0, {k: v for k, v in m.items() if k != "fv"})
                continue
            bud, _, w = max(bids, key=lambda x: (x[0], x[1]))
            self.reveal["bud"][m["id"]]["vinnare"] = w.name
            w.ek -= 0.3 * bud
            prop = {k: v for k, v in m.items() if k != "fv"} | {"agd": "köpt"}
            w.props.append(prop)
            self.note(w, f"Du vann {m['namn']} för {bud:.0f} Mkr. Du betalar 30 %: {-0.3 * bud:.1f} Mkr.",
                      -0.3 * bud, plan=True)
            dd = self._draw(self.dd_deck, self.gd.dd_cards)
            w.ek += dd.effekt_mkr
            self.note(w, f"DD-kort: {dd.rubrik} ({dd.effekt_mkr:+.1f} Mkr).", dd.effekt_mkr)
        self.log(None, "kvartal", {"bud": self.reveal["bud"]})

    def _enter_kvartal_res(self):
        return "info"

    # ════════════════ SLUTRESULTAT ════════════════

    def _enter_final(self):
        res = []
        for p in self.players.values():
            fv_tot = sum(fv(x, self._yield(x)) for x in p.props)
            bta = sum(x["bta"] for x in p.props)
            ek_factor = 0.10 if p.ek >= 0 else 2.00
            rapong = ((0.30 * fv_tot + ek_factor * p.ek + p.tb) / bta * 1000) if bta else p.tb
            n = p.n_q + p.n_h + p.n_t
            f_n = deviation_factor(n)
            score = rapong * f_n
            p.result = {"fv": round(fv_tot, 1), "fv_30": round(0.3 * fv_tot, 1), "ek": round(p.ek, 1),
                        "ek_factor": ek_factor, "tb": round(p.tb, 1), "bta": bta,
                        "rapong": round(rapong, 1), "n": n, "f_n": f_n, "score": round(score, 1),
                        "lardomar": sorted(p.log, key=lambda x: x["mkr"])[:3],
                        "basta": sorted(p.log, key=lambda x: -x["mkr"])[:2]}
            res.append((score, p))
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
        if s == "ac":
            return {"id": r.choice(p.offer["ac"])["id"]}
        if s == "p1":
            fits = [t for t, x in self.shared["market"].items() if x["rutor"] <= p.rutor_kvar]
            if fits and len(p.projects) < MAX_PROJECTS and r.random() < 0.7:
                best = max(fits, key=lambda t: self.shared["market"][t]["bta"] / max(1, self.shared["market"][t]["rutor"]) + r.random() * 200)
                return {"val": "projekt", "typ": best}
            if not fits and p.expansions < 2:
                return {"val": "markexpansion"}
            return {"val": r.choice(["dialog", "riskbuffert"])}
        if s == "upph":
            return {"val": {o["slot"]: max(o["min"], r.choice([2, 2, 3, 3, 4, 1]))
                            for o in p.offer["slots"]}}
        if s == "fas":
            for i in range(len(p.offer["nivaer"]) - 1, -1, -1):
                if not self._validate_fas(p, {"niva": i, "kultur": []}):
                    return {"niva": i, "kultur": []}
            return {"niva": 0, "kultur": []}
        if s == "fc":
            fc = r.choice(p.offer["fc"])
            fs, kap = [], fc["kapacitet"]
            for f in sorted(p.offer["fs"], key=lambda x: -x["kapacitet"]):
                if kap >= len(p.props):
                    break
                fs.append(f["id"])
                kap += f["kapacitet"]
            return {"fc": fc["id"], "fs": fs}
        if s == "kvartal":
            bud, kap = {}, p.kapacitet - len(p.props)
            budget = max(0.0, p.ek) / 0.3
            for m in self.shared["market"]:
                b = round(m["fv"] * r.uniform(1.0, 1.15))
                if kap > 0 and b <= budget and r.random() < 0.6:
                    bud[m["id"]] = b
                    budget -= b
                    kap -= 1
            upp = None
            if p.ek > 10:
                cands = [x for x in p.props if x["energiklass"] not in ("A",)]
                if cands:
                    upp = max(cands, key=lambda x: ENERGY_CLASSES.index(x["energiklass"])
                              if x["energiklass"] in ENERGY_CLASSES else 2)["id"]
            return {"bud": bud, "uppgradera": upp, "salj": None, "fs": None}
        return {}

    # ════════════════ VY ════════════════

    def view(self, pid: Optional[str]) -> dict:
        me = self.players.get(pid) if pid else None
        return {
            "code": self.code, "step": self.step, "round": self.round, "kind": self.kind,
            "deadline": self.deadline, "now": time.time(),
            "del": self._del() if self.step != "lobby" else 0,
            "players": [p.public() for p in self.players.values()],
            "me": me.private() if me else None,
            "shared": self.shared, "reveal": self.reveal,
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
