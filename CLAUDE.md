# PMOPOLY — Husbyggspelet Online

Webbaserat multiplayer-brädspel om fastighetsutveckling. Python/FastAPI-backend med
WebSocket-spelmotor och vanilla-JS-frontend. Deployas till Railway via `Dockerfile`.
Språket i kod, data och dokument är svenska — skriv kommentarer, commit-meddelanden
och dokument på svenska.

## Struktur

- `backend/` — FastAPI-app
  - `main.py` — REST-endpoints, WebSocket `/ws/{room_id}/{player_id}`, `/health`, companion-routes
  - `engine.py` — spelmotorn (tillståndsmaskin för alla skeden, ~4800 rader)
  - `companion.py` — companion-läget (GM styr fysiskt spel, spelarna följer i appen)
  - `data_loader.py` — läser in CSV/JSON från `data/` till `GameData`
  - `models.py`, `room_manager.py`, `ws_handler.py`, `economics.py`, `config.py` (spelkonstanter)
- `frontend/` — statiska HTML/JS/CSS, serveras av backend (`js/phase1-4.js` = skedena)
- `data/` — speldata som CSV per skede (`0_ledning`, `1_projektutveckling`, `2_planering`,
  `3_genomforande`, `4_forvaltning`, `4_forvaltning_v2`) plus `companion_texts.json`,
  `quiz_questions.json`, `shapes.json`
- `tools/` — hjälpskript (validering, import, stresstest)
- Rot-`.md`-filer — regelbok/design (`REGELBOK_CHECKLIST.md`, `FORVALTNING_DESIGN_2-1.md`,
  `FORVALTNING_REGLER.md`, `ANALYS_RAPPORT.md`, `FUTURE_UPGRADES.md`)

## Köra

```bash
pip install -r backend/requirements.txt
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# http://localhost:8000  ·  hälsokontroll: curl localhost:8000/health
```

## Verifiera ändringar

Det finns ingen testsvit eller linter. Innan du kallar arbetet klart:

1. Starta servern (ovan) och kontrollera att datan laddas utan fel och att `/health` svarar `{"status":"ok"}`.
2. Vid ändringar i `data/companion_texts.json` eller prompt-flödet: `python tools/validate_prompts.py` ska ge `0 fel`.
3. Vid ändringar i spelmotorn: kör det berörda flödet, t.ex. via `tools/stresstest_companion.py`
   eller `test_phase4.py` (obs: `test_phase4.py` har hårdkodade Windows-sökvägar `C:\PMOPOLY` som måste
   justeras för att köras i Linux).

## Konventioner

- `data/*.csv` synkas från en extern källa ("SPELET 2") med `sync_csv.py` — källan vinner.
  Ändra inte CSV-filerna för hand utan att säga det tydligt; föreslå hellre ändringen i källan.
- Regelboken är facit för spelmekanik. Hänvisa till paragraf (t.ex. `§8.6`) när du ändrar regler i
  koden, och uppdatera `REGELBOK_CHECKLIST.md` / `ANALYS_RAPPORT.md` om status ändras.
- Terminologi: koden använder `phase1–4`, regelboken "Skede 1–3" + Förvaltning. Blanda inte ihop
  dem i nya namn utan att kolla `FUTURE_UPGRADES.md` (A1).
- Office-filer (`.docx`, `.xlsx`) är binära — ändra dem inte om det inte uttryckligen efterfrågas.
