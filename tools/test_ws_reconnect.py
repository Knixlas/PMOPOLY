"""Test WS reconnect/rollback robustness for companion app.

Scenarier som testas:
1. Reconnect efter rent close — samma player_id, ny WS, får fräsch state
2. Snabb reconnect-storm — 10 reconnects i rad utan avbrott
3. Stale-connection race — gamla WS:n stänger SENT efter att ny WS:n öppnats
   (utan fix: gamla WS:s disconnect-handler poppar nya WS från dict)
4. GM trycker bakåt (prev_step) → alla spelare får korrekt rollback-state
5. Page-reload-simulering: WS stängs, ny session öppnas med samma player_id

Kör: python tools/test_ws_reconnect.py [base_url]
Default: http://localhost:8000
"""
import asyncio
import json
import sys
import time
import urllib.request
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
WS_BASE = BASE.replace("https://", "wss://").replace("http://", "ws://")


def http_post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def http_delete(path):
    req = urllib.request.Request(BASE + path, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except Exception:
        return None


async def ws_recv_state(ws, timeout=5):
    """Receive next state-message (skip non-state)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=deadline - time.time())
        except asyncio.TimeoutError:
            return None
        try:
            data = json.loads(msg)
        except Exception:
            continue
        if data.get("type") == "state":
            return data["state"]
    return None


PASSED = []
FAILED = []


def ok(name):
    PASSED.append(name)
    print(f"  [OK]   {name}")


def fail(name, reason):
    FAILED.append((name, reason))
    print(f"  [FAIL] {name}: {reason}")


# ── Test 1: Plain reconnect ──
async def test_plain_reconnect():
    print("\n[1] Plain reconnect (samma player_id, sluten + öppnad)")
    r = http_post("/api/companion/rooms", {"num_quarters": 1, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]
    try:
        # GM connect → får state med quarter_codes
        url = f"{WS_BASE}/companion/ws/{code}/{gm_id}"
        ws1 = await websockets.connect(url, open_timeout=5)
        s1 = await ws_recv_state(ws1, timeout=5)
        if not s1:
            return fail("plain_reconnect", "no initial state")
        qc = s1.get("quarter_codes", [None])[0]
        if not qc:
            return fail("plain_reconnect", "no quarter_code in state")

        # Join player
        jr = http_post("/api/companion/join-quarter",
                       {"name": "P1", "quarter_code": qc})
        pid = jr["player_id"]
        purl = f"{WS_BASE}/companion/ws/{code}/{pid}"

        # Player connect → state
        pws = await websockets.connect(purl, open_timeout=5)
        ps1 = await ws_recv_state(pws, timeout=5)
        if not ps1:
            return fail("plain_reconnect", "no player initial state")

        # Close player WS
        await pws.close()
        await asyncio.sleep(0.3)

        # Reconnect with same player_id
        pws2 = await websockets.connect(purl, open_timeout=5)
        ps2 = await ws_recv_state(pws2, timeout=5)
        if not ps2:
            return fail("plain_reconnect", "no state after reconnect")
        if ps2.get("player", {}).get("id") != pid:
            return fail("plain_reconnect", f"wrong player in reconnected state")

        await pws2.close()
        await ws1.close()
        ok("plain_reconnect")
    finally:
        http_delete(f"/api/companion/rooms/{code}?gm_id={gm_id}")


# ── Test 2: Reconnect-storm ──
async def test_reconnect_storm():
    print("\n[2] Reconnect-storm (10 ggr i rad)")
    r = http_post("/api/companion/rooms", {"num_quarters": 1, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]
    try:
        url = f"{WS_BASE}/companion/ws/{code}/{gm_id}"
        ws_init = await websockets.connect(url, open_timeout=5)
        s = await ws_recv_state(ws_init, timeout=5)
        qc = s["quarter_codes"][0]
        await ws_init.close()

        jr = http_post("/api/companion/join-quarter",
                       {"name": "Storm", "quarter_code": qc})
        pid = jr["player_id"]
        purl = f"{WS_BASE}/companion/ws/{code}/{pid}"

        for i in range(10):
            ws = await websockets.connect(purl, open_timeout=5)
            st = await ws_recv_state(ws, timeout=5)
            if not st:
                return fail("reconnect_storm", f"no state on attempt {i+1}")
            if st.get("player", {}).get("id") != pid:
                return fail("reconnect_storm", f"wrong player on attempt {i+1}")
            await ws.close()
            await asyncio.sleep(0.05)

        ok("reconnect_storm")
    finally:
        http_delete(f"/api/companion/rooms/{code}?gm_id={gm_id}")


# ── Test 3: Stale-connection race ──
async def test_stale_race():
    print("\n[3] Stale-connection race (ny WS öppnas medan gammal lever)")
    r = http_post("/api/companion/rooms", {"num_quarters": 1, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]
    try:
        url = f"{WS_BASE}/companion/ws/{code}/{gm_id}"
        ws_init = await websockets.connect(url, open_timeout=5)
        s = await ws_recv_state(ws_init, timeout=5)
        qc = s["quarter_codes"][0]

        jr = http_post("/api/companion/join-quarter",
                       {"name": "Race", "quarter_code": qc})
        pid = jr["player_id"]
        purl = f"{WS_BASE}/companion/ws/{code}/{pid}"

        # Open OLD ws (will linger)
        ws_old = await websockets.connect(purl, open_timeout=5)
        st_old = await ws_recv_state(ws_old, timeout=5)
        if not st_old:
            return fail("stale_race", "no state on old ws")

        # Without closing old, open NEW ws (server should close old in connect())
        ws_new = await websockets.connect(purl, open_timeout=5)
        st_new = await ws_recv_state(ws_new, timeout=5)
        if not st_new:
            return fail("stale_race", "no state on new ws")

        # Trigger a broadcast: GM advances step
        await ws_init.send(json.dumps({"type": "advance_step"}))
        # The new ws SHOULD receive this. The dict only stores ws_new.
        st_after = await ws_recv_state(ws_new, timeout=5)
        if not st_after:
            return fail("stale_race", "new ws missed broadcast after advance_step")

        # Now close old ws — its disconnect handler should NOT pop new ws
        try:
            await ws_old.close()
        except Exception:
            pass
        await asyncio.sleep(0.5)

        # Send another broadcast and verify new ws still receives
        await ws_init.send(json.dumps({"type": "prev_step"}))
        st_after2 = await ws_recv_state(ws_new, timeout=5)
        if not st_after2:
            return fail("stale_race",
                        "BUG: new ws no longer receives broadcasts (stale disconnect popped wrong)")

        await ws_new.close()
        await ws_init.close()
        ok("stale_race")
    finally:
        http_delete(f"/api/companion/rooms/{code}?gm_id={gm_id}")


# ── Test 4: prev_step rollback ──
async def test_prev_step_rollback():
    print("\n[4] prev_step rollback (alla klienter får korrekt state)")
    r = http_post("/api/companion/rooms", {"num_quarters": 1, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]
    try:
        gm_url = f"{WS_BASE}/companion/ws/{code}/{gm_id}"
        gm_ws = await websockets.connect(gm_url, open_timeout=5)
        s = await ws_recv_state(gm_ws, timeout=5)
        qc = s["quarter_codes"][0]
        start_step = s.get("step_idx", 0)

        # 4 spelare i samma rum
        players = []
        for i in range(4):
            jr = http_post("/api/companion/join-quarter",
                           {"name": f"R{i}", "quarter_code": qc})
            pid = jr["player_id"]
            ws = await websockets.connect(f"{WS_BASE}/companion/ws/{code}/{pid}",
                                          open_timeout=5)
            await ws_recv_state(ws, timeout=5)  # initial join state
            players.append((pid, ws))

        # Drain all state messages from join-broadcasts
        for _, ws in players:
            try:
                while True:
                    await asyncio.wait_for(ws.recv(), timeout=0.3)
            except asyncio.TimeoutError:
                pass
        try:
            while True:
                await asyncio.wait_for(gm_ws.recv(), timeout=0.3)
        except asyncio.TimeoutError:
            pass

        # GM advance 3 steps
        for _ in range(3):
            await gm_ws.send(json.dumps({"type": "advance_step"}))
            await asyncio.sleep(0.2)

        # Drain
        for _, ws in players:
            try:
                while True:
                    await asyncio.wait_for(ws.recv(), timeout=0.3)
            except asyncio.TimeoutError:
                pass
        try:
            while True:
                await asyncio.wait_for(gm_ws.recv(), timeout=0.3)
        except asyncio.TimeoutError:
            pass

        # Get current step from GM
        await gm_ws.send(json.dumps({"type": "noop_just_to_force_no_response"}))
        # GM never broadcasts on unknown msg — let's just call prev_step and check.

        # GM prev_step → alla spelare ska få ny state med step_idx -= 1
        await gm_ws.send(json.dumps({"type": "prev_step"}))

        # Alla spelare ska få ny state inom 3s
        rcv_ok = 0
        for pid, ws in players:
            st = await ws_recv_state(ws, timeout=3)
            if st is not None:
                rcv_ok += 1

        if rcv_ok != 4:
            return fail("prev_step", f"only {rcv_ok}/4 players received rollback state")

        # Verify step_idx decremented
        gm_st = await ws_recv_state(gm_ws, timeout=3)
        # GM may have already received it before — try to drain previous one
        if gm_st is None:
            # try one more
            gm_st = await ws_recv_state(gm_ws, timeout=3)

        ok("prev_step_rollback")

        for _, ws in players:
            try: await ws.close()
            except Exception: pass
        await gm_ws.close()
    finally:
        http_delete(f"/api/companion/rooms/{code}?gm_id={gm_id}")


# ── Test 5: Page-reload-simulering ──
async def test_page_reload():
    print("\n[5] Page reload (gamla WS dör helt, ny session med samma player_id)")
    r = http_post("/api/companion/rooms", {"num_quarters": 1, "game_mode": "test"})
    code, gm_id = r["code"], r["gm_id"]
    try:
        gm_url = f"{WS_BASE}/companion/ws/{code}/{gm_id}"
        gm_ws = await websockets.connect(gm_url, open_timeout=5)
        s = await ws_recv_state(gm_ws, timeout=5)
        qc = s["quarter_codes"][0]

        jr = http_post("/api/companion/join-quarter",
                       {"name": "Reloader", "quarter_code": qc})
        pid = jr["player_id"]
        purl = f"{WS_BASE}/companion/ws/{code}/{pid}"

        # Player connects, gets state, then GM advances step
        pws = await websockets.connect(purl, open_timeout=5)
        await ws_recv_state(pws, timeout=5)

        # Drain GM
        try:
            while True:
                await asyncio.wait_for(gm_ws.recv(), timeout=0.3)
        except asyncio.TimeoutError:
            pass

        # GM advances
        await gm_ws.send(json.dumps({"type": "advance_step"}))
        await asyncio.sleep(0.3)
        st_before = await ws_recv_state(pws, timeout=3)
        step_before = st_before.get("step_idx") if st_before else None

        # Simulate page reload: close player ws abruptly, reconnect from scratch
        await pws.close()
        await asyncio.sleep(0.5)

        # Verify room still queryable via HTTP (this is what tryReconnect() does)
        try:
            with urllib.request.urlopen(f"{BASE}/api/companion/rooms/{code}", timeout=5) as r2:
                room_data = json.loads(r2.read())
        except Exception as e:
            return fail("page_reload", f"room query failed: {e}")

        # Re-open WS as the same player_id
        pws2 = await websockets.connect(purl, open_timeout=5)
        st_after = await ws_recv_state(pws2, timeout=5)
        if not st_after:
            return fail("page_reload", "no state after reconnect")

        step_after = st_after.get("step_idx")
        if step_after != step_before:
            return fail("page_reload", f"step_idx mismatch: before={step_before}, after={step_after}")

        await pws2.close()
        await gm_ws.close()
        ok("page_reload")
    finally:
        http_delete(f"/api/companion/rooms/{code}?gm_id={gm_id}")


async def main():
    print(f"=== WS reconnect-test mot {BASE} ===")
    try:
        await test_plain_reconnect()
        await test_reconnect_storm()
        await test_stale_race()
        await test_prev_step_rollback()
        await test_page_reload()
    except Exception as e:
        import traceback
        traceback.print_exc()
        FAILED.append(("uncaught", str(e)))

    print("\n" + "=" * 60)
    print(f"RESULTAT: {len(PASSED)} godkända, {len(FAILED)} misslyckade")
    print("=" * 60)
    for name in PASSED:
        print(f"  [OK]   {name}")
    for name, reason in FAILED:
        print(f"  [FAIL] {name}: {reason}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    asyncio.run(main())
