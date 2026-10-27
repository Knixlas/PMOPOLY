"""Room management for multiplayer games."""
import uuid
import random
import copy
from typing import Dict, List, Optional
from models import Player, GamePhase, roll
from data_loader import GameData


PLAYER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]


class GameRoom:
    """A single game room with state."""

    def __init__(self, room_id: str, name: str, host_name: str, game_data: GameData):
        self.room_id = room_id
        self.name = name
        self.host_id: str = ""
        self.game_data = game_data
        self.players: List[Player] = []
        self.phase = GamePhase.LOBBY
        self.turn_index: int = 0
        self.sub_state: str = ""
        self.pending_action: Optional[dict] = None
        self.temp: dict = {}  # Temporary state for multi-step actions
        self.events_log: List[dict] = []  # Event history

        # Card decks (initialized on game start)
        self.politik_deck: List[dict] = []
        self.dialog_deck: List[dict] = []
        self.projekt_stacks: Dict[str, list] = {}
        self.used_projects: List[str] = []  # IDs of returned projects

        # Phase 2: per-player planning event draw/discard piles
        self.pl_draw_piles: Dict[str, list] = {}
        self.pl_discard_piles: Dict[str, list] = {}
        self.pl_step_index: int = 0  # Current planning step (0-12)

        # Phase 3: shared external support deck and faskort
        self.extern_draw: list = []
        self.extern_discard: list = []
        self.gf_fas_nr: int = 0  # Current faskort phase (1-8)
        self.gf_current_card: Optional[dict] = None  # Current faskort for this phase
        self.gf_turn_order: list = []  # Player order for Phase 3
        self.gf_sub_phase: str = ""  # buy_support, draw_event, resolve_faskort, etc.

        # Phase 4: management state
        self.f4_quarter: int = 0
        self.f4_yield_b: float = 0.0
        self.f4_yield_k: float = 0.0
        self.f4_yield_cards: dict = {}  # {"bostader": [...], "kommersiellt": [...]}
        self.f4_world_events: list = []
        self.f4_dd_deck: list = []
        self.f4_mgmt_decks: dict = {}  # {player_id: {typ: [cards...]}}
        self.f4_market_props: list = []
        self.f4_no_trading: bool = False
        self.f4_energy_discount: float = 1.0
        self.f4_hired_ids: set = set()  # Global hired staff IDs
        self.f4_final_results: list = []  # Sätts av _f4_final_valuation vid spelslut
        # Historik per kvartal för grafer i Skede 3-UI. Lista av snapshots:
        # {quarter, yield_b, yield_k, players: [{id, ek, dn_total, score}]}
        self.f4_history: list = []

        # Add host
        host_id = str(uuid.uuid4())[:8]
        self.host_id = host_id
        self.players.append(Player(
            id=host_id, name=host_name, color=PLAYER_COLORS[0]
        ))

    @property
    def current_player(self) -> Optional[Player]:
        if not self.players:
            return None
        return self.players[self.turn_index % len(self.players)]

    def add_player(self, name: str) -> Optional[Player]:
        if len(self.players) >= 4:
            return None
        if self.phase != GamePhase.LOBBY:
            return None
        pid = str(uuid.uuid4())[:8]
        color = PLAYER_COLORS[len(self.players)]
        p = Player(id=pid, name=name, color=color)
        self.players.append(p)
        return p

    def add_ai_player(self, name: str = "AI-motspelare") -> Optional[Player]:
        """Lägg till en passiv AI-spelare. AI:n gör default-val (skip på alla
        valfria moment, hire första FC + första FS automatiskt). Använd för
        ensam-läge så man har en motpart att jämföra slutpoäng mot."""
        if len(self.players) >= 4:
            return None
        if self.phase != GamePhase.LOBBY:
            return None
        pid = "ai-" + str(uuid.uuid4())[:6]
        color = PLAYER_COLORS[len(self.players)]
        p = Player(id=pid, name=name, color=color, is_ai=True)
        self.players.append(p)
        return p

    def get_player(self, player_id: str) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def start_game(self):
        """Initialize game state and begin Phase 1."""
        # Shuffle project stacks (deep copy from game data)
        for typ, projects in self.game_data.projects.items():
            stack = copy.deepcopy(projects)
            random.shuffle(stack)
            self.projekt_stacks[typ] = stack

        # Shuffle card decks
        self.politik_deck = list(range(len(self.game_data.politik)))
        random.shuffle(self.politik_deck)
        self.dialog_deck = list(range(len(self.game_data.dialog)))
        random.shuffle(self.dialog_deck)

        # Mark expansion deck (shared, shuffled)
        self.mark_expansion_deck = copy.deepcopy(self.game_data.mark_expansion_deck)
        random.shuffle(self.mark_expansion_deck)

        # Randomize turn order
        random.shuffle(self.players)

        # All players get mark+tomt
        for p in self.players:
            p.has_mark_tomt = True

        # Begin Phase 1: First hire PC, then pick projects
        self.phase = GamePhase.PHASE1_PC_HIRE
        self.turn_index = 0
        self.temp = {"pc_hired_ids": set()}
        from engine import _setup_pc_hire
        _setup_pc_hire(self)

    def start_game_preset(self, preset_name: str) -> dict:
        """Provspels-genväg: hoppa direkt till Skede 2 eller Skede 3 med en
        fördefinierad portfölj. Setupar projekt-stackar och decks som vanligt
        (eftersom följande faser drar kort därifrån) men hoppar över Skede 1.

        preset_name: 'skede_2' eller 'skede_3'.
        """
        # Initiera projekt-stackar + kort-decks som vid normal start
        for typ, projects in self.game_data.projects.items():
            stack = copy.deepcopy(projects)
            random.shuffle(stack)
            self.projekt_stacks[typ] = stack
        self.politik_deck = list(range(len(self.game_data.politik)))
        random.shuffle(self.politik_deck)
        self.dialog_deck = list(range(len(self.game_data.dialog)))
        random.shuffle(self.dialog_deck)
        self.mark_expansion_deck = copy.deepcopy(self.game_data.mark_expansion_deck)
        random.shuffle(self.mark_expansion_deck)

        random.shuffle(self.players)

        from engine import _setup_preset_skede2, _setup_preset_skede3
        if preset_name == "skede_2":
            return _setup_preset_skede2(self)
        elif preset_name == "skede_3":
            return _setup_preset_skede3(self)
        else:
            return {"type": "error", "message": f"Okänd preset: {preset_name}"}

    def _setup_mark_tomt_action(self):
        """Set up action for current player to pick a project type."""
        player = self.current_player
        available_types = [t for t, stack in self.projekt_stacks.items() if len(stack) > 0]
        self.sub_state = "pick_project_type"
        self.pending_action = {
            "action": "pick_project_type",
            "player_id": player.id,
            "options": available_types,
            "message": f"Välj vilken typ av projekt du vill börja med",
        }

    def next_turn(self):
        """Advance to next player's turn."""
        self.turn_index = (self.turn_index + 1) % len(self.players)

    def to_dict(self) -> dict:
        from config import YIELD_QUEUE_SIZE
        # Live-slutresultat (visas under Skede 3 i sidopanelen).
        live_scores = {}
        if self.phase == GamePhase.PHASE4_FORVALTNING:
            try:
                from engine import calc_live_score
                for p in self.players:
                    live_scores[p.id] = calc_live_score(self, p)
            except Exception:
                pass
        return {
            "room_id": self.room_id,
            "name": self.name,
            "phase": self.phase.value,
            "players": [p.to_dict() for p in self.players],
            "turn_index": self.turn_index,
            "current_player_id": self.current_player.id if self.current_player else None,
            "sub_state": self.sub_state,
            "pending_action": self.pending_action,
            "events_log": self.events_log[-20:],  # Last 20 events
            # Förvaltning 2.0 – marknadskartan + yield-kö (synliga närmaste rörelser).
            "f4_quarter": self.f4_quarter,
            "f4_yield_b": round(self.f4_yield_b, 2),
            "f4_yield_k": round(self.f4_yield_k, 2),
            "f4_yield_queue_bostader": list(self.f4_yield_cards.get("bostader", []))[:YIELD_QUEUE_SIZE],
            "f4_yield_queue_kommersiellt": list(self.f4_yield_cards.get("kommersiellt", []))[:YIELD_QUEUE_SIZE],
            "f4_final_results": self.f4_final_results,
            "f4_live_scores": live_scores,
            "f4_history": self.f4_history,
        }

    def to_lobby_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "players": len(self.players),
            "max_players": 4,
            "phase": self.phase.value,
            "player_names": [p.name for p in self.players],
        }


class RoomManager:
    """Manages all game rooms."""

    def __init__(self, game_data: GameData):
        self.rooms: Dict[str, GameRoom] = {}
        self.game_data = game_data

    def create_room(self, name: str, host_name: str) -> GameRoom:
        room_id = str(uuid.uuid4())[:8]
        room = GameRoom(room_id, name, host_name, self.game_data)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        return self.rooms.get(room_id)

    def list_rooms(self) -> List[dict]:
        return [r.to_lobby_dict() for r in self.rooms.values()
                if r.phase == GamePhase.LOBBY]

    def remove_room(self, room_id: str):
        self.rooms.pop(room_id, None)
