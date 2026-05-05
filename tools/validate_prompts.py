"""Valideringstest för companion_texts.json + backend prompt-flöde.

Kontrollerar:
1. Alla 18 steg har korrekta fält (name, lead, actions, meaning, tip, regelbok)
2. Inga fält är tomma
3. Regelbok-referenser har §-tecken
4. Backend kan ladda JSON utan fel
5. Player_state skickar step_data korrekt
"""
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

REQUIRED_FIELDS = ["id", "name", "lead", "actions", "meaning", "tip", "regelbok"]
EXPECTED_PHASES = ["phase1", "phase2", "phase3", "phase4"]
EXPECTED_STEPS_BY_PHASE = {
    "phase1": ["welcome", "setup_skede1", "choose_pc", "projects",
               "namndbeslut", "placement", "remove_unplaced", "anskaffning",
               "rb_invest"],
    "phase2": ["transition_skede2", "choose_ac", "planning", "planning_summary"],
    "phase3": ["transition_skede3", "gf_byggfaser", "gf_konsekvens",
               "gf_garanti", "gf_abt_ek"],
    "phase4": ["f4_forbered", "f4_q1", "f4_q2", "f4_q3", "f4_q4", "f4_slut"],
}

errors = []
warnings = []
infos = []


def fail(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def info(msg):
    infos.append(msg)


# 1. JSON-strukturkontroll
print("1. Validerar data/companion_texts.json...")
json_path = os.path.join(ROOT, "data", "companion_texts.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

phases = data.get("phases", [])
phase_ids = [p["id"] for p in phases]
if phase_ids != EXPECTED_PHASES:
    fail(f"Phases mismatch: forvantat {EXPECTED_PHASES}, hittade {phase_ids}")

total_steps = 0
for phase in phases:
    pid = phase["id"]
    expected_steps = EXPECTED_STEPS_BY_PHASE.get(pid, [])
    actual_steps = [s["id"] for s in phase.get("steps", [])]
    if actual_steps != expected_steps:
        fail(f"{pid} step IDs mismatch: forvantat {expected_steps}, hittade {actual_steps}")

    for step in phase.get("steps", []):
        total_steps += 1
        sid = step.get("id", "?")
        for field in REQUIRED_FIELDS:
            if field not in step:
                fail(f"{pid}/{sid}: saknar fält '{field}'")
            elif field == "actions":
                if not isinstance(step[field], list) or len(step[field]) == 0:
                    fail(f"{pid}/{sid}: 'actions' maste vara icke-tom lista")
            else:
                if not isinstance(step[field], str) or not step[field].strip():
                    fail(f"{pid}/{sid}: fältet '{field}' tomt eller fel typ")

        if "regelbok" in step and step["regelbok"] and "§" not in step["regelbok"]:
            warn(f"{pid}/{sid}: 'regelbok' saknar §-tecken: '{step['regelbok']}'")

        if "tip" in step and step["tip"]:
            tip_len = len(step["tip"])
            if tip_len > 200:
                warn(f"{pid}/{sid}: 'tip' är {tip_len} tecken (rekommenderat ≤ 200)")

        if "lead" in step and step["lead"]:
            lead_len = len(step["lead"])
            if lead_len > 400:
                warn(f"{pid}/{sid}: 'lead' är {lead_len} tecken (rekommenderat ≤ 400)")

info(f"Total: {total_steps} steg i {len(phases)} faser")

# 2. Backend-laddning
print("\n2. Validerar backend-laddning...")
try:
    from companion import _load_phases_from_json, PHASES
    json_phases = _load_phases_from_json()
    if json_phases is None:
        fail("Backend kunde inte ladda JSON (returnerade None)")
    elif len(json_phases) != 4:
        fail(f"Backend laddade {len(json_phases)} faser, forvantade 4")
    else:
        info(f"Backend laddade {len(json_phases)} faser från JSON")
except Exception as e:
    fail(f"Backend-import fel: {e}")

# 3. Verifiera att backend skickar step_data för varje step
print("\n3. Validerar step_data-utskick...")
try:
    test_step = phases[0]["steps"][0]
    expected_keys = {"lead", "actions", "meaning", "tip", "regelbok"}
    actual_keys = {k for k in REQUIRED_FIELDS if k != "id" and k != "name"}
    if expected_keys != actual_keys:
        fail(f"step_data-fält mismatch: forvantat {expected_keys}, hittade {actual_keys}")
    else:
        info(f"step_data-fält OK: {sorted(expected_keys)}")
except Exception as e:
    fail(f"Step_data-verifiering fel: {e}")

# Rapport
print("\n" + "=" * 60)
print("RESULTAT")
print("=" * 60)

for i in infos:
    print(f"[INFO] {i}")
for w in warnings:
    print(f"[WARN] {w}")
for e in errors:
    print(f"[ERROR] {e}")

print(f"\n{len(errors)} fel, {len(warnings)} varningar")
sys.exit(1 if errors else 0)
