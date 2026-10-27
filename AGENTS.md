# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this is

PMOPOLY ("Åkepol" / "Husbyggspelet") is a Swedish multiplayer property-development board game shipped as a single FastAPI app. The same backend serves **two distinct front-ends**:

- **Online multiplayer game** at `/` — fully digital, 1–4 players, server-driven state machine that enforces every rule.
- **Companion app** at `/companion` — assistant for **physical** in-person sessions. It tracks state, draws cards, runs quizzes, and shows GM/dashboard views, but humans roll dice and move pieces on the physical board.

Both share the same data files and the same `GameData` loader, but they are otherwise separate code paths (`engine.py` vs `companion.py`). UI text, rules, comments and CSV column headers are in Swedish — keep new content in Swedish to match.

## Running it

```
# Local dev (Windows)
start.bat                          # installs deps + runs uvicorn with --reload on :8000

# Direct
pip install -r backend/requirements.txt
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

No frontend build step — `frontend/` is plain HTML + ES modules + CSS, served by FastAPI's `StaticFiles`. `js/` and `css/` use `NoCacheStaticFiles` (see `backend/main.py:130`) so hard refresh is enough during dev.

Deployment is via Docker / Railway (`Dockerfile`, `railway.toml`); healthcheck is `GET /health`.

### Tests
There is no pytest suite. Validation scripts live at the repo root and in `tools/`:
- `python test_phase4.py` — end-to-end simulation of Phase 4 state machine
- `python tools/stresstest_companion.py` — companion stress test
- `python tools/validate_prompts.py` — sanity-check stegprompt data

## Architecture

### Backend (`backend/`, FastAPI)
- `main.py` — REST + WebSocket routes for **both** apps. Online: `/api/rooms/*`, `/ws/{room_id}/{player_id}`. Companion: `/api/companion/*`, `/companion/ws/{code}/{player_id}`.
- `data_loader.py` — `GameData` loads every CSV/XLSX/JSON in `data/` at startup. `detect_encoding()` tries utf-8-sig → utf-8 → cp1252 → latin-1 because CSVs are exported from Excel and arrive in mixed encodings. CSVs use **`;` as delimiter**.
- `config.py` — all game constants (board squares, dice map, phase costs, yield modifiers, planning step order) and CSV path map (`DATA_FILES`).
- `models.py` — dataclasses + `GamePhase` enum. The enum drives the online game's state machine.
- `room_manager.py` — `GameRoom` holds **all** mutable state for an online game (decks, turn order, per-phase scratch state).
- `engine.py` — single entry point `process_action(room, player_id, action)` (`engine.py:21`) dispatches on `room.phase` to `_handle_*` functions, one per `GamePhase`. The room is mutated in place; result events are broadcast by `ws_handler.py`.
- `economics.py` — Phase 1 economic calculations split out from `engine.py`.
- `ws_handler.py` — `ConnectionManager` broadcasts. Note the special `broadcast_state` path during `PUZZLE_PLACEMENT`, which sends **per-player** state instead of shared state.
- `companion.py` — entirely separate `CompanionRoom`/`CompanionPlayer` model with its own websocket handler and phase/step definitions. Phases can be overridden by `data/companion_texts.json` (see `_load_phases_from_json` in `companion.py:12`).

### Frontend (`frontend/`)
- `index.html` + `js/app.js` — online game entry. View switcher (`lobby` / `waiting` / `game`) + WebSocket reconnect loop. Phase-specific UI lives in `js/phase1.js` … `phase4.js`, dispatched from `js/game.js`.
- `js/components.js` — shared SVG board rendering, dice/card modals, instruction overlay.
- `js/puzzle.js` — Phase 1 puzzle placement (16-cell base grid + Mark expansion pieces).
- `companion.html` (~4300 lines, single page) — the entire companion UI; loads `/companion/ws/{code}/{player_id}` and switches between GM and player views based on `is_gm` in the state payload.
- `companion-dashboard.html`, `companion-quiz-dashboard.html` — public read-only dashboards (e.g. projected on a screen during a session).
- `balansrakning.html` — printable paper fallback form if the app fails mid-conference.
- `analytics.html` — viewer for archived games in `data/game_logs/`.

### Data flow (CRITICAL)

CSV game data is **edited externally**, not in this repo. The source of truth is OneDrive:
```
C:\Users\niklas.sviden\OneDrive - Åke Sundvalls Byggnads AB\SPELET 2
```
PMOPOLY/data/ is a **one-way mirror**. Sync with `sync_csv.sh` (bash) or `python tools/sync_from_spelet2.py` (preferred — handles cp1252 → utf-8 and combines split files). Before any task that depends on CSV content, sync first.

Known filename mismatches that the sync script intentionally preserves:
- SPELET 2 `PU_markexpansion.csv` → PMOPOLY `PU_markepansion.csv` (typo kept)
- SPELET 2 `GF_faskort.csv` → PMOPOLY `GF_Faskort_utforande.csv`
- SPELET 2 has `PU_BTA.csv` + `PU_BYA.csv` separately; PMOPOLY combines into `PU_BTABYA.csv`
- SPELET 2 has `PU_personal.csv` + `PL_personal.csv`; PMOPOLY combines into `data/PU_PL_personal.csv` (root, not in a subfolder)

### Game state model

Rule-of-thumb terminology: the rule book calls these "Skede 1 / 2.1 / 2.2 / 3", but the code calls them `phase1` / `phase2` / `phase3` / `phase4`. There is an open refactor to align these (`REGELBOK_CHECKLIST.md` A1) — don't rename casually, the strings appear in CSVs, JSON state, and frontend dispatch.

`GamePhase` (in `backend/models.py:10`) enumerates every state machine node; `engine.py:21` is the only entry point. To add a new step:
1. Add a `GamePhase` enum value
2. Add a branch in `process_action`
3. Add the `_handle_*` function that mutates `room` and returns `{"events": [...]}`
4. Set `room.phase = GamePhase.NEXT` at the end of the previous handler

### Companion vs online — when adding features

- If the rule needs server-enforced legality (online game): change `engine.py`.
- If it's an aid for humans playing physically (companion): change `companion.py` + `companion.html`.
- Shared static reference data (CEO/CFO/COO cards, DD cards, etc.) → CSV in `data/`, loaded by both. New companion-only structured content can be added to `data/companion_texts.json` or `data/quiz_questions.json`.

## Conventions

- **Language**: All user-facing strings, UI labels, CSV columns, and comments are Swedish. Match the existing tone (informal, "du"-form).
- **CSV files**: delimiter `;`, encoding usually cp1252 from Excel — use `data_loader.detect_encoding()` when reading new ones.
- **No build tools**: don't introduce a bundler, TypeScript, or a CSS preprocessor. Frontend is plain ES modules.
- **Single-process state**: everything is in-memory in `RoomManager` / `CompanionManager`. There is no DB. Saved setups go to `data/room_setups/`, `data/quiz_setups/`; finished games to `data/game_logs/`.
- **Windows-first**: the working directory is `C:\pmoPOLY`. Use the `Bash` tool when you need a POSIX shell (sync script, git tricks); PowerShell is the default.

## Imported Claude Cowork project instructions

Det här är den digitala versionen av ÅKEPOL
