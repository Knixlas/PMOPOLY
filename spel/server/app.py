"""ÅKEPOL-servern: partier som rum, en WebSocket per enhet, webbklienten som statiska filer.

    uvicorn spel.server.app:app --port 8000        (från repots rot)

REST
  POST /api/rum            {"kvarter": [{"namn", "styrning": "människa"|"bott", "bottar"?}], "slump": "digital"|"inmatad"}
  GET  /api/rum            alla rum (senaste först)
  GET  /api/rum/{id}       läget
  POST /api/rum/{id}/svar  {"kvarter", "nr", "svar": {...}} (samma som över WebSocket)
WebSocket
  /ws/{id}/{kvarter}       servern skickar {"typ": "lage", ...} vid varje ändring;
                           enheten skickar {"typ": "svar", "nr", "svar": {"val": i} | {"flera": [i]} |
                           {"svar": true/12} | {"placering": [...]} | {"forslag": true}}
Partierna sparas i SPEL_DATA (standard spel/server/data/partier) och återskapas vid start.
"""
import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from motor.data import Kortdata
from motor.parti import REGELVERSION

from .rum import Rum, SvarsFel, nytt_id

ROT = Path(__file__).resolve().parent
KATALOG = Path(os.environ.get("SPEL_DATA", ROT / "data" / "partier"))
WEBB = Path(os.environ.get("SPEL_WEBB", ROT.parent / "webb" / "dist"))

app = FastAPI(title="ÅKEPOL")
DATA = Kortdata()
RUM: dict[str, Rum] = {}
ANSLUTNA: dict[str, set] = {}


class KvarterIn(BaseModel):
    namn: str = Field(min_length=1, max_length=30)
    styrning: str = "människa"
    bottar: dict = Field(default_factory=dict)


class RumIn(BaseModel):
    kvarter: list[KvarterIn] = Field(min_length=1, max_length=4)
    slump: str = "digital"
    fro: int | None = None


class SvarIn(BaseModel):
    kvarter: str
    nr: int
    svar: dict


@app.on_event("startup")
def ladda_sparade():
    if KATALOG.exists():
        for fil in sorted(KATALOG.glob("*.json")):
            try:
                rum = Rum.ladda(fil, DATA)
                RUM[rum.id] = rum
            except Exception as e:                   # noqa: BLE001 — ett trasigt parti ska inte stoppa servern
                print(f"Kunde inte återskapa {fil.name}: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "regelversion": REGELVERSION, "partier": len(RUM)}


@app.post("/api/rum")
async def skapa(r: RumIn):
    namn = [k.namn.strip() for k in r.kvarter]
    if len(set(namn)) != len(namn) or "bordet" in namn:
        raise HTTPException(400, "kvarteren behöver olika namn")
    if r.slump not in ("digital", "inmatad") or any(k.styrning not in ("människa", "bott") for k in r.kvarter):
        raise HTTPException(400, "okänt spelsätt")
    uppstart = {"regelversion": REGELVERSION, "fro": r.fro if r.fro is not None else int.from_bytes(os.urandom(4), "big"),
                "slump": r.slump,
                "kvarter": [{"namn": k.namn.strip(), "styrning": k.styrning, **({"bottar": k.bottar} if k.bottar else {})}
                            for k in r.kvarter]}
    id_ = nytt_id()
    rum = await run_in_threadpool(Rum, id_, uppstart, [], KATALOG, DATA)
    RUM[id_] = rum
    return {"id": id_, "lage": rum.lage()}


@app.get("/api/rum")
def lista():
    return [{"id": r.id, "skapad": r.skapad, "kvarter": [k["namn"] for k in r.uppstart["kvarter"]],
             "slump": r.uppstart.get("slump"), "klart": r.klart,
             "skede": (r.bild or {}).get("namn")} for r in sorted(RUM.values(), key=lambda r: -r.skapad)]


def _rum(id_):
    if id_ not in RUM:
        raise HTTPException(404, "partiet finns inte")
    return RUM[id_]


@app.get("/api/rum/{id_}")
def lage(id_: str, kvarter: str | None = None):
    return _rum(id_).lage(kvarter)


async def _svara(rum, kvarter, nr, svar):
    await run_in_threadpool(rum.svara, kvarter, nr, svar)
    await _sand_alla(rum)


@app.post("/api/rum/{id_}/svar")
async def svara(id_: str, s: SvarIn):
    rum = _rum(id_)
    try:
        await _svara(rum, s.kvarter, s.nr, s.svar)
    except SvarsFel as e:
        raise HTTPException(409, str(e)) from None
    return rum.lage(s.kvarter)


@app.delete("/api/rum/{id_}")
async def radera(id_: str):
    rum = _rum(id_)
    RUM.pop(id_, None)
    await run_in_threadpool(rum.radera)
    for ws, _ in list(ANSLUTNA.pop(id_, set())):      # de som är med i partiet får veta det
        try:
            await ws.send_json({"typ": "raderat"})
            await ws.close()
        except Exception:                             # noqa: BLE001
            pass
    return {"raderat": id_}


async def _sand_alla(rum):
    for ws, kvarter in list(ANSLUTNA.get(rum.id, set())):
        try:
            await ws.send_json({"typ": "lage", **rum.lage(kvarter)})
        except Exception:                             # noqa: BLE001 — frånkopplad; städas vid disconnect
            pass


@app.websocket("/ws/{id_}/{kvarter}")
async def ws_rum(ws: WebSocket, id_: str, kvarter: str):
    await ws.accept()
    if id_ not in RUM:
        await ws.send_json({"typ": "fel", "text": "partiet finns inte"})
        await ws.close()
        return
    rum = RUM[id_]
    post = (ws, kvarter)
    ANSLUTNA.setdefault(id_, set()).add(post)
    try:
        await ws.send_json({"typ": "lage", **rum.lage(kvarter)})
        while True:
            msg = await ws.receive_json()
            if msg.get("typ") == "svar":
                try:
                    await _svara(rum, kvarter, msg.get("nr"), msg.get("svar") or {})
                except SvarsFel as e:
                    await ws.send_json({"typ": "fel", "text": str(e)})
            elif msg.get("typ") == "ping":
                await ws.send_json({"typ": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        ANSLUTNA.get(id_, set()).discard(post)


# ---------------------------------------------------------------------------- webbklienten
if WEBB.exists():
    app.mount("/assets", StaticFiles(directory=WEBB / "assets"), name="assets")
    if (WEBB / "bilder").exists():
        app.mount("/bilder", StaticFiles(directory=WEBB / "bilder"), name="bilder")

    @app.get("/{sokvag:path}")
    def klient(sokvag: str):
        fil = WEBB / sokvag
        if sokvag and fil.is_file() and WEBB in fil.resolve().parents:
            return FileResponse(fil)
        return FileResponse(WEBB / "index.html")
