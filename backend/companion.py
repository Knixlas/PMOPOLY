"""Companion app — manual mode for physical board game sessions."""
import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket


# ── Phase/step definitions ──

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
    gf_garanti_abt: int = 0  # Garantibesiktning ABT
    # Phase 4 assets
    fastighetschef: Optional[dict] = None  # FC
    fastighetsskotare: Optional[dict] = None  # FS
    fastigheter: List[dict] = field(default_factory=list)  # Projects converted to properties
    # Each fastighet: {id, namn, typ, bta, anskaffning, energiklass, marknadsvarde,
    #                   events: [{kvartal, ek, energi}], sold: bool, kopeskilling: float}
    f4_yield_bostader: float = 4.5  # Current yield % for bostäder
    f4_yield_kommersiellt: float = 5.5  # Current yield % for kommersiellt
    f4_quarters: Dict[str, dict] = field(default_factory=dict)  # "1"-"4" -> {ek_change}
    f4_personal_cost: float = 0.0  # Per-quarter FC+FS salary
    f4_final_score: float = 0.0

    def step_done(self, step_id: str) -> bool:
        """Check if player appears done with a given step."""
        if step_id == "choose_pc":
            return self.projektchef is not None
        elif step_id == "projects":
            return len(self.projects) >= 1
        elif step_id == "namndbeslut":
            return len(self.projects) >= 1  # GM judges manually
        elif step_id == "rb_invest":
            return True  # Always "done" — voluntary step
        elif step_id == "choose_ac":
            return self.arbetschef is not None
        elif step_id == "planning":
            return len(self.pl_choices) > 0
        elif step_id == "planning_summary":
            return True
        elif step_id in ("gf_byggfaser", "gf_konsekvens", "gf_garanti", "gf_abt_ek"):
            return True
        elif step_id in ("f4_forbered", "f4_kvartal", "f4_slut"):
            return True
        return False

    @property
    def profit_score(self) -> float:
        """Estimate profit chance from current assets. Higher = better."""
        if not self.projects:
            return 0
        # Net revenue potential
        total_ansk = sum(p.get("anskaffning", 0) for p in self.projects)
        total_kost = sum(p.get("kostnad", 0) for p in self.projects)
        net = total_ansk - total_kost
        # Lower Q/H = easier to fulfill = less risk (bonus for low values)
        qh_bonus = max(0, 20 - self.q_krav - self.h_krav) * 2
        # Riskbuffertar give safety
        rb_bonus = self.riskbuffertar * 5
        # PC quality
        pc_bonus = 0
        if self.projektchef:
            pc_bonus = self.projektchef.get("kapacitet", 0) * 3
            pc_bonus += self.projektchef.get("namnd_bonus", 0) * 4
        return round(net + qh_bonus + rb_bonus + pc_bonus, 1)

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
            "gf_garanti_abt": self.gf_garanti_abt,
            "fastighetschef": self.fastighetschef,
            "fastighetsskotare": self.fastighetsskotare,
            "fastigheter": self.fastigheter,
            "f4_yield_bostader": self.f4_yield_bostader,
            "f4_yield_kommersiellt": self.f4_yield_kommersiellt,
            "f4_quarters": self.f4_quarters,
            "f4_final_score": round(self.f4_final_score, 1),
            "profit_score": self.profit_score,
        }


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
        d["step_done"] = p.step_done(step["id"]) if step else False
        return d

    def leaderboard(self) -> dict:
        """All players and districts ranked by profit_score."""
        all_p = [p for p in self.players.values() if not p.is_gm and p.projects]
        ranked = sorted(all_p, key=lambda p: p.profit_score, reverse=True)
        players = []
        for i, p in enumerate(ranked):
            q_name = self.quarter_names[p.quarter_idx] if p.quarter_idx < len(self.quarter_names) else "?"
            players.append({
                "rank": i + 1,
                "name": p.name,
                "block_name": p.block_name,
                "district": q_name,
                "profit_score": p.profit_score,
                "num_projects": len(p.projects),
                "total_bta": sum(pr.get("bta", 0) for pr in p.projects),
                "q_krav": p.q_krav,
                "h_krav": p.h_krav,
                "riskbuffertar": p.riskbuffertar,
                "pc_name": p.projektchef.get("namn", "") if p.projektchef else "—",
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
                "num_players": len(qp),
            })
        districts.sort(key=lambda d: d["avg_score"], reverse=True)
        for i, d in enumerate(districts):
            d["rank"] = i + 1

        return {"players": players, "districts": districts}

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
        }


# ── Connection & Room Manager ──

class CompanionManager:
    def __init__(self):
        self.rooms: Dict[str, CompanionRoom] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}  # code -> {player_id -> ws}

    def create_room(self, num_quarters: int) -> tuple:
        """Returns (room, gm_id)."""
        import random
        code = uuid.uuid4().hex[:6].upper()
        gm_id = uuid.uuid4().hex[:8]
        names = random.sample(DISTRICT_NAMES, min(num_quarters, len(DISTRICT_NAMES)))
        if num_quarters > len(DISTRICT_NAMES):
            names += [f"Stadsdel {i+1}" for i in range(len(DISTRICT_NAMES), num_quarters)]
        # Generate unique code per quarter
        q_codes = []
        for _ in range(num_quarters):
            qc = uuid.uuid4().hex[:4].upper()
            q_codes.append(qc)
        room = CompanionRoom(code=code, gm_id=gm_id, num_quarters=num_quarters,
                             quarter_names=names, quarter_codes=q_codes)
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
            except Exception:
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
            phase = room.current_phase
            if phase and room.step_idx < len(phase["steps"]) - 1:
                room.step_idx += 1
            elif room.phase_idx < len(PHASES) - 1:
                room.phase_idx += 1
                room.step_idx = 0
            await self.broadcast_state(room)

        elif msg_type == "prev_step" and player.is_gm:
            if room.step_idx > 0:
                room.step_idx -= 1
            elif room.phase_idx > 0:
                room.phase_idx -= 1
                phase = PHASES[room.phase_idx]
                room.step_idx = len(phase["steps"]) - 1
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
            if "gf_garanti_abt" in assets:
                player.gf_garanti_abt = int(assets["gf_garanti_abt"])
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
            # Update GM dashboard
            await self.broadcast_state(room)

        elif msg_type == "get_state":
            if player.is_gm:
                await self.send_to(code, player_id, {"type": "state", "state": room.to_dict()})
            else:
                await self.send_to(code, player_id, {"type": "state", "state": room.player_state(player_id)})


companion_manager = CompanionManager()
