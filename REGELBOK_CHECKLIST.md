# Regelbok-implementation — checklista

Tracker för diskrepanser mellan `ÅKEPOL_Regelbok.docx` (källan) och nuvarande implementation. Sorterad **biggest first**. Regelboken ändras inte; kod/data anpassas till regelboken.

Status-emoji: ⬜ ej påbörjad · 🟡 pågår · ✅ klar · ❓ behöver klargörande

---

## A. Arkitektur-skiften (störst påverkan)

### A1. ⬜ 3 skeden — "fas" bara i Skede 2.2 (Genomförande)
**Regelboken (1.4):** Spelet är **3 skeden** — Skede 1 (Projektutveckling), Skede 2 (Planering 2.1 + Genomförande 2.2 på SAMMA bräde), Skede 3 (Förvaltning).
**Koden:** `phase1_*`, `phase2_*`, `phase3_*`, `phase4_*` (4 faser). Backend, UI och companion-app använder phase1-4.
**Bekräftat med dig (2026-05-01):** Du vill ha 3 skeden. Ordet "fas" ska **bara** finnas inuti Skede 2.2 (de 8 utförandefaserna med FAS-kort).
**Plan:**
- Backend: nya identifierare `skede1_*`, `skede2_planering_*`, `skede2_genomforande_*` (där "fas" lever som sub-state), `skede3_*`
- UI/labels: alla "Fas 1/2/3/4" → "Skede 1/2.1/2.2/3"; behåll "Fas 1–8" inuti Genomförandet
- Backwards-compat: aliasera gamla phase-namnen i game state under övergången
**Omfattning:** Stor refaktor — `engine.py`, `config.py`, `phase1.js`–`phase4.js`, `instructions.js`, companion-vyer, save/load.

### A2. ⬜ CEO / CFO / COO-kort (gimmick — bara Företagskultur)
**Regelboken (1.5, 2.3):** "8 st av varje, 24 totalt".
**Faktiska data (`L_personal.csv`):** **6 av varje, 18 totalt** (CEO-1…6, CFO-1…6, COO-1…6). Avvikelse mot regelboken — du har 6 st, inte 8.
**Innehåll:** Namn (Skepparen, Förhandlaren, Värden, Profilen, Klippan, Medlaren, Urmakaren, …), specialisering, kompetenser (STA/KOM/SAM/NOG/INN/ABM), beskrivning, 4 bedrifter, bild-path, färgteman.
**Bekräftat med dig:** Korten är en gimmick / Företagskultur-touch. Enkla.
**Plan:**
- Importera L_personal.csv till `data/0_ledning/L_personal.csv` (eller liknande)
- Setup-steg innan Skede 1: välj 1 CEO + 1 CFO + 1 COO (parallellt, alla samtidigt)
- Lagra på player-state: `ceo`, `cfo`, `coo`
- Visa i companion (kort med namn + specialisering)
- Kompetensbidraget verkar redan finnas i kortdatat — verifiera om det aktiveras i Genomförandet
**Källa:** `C:\Users\niklas.sviden\OneDrive - Åke Sundvalls Byggnads AB\SPELET 2\0. Ledning\L_personal.csv`

### A3. ✅ Branding "ÅKEPOL"/"Åkepol" istället för "PMOPOLY"
Done i akepol-skin (huvudapp) + akepol-companion (companion-vyer). Återstår i: backend strängar, README, dokumentation, domännamn (`pmopoly-production.up.railway.app`).

### A4. ⬜ Dotterbolag (nytt) — 20 bolag, bara namn-input i companion
**Källa:** `L_dotterbolag.csv` — 20 dotterbolag (DB-1…DB-20: Cornelia Stadsutveckling AB, Augustkvarteret AB, Pilbäcken Kvartersbolag, …). Alla har samma beskrivning (dotterbolag till Holiday House Holding AB).
**Bekräftat med dig:** Lämnas utanför companion. Det räcker att spelaren skriver in företagsnamnet vid "login" (vi har redan `placeholder="Ert företagsnamn"` med maxlength 60).
**Status:** Ingen kodändring behövs i companion. Eventuellt visa förslag på namn (random från CSV) som inspiration — men inte hård koppling.

---

## B. Mekaniska ändringar (medelstora)

### B1. ✅ B-ÄTA flöde
Per din clarification: B-ÄTA går till kassan, ej till TB/TG.
Fixat i `backend/companion.py::_calc_tb` + alla `projectedScore`-faser + dashboard-display + player-summary i `frontend/companion.html`. Uncommittat.

### B2. ⬜ Slutformel — verifiera mot 9.1
**Regelboken:** `Råpoäng = (FV × 30% × Energibonus + Eget kapital + TB) ÷ (BTA / 1000)`
- FV per fastighet = (driftnetto × 4) ÷ (yield/100)
- TB sätts till 0 om ABT-budget var 0 eller negativ
- BTA = placerade projekt + sålda BRF + köpta fastigheter
**Koden:** Profit_score-beräkning i `companion.py::profit_score` och `companion.html::projectedScore()`. Måste granskas formel-för-formel mot 9.1.

### B3. ⬜ Måluppfyllelse-faktor f(n) — regelbokens straffaktor är "måluppfyllelsen"
**Bekräftat med dig (2026-05-01):** Det är **samma sak** som f(n) i regelboken §9.2. Måluppfyllelsen sätts av projektmålen i Skede 1 (Q-krav, H-krav, T-krav) och avgörs av utfallet i Skede 2 (Planering + Genomförande). När utfall ≠ krav → differens → straff på råpoängen. Den är inte kopplad till fastigheterna i Skede 3, utan till Genomförandet.

**Formel (regelboken §9.2 + din linjära förlängning):**
- n = Q-avvikelse + H-avvikelse + T-avvikelse (per §7.7: Q-krav − Q-utfall om Q-utfall lägre, H samma, T-utfall − 12 om T över)

| n | f(n) |
|---|------|
| 0 | 100% |
| 1 | 90% |
| 2 | 82% |
| 3 | 75% |
| 4 | 70% |
| 5 | 65% |
| 6 | 61% |
| 7 | 58% |
| 8 | 55% |
| 9 | 52% |
| 10 | 50% |
| ≥11 | max(0, 50 − (n − 10))% (sjunker 1pp per ytterligare avvikelse, går linjärt till 0 vid n=60) |

**Påverkan:** Vid Skede 2-avslut (§7.7) sparas n stycken "avvikelsekort" framför kvarteret. Vid slutvärdering: råpoäng × f(n) = slutpoäng.

**Koden:** Söker straffaktor-tabellen. Om saknas helt: implementera. Om finns med fel värden: korrigera.

**Plan att implementera:**
- Backend: ny helper `def deviation_factor(n: int) -> float` i `economics.py` eller `models.py`
- Tillämpa multiplikatorn i slutpoäng-beräkningen (`profit_score` när phase4 + final score)
- Säkerställ att n räknas korrekt i §7.7 (Q-, H-, T-avvikelser summerade och sparade på player-state)
- Companion: visa förväntad f(n) under spelet ("Du ligger på 4 fel = 70%") så ni har feedback i realtid

**Status:** Specs klara, redo att implementera.

### B4. ⚠️ Energiklass-bonus — regelboken har fel, kodens skala är nästan rätt
**Bekräftat med dig (2026-05-01):**
- A = 1,10
- B = 1,05
- C = 1,00 (referens)
- D = 0,95
- E = **0** (hård bestraffning — E-fastighet ger 0 i FV-bidrag)

**Regelboken (§9.1) har fel värden** (säger A=1.20, B=1.15, C=1.10, D=1.05, E=1.00). Behöver uppdateras.

**Koden idag:**
- `backend/config.py:39`: `EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.90, "F": 0.85}` — fel E (0.90 → 0), extra F-klass
- `frontend/companion.html:649,1479`: `eklMap = {'A':1.10,'B':1.05,'C':1.00,'D':0.95,'E':0.90,'F':0.85}` — samma fel

**Plan:**
- Byt E=0,90 → E=0 i config.py, companion.html (3 ställen)
- Avgör F-klass: ta bort eller F=0?
- Bonus tillämpas BARA vid slutsammanräkning (§9.1)
- Uppdatera regelboken §9.1 + §13 med rätt värden

### B5. ✅ Hörnrutor — Länsstyrelsen höjer, Skönhetsrådet sänker (bekräftat)
**Regelboken (3.7):** Båda "minska Q-krav och/eller H-krav totalt 2 steg".
**Bekräftat med dig:** Avsiktligt ändrat. Länsstyrelsen **höjer** valfritt krav, Skönhetsrådet **sänker**. Symmetri: en push, en pull.
**Status:** Texten i `game.js` är redan korrekt (uncommittad i dina pre-mods).

### B6. ⬜ T-utfall startvärde + tak-justering
**Regelboken (3.1, 5.2):** T-utfall (färgad kub) startar på 12. I **Planeringens setup** (inte tidigare) ökar det med kvarterets HÖGSTA projekts T-värde (max till 14). Kan aldrig sjunka under 8.
**Koden:** Behöver verifieras att T-justeringen sker exakt vid Planeringens setup-steg och att golvet 8 finns överallt.

### B7. ⬜ AC-val: kvarter med lägst ABT-kostnad väljer först
**Regelboken (5.4):** "Kvarteret med lägst ABT-kostnad väljer först. Övriga väljer i tur och ordning."
**Koden:** Verifiera att ordningen sätts dynamiskt baserat på ABT-kost.

### B8. ⬜ Personalstyrkan måste täcka antalet fastigheter (Skede 3)
**Regelboken (8.2):** "Vid köp av fastigheter måste personalens ackumulerade kapacitet vara lika eller över antalet fastigheter ni äger. Personalstyrkan kan inte minskas, även om ni har övertalighet."
**Koden:** Verifiera att köp blockeras om personalkapacitet < antal fastigheter.

### B9. ⬜ Moderbolagslån — konsekvenser i Förvaltningen
**Regelboken (6.2):** Om lån tagits:
- Säljkrav ner till 1 fastighet
- Köpstopp på sekundärmarknaden
- Uppgraderingsstopp för energiklasser
**Koden:** Verifiera att dessa restriktioner är hårda regler i engine.py.

---

## C. Spelmoment att verifiera

### C1. ⬜ Hörnrutor — pos 1, 7, 13, 19 på 24-rutors bräde
**Regelboken (3.7, 3.1):** 24 rutor i ring, 4 hörnrutor på pos 1, 7, 13, 19.
**Koden:** `backend/config.py` BOARD_SQUARES — verifiera positioner och typer matchar.

### C2. ⬜ 13 planeringssteg + 8 utförandefaser
**Regelboken (5.3, 6.7):** 13 PL-steg, 8 GF-faser. 80 kulturkort totalt (delas).
**Koden:** Datamängderna i `data/2_planering/` och `data/3_genomforande/` — räkna. `GF_Faskort_utforande.csv` har 32 rader, måste granskas (8 faser × 4 utfall = 32?).

### C3. ⬜ Mark = 4×4 (16 celler), Tomt = 16×16 (256 celler)
**Regelboken (3.2):** Mark är ursprungliga byggrätten 4×4. Tomt är hela området 16×16.
**Koden:** Pussel-logik i `frontend/js/puzzle.js`. Verifiera dimensioner.

### C4. ⬜ Markexpansion = 5 Mkr per styck
**Regelboken (3.7):** "Markexpansion kostar 5 Mkr per styck. Beloppet dras från anskaffningssumman."
**Koden:** Verifierat — `frontend/companion.html:359` använder `+ self.mark_expansions * 5`.

### C5. ⬜ Q-krav, H-krav startvärde = 6 (från Detaljplanen)
**Regelboken (3.1):** Båda startar på 6. Justeras endast under Skede 1.
**Koden:** Initial-värden i game state. Verifiera.

### C6. ⬜ Riskbuffert-regler
**Regelboken (3.6):**
- Omslag: max 1 Rb per slag, max 1 omslag per slagomgång (ingen tredje serve)
- Sänka krav vid Skede 1→2: 1 Rb = 1 steg, T ≥ 8, Q/H ≥ 0
**Koden:** Verifiera reroll-logik och kravsänkning.

### C7. ⬜ D20 + erfarenhet, max 12, gäller INTE nämndbeslut
**Regelboken (4.1, 10):** Erfarenhetstaket är 12. Vid nämndbeslut: D20 + nämndbonus från PC, **erfarenhet räknas INTE**.
**Koden:** Verifiera båda fallen.

### C8. ⬜ Kvartertyp BOSTÄDER / BOSTAD+1 / ÖVRIGA
**Regelboken (4.4):** Klassas efter projektmix när pusslet är klart. Påverkar händelsekort i PL och FAS-kort i GF.
**Koden:** Verifiera klassificeringslogik och hur kvartertyp påverkar kort-utfall.

### C9. ⬜ Köp/sälj på sekundärmarknad
**Regelboken (8.6):**
- Bud läggs på totala marknadsvärdet, men bara 30% kontant, 70% låne­finansiering
- Lägsta accepterade bud = 80% av MV
- Banken köper alltid tillbaka för 80%
- DD-kort dras vid varje köp
**Koden:** Verifiera mekanik i Förvaltningen.

### C10. ⬜ BRF-försäljning efter Skede 2
**Regelboken (7.6):** Intäkt = MV − anskaffning + rörlig intäkt (slå projektkortets tärning).
**Koden:** Verifiera formel och tärningsslag i engine.py.

### C11. ⬜ Garantibesiktning antal
**Regelboken (7.4):** 1 garantibesiktningskort per draget konsekvenskort + 1 per leverantör nivå 1-2 sparad. Alltid ≤ 0.
**Koden:** Verifiera räkneformel.

### C12. ⬜ Energiförbättring 3 Mkr/steg, flera per kvartal
**Regelboken (8.8):** "Höj energiklass ett steg per gång till en fast kostnad av 3 Mkr per steg. Ni kan göra flera höjningar samma kvartal om kvarteret har råd."
**Koden:** Verifiera kostnad och tak per kvartal.

---

## D. Småfix (kosmetiska / terminologi)

### D1. ⬜ Skedesnamn i UI
"Fas 1: Projektutveckling" → "Skede 1: Projektutveckling"
"Fas 2: Planering" → "Skede 2.1: Planering"
"Fas 3: Genomförande" → "Skede 2.2: Genomförande"
"Fas 4: Förvaltning" → "Skede 3: Förvaltning"

### D2. ⬜ Anskaffning vs anskaffningskostnad
**Regelboken (5.1):** "Skriv inte anskaffningskostnad" — anskaffningen är budget, aldrig kostnad.
**Koden:** Sök efter "anskaffningskostnad" och byt mot "anskaffning".

### D3. ⬜ Termordlista i regelboken finns — bygg in i companion-tooltips
Termer som STA/KOM/SAM/NOG/INN/ABM, BTA/BYA, ABT-budget vs ABT-kostnad etc. har klara definitioner i §11–12.

---

## E. Övrigt / oklara

### E1. ❓ Energiklass F finns i koden men inte i regelboken
Regelboken §9.1 listar bara A–E. Koden har F-klass i `eklMap` (värde 0.85). **Fråga: tas F bort eller behålls?**

### E2. ❓ EK-faktor i score (0.10 om EK ≥ 0, 2.00 om < 0)
Finns i `companion.html` profit_score. Inte i regelboken. **Är detta avsiktligt?**

### E3. ❓ Yieldkort uppdaterar yield löpande
**Regelboken (8.5, 8.11):** Marknadsvärde varierar mellan kvartalen pga yieldkort. Kolla att frontend reagerar på yield-uppdatering varje kvartal.

---

## Loggning

| Datum | Punkt | Status | Noter |
|-------|-------|--------|-------|
| 2026-05-01 | A3 | ✅ | akepol-skin + akepol-companion mergat/pushat |
| 2026-05-01 | B1 | ✅ | B-ÄTA flödar till kassan, inte TB/TG. Uncommittat i working tree. |
| 2026-05-01 | A1 | bekräftat | 3 skeden, "fas" bara i Skede 2.2 |
| 2026-05-01 | A2 | bekräftat | L_personal.csv har 6/6/6 = 18 kort (inte 24 som regelboken säger). Gimmick-stil. |
| 2026-05-01 | A4 | bekräftat | L_dotterbolag.csv lämnas utanför companion — företagsnamn-input räcker |
| 2026-05-01 | B5 | bekräftat | Länsstyrelsen höjer, Skönhetsrådet sänker — avsiktlig avvikelse från regelboken |
| 2026-05-01 | B3 | specat | Måluppfyllelse = f(n) från regelboken §9.2 + linjär till 0 vid n≥11. Ej kopplat till fastigheter, kopplat till Genomförandet. |
| 2026-05-01 | B4 | ✅ | Energiklass: A=1.10, B=1.05, C=1.00, D=0.95, E=0. F-klass borttagen. Regelbok + Verksamhetsplan uppdaterade i OneDrive. Commit `fba6b74` på `slutformel-fix`. |
| 2026-05-01 | B3 | ✅ | f(n) implementerat i `backend/economics.py` (`deviation_factor`, `calc_deviation_n`) + applicerat på slutpoäng + display i companion. Commit `fba6b74` på `slutformel-fix`. |
| 2026-05-01 | B2 | ✅ | Grundformel `+ TG` → `+ TB` (Mkr) per §9.1. TB=0 om ABT-budget ≤ 0. Commit `fba6b74` på `slutformel-fix`. |
