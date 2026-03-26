"""PMOPOLY - Web-based multiplayer property development game."""
import os
import sys

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from config import FRONTEND_DIR
from data_loader import GameData
from room_manager import RoomManager
from ws_handler import manager, handle_ws_message
from companion import companion_manager


# Global state
game_data: GameData = None
room_mgr: RoomManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global game_data, room_mgr
    print("PMOPOLY starting...")
    print("  Loading game data...")
    game_data = GameData()
    room_mgr = RoomManager(game_data)
    print("  Ready!")
    yield
    print("PMOPOLY shutting down.")


app = FastAPI(title="PMOPOLY", lifespan=lifespan)


# ── REST API ──

@app.post("/api/rooms")
async def create_room(body: dict):
    name = body.get("name", "Spelrum")
    host_name = body.get("host_name", "Spelare 1")
    room = room_mgr.create_room(name, host_name)
    return {
        "room_id": room.room_id,
        "player_id": room.host_id,
        "room": room.to_lobby_dict(),
    }


@app.get("/api/rooms")
async def list_rooms():
    return {"rooms": room_mgr.list_rooms()}


@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, body: dict):
    room = room_mgr.get_room(room_id)
    if not room:
        return JSONResponse({"error": "Rum hittades inte"}, status_code=404)

    name = body.get("name", "Spelare")
    player = room.add_player(name)
    if not player:
        return JSONResponse({"error": "Rummet är fullt eller spelet har startat"}, status_code=400)

    # Notify existing players
    await manager.broadcast_state(room)

    return {
        "room_id": room.room_id,
        "player_id": player.id,
        "room": room.to_lobby_dict(),
    }


@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str):
    room = room_mgr.get_room(room_id)
    if not room:
        return JSONResponse({"error": "Rum hittades inte"}, status_code=404)
    return {"room": room.to_dict()}


# ── WebSocket ──

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str, player_id: str):
    room = room_mgr.get_room(room_id)
    if not room:
        await ws.close(code=4004, reason="Room not found")
        return

    player = room.get_player(player_id)
    if not player:
        await ws.close(code=4003, reason="Player not found")
        return

    await manager.connect(ws, room_id, player_id)

    try:
        # Send current state on connect
        await ws.send_json({
            "type": "game_state",
            "state": room.to_dict(),
        })
        # Notify others
        await manager.broadcast(room_id, {
            "type": "player_connected",
            "player_name": player.name,
        })

        while True:
            message = await ws.receive_text()
            await handle_ws_message(ws, room, player_id, message)

    except WebSocketDisconnect:
        manager.disconnect(room_id, player_id)
        await manager.broadcast(room_id, {
            "type": "player_disconnected",
            "player_name": player.name,
        })


# ── Static files (frontend) ──

class NoCacheStaticFiles(StaticFiles):
    """Static files with no-cache headers for dev."""
    async def __call__(self, scope, receive, send):
        async def send_with_nocache(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"cache-control", b"no-cache, no-store, must-revalidate"))
                message["headers"] = headers
            await send(message)
        await super().__call__(scope, receive, send_with_nocache)

app.mount("/css", NoCacheStaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", NoCacheStaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/img", StaticFiles(directory=os.path.join(FRONTEND_DIR, "img")), name="img")


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/companion")
async def companion_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "companion.html"),
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/companion/gm")
async def companion_gm():
    return FileResponse(os.path.join(FRONTEND_DIR, "companion.html"),
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


# ── Companion API ──

@app.post("/api/companion/rooms")
async def companion_create_room(body: dict):
    num_quarters = int(body.get("num_quarters", 4))
    room, gm_id = companion_manager.create_room(num_quarters)
    return {"code": room.code, "gm_id": gm_id}


@app.get("/api/companion/rooms/{code}")
async def companion_get_room(code: str):
    room = companion_manager.get_room(code)
    if not room:
        return JSONResponse({"error": "Rum hittades inte"}, status_code=404)
    return {
        "code": room.code,
        "num_quarters": room.num_quarters,
        "quarter_names": room.quarter_names,
        "num_players": len([p for p in room.players.values() if not p.is_gm]),
    }


@app.post("/api/companion/rooms/{code}/join")
async def companion_join_room(code: str, body: dict):
    name = body.get("name", "Spelare")
    quarter_idx = int(body.get("quarter_idx", 0))
    result = companion_manager.join_room(code, name, quarter_idx)
    if not result:
        return JSONResponse({"error": "Kunde inte gå med (stadsdelen full eller rummet finns ej)"}, status_code=400)
    room, player_id = result
    await companion_manager.broadcast_state(room)
    return {"code": room.code, "player_id": player_id}


@app.post("/api/companion/join-quarter")
async def companion_join_quarter(body: dict):
    """Join by quarter code (4 chars) instead of room code."""
    name = body.get("name", "Spelare")
    quarter_code = body.get("quarter_code", "").strip().upper()
    if not quarter_code:
        return JSONResponse({"error": "Ange stadsdelskod"}, status_code=400)
    result = companion_manager.find_room_by_quarter_code(quarter_code)
    if not result:
        return JSONResponse({"error": "Stadsdelskoden hittades inte"}, status_code=404)
    room, quarter_idx = result
    join_result = companion_manager.join_room(room.code, name, quarter_idx)
    if not join_result:
        return JSONResponse({"error": "Stadsdelen är full (max 4 spelare)"}, status_code=400)
    _, player_id = join_result
    await companion_manager.broadcast_state(room)
    return {"code": room.code, "player_id": player_id, "quarter_name": room.quarter_names[quarter_idx]}


@app.get("/companion/dashboard/{code}")
async def companion_dashboard(code: str):
    """External public dashboard."""
    return FileResponse(os.path.join(FRONTEND_DIR, "companion-dashboard.html"),
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/api/companion/leaderboard/{code}")
async def companion_leaderboard(code: str):
    room = companion_manager.get_room(code)
    if not room:
        return JSONResponse({"error": "Rum hittades inte"}, status_code=404)
    phase = room.current_phase
    step = room.current_step
    lb = room.leaderboard()
    return {
        "phase_name": phase["name"] if phase else "—",
        "step_name": step["name"] if step else "—",
        "players": lb["players"],
        "districts": lb["districts"],
        "total_players": lb["total_players"],
        "total_districts": lb["total_districts"],
    }


@app.get("/api/companion/data/pc")
async def companion_pc_data():
    return {"pc": game_data.pc_staff}


@app.get("/api/companion/data/ac")
async def companion_ac_data():
    return {"ac": game_data.ac_staff}


@app.get("/api/companion/data/planning")
async def companion_planning_data():
    """Return all suppliers and organisations for planning steps."""
    suppliers = {}
    for namn, levels in game_data.suppliers.items():
        suppliers[namn] = [s.to_dict("C") for s in levels]  # Default to class C
    orgs = {}
    for namn, levels in game_data.organisations.items():
        orgs[namn] = [o.to_dict() for o in levels]
    # Planning step order with type info
    steps = [
        {"id": "stodfunktioner", "name": "St\u00f6dfunktioner", "type": "org", "key": "St\u00f6dfunktioner"},
        {"id": "mark", "name": "MARK", "type": "supplier", "key": "MARK"},
        {"id": "husunderbyggnad", "name": "HUSUNDERBYGGNAD", "type": "supplier", "key": "HUSUNDERBYGGNAD"},
        {"id": "digitalisering", "name": "Digitalisering", "type": "org", "key": "Digitalisering"},
        {"id": "stomme", "name": "STOMME", "type": "supplier", "key": "STOMME"},
        {"id": "installationer", "name": "INSTALLATIONER", "type": "supplier", "key": "INSTALLATIONER"},
        {"id": "opteam", "name": "Operativt team", "type": "org", "key": "Operativt team"},
        {"id": "gemarbeten", "name": "GEM. ARBETEN", "type": "supplier", "key": "GEMENSAMMA ARBETEN"},
        {"id": "yttertak", "name": "YTTERTAK", "type": "supplier", "key": "YTTERTAK"},
        {"id": "fasader", "name": "FASADER", "type": "supplier", "key": "FASADER"},
        {"id": "marknadsteam", "name": "Marknadsteam", "type": "org", "key": "Marknadsteam"},
        {"id": "stomkomp", "name": "STOMKOMPLETTERING", "type": "supplier", "key": "STOMKOMPLETTERING"},
        {"id": "invytskikt", "name": "INV YTSKIKT", "type": "supplier", "key": "INV YTSKIKT"},
    ]
    return {"suppliers": suppliers, "organisations": orgs, "steps": steps}


@app.get("/api/companion/data/projects")
async def companion_project_data():
    result = {}
    for typ, stack in game_data.projects.items():
        # Deduplicate by namn — show each unique project once
        seen = set()
        unique = []
        for p in stack:
            if p.namn not in seen:
                seen.add(p.namn)
                unique.append(p.to_dict())
        result[typ] = unique
    return {"projects": result}


@app.get("/api/companion/data/fcfs")
async def companion_fcfs_data():
    """Return FC and FS staff for Phase 4."""
    fc = [s.to_dict() for s in game_data.staff if s.roll == "FC"]
    fs = [s.to_dict() for s in game_data.staff if s.roll == "FS"]
    return {"fc": fc, "fs": fs}


@app.get("/api/companion/data/texts")
async def companion_texts():
    """Return editable help texts from JSON file."""
    import json
    texts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "companion_texts.json")
    try:
        with open(texts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"phases": []}


@app.get("/api/companion/analytics/games")
async def analytics_games():
    """List all logged games."""
    import json as _json
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "game_logs")
    if not os.path.exists(log_dir):
        return {"games": []}
    games = []
    for fname in sorted(os.listdir(log_dir), reverse=True):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(log_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = _json.load(f)
            events = data.get("events", [])
            created = next((e for e in events if e["event"] == "room_created"), None)
            finished = next((e for e in events if e["event"] == "game_finished"), None)
            players = [e for e in events if e["event"] == "player_joined"]
            games.append({
                "file": fname,
                "code": created["data"].get("code") if created else fname[:6],
                "date": created["time"] if created else "",
                "num_players": len(players),
                "finished": finished is not None,
                "final_scores": finished["data"].get("final_scores") if finished else None,
                "num_events": len(events),
            })
        except Exception:
            continue
    return {"games": games}


@app.get("/api/companion/analytics/game/{filename}")
async def analytics_game_detail(filename: str):
    """Get full event log for a specific game."""
    import json as _json
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "game_logs")
    fpath = os.path.join(log_dir, filename)
    if not os.path.exists(fpath):
        return {"error": "Game not found"}
    with open(fpath, "r", encoding="utf-8") as f:
        return _json.load(f)


@app.get("/companion/analytics")
async def companion_analytics_page():
    """Serve analytics dashboard page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "analytics.html"))


@app.websocket("/companion/ws/{code}/{player_id}")
async def companion_ws(ws: WebSocket, code: str, player_id: str):
    room = companion_manager.get_room(code)
    if not room:
        await ws.close(code=4004, reason="Room not found")
        return
    player = room.players.get(player_id)
    if not player:
        await ws.close(code=4003, reason="Player not found")
        return

    await companion_manager.connect(code, player_id, ws)
    try:
        # Send initial state
        if player.is_gm:
            await ws.send_json({"type": "state", "state": room.to_dict()})
        else:
            await ws.send_json({"type": "state", "state": room.player_state(player_id)})

        while True:
            message = await ws.receive_text()
            import json
            data = json.loads(message)
            await companion_manager.handle_message(code, player_id, data)

    except WebSocketDisconnect:
        companion_manager.disconnect(code, player_id)
    except Exception as e:
        print(f"COMPANION WS ERROR [{code}/{player_id}]: {e}")
        import traceback
        traceback.print_exc()
        companion_manager.disconnect(code, player_id)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
