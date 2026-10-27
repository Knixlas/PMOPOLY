"""WebSocket handler for real-time game communication."""
import json
from typing import Dict, Set
from fastapi import WebSocket
from room_manager import GameRoom, RoomManager
from models import GamePhase
import asyncio
from engine import process_action, ai_default_action


class ConnectionManager:
    """Manages WebSocket connections per room."""

    def __init__(self):
        # room_id -> {player_id -> WebSocket}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, ws: WebSocket, room_id: str, player_id: str):
        await ws.accept()
        if room_id not in self.connections:
            self.connections[room_id] = {}
        self.connections[room_id][player_id] = ws

    def disconnect(self, room_id: str, player_id: str):
        if room_id in self.connections:
            self.connections[room_id].pop(player_id, None)
            if not self.connections[room_id]:
                del self.connections[room_id]

    async def send_to_player(self, room_id: str, player_id: str, data: dict):
        conn = self.connections.get(room_id, {}).get(player_id)
        if conn:
            try:
                await conn.send_json(data)
            except Exception:
                pass

    async def broadcast(self, room_id: str, data: dict):
        conns = self.connections.get(room_id, {})
        for pid, ws in list(conns.items()):
            try:
                await ws.send_json(data)
            except Exception:
                conns.pop(pid, None)

    async def broadcast_state(self, room: GameRoom):
        """Send full game state to all connected players.
        In puzzle phase, each player gets their own puzzle data."""
        if room.phase == GamePhase.PUZZLE_PLACEMENT:
            await self._broadcast_puzzle_state(room)
        else:
            state = room.to_dict()
            await self.broadcast(room.room_id, {
                "type": "game_state",
                "state": state,
            })
        # Om pending_action gäller en AI-spelare — kör AI:ns default-val automatiskt.
        await self._maybe_step_ai(room)

    async def _maybe_step_ai(self, room: GameRoom):
        """Om pending_action är AI:ns tur: kör AI:s default och rebroadcast.
        Loopar tills nästa pending_action är en mänsklig spelare (eller ingen).
        Avbryter vid fel-result eller om pending_action inte ändras (skydd mot
        oändliga loops om AI:s val inte accepteras)."""
        last_sub = None  # senaste current_marker-tupeln (inkluderar EK + list-längder)
        stuck_count = 0
        for _ in range(30):  # säkerhets-cap
            pending = room.pending_action
            if not pending:
                return
            pid = pending.get("player_id")
            if not pid:
                return
            player = room.get_player(pid)
            if not player or not getattr(player, "is_ai", False):
                return
            action = ai_default_action(room, player)
            if not action:
                # AI saknar handlingsregel för denna sub_state — logga och avbryt
                await self.broadcast(room.room_id, {
                    "type": "events",
                    "events": [{
                        "type": "event",
                        "text": f"⚠ AI ({player.name}) saknar regel för "
                                f"sub_state={room.sub_state!r} / "
                                f"action={pending.get('action')!r} — väntar.",
                    }],
                })
                return
            # Stuck-detektion: inkludera EK + längd på listor så att iterativa
            # actions (t.ex. flera energi-uppgraderingar i samma kvartal) inte
            # räknas som stuck. Vi bryter bara när INTET förändras mellan varv.
            upgr_len = len(pending.get("upgradeable", []) or [])
            avail_len = len(pending.get("available", []) or [])
            current_marker = (room.sub_state, pid, pending.get("action"),
                              round(player.eget_kapital, 1), upgr_len, avail_len)
            if current_marker == last_sub:
                stuck_count += 1
                if stuck_count >= 3:
                    await self.broadcast(room.room_id, {
                        "type": "events",
                        "events": [{
                            "type": "event",
                            "text": f"⚠ AI fastnade på {current_marker} — avbryter.",
                        }],
                    })
                    return
            else:
                stuck_count = 0
                last_sub = current_marker
            await asyncio.sleep(0.3)  # synligt för spelaren att AI agerar
            result = process_action(room, pid, action)
            if isinstance(result, dict) and result.get("type") == "error":
                await self.broadcast(room.room_id, {
                    "type": "events",
                    "events": [{
                        "type": "event",
                        "text": f"⚠ AI-fel: {result.get('message','?')} — avbryter.",
                    }],
                })
                return
            events = result.get("events", []) if isinstance(result, dict) else []
            if events:
                await self.broadcast(room.room_id, {"type": "events", "events": events})
            if room.phase == GamePhase.PUZZLE_PLACEMENT:
                await self._broadcast_puzzle_state(room)
            else:
                state = room.to_dict()
                await self.broadcast(room.room_id, {"type": "game_state", "state": state})

    async def _broadcast_puzzle_state(self, room: GameRoom):
        """Send per-player puzzle state during puzzle placement."""
        base_state = room.to_dict()
        conns = self.connections.get(room.room_id, {})

        for pid, ws in list(conns.items()):
            player = room.get_player(pid)
            if not player:
                continue

            # Build per-player state with puzzle info
            state = dict(base_state)
            base_cells = [[r, c] for r in range(2, 6) for c in range(2, 6)]
            base_set = {(r, c) for r in range(2, 6) for c in range(2, 6)}
            current_expansions = len(player.puzzle_grid_cells) - len(
                base_set & {(r, c) for r, c in player.puzzle_grid_cells})
            max_expansions = player.mark_expansions * 5

            # Mark expansion pieces (unplaced and placed)
            mark_placed_ids = set(player.puzzle_mark_placements.keys())
            mark_pieces = []
            for piece in player.mark_expansion_pieces:
                mark_pieces.append({
                    "id": piece["id"],
                    "cells": piece["cells"],
                    "placed": piece["id"] in mark_placed_ids,
                })

            state["my_puzzle"] = {
                "grid_cells": player.puzzle_grid_cells,
                "placements": player.puzzle_placements,
                "mark_placements": player.puzzle_mark_placements,
                "confirmed": player.puzzle_confirmed,
                "mark_pieces": mark_pieces,
                "shapes": {
                    proj.id: {
                        "namn": proj.namn,
                        "typ": proj.typ,
                        "cells": room.game_data.shapes.get(proj.namn, []),
                    }
                    for proj in player.projects
                },
            }

            # Show other players' confirmation status only
            state["puzzle_status"] = [
                {"name": p.name, "confirmed": p.puzzle_confirmed,
                 "placed_count": len(p.puzzle_placements)}
                for p in room.players
            ]

            try:
                await ws.send_json({"type": "game_state", "state": state})
            except Exception:
                conns.pop(pid, None)


manager = ConnectionManager()


async def handle_ws_message(ws: WebSocket, room: GameRoom, player_id: str, message: str):
    """Handle incoming WebSocket message from a player."""
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        await ws.send_json({"type": "error", "message": "Ogiltigt meddelande"})
        return

    msg_type = data.get("type")

    if msg_type == "start_game":
        # Only host can start
        if player_id != room.host_id:
            await ws.send_json({"type": "error", "message": "Bara värden kan starta"})
            return
        if len(room.players) < 1:
            await ws.send_json({"type": "error", "message": "Behöver minst 1 spelare"})
            return

        room.start_game()
        await manager.broadcast_state(room)
        return

    if msg_type == "start_game_preset":
        # Provspels-genväg: hoppa direkt till Skede 2 eller Skede 3 med standardportfölj.
        if player_id != room.host_id:
            await ws.send_json({"type": "error", "message": "Bara värden kan starta"})
            return
        preset_name = data.get("preset", "")
        result = room.start_game_preset(preset_name)
        if result.get("type") == "error":
            await ws.send_json(result)
            return
        events = result.get("events", [])
        if events:
            await manager.broadcast(room.room_id, {"type": "events", "events": events})
        await manager.broadcast_state(room)
        return

    elif msg_type == "action":
        result = process_action(room, player_id, data)

        if result.get("type") == "error":
            await ws.send_json(result)
            return

        # Broadcast events to all players
        events = result.get("events", [])
        if events:
            await manager.broadcast(room.room_id, {
                "type": "events",
                "events": events,
            })

        # Send updated state to all
        await manager.broadcast_state(room)

    elif msg_type == "chat":
        player = room.get_player(player_id)
        name = player.name if player else "Okänd"
        await manager.broadcast(room.room_id, {
            "type": "chat",
            "player_name": name,
            "message": data.get("message", ""),
        })

    elif msg_type == "get_state":
        await ws.send_json({
            "type": "game_state",
            "state": room.to_dict(),
        })
