"""Companion app — manual mode for physical board game sessions."""
import uuid
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from fastapi import WebSocket


# ── Phase/step definitions ──

PHASES = [
    {"id": "phase1", "name": "Fas 1: Projektutveckling", "steps": [
        {"id": "choose_pc", "name": "Välj Projektchef"},
        {"id": "projects", "name": "Projektval & Brädspel"},
        {"id": "namndbeslut", "name": "Nämndbeslut"},
        {"id": "ekonomi", "name": "Ekonomi"},
    ]},
]


QUARTER_NAMES = [
    "Solbacken", "Ekudden", "Björkhagen", "Tallåsen",
    "Sjöängen", "Strandliden", "Bergslund", "Ängslyckan",
    "Åkervallen", "Parkvillan", "Havsutsikten", "Skogsdungen",
    "Klippudden", "Furuliden", "Mossängen", "Kastanjegården",
    "Vintergatans", "Sommarbo", "Strömsborg", "Klockelund",
]


@dataclass
class CompanionPlayer:
    id: str
    name: str
    quarter_idx: int
    is_gm: bool = False
    # Phase 1 assets
    projektchef: Optional[dict] = None
    projects: List[dict] = field(default_factory=list)
    q_krav: int = 4
    h_krav: int = 4
    riskbuffertar: int = 0
    mark_expansions: int = 0
    eget_kapital: float = 0.0
    abt_budget: float = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quarter_idx": self.quarter_idx,
            "is_gm": self.is_gm,
            "projektchef": self.projektchef,
            "projects": self.projects,
            "q_krav": self.q_krav,
            "h_krav": self.h_krav,
            "riskbuffertar": self.riskbuffertar,
            "mark_expansions": self.mark_expansions,
            "eget_kapital": round(self.eget_kapital, 1),
            "abt_budget": round(self.abt_budget, 1),
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
            "players": [p.to_dict() for p in qp],
        }

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
        names = random.sample(QUARTER_NAMES, min(num_quarters, len(QUARTER_NAMES)))
        if num_quarters > len(QUARTER_NAMES):
            names += [f"Kvarter {i+1}" for i in range(len(QUARTER_NAMES), num_quarters)]
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
        player_id = uuid.uuid4().hex[:8]
        player = CompanionPlayer(id=player_id, name=name, quarter_idx=quarter_idx)
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

        elif msg_type == "update_assets" and not player.is_gm:
            assets = data.get("assets", {})
            if "projektchef" in assets:
                player.projektchef = assets["projektchef"]
            if "projects" in assets:
                player.projects = assets["projects"]
            if "q_krav" in assets:
                player.q_krav = int(assets["q_krav"])
            if "h_krav" in assets:
                player.h_krav = int(assets["h_krav"])
            if "riskbuffertar" in assets:
                player.riskbuffertar = int(assets["riskbuffertar"])
            if "mark_expansions" in assets:
                player.mark_expansions = int(assets["mark_expansions"])
            if "eget_kapital" in assets:
                player.eget_kapital = float(assets["eget_kapital"])
            if "abt_budget" in assets:
                player.abt_budget = float(assets["abt_budget"])
            # Update GM dashboard
            await self.broadcast_state(room)

        elif msg_type == "get_state":
            if player.is_gm:
                await self.send_to(code, player_id, {"type": "state", "state": room.to_dict()})
            else:
                await self.send_to(code, player_id, {"type": "state", "state": room.player_state(player_id)})


companion_manager = CompanionManager()
