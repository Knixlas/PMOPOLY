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
    return FileResponse(os.path.join(FRONTEND_DIR, "companion.html"))


@app.get("/companion/gm")
async def companion_gm():
    return FileResponse(os.path.join(FRONTEND_DIR, "companion.html"))


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
    return FileResponse(os.path.join(FRONTEND_DIR, "companion-dashboard.html"))


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
    }


@app.get("/api/companion/data/pc")
async def companion_pc_data():
    return {"pc": game_data.pc_staff}


@app.get("/api/companion/data/projects")
async def companion_project_data():
    result = {}
    for typ, stack in game_data.projects.items():
        result[typ] = [p.to_dict() for p in stack]
    return {"projects": result}


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


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
