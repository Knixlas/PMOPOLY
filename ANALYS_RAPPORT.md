# Analys-rapport — kvarvarande checklist­punkter

Granskning av kod mot regelboken efter Paket 1–7 är mergade. Fokus: B6, C9, E2, E3.

Status-emoji: ✅ ok · ⚠️ avvikelse · ❓ behöver klargörande

---

## B6. ✅ T-utfall startvärde + tak-justering

**Regelboken (§3.1, §5.2):** T-utfall (färgad kub) startar på 12. I Planeringens setup ökar det med kvarterets HÖGSTA projekts T-värde (max +2 till 14). Kan aldrig sjunka under 8.

**Koden:**
- [`backend/config.py:18`](backend/config.py:18): `MIN_T = 8` ✅
- [`backend/engine.py:1003`](backend/engine.py:1003): `p.pl_t = 12 + max_t - p.t_bonus` ✅ (vid Skede 2-setup)
- [`backend/engine.py:1143/1182/1379/1420`](backend/engine.py:1143): alla T-justeringar har `max(MIN_T, ...)` ✅

**Datavalidering:** Alla projekt i `data/1_projektutveckling/PU_projekt.csv` har T-värden ≤ 2. Eftersom max projekt-T är 2 ger formeln naturligt T-utfall ≤ 14. Ingen explicit cap behövs idag.

**Status:** ✅ Korrekt. Om datan ändras så att projekt får T > 2 behövs en cap, men idag matchar regelboken.

---

## C9. ⚠️ Sekundärmarknad — förenklad mekanik, saknar budgivning

**Regelboken (§8.6):**
- Bud läggs på det totala marknadsvärdet
- Köparen betalar **bara 30 % kontant** (70 % lånefinansiering)
- **Lägsta accepterade bud är 80 %** av MV
- **Banken köper alltid tillbaka för 80 %**
- DD-kort dras vid varje köp

**Koden:**
- [`backend/config.py:33`](backend/config.py:33): `LOAN_RATIO = 0.70` → `1 - 0.70 = 0.30` ✅ matchar 30 %
- [`backend/engine.py:3510`](backend/engine.py:3510): `cost = fv * (1 - LOAN_RATIO)` ✅ köparen betalar 30 % av FV
- [`backend/engine.py:3383`](backend/engine.py:3383): `earn = fv * (1 - LOAN_RATIO)` ✅ säljaren får 30 %
- [`backend/engine.py:3521-3528`](backend/engine.py:3521): DD-kort triggas vid köp ✅

**Avvikelser:**
1. **Ingen budgivnings-mekanik** — `cost = fv * 0.30` (alltid 30 % av MV). Regelboken säger budet kan variera (80–100 %+ av MV). Koden kör fast pris = MV.
2. **Inget 80 %-golv** för bud på sekundärmarknaden.
3. **Banken-tillbaka-80 %** — det är oklart om denna existerar i koden. Vid sale `earn = fv * 0.30` ger säljaren 30 % av FV. Regelboken säger banken alltid garanterar 80 %, men 80 % är på BUDET — inte på FV. Säljaren får alltså 30 % av minst 80 % av MV = 24 % av MV. Detta är inte uttryckligen kodat.

**Frågor till dig:**
- Ska budgivnings-mekanik byggas in i full-game mode, eller är "fast pris = MV" en medveten förenkling för spelflödet?
- Bank-tillbakaköp för 80 % — ska det implementeras (säljaren får alltid minst 0.30 × 0.80 × MV = 24 % av MV)?

I companion-mode räknar GM:n manuellt så det är inte kritiskt för fysisk plan-spel.

---

## E2. ⚠️ EK-faktor 0.10 / 2.00 — avviker från regelboken §9.1

**Regelboken (§9.1):** `Råpoäng = (FV × 30 % × Energibonus + Eget kapital + TB) ÷ (BTA / 1000)`. **Eget kapital räknas rakt av**, ingen multiplikator.

**Excel SSOT** (rad 92): `Score = (FV×30% + EK + TB) / BTA × 1000` — också utan EK-faktor.

**Koden:**
- [`backend/economics.py:152`](backend/economics.py:152): `ek_factor = 0.10 if ek >= 0 else 2.00`
- [`backend/economics.py:155`](backend/economics.py:155): `rapong = (0.30 * fv + ek_factor * ek + tb) / owned_bta * 1000`

Vid **positiv EK 100 Mkr:** koden räknar 10 Mkr (×0.10), regelboken säger 100 Mkr.
Vid **negativ EK −50 Mkr:** koden räknar −100 Mkr (×2.00), regelboken säger −50 Mkr.

**Konsekvens:** Slutpoängen blir signifikant lägre i koden än i regelbokens formel. Avvikelsen kommer från `Spelordning.docx` (gamla flödet) som sade "10 % av eget kapital" — men du har sagt att Spelordningen är inaktuell och att Excel SSOT är källa.

**Frågor till dig:**
- Ta bort EK-faktorn helt så koden matchar regelbok + SSOT (`+ ek` rakt av)?
- Eller behåll asymmetrin (EK ger lite, negativ EK straffas hårt) som spel-balans-mekanik och uppdatera regelboken §9.1 + SSOT istället?

Stort beslut — påverkar slutpoängen rejält. **Rekommendation:** ta bort faktorn och matcha regelboken (1.00). Om spelet blir för "lätt" kan straffaktorn f(n) ramparas upp istället.

---

## E3. ⚠️ Yieldkort — koden drar i Q2–Q4, regelboken/SSOT säger Q1–Q3

**Regelboken (§8.5, §8.11):** Yielden uppdateras av yieldkort, marknadsvärdet varierar mellan kvartalen.
**Excel SSOT** (rad 87): "Dra yieldkort och justera till aktuell yield" — del av kvartalsspiralen.
**Mitt prompt-förslag** (Q4): "Inget yieldkort dras detta kvartal — yielden låses".
**Spelordning.docx** (gammal): "Ändra Yield (i Q1–3)".

**Koden:**
- [`backend/engine.py:3024`](backend/engine.py:3024): `if q >= 2:` — dragning sker i Q2, Q3, Q4
- Q1 har inget kort-drag (yielden förblir startvärdet `YIELD_START_BOSTADER = 4.0`, `YIELD_START_KOMMERSIELLT = 5.0`)

**Avvikelse:** Förmodligen ska yieldkort dras i Q1–Q3 (3 dragningar totalt), inte Q2–Q4. Q4 låser yielden eftersom resultatberäkning sker före slutet.

**Mekaniskt:** koden drar 3 yieldkort totalt (Q2, Q3, Q4) — antalet är rätt, men kvartalen är förskjutna.

**Konsekvens:** I Q4 ändras yielden trots att slutvärderingen sker i Q4. I Q1 är yielden låst på startvärdet trots att den ska variera redan från Q1.

**Frågor till dig:**
- Ändra till `if q <= 3` så yieldkort dras i Q1, Q2, Q3 (Q4 låst)?
- Eller behåll Q2–Q4-drag (om det finns spel-balansmotiv)?

**Rekommendation:** Ändra till Q1–Q3 så det matchar SSOT + regelboken.

---

## Sammanfattning

| Punkt | Status | Åtgärd |
|-------|--------|--------|
| B6 T-utfall | ✅ | Inget — koden korrekt |
| C9 Sekundärmarknad | ⚠️ | Klargörande: budgivning + bank-80%-tillbakaköp |
| E2 EK-faktor | ⚠️ | **Stort beslut:** ta bort 0.10/2.00-faktorn? |
| E3 Yieldkort | ⚠️ | **Snabbfix:** byt `q >= 2` till `q <= 3` |

**Förslag på Paket 8:**
1. E3 yieldkort Q1–Q3 (snabb fix, en rad)
2. E2 EK-faktor (om du svarar "ta bort")
3. C9 sekundärmarknad-förbättringar (om du svarar något)

Säg vilka punkter du vill att jag implementerar och vilka som lämnas (eller går till regelboks-uppdatering istället).
