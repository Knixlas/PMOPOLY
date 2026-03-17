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


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
