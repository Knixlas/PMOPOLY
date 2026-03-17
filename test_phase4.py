"""
Phase 4 (Forvaltning) simulation test for PMOPOLY.
Walks through the entire Phase 4 state machine with 2 test players.
"""
import sys
import os
import copy
import random
import json

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Setup path and working directory
sys.path.insert(0, r"C:\PMOPOLY\backend")
os.chdir(r"C:\PMOPOLY")

from data_loader import GameData
from room_manager import GameRoom
from engine import _setup_forvaltning, _handle_forvaltning, GamePhase
from models import Player, Project

# ── Load game data ──
print("=" * 70)
print("PMOPOLY Phase 4 Simulation Test")
print("=" * 70)
print("\nLoading game data...")
game_data = GameData()

# ── Create room with 2 players ──
print("\nCreating game room with 2 players...")
room = GameRoom("test-room", "TestRoom", "Alice", game_data)
bob = room.add_player("Bob")
print(f"  Players: {[p.name for p in room.players]}")
print(f"  Player IDs: {[p.id for p in room.players]}")

# ── Setup players as if they completed Phases 1-3 ──
print("\nSetting up players with Phase 1-3 completion state...")

# Grab real projects from game data (non-BRF for interesting Phase 4)
all_projects = []
for typ, proj_list in game_data.projects.items():
    for p in proj_list:
        all_projects.append(copy.deepcopy(p))

# Filter to get a mix of types
hr_projects = [p for p in all_projects if p.typ == "Hyresrätt"]
kon_projects = [p for p in all_projects if p.typ == "KONTOR"]
lok_projects = [p for p in all_projects if p.typ == "LOKAL"]
fsk_projects = [p for p in all_projects if p.typ == "FÖRSKOLOR"]
brf_projects = [p for p in all_projects if p.typ == "BRF"]

for player in room.players:
    # Give each player 2-3 projects (mix of types including one BRF to test BRF removal)
    player.projects = []
    if player.name == "Alice":
        if hr_projects:
            player.projects.append(copy.deepcopy(hr_projects[0]))
        if kon_projects:
            player.projects.append(copy.deepcopy(kon_projects[0]))
        if brf_projects:
            player.projects.append(copy.deepcopy(brf_projects[0]))
    else:
        if lok_projects:
            player.projects.append(copy.deepcopy(lok_projects[0]))
        if fsk_projects:
            player.projects.append(copy.deepcopy(fsk_projects[0]))
        if hr_projects and len(hr_projects) > 1:
            player.projects.append(copy.deepcopy(hr_projects[1]))
        elif hr_projects:
            player.projects.append(copy.deepcopy(hr_projects[0]))

    # Set economics from Phase 1-3
    player.eget_kapital = 50.0
    player.abt_budget = 100.0
    player.abt_start = 100.0
    player.abt_overflow = 0.0
    player.abt_borrowing_cost = 0.0
    player.abt_loans_net = 0.0

    # Set energy classes for projects
    for proj in player.projects:
        player.projekt_energiklass[proj.namn] = proj.energiklass

    print(f"  {player.name}: {len(player.projects)} projects "
          f"({', '.join(p.typ + ':' + p.namn for p in player.projects)})")
    print(f"    EK={player.eget_kapital}, ABT={player.abt_budget}")
    print(f"    Energy classes: {player.projekt_energiklass}")

# ── Set phase to Phase 4 ──
room.phase = GamePhase.PHASE4_FORVALTNING
print("\n" + "=" * 70)
print("Starting Phase 4: Forvaltning")
print("=" * 70)

# ── Initialize Phase 4 ──
_setup_forvaltning(room)
print(f"\nAfter setup:")
print(f"  Quarter: {room.f4_quarter}")
print(f"  Yield B: {room.f4_yield_b}%, Yield K: {room.f4_yield_k}%")
for p in room.players:
    print(f"  {p.name}: {len(p.fastigheter)} fastigheter, "
          f"{len(p.staff)} staff, EK={p.eget_kapital:.1f}")

# ── Simulation loop ──
print("\n" + "=" * 70)
print("Running simulation loop...")
print("=" * 70)

MAX_ITER = 500
iteration = 0
errors = []

while iteration < MAX_ITER:
    iteration += 1

    # Check if finished
    if room.phase == GamePhase.FINISHED:
        print(f"\n>>> GAME FINISHED at iteration {iteration}")
        break

    # Check pending action
    pa = room.pending_action
    if pa is None:
        print(f"\n[{iteration}] WARNING: No pending action, phase={room.phase}, sub={room.sub_state}")
        # Try to check if we're stuck
        errors.append(f"No pending action at iter {iteration}")
        break

    player_id = pa.get("player_id")
    player = room.get_player(player_id)
    action_type = pa.get("action")
    sub = room.sub_state
    player_name = player.name if player else "???"

    # Build action based on current state
    action = None
    description = ""

    if sub in ("f4_hire_staff", "f4_rehire"):
        # Hiring: pick first available staff if must_hire, otherwise skip
        must_hire = pa.get("must_hire", False)
        available = pa.get("available", [])
        current_cap = pa.get("current_cap", 0)
        required = pa.get("required", 0)
        has_fc = pa.get("has_fc", False)

        if must_hire and available:
            # Need FC? Pick an FC first
            if not has_fc:
                fc_staff = [s for s in available if s.get("roll") == "FC"]
                if fc_staff:
                    staff_pick = fc_staff[0]
                else:
                    staff_pick = available[0]
            else:
                # Need more capacity
                staff_pick = available[0]
            action = {"action": "f4_hire", "value": staff_pick["id"]}
            description = f"Hire {staff_pick.get('namn', staff_pick['id'])} ({staff_pick.get('roll', '?')})"
        else:
            # Done hiring
            action = {"action": "f4_hire", "value": None}
            description = "Done hiring (skip)"

    elif sub == "f4_world_event":
        action = {"action": "continue"}
        description = f"World event: {pa.get('message', '')}"

    elif sub == "f4_rent_result":
        action = {"action": "continue"}
        description = f"Rent negotiation result"

    elif sub == "f4_mgmt_events":
        action = {"action": "continue"}
        mgmt = pa.get("mgmt_results", [])
        description = f"Mgmt events ({len(mgmt)} cards)"

    elif sub == "f4_energy_upgrade":
        # Skip energy upgrades to keep test simple
        action = {"action": "f4_energy_upgrade", "value": None}
        description = "Skip energy upgrade"

    elif sub == "f4_market":
        # Skip market (no buy/sell)
        action = {"action": "f4_market", "value": "skip"}
        description = "Skip market"

    elif sub == "f4_market_sell":
        # Skip selling
        forced = pa.get("forced", False)
        if forced and pa.get("sell_list"):
            action = {"action": "f4_market_sell", "value": 0}
            description = "Forced sell first property"
        else:
            action = {"action": "f4_market_sell", "value": None}
            description = "Skip selling"

    elif sub == "f4_market_buy":
        # Skip buying
        action = {"action": "f4_market_buy", "value": None}
        description = "Skip buying"

    elif sub == "f4_player_info":
        action = {"action": "continue"}
        description = "Continue from player info"

    elif action_type == "continue":
        action = {"action": "continue"}
        description = f"Continue ({sub})"

    else:
        print(f"\n[{iteration}] UNHANDLED: sub={sub}, action={action_type}")
        print(f"  pending_action keys: {list(pa.keys())}")
        errors.append(f"Unhandled state: sub={sub}, action={action_type}")
        break

    # Execute action
    print(f"[{iteration:3d}] Q{room.f4_quarter} {player_name:6s} | {sub:25s} | {description}")

    result = _handle_forvaltning(room, player, action)
    result_type = result.get("type")

    if result_type == "error":
        err_msg = result.get("message", "Unknown error")
        print(f"       ERROR: {err_msg}")
        errors.append(f"Iter {iteration}: {err_msg} (sub={sub}, action={action})")
        # If must_hire error and we sent None, try hiring first available
        if "anställa" in err_msg.lower() and pa.get("available"):
            fallback = pa["available"][0]
            action = {"action": "f4_hire", "value": fallback["id"]}
            print(f"       RETRY: Hiring {fallback.get('namn', fallback['id'])}")
            result = _handle_forvaltning(room, player, action)
            if result.get("type") == "error":
                print(f"       RETRY FAILED: {result.get('message')}")
                break

    # Print events from result
    for ev in result.get("events", []):
        ev_text = ev.get("text", "")
        if ev_text:
            print(f"       >> {ev_text}")

else:
    if room.phase != GamePhase.FINISHED:
        print(f"\n>>> MAX ITERATIONS ({MAX_ITER}) reached without finishing!")
        errors.append("Max iterations reached")

# ── Final results ──
print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)
print(f"Phase: {room.phase}")
print(f"Iterations used: {iteration}")
print(f"Final quarter: {room.f4_quarter}")
print(f"Yield B: {room.f4_yield_b:.2f}%, Yield K: {room.f4_yield_k:.2f}%")

print("\nPlayer scores:")
for p in room.players:
    print(f"  {p.name}:")
    print(f"    EK:         {p.eget_kapital:.1f} Mkr")
    print(f"    FV (30%):   {p.f4_fv_30:.1f} Mkr")
    print(f"    Real EK:    {p.f4_real_ek:.1f} Mkr")
    print(f"    TB:         {p.f4_tb:.1f} Mkr")
    print(f"    Score:      {p.f4_score:.1f} Mkr")
    print(f"    Fastigheter: {len(p.fastigheter)}")
    print(f"    Staff:      {len(p.staff)}")

if errors:
    print(f"\nERRORS ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print("\nNo errors encountered!")

# Verification
if room.phase == GamePhase.FINISHED:
    print("\n>>> PASS: Phase 4 reached FINISHED state successfully!")
else:
    print(f"\n>>> FAIL: Phase is {room.phase}, expected FINISHED")

print("\n" + "=" * 70)
print("Test complete.")
print("=" * 70)
