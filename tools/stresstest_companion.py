"""Stresstest companion mot Railway: 7 stadsdelar × 4 kvarter = 28 spelare + 7 GMs.

Mäter:
- Connect-tid per WebSocket
- Latens för broadcast (GM kallar next_step → alla 4 spelare får state)
- Error rate
- Total runtid

Kör: python tools/stresstest_companion.py [base_url]
"""
import asyncio
import json
import time
import sys
import statistics
import urllib.request
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://pmopoly-production.up.railway.app"
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")

NUM_DISTRICTS = 7
PLAYERS_PER_DISTRICT = 4
TOTAL_PLAYERS = NUM_DISTRICTS * PLAYERS_PER_DISTRICT  # 28


async def http_post(path, body):
    """Async HTTP POST via thread."""
    def _do():
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    return await asyncio.to_thread(_do)


async def http_get(path):
    def _do():
        with urllib.request.urlopen(BASE + path, timeout=15) as r:
            return json.loads(r.read())
    return await asyncio.to_thread(_do)


async def create_room(district_idx):
    """Create a room with 4 quarters. Return (code, gm_id, quarter_codes)."""
    t = time.time()
    r = await http_post("/api/companion/rooms", {"num_quarters": 4, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]

    # Pull quarter_codes via GM WebSocket
    qcs = None
    async with websockets.connect(f"{WS_BASE}/companion/ws/{code}/{gm_id}", open_timeout=10) as ws:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if msg.get("type") == "state" and msg["state"].get("quarter_codes"):
            qcs = msg["state"]["quarter_codes"]
    elapsed = time.time() - t
    return code, gm_id, qcs, elapsed


async def join_player(quarter_code, name):
    t = time.time()
    r = await http_post("/api/companion/join-quarter", {"name": name, "quarter_code": quarter_code})
    elapsed = time.time() - t
    return r["code"], r["player_id"], elapsed


class Client:
    """En WebSocket-klient (player eller GM)."""
    def __init__(self, name, room_code, player_id, role):
        self.name = name
        self.room_code = room_code
        self.player_id = player_id
        self.role = role
        self.ws = None
        self.connected_at = None
        self.first_state_at = None
        self.broadcasts_received = []  # (recv_at, sent_at_estimate)
        self.errors = []
        self.message_count = 0

    async def run(self):
        url = f"{WS_BASE}/companion/ws/{self.room_code}/{self.player_id}"
        try:
            t0 = time.time()
            self.ws = await websockets.connect(url, open_timeout=10)
            self.connected_at = time.time() - t0
            async for msg in self.ws:
                self.message_count += 1
                try:
                    data = json.loads(msg)
                except Exception:
                    continue
                if data.get("type") == "state":
                    if self.first_state_at is None:
                        self.first_state_at = time.time()
                    else:
                        self.broadcasts_received.append(time.time())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.errors.append(str(e))
        finally:
            try:
                if self.ws:
                    await self.ws.close()
            except Exception:
                pass


async def trigger_next_step(gm_client):
    """GM skickar 'advance_step'. Mät broadcast-latens till spelare."""
    if not gm_client.ws:
        return None
    sent_at = time.time()
    try:
        await gm_client.ws.send(json.dumps({"type": "advance_step"}))
    except Exception:
        return None
    return sent_at


async def main():
    print(f"=== Stresstest mot {BASE} ===")
    print(f"Skapar {NUM_DISTRICTS} stadsdelar × {PLAYERS_PER_DISTRICT} kvarter = {TOTAL_PLAYERS} spelare + {NUM_DISTRICTS} GMs")
    print()

    # 1) Create all rooms in parallel
    print("Skapar rum...")
    room_results = await asyncio.gather(
        *[create_room(i) for i in range(NUM_DISTRICTS)],
        return_exceptions=True
    )
    rooms = []
    for r in room_results:
        if isinstance(r, Exception):
            print(f"  [FAIL]Room creation failed: {r}")
            return
        code, gm_id, qcs, t = r
        rooms.append((code, gm_id, qcs))
        print(f"  [OK]{code} created in {t*1000:.0f}ms (qcs: {qcs})")
    print()

    # 2) Join all 28 players in parallel
    print("Joinar 28 spelare...")
    join_tasks = []
    for d_idx, (room_code, gm_id, qcs) in enumerate(rooms):
        for p_idx, qc in enumerate(qcs):
            name = f"D{d_idx}-Q{p_idx}"
            join_tasks.append((d_idx, p_idx, qc, name))

    join_t0 = time.time()
    join_results = await asyncio.gather(
        *[join_player(qc, name) for _, _, qc, name in join_tasks],
        return_exceptions=True
    )
    join_t = time.time() - join_t0
    join_times = [r[2] for r in join_results if not isinstance(r, Exception)]
    print(f"  [OK]Alla joinade på {join_t*1000:.0f}ms (per-spelare: median {statistics.median(join_times)*1000:.0f}ms, max {max(join_times)*1000:.0f}ms)")
    print()

    # 3) Spawn all WebSocket clients (28 players + 7 GMs)
    print("Etablerar 35 WebSocket-anslutningar parallellt...")
    clients = []
    for i, (d_idx, p_idx, qc, name) in enumerate(join_tasks):
        room_code, p_id, _ = join_results[i]
        clients.append(Client(name, room_code, p_id, "player"))
    for d_idx, (room_code, gm_id, _) in enumerate(rooms):
        clients.append(Client(f"GM{d_idx}", room_code, gm_id, "gm"))

    ws_t0 = time.time()
    tasks = [asyncio.create_task(c.run()) for c in clients]
    # Wait for first_state_at on each client (with timeout)
    deadline = time.time() + 20
    while time.time() < deadline:
        if all(c.first_state_at is not None for c in clients):
            break
        await asyncio.sleep(0.1)
    ws_total = time.time() - ws_t0

    connect_times = [c.connected_at * 1000 for c in clients if c.connected_at is not None]
    state_times = [(c.first_state_at - ws_t0) * 1000 for c in clients if c.first_state_at is not None]
    print(f"  [OK]Anslutna på {ws_total*1000:.0f}ms")
    print(f"    Connect-tid: median {statistics.median(connect_times):.0f}ms, p95 {sorted(connect_times)[int(len(connect_times)*0.95)]:.0f}ms, max {max(connect_times):.0f}ms")
    print(f"    First-state-tid: median {statistics.median(state_times):.0f}ms, max {max(state_times):.0f}ms")
    print(f"    Errors: {sum(1 for c in clients if c.errors)} st")
    print()

    # 4) Trigger broadcasts: each GM clicks next_step and we measure spread
    print("Testar broadcast-latens (GM next_step → alla 4 i rummet)...")
    for round_num in range(3):
        round_start = time.time()
        for c in clients:
            c.broadcasts_received = []  # reset

        gm_clients = [c for c in clients if c.role == "gm"]
        send_times = await asyncio.gather(*[trigger_next_step(g) for g in gm_clients])

        # Wait for broadcasts
        await asyncio.sleep(2)

        latencies = []
        for d_idx, gm in enumerate(gm_clients):
            if send_times[d_idx] is None:
                continue
            room_code = gm.room_code
            for p in clients:
                if p.role == "player" and p.room_code == room_code:
                    if p.broadcasts_received:
                        # First received after send_time
                        for recv_t in p.broadcasts_received:
                            if recv_t >= send_times[d_idx]:
                                latencies.append((recv_t - send_times[d_idx]) * 1000)
                                break
        if latencies:
            print(f"  Runda {round_num+1}: {len(latencies)} broadcasts, median {statistics.median(latencies):.0f}ms, max {max(latencies):.0f}ms")
        else:
            print(f"  Runda {round_num+1}: inga broadcasts mätta")
    print()

    # 5) Cleanup
    print("Stänger anslutningar och raderar rum...")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    for room_code, gm_id, _ in rooms:
        try:
            req = urllib.request.Request(
                f"{BASE}/api/companion/rooms/{room_code}?gm_id={gm_id}",
                method="DELETE"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    print("[OK] Klar")


if __name__ == "__main__":
    asyncio.run(main())
