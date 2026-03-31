"""Companion app — manual mode for physical board game sessions."""
import uuid
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket


# ── Phase/step definitions (loaded from JSON, fallback to hardcoded) ──
def _load_phases_from_json():
    """Load phases from companion_texts.json if available."""
    texts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "companion_texts.json")
    try:
        with open(texts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("phases", [])
    except Exception:
        return None

PHASES = [
    {"id": "phase1", "name": "Fas 1: Projektutveckling", "steps": [
        {"id": "choose_pc", "name": "1.2 Välj Projektchef", "help":
            "Varje spelare väljer 1 av 10 projektchefer. Gratis.\n\n"
            "Attribut att jämföra:\n"
            "• Riskbuffertar (Rb) — säkerhetsmarginal\n"
            "• Lindring — bonus på politik/dialogkort under PU-brädet\n"
            "• Nämndbonus — bonus vid nämndbeslut (steg 1.8)\n"
            "• Q/H/T-bonus — tillämpas i fas 2\n"
            "• Kompetens — spelbar som kort i fas 3\n\n"
            "Tips: Hög lindring = bra under PU-brädet. Hög nämndbonus = tryggare med BRF. "
            "Hög Rb = mer flexibilitet senare."},
        {"id": "projects", "name": "1.4–1.6 Projektval & Brädspel", "help":
            "Välj ett startprojekt (1.4), sedan spelas PU-brädet (1.5–1.6).\n\n"
            "Under brädspelet:\n"
            "• Projektrutor — ta ett projekt av typen\n"
            "• Stadshuset — ta, byt eller lämna tillbaka\n"
            "• Stjärna — +1 riskbuffert\n"
            "• Skönhetsrådet — −2 Q-krav\n"
            "• Länsstyrelsen — −2 H-krav\n"
            "• Dialogkort — slå D20 + PC-lindring\n"
            "• Politikkort — slå D20 + PC-lindring\n"
            "• Stadsbyggnadskontoret — markexpansion (+5 Mkr)\n\n"
            "Registrera dina projekt och uppdatera Q/H/Rb med +/- knapparna.\n"
            "Tips: Max 9 projekt. KOMPLEX kvarter (bostäder + 2 andra typer) ger svårast händelsekort."},
        {"id": "namndbeslut", "name": "1.8 Nämndbeslut", "help":
            "Projekt med nämndkrav > 1: slå D20 + PC:s nämndbonus.\n\n"
            "• Resultat ≥ krav = godkänt\n"
            "• Misslyckat: använd Rb för omslag, eller ta bort projektet\n"
            "• Utvecklingskostnaden är redan betald\n\n"
            "Ta bort underkända projekt med ✕-knappen.\n\n"
            "Du kan också köpa nya projekt från projektbanken — men de kostar 3× utvecklingskostnad!\n\n"
            "Tips: Rb kan rädda ett misslyckat projekt — värt det för dyra projekt!"},
        {"id": "rb_invest", "name": "1.12 Rb-investering", "help":
            "Fördela kvarvarande riskbuffertar:\n\n"
            "• −1 Q-krav per Rb\n"
            "• −1 H-krav per Rb\n"
            "• −1 T (byggtid) per Rb\n\n"
            "Resterande Rb sparas till fas 3 (omslag på händelsekort).\n"
            "Tips: Sänk det krav som är svårast att uppfylla med leverantörer i fas 2."},
    ]},
    {"id": "phase2", "name": "Fas 2: Projektplanering", "steps": [
        {"id": "choose_ac", "name": "2.1 Välj Arbetschef", "help":
            "Varje spelare väljer 1 av 10 arbetschefer. Gratis.\n\n"
            "Attribut att jämföra:\n"
            "• Riskbuffertar (Rb) — extra säkerhet\n"
            "• Erfarenhet — permanent bonus på ALLA händelsekort (fas 2+3)\n"
            "• Kompetens (STA/KOM/SAM/NOG/INN/ABM) — spelbar som kort i fas 3\n"
            "• Q/H/T-bonus — tillämpas direkt\n\n"
            "Tips: +2 erfarenhet är extremt värdefullt — det lindrar ALLA händelsekort. "
            "Men det kostar kompetenspoäng. En AC med INN:4 kan vara avgörande."},
        {"id": "planning", "name": "2.3 Planeringssteg", "help":
            "13 steg i ordning: Stödf. → Mark → Husund. → Dig. → Stomme → Install. → "
            "Op.team → Gem.arb → Yttertak → Fasader → Markn. → Stomkomp. → Inv.ytsk.\n\n"
            "Per steg:\n"
            "• Välj leverantör/organisation (nivå 1–4)\n"
            "• Pris beror på BYA/BTA-klass, dras från ABT\n"
            "• Q, H, T, erfarenhet uppdateras\n"
            "• Dra ett händelsekort → D20 + erfarenhet\n\n"
            "Registrera dina leverantörsval och uppdatera Q/H/T/ABT med +/- knapparna.\n\n"
            "Tips: Kolla TG (täckningsgrad) varje steg. Under 20%? Dags att välja billigare."},
        {"id": "planning_summary", "name": "2.5 Planeringssummering", "help":
            "Kontrollera dina värden:\n\n"
            "• Q vs Q-krav — uppfyllt?\n"
            "• H vs H-krav — uppfyllt?\n"
            "• T (byggtid i månader)\n"
            "• ABT kvar — tillräcklig marginal?\n"
            "• Erfarenhet — påverkar fas 3\n\n"
            "Alla leverantörs- och organisationskort sparas som kompetenskort för fas 3."},
    ]},
    {"id": "phase3", "name": "Fas 3: Genomförande", "steps": [
        {"id": "gf_byggfaser", "name": "3.1–3.4 Byggfaser (8 st)", "help":
            "8 byggfaser. Per fas:\n\n"
            "1. Köp företagskulturkort (valfritt)\n"
            "   Kostnad ökar per fas: 2–7 Mkr. Ger kompetenspoäng.\n\n"
            "2. Dra händelsekort\n"
            "   D20 + erfarenhet (inkl. AC). Effekt på ABT.\n\n"
            "3. Välj utfallsnivå på faskort\n"
            "   • Negativt — gratis, straff (Q/H/T-förlust)\n"
            "   • Neutralt — kräver kompetenskort\n"
            "   • Positivt — högre krav, minimal kostnad\n"
            "   • Bonus — högsta krav, kan ge vinst\n\n"
            "4. Spela kompetenskort (om Neutralt+)\n"
            "   Leverantörs-, org-, AC- eller kulturkort.\n"
            "   D-klass: +2 bonus, C-klass: +1.\n\n"
            "Tips: Planera alla 8 faser! Spela inte allt på fas 1–3."},
        {"id": "gf_konsekvens", "name": "3.5 Konsekvenskort", "help":
            "Kontrollera Q, H och T:\n\n"
            "• Q under krav → 1 konsekvenskort per poäng under\n"
            "• H under krav → 1 konsekvenskort per poäng under\n"
            "• T > 12 → 1 konsekvenskort per månad över\n\n"
            "Per kort: slå D20 + erfarenhet. Effekt = ABT-kostnad.\n\n"
            "Registrera ABT-ändringar med +/- knapparna."},
        {"id": "gf_garanti", "name": "3.6 Garantibesiktning", "help":
            "Trigger:\n"
            "• Leverantörer nivå 1–2: 1 kort per styck\n"
            "• Organisationer nivå 1–2: 1 kort per styck\n"
            "• Q under krav: extra kort\n\n"
            "Per kort: slå D20. Effekt = ABT-kostnad.\n\n"
            "Registrera ABT-ändringar med +/- knapparna."},
        {"id": "gf_abt_ek", "name": "3.7–3.8 ABT→EK & Förskott", "help":
            "Kvarvarande ABT-budget överförs till EK.\n\n"
            "Förskott (projektvinster):\n"
            "• BRF: (Marknadsvärde − Anskaffning) + tärning → EK\n"
            "• Övriga: bara tärning → EK\n\n"
            "Registrera ditt slutliga EK."},
    ]},
    {"id": "phase4", "name": "Fas 4: Förvaltning", "steps": [
        {"id": "f4_forbered", "name": "4.1 Förbered förvaltning", "help":
            "Projekt blir fastigheter. BRF säljs och ökar EK med (MV − Anskaffning).\n"
            "Kvarvarande = förvaltningsportfölj.\n\n"
            "• Välj FC (Fastighetschef) och FS (Fastighetsskötare)\n"
            "• Sätt energiklass per fastighet (A–F)\n"
            "• Köp/sälj fastigheter om önskat"},
        {"id": "f4_q1", "name": "4.2–4.3 Kvartal 1", "help":
            "Kvartal 1:\n"
            "• Ange yield (bostäder + kommersiellt) → marknadsvärde uppdateras\n"
            "• Dra händelsekort per fastighet → registrera EK/energi-effekter\n"
            "• Lön FC+FS dras automatiskt\n"
            "• Köp/sälj fastigheter"},
        {"id": "f4_q2", "name": "4.4–4.5 Kvartal 2", "help":
            "Kvartal 2:\n"
            "• Ange yield → marknadsvärde uppdateras\n"
            "• Händelsekort per fastighet\n"
            "• Hyresförhandling (om hyresrätt)\n"
            "• Lön, köp/sälj"},
        {"id": "f4_q3", "name": "4.6–4.7 Kvartal 3", "help":
            "Kvartal 3:\n"
            "• Ange yield → marknadsvärde uppdateras\n"
            "• Händelsekort per fastighet\n"
            "• Lön, köp/sälj"},
        {"id": "f4_q4", "name": "4.8–4.9 Kvartal 4", "help":
            "Kvartal 4:\n"
            "• Ange yield → marknadsvärde uppdateras\n"
            "• Händelsekort per fastighet\n"
            "• Hyresförhandling (om hyresrätt)\n"
            "• Lön, köp/sälj"},
        {"id": "f4_slut", "name": "5.1–5.2 Slutvärdering", "help":
            "Beräkna slutpoäng:\n\n"
            "FV = DN/yield × energiklassmodifier per fastighet\n"
            "FV × 30% = ägarandel\n\n"
            "Slutpoäng = (FV×30% + EK + TB) / BTA × 1000 [kr/kvm]\n\n"
            "Högst poäng vinner!"},
    ]},
]

# Try to load from JSON (overrides hardcoded if file exists)
_json_phases = _load_phases_from_json()
if _json_phases:
    PHASES = _json_phases


DISTRICT_NAMES = [
    "Solbacken", "Ekudden", "Björkhagen", "Tallåsen",
    "Sjöängen", "Strandliden", "Bergslund", "Ängslyckan",
    "Åkervallen", "Parkvillan", "Havsutsikten", "Skogsdungen",
    "Klippudden", "Furuliden", "Mossängen", "Kastanjegården",
    "Vintergatan", "Sommarbo", "Strömsborg", "Klockelund",
]

BLOCK_NAMES = [
    "Eken", "Linden", "Björken", "Granen", "Cedern", "Almen",
    "Poppeln", "Aspen", "Lönnen", "Rönnen", "Valnöten", "Kastanjen",
    "Olivträdet", "Magnolian", "Syrenen", "Jasmin", "Rosen", "Tulpanen",
    "Lavendeln", "Klematis", "Blåklinten", "Prästkragen", "Vallmon",
    "Smultronet", "Hallonbusken", "Vinbäret", "Krusbäret", "Nyponet",
    "Vitsippan", "Blåsippan", "Liljekonvaljen", "Snödroppen",
    "Krokus", "Iris", "Dahlia", "Pionen", "Orkidén", "Solrosen",
    "Fjällvinden", "Norrsken", "Midnattssol", "Skymningen",
]


# ── Quiz helpers ──

def _quiz_points(base_points: float, time_taken: float, time_limit: float) -> float:
    """Calculate quiz points based on response time.
    100% at ≤2s, linear decay to 1% at time_limit."""
    if time_taken <= 2.0:
        return base_points
    if time_taken >= time_limit:
        return round(base_points * 0.01, 1)
    fraction = 1.0 - 0.99 * (time_taken - 2.0) / (time_limit - 2.0)
    return round(base_points * max(fraction, 0.01), 1)


def _check_answer(question: dict, answer) -> bool:
    """Validate answer against question. Returns True if correct."""
    q_type = question.get("type", "text")
    correct = question.get("correct")

    if q_type == "multiple_choice":
        try:
            return int(answer) == int(correct)
        except (ValueError, TypeError):
            return False
    elif q_type == "number":
        try:
            tolerance = question.get("tolerance", 0)
            return abs(float(answer) - float(correct)) <= tolerance
        except (ValueError, TypeError):
            return False
    elif q_type == "text":
        if not answer or not correct:
            return False
        answer_str = str(answer).strip().lower()
        if isinstance(correct, list):
            return any(answer_str == c.strip().lower() for c in correct)
        return answer_str == str(correct).strip().lower()
    return False


@dataclass
class QuizAnswer:
    player_id: str
    answer: object  # int for MC, float for number, str for text
    correct: bool
    time_taken: float
    points_earned: float


@dataclass
class ActiveQuiz:
    question: dict
    sent_at: float
    answers: Dict[str, QuizAnswer] = field(default_factory=dict)
    closed: bool = False


@dataclass
class CompanionPlayer:
    id: str
    name: str
    quarter_idx: int
    is_gm: bool = False
    block_name: str = ""  # Personal quarter/block name within district
    # Phase 1 assets
    projektchef: Optional[dict] = None
    projects: List[dict] = field(default_factory=list)
    q_krav: int = 0
    h_krav: int = 0
    riskbuffertar: int = 0
    q_achieved: int = 0  # Q points earned (PC, AC, suppliers)
    h_achieved: int = 0  # H points earned
    rb_spent_q: int = 0
    rb_spent_h: int = 0
    rb_spent_t: int = 0
    mark_expansions: int = 0
    dev_cost_total: float = 0.0  # Cumulative dev cost (never decreases)
    eget_kapital: float = 0.0
    abt_budget: float = 0.0
    # Phase 2 assets
    arbetschef: Optional[dict] = None
    pl_choices: Dict[str, dict] = field(default_factory=dict)  # step_id -> {name, niva, q, h, t, erf, cost}
    pl_events: Dict[str, dict] = field(default_factory=dict)  # step_id -> {q, h, abt} event card effects
    # Phase 3 assets - per byggfas (1-8)
    gf_phases: Dict[str, dict] = field(default_factory=dict)  # "1"-"8" -> {q, h, t, abt}
    gf_kons_q: int = 0   # Konsekvenskort ABT for kvalitet
    gf_kons_h: int = 0   # Konsekvenskort ABT for hållbarhet
    gf_kons_t: int = 0   # Konsekvenskort ABT for tid
    gf_kons_q_adj: int = 0   # Konsekvenskort Q-adjustment (lowers requirement)
    gf_kons_h_adj: int = 0   # Konsekvenskort H-adjustment (lowers requirement)
    gf_kons_t_q: int = 0    # Q-påverkan från tidskort (sänker Q)
    gf_kons_t_h: int = 0    # H-påverkan från tidskort (sänker H)
    gf_garanti_abt: int = 0  # Garantibesiktning ABT
    gf_brf_rorlig: float = 0.0  # Rörlig intäkt BRF
    gf_moderbolagslan: float = 0.0  # Moderbolagslån (legacy)
    gf_moderbolagslan_antal: int = 0  # Number of moderbolagslån
    # Phase 4 assets
    fastighetschef: Optional[dict] = None  # FC
    fastighetsskotare: Optional[dict] = None  # FS
    fastigheter: List[dict] = field(default_factory=list)  # Projects converted to properties
    # Each fastighet: {id, namn, typ, bta, anskaffning, energiklass, marknadsvarde,
    #                   events: [{kvartal, ek, energi}], sold: bool, kopeskilling: float}
    f4_yield_bostader: float = 4.0  # Current yield % for bostäder
    f4_yield_kommersiellt: float = 5.0  # Current yield % for kommersiellt
    f4_quarters: Dict[str, dict] = field(default_factory=dict)  # "1"-"4" -> {ek_change}
    f4_personal_cost: float = 0.0  # Per-quarter FC+FS salary
    f4_final_score: float = 0.0
    f4_market_bought: Dict[str, int] = field(default_factory=dict)  # step_id -> num bought this quarter
    steps_done: Dict[str, bool] = field(default_factory=dict)
    prev_profit_score: float = 0.0  # Previous projected score for trend arrow

    def step_auto_done(self, step_id: str) -> bool:
        """Check if player is auto-done with a given step based on data."""
        if step_id == "choose_pc":
            return self.projektchef is not None
        elif step_id == "choose_ac":
            return self.arbetschef is not None
        elif step_id == "projects":
            return len(self.projects) > 0
        elif step_id == "planning":
            return len(self.pl_choices) >= 13
        elif step_id == "gf_abt_ek":
            return self.eget_kapital != 0
        elif step_id == "f4_forbered":
            return len(self.fastigheter or []) > 0
        return False

    def step_done(self, step_id: str) -> bool:
        """Check if player is done with a given step (auto or manual)."""
        if self.step_auto_done(step_id):
            return True
        return self.steps_done.get(step_id, False)

    def step_has_data(self, step_id: str) -> bool:
        """Check if player has some data for a step (but not necessarily done)."""
        if step_id == "choose_pc":
            return self.projektchef is not None
        elif step_id == "projects":
            return len(self.projects) > 0
        elif step_id == "namndbeslut":
            return len(self.projects) > 0
        elif step_id == "choose_ac":
            return self.arbetschef is not None
        elif step_id == "planning":
            return len(self.pl_choices) > 0
        elif step_id == "gf_byggfaser":
            return len(self.gf_phases) > 0
        elif step_id == "gf_konsekvens":
            return self.gf_kons_q != 0 or self.gf_kons_h != 0 or self.gf_kons_t != 0
        elif step_id == "gf_garanti":
            return self.gf_garanti_abt != 0
        elif step_id == "gf_abt_ek":
            return self.eget_kapital != 0
        elif step_id == "f4_forbered":
            return len(self.fastigheter or []) > 0
        elif step_id in ("f4_q1", "f4_q2", "f4_q3", "f4_q4"):
            return len(self.fastigheter or []) > 0
        elif step_id == "f4_slut":
            return self.f4_final_score != 0
        return False

    @property
    def _calc_tb(self) -> float:
        """Calculate TB (Täckningsbidrag) = anskaffning - kostnader - ABT-förbrukning."""
        total_ansk = sum(p.get("anskaffning", 0) for p in self.projects)
        total_kost = sum(p.get("kostnad", 0) for p in self.projects) + 15 + self.mark_expansions * 5
        abt_used = 0
        for ch in (self.pl_choices or {}).values():
            abt_used += ch.get("cost", 0) if isinstance(ch, dict) else 0
        for ev in (self.pl_events or {}).values():
            abt_used += ev.get("abt", 0) if isinstance(ev, dict) else 0
        for gf in (self.gf_phases or {}).values():
            abt_used += gf.get("abt", 0) if isinstance(gf, dict) else 0
        abt_used += getattr(self, 'gf_kons_q', 0) + getattr(self, 'gf_kons_h', 0) + getattr(self, 'gf_kons_t', 0) + getattr(self, 'gf_garanti_abt', 0)
        return total_ansk - total_kost - abt_used

    @property
    def profit_score(self) -> float:
        """Projected final score. Becomes more accurate each phase.
        Score = (0.30 × FV + EK_factor × EK) / ägd_BTA × 1000 + TB
        Phase 1: estimate from anskaffning + Q/H-risk bonus
        Phase 2-3: add TB projection + planning quality
        Phase 4+: actual FV from yield + real EK + real TB"""
        fasts = self.fastigheter or []
        owned = [f for f in fasts if not f.get("sold")]

        if owned:
            # Phase 4+: use actual fastighetsvärde
            fv = sum(f.get("marknadsvarde", f.get("anskaffning", 0)) for f in owned)
            bta = sum(f.get("bta", 0) for f in owned)
            ek = self.eget_kapital
            tb = self._calc_tb
        elif self.projects:
            # Phase 1-3: project-based estimate
            fv = sum(p.get("marknadsvarde", p.get("anskaffning", 0)) for p in self.projects)
            bta = sum(p.get("bta", 0) for p in self.projects)
            ek = self.eget_kapital
            tb = self._calc_tb if self.pl_choices else 0
            # Phase 1 bonus: lower Q/H = less risk
            if not self.pl_choices:
                risk_bonus = max(0, 20 - self.q_krav - self.h_krav) * 2
                pc_bonus = 0
                if self.projektchef:
                    pc_bonus = self.projektchef.get("lindring", 0) * 2
                    pc_bonus += self.projektchef.get("namnd_bonus", 0) * 3
                tb = risk_bonus + pc_bonus + self.riskbuffertar * 3
        else:
            return 0

        if bta > 0:
            ek_factor = 0.10 if ek >= 0 else 2.00
            return round((0.30 * fv + ek_factor * ek) / bta * 1000 + tb, 1)
        return round(tb, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quarter_idx": self.quarter_idx,
            "is_gm": self.is_gm,
            "block_name": self.block_name,
            "projektchef": self.projektchef,
            "projects": self.projects,
            "q_krav": self.q_krav,
            "h_krav": self.h_krav,
            "riskbuffertar": self.riskbuffertar,
            "q_achieved": self.q_achieved,
            "h_achieved": self.h_achieved,
            "rb_spent_q": self.rb_spent_q,
            "rb_spent_h": self.rb_spent_h,
            "rb_spent_t": self.rb_spent_t,
            "mark_expansions": self.mark_expansions,
            "dev_cost_total": round(self.dev_cost_total, 1),
            "eget_kapital": round(self.eget_kapital, 1),
            "abt_budget": round(self.abt_budget, 1),
            "arbetschef": self.arbetschef,
            "pl_choices": self.pl_choices,
            "pl_events": self.pl_events,
            "gf_phases": self.gf_phases,
            "gf_kons_q": self.gf_kons_q,
            "gf_kons_h": self.gf_kons_h,
            "gf_kons_t": self.gf_kons_t,
            "gf_kons_q_adj": self.gf_kons_q_adj,
            "gf_kons_h_adj": self.gf_kons_h_adj,
            "gf_kons_t_q": self.gf_kons_t_q,
            "gf_kons_t_h": self.gf_kons_t_h,
            "gf_garanti_abt": self.gf_garanti_abt,
            "gf_brf_rorlig": round(self.gf_brf_rorlig, 1),
            "gf_moderbolagslan": round(self.gf_moderbolagslan, 1),
            "gf_moderbolagslan_antal": self.gf_moderbolagslan_antal,
            "fastighetschef": self.fastighetschef,
            "fastighetsskotare": self.fastighetsskotare,
            "fastigheter": self.fastigheter,
            "f4_yield_bostader": self.f4_yield_bostader,
            "f4_yield_kommersiellt": self.f4_yield_kommersiellt,
            "f4_quarters": self.f4_quarters,
            "f4_final_score": round(self.f4_final_score, 1),
            "f4_market_bought": self.f4_market_bought,
            "steps_done": self.steps_done,
            "prev_profit_score": round(self.prev_profit_score, 1),
            "profit_score": self.profit_score,
        }


class GameLogger:
    """Logs game events to a JSON file for serious (analytics) games."""

    def __init__(self, room_code: str, room_config: dict):
        self.room_code = room_code
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "game_logs")
        os.makedirs(log_dir, exist_ok=True)
        self.filepath = os.path.join(log_dir, f"{room_code}_{ts}.json")
        self.events: list = []
        self.log("room_created", None, room_config)

    def log(self, event_type: str, player_id: Optional[str], data: dict):
        self.events.append({
            "ts": time.time(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": event_type,
            "player_id": player_id,
            "data": data,
        })
        if len(self.events) % 10 == 0:
            self.flush()

    def flush(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"events": self.events}, f, ensure_ascii=False, indent=1)
        except Exception as e:
            print(f"GameLogger flush error: {e}")

    def snapshot(self, room):
        """Take full state snapshot of all players."""
        for p in room.players.values():
            if not p.is_gm:
                self.log("state_snapshot", p.id, p.to_dict())
        self.flush()

    def finalize(self, room):
        """Write final summary at game end."""
        summary = {
            "num_players": sum(1 for p in room.players.values() if not p.is_gm),
            "final_scores": {
                p.id: {"name": p.name, "score": p.profit_score}
                for p in room.players.values() if not p.is_gm
            },
        }
        self.log("game_finished", None, summary)
        self.flush()


@dataclass
class CompanionRoom:
    code: str  # GM session code
    gm_id: str
    num_quarters: int
    quarter_names: List[str] = field(default_factory=list)
    quarter_codes: List[str] = field(default_factory=list)  # one code per quarter
    players: Dict[str, CompanionPlayer] = field(default_factory=dict)
    phase_idx: int = 0
    step_idx: int = 0
    game_mode: str = "test"  # "test" or "serious"
    logger: Optional[object] = None  # GameLogger instance for serious games
    f4_omvarldskort: Dict[str, dict] = field(default_factory=dict)  # step_id -> drawn omvärldskort
    # Quiz state
    quiz_questions: List[dict] = field(default_factory=list)
    quiz_active: Optional[ActiveQuiz] = None
    quiz_history: List[dict] = field(default_factory=list)
    quiz_scores: Dict[str, float] = field(default_factory=dict)
    quiz_correct_counts: Dict[str, int] = field(default_factory=dict)
    quiz_answer_times: Dict[str, List[float]] = field(default_factory=dict)
    quiz_count_in_score: bool = False
    quiz_questions_sent: List[str] = field(default_factory=list)
    game_finalized: bool = False

    @property
    def current_phase(self):
        if self.phase_idx < len(PHASES):
            return PHASES[self.phase_idx]
        return None

    @property
    def current_step(self):
        phase = self.current_phase
        if phase and self.step_idx < len(phase["steps"]):
            return phase["steps"][self.step_idx]
        return None

    def quarter_summary(self, quarter_idx: int) -> dict:
        qp = [p for p in self.players.values() if p.quarter_idx == quarter_idx and not p.is_gm]
        total_projects = sum(len(p.projects) for p in qp)
        total_bta = sum(sum(pr.get("bta", 0) for pr in p.projects) for p in qp)
        avg_q = round(sum(p.q_krav for p in qp) / max(len(qp), 1), 1)
        avg_h = round(sum(p.h_krav for p in qp) / max(len(qp), 1), 1)
        return {
            "quarter_idx": quarter_idx,
            "name": self.quarter_names[quarter_idx] if quarter_idx < len(self.quarter_names) else f"Kvarter {quarter_idx + 1}",
            "code": self.quarter_codes[quarter_idx] if quarter_idx < len(self.quarter_codes) else "",
            "num_players": len(qp),
            "total_projects": total_projects,
            "total_bta": total_bta,
            "avg_q_krav": avg_q,
            "avg_h_krav": avg_h,
            "players": [self._player_with_status(p) for p in qp],
        }

    def _player_with_status(self, p: CompanionPlayer) -> dict:
        d = p.to_dict()
        step = self.current_step
        step_id = step["id"] if step else None
        d["step_done"] = p.step_done(step_id) if step_id else False
        d["step_has_data"] = p.step_has_data(step_id) if step_id else False
        return d

    @staticmethod
    def _tier(score: float) -> str:
        """Return tier label based on score thresholds."""
        if score > 80:
            return "dominant"
        elif score > 60:
            return "stark"
        elif score >= 30:
            return "medel"
        else:
            return "risk"

    def quiz_leaderboard(self) -> dict:
        """Quiz-specific leaderboard."""
        all_p = [p for p in self.players.values() if not p.is_gm]
        entries = []
        for p in all_p:
            q_score = self.quiz_scores.get(p.id, 0)
            correct = self.quiz_correct_counts.get(p.id, 0)
            times = self.quiz_answer_times.get(p.id, [])
            avg_time = round(sum(times) / len(times), 1) if times else 0
            q_name = self.quarter_names[p.quarter_idx] if p.quarter_idx < len(self.quarter_names) else "?"
            entries.append({
                "id": p.id,
                "name": p.name,
                "block_name": p.block_name,
                "district": q_name,
                "quiz_points": round(q_score, 1),
                "correct_answers": correct,
                "total_answered": len(times),
                "avg_time": avg_time,
            })
        entries.sort(key=lambda e: e["quiz_points"], reverse=True)
        for i, e in enumerate(entries):
            e["rank"] = i + 1
        return {
            "players": entries,
            "total_questions_sent": len(self.quiz_questions_sent),
            "quiz_count_in_score": self.quiz_count_in_score,
        }

    def leaderboard(self) -> dict:
        """All players and districts ranked by profit_score."""
        all_p = [p for p in self.players.values() if not p.is_gm and p.projects]
        ranked = sorted(all_p, key=lambda p: p.profit_score + (self.quiz_scores.get(p.id, 0) if self.quiz_count_in_score else 0), reverse=True)
        total_players = len(ranked)
        players = []
        for i, p in enumerate(ranked):
            q_name = self.quarter_names[p.quarter_idx] if p.quarter_idx < len(self.quarter_names) else "?"
            score = p.profit_score + (self.quiz_scores.get(p.id, 0) if self.quiz_count_in_score else 0)
            players.append({
                "rank": i + 1,
                "total_players": total_players,
                "tier": self._tier(score),
                "id": p.id,
                "name": p.name,
                "block_name": p.block_name,
                "quarter": q_name,
                "district": q_name,
                "profit_score": score,
                "prev_profit_score": round(p.prev_profit_score, 1),
                "num_projects": len(p.projects),
                "total_bta": sum(pr.get("bta", 0) for pr in p.projects),
                "q_krav": p.q_krav,
                "h_krav": p.h_krav,
                "riskbuffertar": p.riskbuffertar,
                "eget_kapital": round(p.eget_kapital, 1),
                "pc_name": p.projektchef.get("namn", "") if p.projektchef else "\u2014",
            })

        # District ranking (average profit_score of players)
        districts = []
        for i in range(self.num_quarters):
            qp = [p for p in self.players.values() if p.quarter_idx == i and not p.is_gm and p.projects]
            if not qp:
                continue
            avg_score = round(sum(p.profit_score for p in qp) / len(qp), 1)
            name = self.quarter_names[i] if i < len(self.quarter_names) else f"Stadsdel {i+1}"
            districts.append({
                "name": name,
                "avg_score": avg_score,
                "district_tier": self._tier(avg_score),
                "num_players": len(qp),
                "quarters": [name],
            })
        districts.sort(key=lambda d: d["avg_score"], reverse=True)
        total_districts = len(districts)
        for i, d in enumerate(districts):
            d["rank"] = i + 1
            d["district_rank"] = i + 1
            d["total_districts"] = total_districts

        return {"players": players, "districts": districts, "total_players": total_players, "total_districts": total_districts}

    def to_dict(self):
        phase = self.current_phase
        step = self.current_step
        return {
            "code": self.code,
            "num_quarters": self.num_quarters,
            "quarter_names": self.quarter_names,
            "quarter_codes": self.quarter_codes,
            "phase": phase["id"] if phase else None,
            "phase_name": phase["name"] if phase else None,
            "step": step["id"] if step else None,
            "step_name": step["name"] if step else None,
            "step_help": step.get("help", "") if step else "",
            "phase_idx": self.phase_idx,
            "step_idx": self.step_idx,
            "quarters": [self.quarter_summary(i) for i in range(self.num_quarters)],
            "game_mode": self.game_mode,
            "log_event_count": len(self.logger.events) if self.logger else 0,
            "f4_omvarldskort": self.f4_omvarldskort,
            "game_finalized": self.game_finalized,
            # Quiz state for GM
            "quiz_count_in_score": self.quiz_count_in_score,
            "quiz_scores": {pid: round(s, 1) for pid, s in self.quiz_scores.items()},
            "quiz_questions_sent": self.quiz_questions_sent,
            "quiz_questions": self.quiz_questions,
            "quiz_history_count": len(self.quiz_history),
            "quiz_active": {
                "question": {k: v for k, v in self.quiz_active.question.items()},
                "sent_at": self.quiz_active.sent_at,
                "closed": self.quiz_active.closed,
                "answers": {
                    pid: {
                        "player_name": self.players[pid].name if pid in self.players else "?",
                        "correct": a.correct,
                        "time_taken": round(a.time_taken, 1),
                        "points_earned": round(a.points_earned, 1),
                        "answer": a.answer,
                    }
                    for pid, a in self.quiz_active.answers.items()
                },
                "num_eligible": sum(1 for p in self.players.values() if not p.is_gm),
            } if self.quiz_active else None,
        }

    def player_state(self, player_id: str) -> dict:
        """State for a specific player."""
        player = self.players.get(player_id)
        if not player:
            return {}
        phase = self.current_phase
        step = self.current_step
        return {
            "code": self.code,
            "phase": phase["id"] if phase else None,
            "phase_name": phase["name"] if phase else None,
            "step": step["id"] if step else None,
            "step_name": step["name"] if step else None,
            "step_help": step.get("help", "") if step else "",
            "player": player.to_dict(),
            "f4_omvarldskort": self.f4_omvarldskort,
            "game_finalized": self.game_finalized,
            "quiz_score": round(self.quiz_scores.get(player_id, 0), 1),
            "quiz_count_in_score": self.quiz_count_in_score,
            "quiz_active_question": (
                {k: v for k, v in self.quiz_active.question.items() if k != "correct"}
                if self.quiz_active and not self.quiz_active.closed and player_id not in self.quiz_active.answers
                else None
            ),
        }


# ── Connection & Room Manager ──

class CompanionManager:
    def __init__(self):
        self.rooms: Dict[str, CompanionRoom] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}  # code -> {player_id -> ws}

    def create_room(self, num_quarters: int, game_mode: str = "test",
                    quarter_names: list = None, quarter_codes: list = None,
                    quiz_questions: list = None) -> tuple:
        """Returns (room, gm_id)."""
        import random
        code = uuid.uuid4().hex[:6].upper()
        gm_id = uuid.uuid4().hex[:8]
        # Use provided names or generate random ones
        if quarter_names and len(quarter_names) >= num_quarters:
            names = list(quarter_names[:num_quarters])
        else:
            names = random.sample(DISTRICT_NAMES, min(num_quarters, len(DISTRICT_NAMES)))
            if num_quarters > len(DISTRICT_NAMES):
                names += [f"Stadsdel {i+1}" for i in range(len(DISTRICT_NAMES), num_quarters)]
        # Use provided codes or generate unique codes per quarter
        if quarter_codes and len(quarter_codes) >= num_quarters:
            # Validate no collisions with existing rooms
            existing_codes = {qc for r in self.rooms.values() for qc in r.quarter_codes}
            if not any(qc in existing_codes for qc in quarter_codes[:num_quarters]):
                q_codes = list(quarter_codes[:num_quarters])
            else:
                q_codes = []
                for _ in range(num_quarters):
                    qc = uuid.uuid4().hex[:4].upper()
                    q_codes.append(qc)
        else:
            q_codes = []
            for _ in range(num_quarters):
                qc = uuid.uuid4().hex[:4].upper()
                q_codes.append(qc)
        room = CompanionRoom(code=code, gm_id=gm_id, num_quarters=num_quarters,
                             quarter_names=names, quarter_codes=q_codes,
                             game_mode=game_mode)
        # Set up logger for serious games
        if game_mode == "serious":
            room.logger = GameLogger(code, {
                "num_quarters": num_quarters,
                "quarter_names": names,
                "game_mode": game_mode,
            })
        # Load quiz questions: prefer provided list (from setup), else load from file
        if quiz_questions is not None:
            room.quiz_questions = list(quiz_questions)
        else:
            quiz_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "data", "quiz_questions.json")
            try:
                with open(quiz_path, "r", encoding="utf-8") as f:
                    qdata = json.load(f)
                    room.quiz_questions = qdata.get("questions", [])
                    default_tl = qdata.get("default_time_limit", 30)
                    default_pts = qdata.get("default_points", 100)
                    for q in room.quiz_questions:
                        q.setdefault("time_limit", default_tl)
                        q.setdefault("points", default_pts)
            except Exception:
                room.quiz_questions = []

        gm = CompanionPlayer(id=gm_id, name="Game Master", quarter_idx=-1, is_gm=True)
        room.players[gm_id] = gm
        self.rooms[code] = room
        return room, gm_id

    def find_room_by_quarter_code(self, quarter_code: str) -> Optional[tuple]:
        """Find room and quarter_idx by quarter code. Returns (room, quarter_idx) or None."""
        quarter_code = quarter_code.upper()
        for room in self.rooms.values():
            for i, qc in enumerate(room.quarter_codes):
                if qc == quarter_code:
                    return room, i
        return None

    def join_room(self, code: str, name: str, quarter_idx: int) -> Optional[tuple]:
        """Returns (room, player_id) or None."""
        room = self.rooms.get(code)
        if not room:
            return None
        # Check quarter capacity
        quarter_players = [p for p in room.players.values() if p.quarter_idx == quarter_idx and not p.is_gm]
        if len(quarter_players) >= 4:
            return None
        import random
        player_id = uuid.uuid4().hex[:8]
        # Assign a random block name
        used_blocks = {p.block_name for p in room.players.values() if p.block_name}
        available_blocks = [b for b in BLOCK_NAMES if b not in used_blocks]
        block = random.choice(available_blocks) if available_blocks else f"Kvarter {len(room.players)}"
        player = CompanionPlayer(id=player_id, name=name, quarter_idx=quarter_idx, block_name=block)
        room.players[player_id] = player
        # Log player join for serious games
        if room.game_mode == "serious" and room.logger:
            q_name = room.quarter_names[quarter_idx] if quarter_idx < len(room.quarter_names) else f"Kvarter {quarter_idx + 1}"
            room.logger.log("player_joined", player_id, {"name": name, "quarter": q_name})
        return room, player_id

    def get_room(self, code: str) -> Optional[CompanionRoom]:
        return self.rooms.get(code)

    # ── WebSocket ──

    async def connect(self, code: str, player_id: str, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(code, {})[player_id] = ws

    def disconnect(self, code: str, player_id: str):
        conns = self.connections.get(code, {})
        conns.pop(player_id, None)

    async def send_to(self, code: str, player_id: str, data: dict):
        ws = self.connections.get(code, {}).get(player_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(code, player_id)

    async def broadcast(self, code: str, data: dict):
        conns = self.connections.get(code, {})
        for pid, ws in list(conns.items()):
            try:
                await ws.send_json(data)
            except Exception:
                conns.pop(pid, None)

    async def broadcast_state(self, room: CompanionRoom):
        """Send personalized state to each player, full state to GM."""
        conns = self.connections.get(room.code, {})
        for pid, ws in list(conns.items()):
            player = room.players.get(pid)
            if not player:
                continue
            try:
                if player.is_gm:
                    await ws.send_json({"type": "state", "state": room.to_dict()})
                else:
                    await ws.send_json({"type": "state", "state": room.player_state(pid)})
            except Exception as exc:
                import traceback
                print(f"BROADCAST ERROR for {pid}: {exc}")
                traceback.print_exc()
                conns.pop(pid, None)

    async def handle_message(self, code: str, player_id: str, data: dict):
        room = self.rooms.get(code)
        if not room:
            return
        player = room.players.get(player_id)
        if not player:
            return

        msg_type = data.get("type")

        if msg_type == "advance_step" and player.is_gm:
            # Save current profit_score as prev for trend arrows
            for p in room.players.values():
                if not p.is_gm:
                    p.prev_profit_score = p.profit_score
            old_phase, old_step = room.phase_idx, room.step_idx
            phase = room.current_phase
            if phase and room.step_idx < len(phase["steps"]) - 1:
                room.step_idx += 1
            elif room.phase_idx < len(PHASES) - 1:
                room.phase_idx += 1
                room.step_idx = 0
            # Log step advance + snapshot for serious games
            if room.game_mode == "serious" and room.logger:
                new_step = room.current_step
                room.logger.log("step_advanced", None, {
                    "from_phase": old_phase, "from_step": old_step,
                    "to_phase": room.phase_idx, "to_step": room.step_idx,
                    "step_name": new_step["name"] if new_step else None,
                })
                room.logger.snapshot(room)
                # Check if this is the final step — finalize
                if room.phase_idx == len(PHASES) - 1:
                    last_phase = PHASES[-1]
                    if room.step_idx == len(last_phase["steps"]) - 1:
                        room.logger.finalize(room)
            await self.broadcast_state(room)

        elif msg_type == "prev_step" and player.is_gm:
            # Save current profit_score as prev for trend arrows
            for p in room.players.values():
                if not p.is_gm:
                    p.prev_profit_score = p.profit_score
            if room.step_idx > 0:
                room.step_idx -= 1
            elif room.phase_idx > 0:
                room.phase_idx -= 1
                phase = PHASES[room.phase_idx]
                room.step_idx = len(phase["steps"]) - 1
            await self.broadcast_state(room)

        elif msg_type in ("gm_reset", "reset_room") and player.is_gm:
            # Delete room entirely
            code = room.code
            if code in self.rooms:
                del self.rooms[code]
            # Close all WebSocket connections for this room
            for pid, ws_set in list(self.connections.get(code, {}).items()):
                for ws in list(ws_set):
                    try:
                        await ws.close(1000, "Session reset by GM")
                    except Exception:
                        pass
            self.connections.pop(code, None)
            return  # Don't broadcast — room is gone

        elif msg_type == "finalize_game" and player.is_gm:
            # Create logger if not exists (test mode converting to save)
            if not room.logger:
                room.logger = GameLogger(room.code, {
                    "num_quarters": room.num_quarters,
                    "quarter_names": room.quarter_names,
                    "game_mode": room.game_mode or "test",
                })
            # Snapshot all players, then finalize
            room.logger.snapshot(room)
            room.logger.finalize(room)
            room.game_finalized = True
            await self.broadcast_state(room)

        elif msg_type == "rename_quarter" and player.is_gm:
            idx = data.get("quarter_idx")
            new_name = data.get("name", "").strip()
            if idx is not None and 0 <= idx < room.num_quarters and new_name:
                room.quarter_names[idx] = new_name
            await self.broadcast_state(room)

        elif msg_type == "rename_block" and not player.is_gm:
            new_name = data.get("name", "").strip()
            if new_name:
                player.block_name = new_name
            await self.broadcast_state(room)

        elif msg_type == "update_assets" and not player.is_gm:
            assets = data.get("assets", {})
            if "projektchef" in assets:
                player.projektchef = assets["projektchef"]
            if "projects" in assets:
                player.projects = assets["projects"]
                # Dev cost only goes up — track cumulative
                current_dev = sum(p.get("kostnad", 0) for p in player.projects)
                player.dev_cost_total = max(player.dev_cost_total, current_dev)
            if "q_krav" in assets:
                player.q_krav = int(assets["q_krav"])
            if "h_krav" in assets:
                player.h_krav = int(assets["h_krav"])
            if "riskbuffertar" in assets:
                player.riskbuffertar = int(assets["riskbuffertar"])
            if "q_achieved" in assets:
                player.q_achieved = int(assets["q_achieved"])
            if "h_achieved" in assets:
                player.h_achieved = int(assets["h_achieved"])
            if "rb_spent_q" in assets:
                player.rb_spent_q = int(assets["rb_spent_q"])
            if "rb_spent_h" in assets:
                player.rb_spent_h = int(assets["rb_spent_h"])
            if "rb_spent_t" in assets:
                player.rb_spent_t = int(assets["rb_spent_t"])
            if "mark_expansions" in assets:
                player.mark_expansions = int(assets["mark_expansions"])
            if "eget_kapital" in assets:
                player.eget_kapital = float(assets["eget_kapital"])
            if "abt_budget" in assets:
                player.abt_budget = float(assets["abt_budget"])
            if "arbetschef" in assets:
                player.arbetschef = assets["arbetschef"]
            if "pl_choices" in assets:
                player.pl_choices = assets["pl_choices"]
            if "pl_events" in assets:
                player.pl_events = assets["pl_events"]
            if "gf_phases" in assets:
                player.gf_phases = assets["gf_phases"]
            if "gf_kons_q" in assets:
                player.gf_kons_q = int(assets["gf_kons_q"])
            if "gf_kons_h" in assets:
                player.gf_kons_h = int(assets["gf_kons_h"])
            if "gf_kons_t" in assets:
                player.gf_kons_t = int(assets["gf_kons_t"])
            if "gf_kons_q_adj" in assets:
                player.gf_kons_q_adj = int(assets["gf_kons_q_adj"])
            if "gf_kons_h_adj" in assets:
                player.gf_kons_h_adj = int(assets["gf_kons_h_adj"])
            if "gf_kons_t_q" in assets:
                player.gf_kons_t_q = int(assets["gf_kons_t_q"])
            if "gf_kons_t_h" in assets:
                player.gf_kons_t_h = int(assets["gf_kons_t_h"])
            if "gf_garanti_abt" in assets:
                player.gf_garanti_abt = int(assets["gf_garanti_abt"])
            if "gf_brf_rorlig" in assets:
                player.gf_brf_rorlig = float(assets["gf_brf_rorlig"])
            if "gf_moderbolagslan" in assets:
                player.gf_moderbolagslan = float(assets["gf_moderbolagslan"])
            if "gf_moderbolagslan_antal" in assets:
                player.gf_moderbolagslan_antal = int(assets["gf_moderbolagslan_antal"])
            if "fastighetschef" in assets:
                player.fastighetschef = assets["fastighetschef"]
            if "fastighetsskotare" in assets:
                player.fastighetsskotare = assets["fastighetsskotare"]
            if "fastigheter" in assets:
                player.fastigheter = assets["fastigheter"]
            if "f4_yield_bostader" in assets:
                player.f4_yield_bostader = float(assets["f4_yield_bostader"])
            if "f4_yield_kommersiellt" in assets:
                player.f4_yield_kommersiellt = float(assets["f4_yield_kommersiellt"])
            if "f4_quarters" in assets:
                player.f4_quarters = assets["f4_quarters"]
            if "f4_final_score" in assets:
                player.f4_final_score = float(assets["f4_final_score"])
            if "f4_market_bought" in assets:
                player.f4_market_bought = assets["f4_market_bought"]
            # Log asset changes for serious games
            if room.game_mode == "serious" and room.logger:
                step = room.current_step
                room.logger.log("asset_update", player_id, {
                    "step": step["id"] if step else None,
                    "changes": list(assets.keys()),
                    "profit_score": player.profit_score,
                })
            # Update GM dashboard
            await self.broadcast_state(room)

        elif msg_type == "mark_done" and not player.is_gm:
            step = data.get("step", "")
            if step:
                player.steps_done[step] = True
            await self.broadcast_state(room)

        elif msg_type == "unmark_done" and not player.is_gm:
            step = data.get("step", "")
            if step and step in player.steps_done:
                del player.steps_done[step]
            await self.broadcast_state(room)

        elif msg_type == "draw_omvarld" and player.is_gm:
            # GM draws omvärldskort for a given step
            step_id = data.get("step_id")
            card = data.get("card")
            if step_id and card:
                room.f4_omvarldskort[step_id] = card
            await self.broadcast_state(room)

        elif msg_type == "get_state":
            if player.is_gm:
                await self.send_to(code, player_id, {"type": "state", "state": room.to_dict()})
            else:
                await self.send_to(code, player_id, {"type": "state", "state": room.player_state(player_id)})

        # ── Quiz handlers ──

        elif msg_type == "quiz_send" and player.is_gm:
            question_id = data.get("question_id")
            if room.quiz_active:
                return  # Already a question active
            question = next((q for q in room.quiz_questions if q["id"] == question_id), None)
            if not question:
                return
            room.quiz_active = ActiveQuiz(question=question, sent_at=time.time())
            room.quiz_questions_sent.append(question_id)
            # Send question to all players (strip correct answer)
            safe_q = {k: v for k, v in question.items() if k not in ("correct", "tolerance")}
            safe_q["time_limit"] = question.get("time_limit", 30)
            safe_q["points"] = question.get("points", 100)
            await self.broadcast(code, {"type": "quiz_question", "question": safe_q})
            await self.broadcast_state(room)

        elif msg_type == "quiz_answer" and not player.is_gm:
            if not room.quiz_active or room.quiz_active.closed:
                return
            if player_id in room.quiz_active.answers:
                return  # Already answered
            answer = data.get("answer")
            time_taken = time.time() - room.quiz_active.sent_at
            question = room.quiz_active.question
            correct = _check_answer(question, answer)
            time_limit = question.get("time_limit", 30)
            base_points = question.get("points", 100)
            points = _quiz_points(base_points, time_taken, time_limit) if correct else 0
            qa = QuizAnswer(player_id=player_id, answer=answer, correct=correct,
                            time_taken=time_taken, points_earned=points)
            room.quiz_active.answers[player_id] = qa
            # Update cumulative scores
            room.quiz_scores[player_id] = room.quiz_scores.get(player_id, 0) + points
            room.quiz_correct_counts[player_id] = room.quiz_correct_counts.get(player_id, 0) + (1 if correct else 0)
            room.quiz_answer_times.setdefault(player_id, []).append(time_taken)
            # Send feedback to answering player (no correct answer revealed yet)
            await self.send_to(code, player_id, {
                "type": "quiz_feedback",
                "correct": correct,
                "points_earned": round(points, 1),
                "time_taken": round(time_taken, 1),
            })
            # Update GM with results
            await self.broadcast_state(room)

        elif msg_type == "quiz_close" and player.is_gm:
            if not room.quiz_active:
                return
            room.quiz_active.closed = True
            question = room.quiz_active.question
            # Archive to history
            room.quiz_history.append({
                "question_id": question["id"],
                "question_text": question["text"],
                "correct_answer": question.get("correct"),
                "num_answered": len(room.quiz_active.answers),
                "num_correct": sum(1 for a in room.quiz_active.answers.values() if a.correct),
            })
            # Broadcast correct answer to all players
            correct_answer = question.get("correct")
            correct_display = correct_answer
            if question.get("type") == "multiple_choice" and isinstance(correct_answer, int):
                options = question.get("options", [])
                correct_display = options[correct_answer] if correct_answer < len(options) else correct_answer
            elif isinstance(correct_answer, list):
                correct_display = correct_answer[0] if correct_answer else ""
            await self.broadcast(code, {
                "type": "quiz_closed",
                "correct_answer": correct_display,
                "question_text": question["text"],
            })
            room.quiz_active = None
            await self.broadcast_state(room)

        elif msg_type == "quiz_toggle_score" and player.is_gm:
            room.quiz_count_in_score = not room.quiz_count_in_score
            await self.broadcast_state(room)

        elif msg_type == "quiz_add" and player.is_gm:
            question = data.get("question")
            if question and isinstance(question, dict):
                # Generate ID if not provided
                if not question.get("id"):
                    question["id"] = f"q_{uuid.uuid4().hex[:6]}"
                room.quiz_questions.append(question)
            await self.broadcast_state(room)

        elif msg_type == "quiz_edit" and player.is_gm:
            question_id = data.get("question_id")
            updates = data.get("question", {})
            for i, q in enumerate(room.quiz_questions):
                if q["id"] == question_id:
                    room.quiz_questions[i].update(updates)
                    room.quiz_questions[i]["id"] = question_id  # Prevent ID change
                    break
            await self.broadcast_state(room)

        elif msg_type == "quiz_delete" and player.is_gm:
            question_id = data.get("question_id")
            if question_id not in room.quiz_questions_sent:
                room.quiz_questions = [q for q in room.quiz_questions if q["id"] != question_id]
            await self.broadcast_state(room)

        elif msg_type == "quiz_load_setup" and player.is_gm:
            questions = data.get("questions", [])
            default_tl = data.get("default_time_limit", 30)
            default_pts = data.get("default_points", 100)
            # Merge: keep unsent existing questions, add new ones, skip duplicates by id
            existing_ids = {q["id"] for q in room.quiz_questions}
            for q in questions:
                q.setdefault("time_limit", default_tl)
                q.setdefault("points", default_pts)
                if q.get("id") and q["id"] not in existing_ids:
                    room.quiz_questions.append(q)
                    existing_ids.add(q["id"])
            await self.broadcast_state(room)


companion_manager = CompanionManager()
