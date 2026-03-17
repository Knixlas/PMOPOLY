"""Game data models for PMOPOLY."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import random
from config import DICE_MAP, D20_THRESHOLDS


class GamePhase(str, Enum):
    LOBBY = "lobby"
    PHASE1_MARK_TOMT = "phase1_mark_tomt"
    PHASE1_BOARD = "phase1_board"
    PHASE1_NAMNDBESLUT = "phase1_namndbeslut"
    PHASE1_PLACEMENT = "phase1_placement"
    PHASE1_EKONOMI = "phase1_ekonomi"
    PHASE2_PLANERING = "phase2_planering"
    PUZZLE_PLACEMENT = "puzzle_placement"
    PHASE3_GENOMFORANDE = "phase3_genomforande"
    PHASE4_FORVALTNING = "phase4_forvaltning"
    FINISHED = "finished"


# ── Dice ──

def roll(die: str) -> int:
    sides = DICE_MAP.get(die.upper().strip())
    if not sides:
        raise ValueError(f"Unknown die: {die}")
    return random.randint(1, sides)


# ── Data Classes ──

@dataclass
class Project:
    id: str
    namn: str
    typ: str
    forekomst: int
    kostnad: int
    formfaktor: int
    bta: int
    anskaffning: int
    marknadsvarde: int
    rorlig_intakt: str  # e.g. "D12"
    kvalitet: int
    hallbarhet: int
    tid: int
    riskbuffert: int
    antal_krav: int
    namndbeslut: int
    energiklass: str
    driftnetto: float
    # Supplier requirements: type -> min level description
    supplier_reqs: Dict[str, str] = field(default_factory=dict)
    # Competency requirements
    led: int = 0
    kom: int = 0
    sam: int = 0
    pro: int = 0
    abm: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "namn": self.namn, "typ": self.typ,
            "kostnad": self.kostnad, "formfaktor": self.formfaktor,
            "bta": self.bta, "anskaffning": self.anskaffning,
            "marknadsvarde": self.marknadsvarde, "rorlig_intakt": self.rorlig_intakt,
            "kvalitet": self.kvalitet, "hallbarhet": self.hallbarhet,
            "tid": self.tid, "riskbuffert": self.riskbuffert,
            "namndbeslut": self.namndbeslut, "energiklass": self.energiklass,
            "driftnetto": self.driftnetto, "forekomst": self.forekomst,
        }


@dataclass
class PolitikDialogCard:
    typ: str          # "Politik" or "Dialog"
    nr: str
    rubrik: str
    text: str
    effects: Dict[str, str]  # threshold range -> effect text

    def to_dict(self) -> dict:
        return {"typ": self.typ, "nr": self.nr, "rubrik": self.rubrik,
                "text": self.text, "effects": self.effects}


@dataclass
class SpecialCard:
    typ: str
    rubrik: str
    poverkar: str
    effekt: str

    def to_dict(self) -> dict:
        return {"typ": self.typ, "rubrik": self.rubrik,
                "poverkar": self.poverkar, "effekt": self.effekt}


@dataclass
class PlanningEventCard:
    kort_id: str        # e.g. "MARK", "OPERATIVT TEAM"
    id: int
    namn: str
    typ: str            # "Negativt", "Neutralt", "Positivt", "Positivt (B)ÄTA"
    fas: str
    svarighetsgrad: str
    beskrivning: str
    summering: str      # Which cards contribute experience
    trigger: str        # "Alla", "STAPLAD, KOMPLEX", "BOSTÄDER"
    klassvillkor: str   # "Alla", "Skalad", "Skalad (BYA)", "Skalad (BTA)", "BTA Klass C+"
    effects: List[str] = field(default_factory=list)  # 4 effect texts, worst→best

    def get_effect(self, roll_plus_exp: int) -> str:
        for i, upper in enumerate(D20_THRESHOLDS):
            if roll_plus_exp <= upper and i < len(self.effects):
                return self.effects[i]
        return self.effects[-1] if self.effects else ""

    def to_dict(self) -> dict:
        return {
            "kort_id": self.kort_id, "id": self.id, "namn": self.namn,
            "typ": self.typ, "beskrivning": self.beskrivning,
            "summering": self.summering, "trigger": self.trigger,
            "klassvillkor": self.klassvillkor, "effects": self.effects,
        }


@dataclass
class Supplier:
    namn: str
    niva: int
    beskrivning: str
    beror_av: str  # "BYA" or "BTA"
    klass_priser: Dict[str, int]  # {"A": 10, ...}
    q: int
    h: int
    t: int
    erfarenhet: int
    kompetenser: Dict[str, int]  # LED, KOM, SAM, PRO, ABM

    def kostnad(self, klass: str) -> int:
        return self.klass_priser.get(klass, 0)

    def to_dict(self, klass: str = "C") -> dict:
        return {
            "namn": self.namn, "niva": self.niva, "beskrivning": self.beskrivning,
            "beror_av": self.beror_av, "kostnad": self.kostnad(klass),
            "klass_priser": self.klass_priser,
            "q": self.q, "h": self.h, "t": self.t,
            "erfarenhet": self.erfarenhet, "kompetenser": self.kompetenser,
        }


@dataclass
class Organisation:
    namn: str
    niva: int
    kostnad_mkr: int
    q: int
    h: int
    t: int
    erfarenhet: int
    riskbuffert: int
    kompetenser: Dict[str, int]

    def to_dict(self) -> dict:
        return {
            "namn": self.namn, "niva": self.niva, "kostnad_mkr": self.kostnad_mkr,
            "q": self.q, "h": self.h, "t": self.t,
            "erfarenhet": self.erfarenhet, "riskbuffert": self.riskbuffert,
            "kompetenser": self.kompetenser,
        }


@dataclass
class PhaseCard:
    id: str
    steg: int
    namn: str
    beskrivning: str
    levels: List[dict]  # [{name, req_b, req_s, req_k, effect}, ...]

    def to_dict(self) -> dict:
        return {"id": self.id, "steg": self.steg, "namn": self.namn,
                "beskrivning": self.beskrivning, "levels": self.levels}


@dataclass
class ExternalSupport:
    id: str
    namn: str
    kompetenser: Dict[str, int]

    def to_dict(self) -> dict:
        return {"id": self.id, "namn": self.namn, "kompetenser": self.kompetenser}


@dataclass
class PenaltyCard:
    typ: str  # T, Q, H
    nr: str
    namn: str
    effects: List[str]
    energiklass_projekt: int = 0  # Number of projects to downgrade on worst outcome

    def get_effect(self, roll_plus_exp: int) -> tuple:
        """Returns (effect_text, should_downgrade_energy)."""
        thresholds = [8, 15, 21, 9999]
        for i, upper in enumerate(thresholds):
            if roll_plus_exp <= upper and i < len(self.effects):
                downgrade = (i == 0 and self.energiklass_projekt > 0)
                return self.effects[i], downgrade
        eff = self.effects[-1] if self.effects else ""
        return eff, False

    def to_dict(self) -> dict:
        return {"typ": self.typ, "nr": self.nr, "namn": self.namn,
                "effects": self.effects, "energiklass_projekt": self.energiklass_projekt}


@dataclass
class Staff:
    roll: str  # FC or FS
    id: str
    namn: str
    specialisering: str
    kapacitet: int
    handelsemotstand: str
    lon: float
    forhandling: str

    def to_dict(self) -> dict:
        return {
            "roll": self.roll, "id": self.id, "namn": self.namn,
            "specialisering": self.specialisering, "kapacitet": self.kapacitet,
            "lon": self.lon, "forhandling": self.forhandling,
        }


@dataclass
class WorldEvent:
    id: str
    rubrik: str
    effekt_typ: str
    effekt_mkr: float
    poverkar: str
    beskrivning: str

    def to_dict(self) -> dict:
        return {"id": self.id, "rubrik": self.rubrik, "effekt_typ": self.effekt_typ,
                "effekt_mkr": self.effekt_mkr, "poverkar": self.poverkar,
                "beskrivning": self.beskrivning}


@dataclass
class ManagementEvent:
    id: str
    typ: str
    rubrik: str
    effekt_mkr: float
    mildring_roll: str = ""    # FC or FS (empty = no mitigation)
    mildring_spec: str = ""    # Specialisering required
    mildring_effekt_mkr: float = 0.0
    trigger: str = "Alla"
    beskrivning: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "typ": self.typ, "rubrik": self.rubrik,
                "effekt_mkr": self.effekt_mkr, "trigger": self.trigger,
                "beskrivning": self.beskrivning,
                "mildring_roll": self.mildring_roll,
                "mildring_spec": self.mildring_spec,
                "mildring_effekt_mkr": self.mildring_effekt_mkr}


@dataclass
class DDCard:
    id: str
    typ: str
    rubrik: str
    effekt_mkr: float
    beskrivning: str

    def to_dict(self) -> dict:
        return {"id": self.id, "typ": self.typ, "rubrik": self.rubrik,
                "effekt_mkr": self.effekt_mkr, "beskrivning": self.beskrivning}


# ── BYA/BTA Classification ──

BYA_CLASSES: List[tuple] = []  # (min, max, class_letter)
BTA_CLASSES: List[tuple] = []


def classify(value: int, table: List[tuple]) -> str:
    for lo, hi, klass in table:
        if lo <= value <= hi:
            return klass
    if table:
        return table[0][2]
    return "D"


# ── Player State ──

@dataclass
class Player:
    id: str
    name: str
    color: str
    # Phase 1
    position: int = 1
    laps: int = 0
    projects: List[Project] = field(default_factory=list)
    riskbuffertar: int = 0
    q_krav: int = 4
    h_krav: int = 4
    t_bonus: int = 0
    mark_expansions: int = 0  # legacy counter (for economics)
    mark_expansion_pieces: List[dict] = field(default_factory=list)  # [{id, cells: [[r,c],...]}]
    has_mark_tomt: bool = False
    # Economics
    eget_kapital: float = 0.0
    abt_budget: float = 0.0
    abt_start: float = 0.0
    abt_overflow: float = 0.0
    abt_borrowing_cost: float = 0.0
    abt_loans_net: float = 0.0
    # Phase 2
    pl_q: int = 0
    pl_h: int = 0
    pl_t: int = 0
    pl_kostnad: float = 0.0
    pl_suppliers: Dict[str, dict] = field(default_factory=dict)
    pl_orgs: Dict[str, dict] = field(default_factory=dict)
    snap_plan_q: int = 0
    snap_plan_h: int = 0
    snap_plan_t: int = 0
    # Phase 3
    used_supplier_keys: List[str] = field(default_factory=list)
    used_org_keys: List[str] = field(default_factory=list)
    used_external_ids: List[str] = field(default_factory=list)
    external_hand: List[dict] = field(default_factory=list)
    projekt_energiklass: Dict[str, str] = field(default_factory=dict)
    snap_exec_q: int = 0
    snap_exec_h: int = 0
    snap_exec_t: int = 0
    abt_remaining_before_transfer: float = 0.0
    # Puzzle placement
    puzzle_grid_cells: List[List[int]] = field(default_factory=list)
    puzzle_placements: Dict[str, dict] = field(default_factory=dict)
    puzzle_mark_placements: Dict[str, dict] = field(default_factory=dict)
    puzzle_confirmed: bool = False
    placed_project_ids: List[str] = field(default_factory=list)
    # Phase 4
    staff: list = field(default_factory=list)
    fastigheter: list = field(default_factory=list)
    driftnetto_bonus: Dict[str, float] = field(default_factory=dict)
    f4_score: float = 0.0
    f4_score_per_bta: float = 0.0
    f4_fv_30: float = 0.0
    f4_real_ek: float = 0.0
    f4_tb: float = 0.0

    @property
    def total_bta(self) -> int:
        return sum(p.bta for p in self.projects)

    @property
    def total_bya(self) -> int:
        return sum(p.formfaktor * 250 for p in self.projects)

    @property
    def available_cells(self) -> int:
        expansion_cells = sum(p["cell_count"] for p in self.mark_expansion_pieces) if self.mark_expansion_pieces else 0
        return 16 + expansion_cells

    @property
    def used_cells(self) -> int:
        return sum(p.formfaktor for p in self.projects)

    @property
    def bta_klass(self) -> str:
        return classify(self.total_bta, BTA_CLASSES)

    @property
    def bya_klass(self) -> str:
        return classify(self.total_bya, BYA_CLASSES)

    @property
    def total_erfarenhet(self) -> int:
        exp = 0
        for s in self.pl_suppliers.values():
            exp += s.erfarenhet if hasattr(s, 'erfarenhet') else s.get("erfarenhet", 0)
        for o in self.pl_orgs.values():
            exp += o.erfarenhet if hasattr(o, 'erfarenhet') else o.get("erfarenhet", 0)
        return exp

    @property
    def kvarter_trigger(self) -> str:
        typer = set(p.typ for p in self.projects)
        bostader = typer & {"BRF", "Hyresrätt"}
        ovriga = typer - {"BRF", "Hyresrätt"}
        if not bostader:
            return "STAPLAD" if len(ovriga) >= 1 else "BOSTÄDER"
        if len(ovriga) >= 2:
            return "KOMPLEX"
        elif len(ovriga) >= 1:
            return "STAPLAD"
        return "BOSTÄDER"

    def relevant_erfarenhet(self, summering: str) -> int:
        """Calculate experience from only relevant cards based on summering text."""
        exp = 0
        summering_upper = summering.upper()
        for namn, s in self.pl_suppliers.items():
            if namn.upper() in summering_upper or f"{namn.upper()} (OM VALD)" in summering_upper:
                exp += s.erfarenhet if hasattr(s, 'erfarenhet') else 0
        for namn, o in self.pl_orgs.items():
            if namn.lower() in summering.lower():
                exp += o.erfarenhet if hasattr(o, 'erfarenhet') else 0
        return exp

    def get_available_competence_cards(self) -> List[dict]:
        """Get playable competence cards from unused suppliers, orgs, and external support."""
        cards = []
        # Unused suppliers
        for key, s in self.pl_suppliers.items():
            if key not in self.used_supplier_keys:
                komp = s.kompetenser if hasattr(s, 'kompetenser') else s.get("kompetenser", {})
                # Class bonus: A/B +0, C +1, D +2 per competency
                niva = s.niva if hasattr(s, 'niva') else s.get("niva", 1)
                bonus = 2 if niva <= 1 else (1 if niva <= 2 else 0)
                boosted = {k: v + (bonus if v > 0 else 0) for k, v in komp.items()}
                cards.append({"source": "supplier", "key": key, "namn": key,
                              "kompetenser": boosted, "original_komp": komp, "bonus": bonus})
        # Unused orgs
        for key, o in self.pl_orgs.items():
            if key not in self.used_org_keys:
                komp = o.kompetenser if hasattr(o, 'kompetenser') else o.get("kompetenser", {})
                cards.append({"source": "org", "key": key, "namn": key, "kompetenser": komp})
        # External support in hand (not yet played this phase)
        for es in self.external_hand:
            eid = es.get("id", "")
            if eid not in self.used_external_ids:
                cards.append({"source": "external", "key": eid, "namn": es.get("namn", ""),
                              "kompetenser": es.get("kompetenser", {})})
        return cards

    def card_is_eligible(self, card) -> bool:
        """Check if a planning event card's trigger matches this player's kvarter."""
        trigger = card.trigger.upper()
        if trigger == "ALLA":
            return True
        player_trigger = self.kvarter_trigger
        triggers = [t.strip() for t in trigger.split(",")]
        for t in triggers:
            if t == player_trigger:
                return True
            if t == "STAPLAD" and player_trigger == "KOMPLEX":
                return True
        return False

    def to_dict(self) -> dict:
        # Serialize suppliers/orgs
        suppliers_dict = {}
        for namn, s in self.pl_suppliers.items():
            if hasattr(s, 'to_dict'):
                klass = self.bya_klass if s.beror_av == "BYA" else self.bta_klass
                suppliers_dict[namn] = s.to_dict(klass)
            else:
                suppliers_dict[namn] = s
        orgs_dict = {}
        for namn, o in self.pl_orgs.items():
            orgs_dict[namn] = o.to_dict() if hasattr(o, 'to_dict') else o

        return {
            "id": self.id, "name": self.name, "color": self.color,
            "position": self.position, "laps": self.laps,
            "projects": [p.to_dict() for p in self.projects],
            "riskbuffertar": self.riskbuffertar,
            "q_krav": self.q_krav, "h_krav": self.h_krav,
            "t_bonus": self.t_bonus,
            "mark_expansions": self.mark_expansions,
            "mark_expansion_pieces": self.mark_expansion_pieces,
            "eget_kapital": round(self.eget_kapital, 1),
            "abt_budget": round(self.abt_budget, 1),
            "abt_start": round(self.abt_start, 1),
            "available_cells": self.available_cells,
            "used_cells": self.used_cells,
            "total_bta": self.total_bta,
            "total_bya": self.total_bya,
            "bta_klass": self.bta_klass,
            "bya_klass": self.bya_klass,
            "pl_q": self.pl_q, "pl_h": self.pl_h, "pl_t": self.pl_t,
            "pl_kostnad": round(self.pl_kostnad, 1),
            "kvarter_trigger": self.kvarter_trigger,
            "total_erfarenhet": self.total_erfarenhet,
            "pl_suppliers": suppliers_dict,
            "pl_orgs": orgs_dict,
            "used_supplier_keys": self.used_supplier_keys,
            "used_org_keys": self.used_org_keys,
            "used_external_ids": self.used_external_ids,
            "external_hand": self.external_hand,
            "projekt_energiklass": self.projekt_energiklass,
            "staff": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.staff],
            "fastigheter": [p.to_dict() if hasattr(p, 'to_dict') else p for p in self.fastigheter],
            "abt_loans_net": round(self.abt_loans_net, 1),
            "abt_borrowing_cost": round(self.abt_borrowing_cost, 1),
            "driftnetto_bonus": self.driftnetto_bonus,
            "f4_score": round(self.f4_score, 1),
            "f4_score_per_bta": round(self.f4_score_per_bta, 1),
            "f4_fv_30": round(self.f4_fv_30, 1),
            "f4_real_ek": round(self.f4_real_ek, 1),
            "f4_tb": round(self.f4_tb, 1),
            "puzzle_confirmed": self.puzzle_confirmed,
            "placed_project_ids": self.placed_project_ids,
        }
