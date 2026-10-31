# REGELBOK_CHECKLIST.md
## Synkroniseringsstatus: ÅKEPOL_Regelbok.docx vs implementation

**Regelboken är källa-sanning. Koden anpassas till regelboken — aldrig tvärtom.**

Bekräftade avvikelser (rubba ej):
- **B5:** Länsstyrelsen höjer, Skönhetsrådet sänker (regelboken säger båda sänker)
- **B4:** Energiklass E = 0 (regelboken §9.1 hade 1.00 — uppdaterad)
- **A2:** L_personal.csv har 18 kort, inte 24
- **B1:** B-ÄTA → kassan, inte TB/TG
- **E2:** EK_factor 0.10/2.00 — avsiktlig asymmetri
- Filnamn-typo `PU_markepansion.csv` (PMOPOLY) ≠ `PU_markexpansion.csv` (SPELET 2)

---

## A – Arkitektur

*(inga fynd ännu)*

---

## B – Mekanik / Ekonomi

### B-SCORE-1. ⬜ Energibonus räknas in i FV under spelet — ska bara gälla vid slutsammanräkning

**Regelboken (§9.1):** "Energibonusen räknas in BARA vid slutsammanräkningen, inte i marknadsvärdet under Skede 3." Energibonus är en multiplikator på Fp = FV × 30 % × Energibonus, alltså tillämpas den i slutformeln utanpå FV — inte som del av FV-beräkningen under löpande spel.

**Koden ([husbyggspelet.py:3718](Old/kategori5_2026-05/husbyggspelet.py:3718) och 3728–3736):** `EK_FV_MODIFIER` används i `calc_fastighetsvarde()` som multiplicerar in energiklassen direkt i FV-värdet vid varje beräkning. Det innebär att energibonusen slår igenom även under kvartalsberäkningar (köp/sälj, statusvisning, etc.) — inte bara vid slutvärderingen.

**Avvikelse:** Energibonus bäddas in i FV under hela spelet; regelboken kräver att den BARA används vid slutsammanräkning. Konsekvensen är att en energiklassuppgradering under Skede 3 omedelbart höjer marknadsvärdet (FV) och köppriset, vilket inte stämmer med regelverket.

**Plan:** Separera `calc_fastighetsvarde()` i en "ren FV"-variant utan energibonus (för löpande bruk) och applicera energibonus utanpå FV × 30 % enbart i slutvalueringen. I slutvärderingen: `fv_30 = base_fv * 0.30 * energy_bonus_factor`.

**Status:** ⬜

---

### B-SCORE-2. ⬜ Energiklass E ger 0.90 i koden, ska ge 0 (−100 %)

**Regelboken (§9.1 tabell):** "E → −100 % (0)". Energibonus för klass E är 0, dvs fastigheten bidrar med noll till Fp.

**Koden ([husbyggspelet.py:3718](Old/kategori5_2026-05/husbyggspelet.py:3718)):** `EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.90, "F": 0.00}`. Klass E = 0.90 (−10 %), klass F = 0.00. Regelboken har ingen klass F.

**Avvikelse:** E borde ge faktor 0, inte 0.90. Koden har dessutom en odefinierad klass "F" = 0.00 som saknar stöd i regelboken.

**Plan:** Ändra `EK_FV_MODIFIER` till `{"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.00}`. Ta bort "F"-nyckeln (finns ej i regelboken).

**Not:** Bekräftad avvikelse "B4: Energiklass E = 0" i hierarkin ovan stämmer med regelbok, koden har INTE korrigerats. Denna punkt är alltså en aktiv fel-implementering.

**Status:** ⬜

---

### B-SCORE-3. ⬜ EK-faktor (0.10/2.00) saknas helt i slutformelns implementation

**Regelboken (§9.1, term "Eget kapital"):** "Kvarvarande kassa minus moderbolagslån (100 Mkr per lån, oavsett att bara 95 betalades ut). Multipliceras med EK_faktor i slutformeln: 0,10 om EK ≥ 0 (positiv kassa räknas till 10 %), 2,00 om EK < 0 (moderbolagslån straffas dubbelt)."

**Koden ([husbyggspelet.py:4417–4422](Old/kategori5_2026-05/husbyggspelet.py:4417)):** `ek_verkligt = player.eget_kapital - loans_gross` — EK används rakt av i formeln utan EK_faktor-multiplikator. Varken 0.10 eller 2.00 tillämpas.

**Avvikelse:** Regelboken kräver att positiv EK skalas ned till 10 % av sitt värde, och negativ EK straffas dubbelt (2×). Koden adderar full EK-summa utan skalning. En kassa på 200 Mkr ska ge 20 Mkr i formelbidraget — koden ger 200 Mkr. En skuld på −100 Mkr ska ge −200 Mkr — koden ger −100 Mkr.

**Plan:** I slutvärderingen: `ek_factor = 0.10 if ek_verkligt >= 0 else 2.00`, sedan `ek_bidrag = ek_verkligt * ek_factor`. Notera: bekräftad avvikelse E2 i hierarkin anger att asymmetrin (0.10/2.00) är avsiktlig — det bekräftar att regelboken är rätt, koden ska ändras.

**Status:** ⬜

---

### B-SCORE-4. ⬜ Moderbolagslån-avdrag: 95 Mkr vs 100 Mkr — EK-beräkning felaktig

**Regelboken (§6.2 och §9.1):** "Lånet är 100 Mkr nominellt, bara 95 Mkr betalas ut till er kassa (5 Mkr i avgift). Vid slutvärderingen dras hela det nominella beloppet (100 Mkr) från eget kapital."

**Koden ([husbyggspelet.py:4417–4419](Old/kategori5_2026-05/husbyggspelet.py:4417)):** `loans_gross = abt_loans_net + abt_borrow_cost`. Här är `abt_loans_net` = nettot som betalades ut (95 per lån) och `abt_borrow_cost` = avgiften (5 per lån). Summan = 100 Mkr per lån. Detta verkar korrekt i princip.

**Kontrollbehov:** Verifiera att `abt_loans_net` verkligen sätts till 95 (inte 100) per lån, och att `abt_borrow_cost` sätts till 5 per lån. Om så är fallet är logiken korrekt men indirekt — en explicit kontroll mot regelbok-definitionen behövs.

**Status:** 🟡 (kräver verifiering av indata, logiken ser korrekt ut)

---

### B-SCORE-5. ⬜ Quiz-poäng ingår i regelbokens slutformel men saknas i koden

**Regelboken (§1.1 och §9.1):** "Slutpoäng = Mu × (Fp + Eget kapital + TB) ÷ (BTA / 1000) + quiz". Termen "+quiz" är explicit del av formeln.

**Koden ([husbyggspelet.py:4421–4428](Old/kategori5_2026-05/husbyggspelet.py:4421)):** `score_abs = total_fv + ek_verkligt + tb` följt av `rapoang = (score_abs / total_bta * 1000)`. Ingen quiz-poäng adderas. Varken quiz-variabel, quiz-inmatning eller quiz-beräkning förekommer i koden.

**Avvikelse:** En hel poängkategori (+quiz) saknas i slutberäkningen. Beroende på quiz-poängens storlek kan detta påverka vinnaren.

**Plan:** Fråga Niklas om quiz-poäng: Hur räknas de? Är det ett fast antal poäng från ett faktafråge-quiz utanför spelet, eller en mekanik som ännu inte implementerats? Registrera som ❓ tills svar finns.

**Status:** ❓

---

### B-SCORE-6. ⬜ Sålda BRF-projekts BTA räknas inte in i BTA-divisorn vid slutvärdering

**Regelboken (§9.3):** "Vid slutvärderingen räknas total BTA som summan av alla projekt kvarteret PLACERAT på marken (inklusive expansioner), plus BRF som sålts efter Skede 2, plus eventuella fastigheter som köpts på sekundärmarknaden under Förvaltningen."

**Koden ([husbyggspelet.py:4394–4403](Old/kategori5_2026-05/husbyggspelet.py:4394)):** `total_bta = 0` och sedan `total_bta += prop.bta` per fastighet i `player.fastigheter`. `player.fastigheter` är de förvaltade fastigheterna (non-BRF). Sålda BRF-projekt lagras inte separat med sin BTA — BRF-försäljningslogiken (rad 3630–3636) lägger intäkten i `player.eget_kapital` men sparar inte projektkortets BTA.

**Avvikelse:** BTA-divisorn är för liten för spelare som säljer BRF. En BRF-säljare får orättvist högt poängtal per kvm (kastan från BRF-försäljning delas på bara kvarvarande fastighets-BTA). Regelboken kallar detta explicit ett "rättviseproblem" (§9.3).

**Plan:** Lägg till fält `sold_brf_bta: int = 0` på Player. Vid BRF-försäljning: `player.sold_brf_bta += proj.bta`. I slutvärderingen: `total_bta += player.sold_brf_bta`.

**Status:** ⬜

---

### B-SCORE-7. ⬜ FV-beräkning använder driftnetto/kvartal men regelboken anger driftnetto/år × 4

**Regelboken (§9.1 tabell, rad FV):** "FV per fastighet = (driftnetto (år) × 4) ÷ (yield/100)." Driftnettot avser ett helt år.

**Kommentar:** Regelboken skriver "driftnetto (år) × 4" vilket ser konstigt ut om driftnetto redan är per år — men notera att §1.7 definierar driftnetto som "Hyresintäkter − driftkostnader" utan tidsenhet, och projektkortet anger `driftnetto` i Mkr/kvartal. Formeln driftnetto_kvartal × 4 = driftnetto_år är alltså korrekt.

**Koden ([husbyggspelet.py:3733](Old/kategori5_2026-05/husbyggspelet.py:3733)):** `annual_dn = (prop.driftnetto if prop.driftnetto else 0) * 4`. Koden multiplicerar med 4, vilket stämmer med att driftnettot på kortet är per kvartal.

**Avvikelse:** Ingen — logiken är korrekt. Men formeln `÷ (yield/100)` i regelboken ger FV = annual_dn / (yield_pct/100), vilket är vad koden gör. Markeras som ✅.

**Status:** ✅

---

### B-SCORE-8. ⬜ Fp-formeln bruten: energibonus appliceras på FV, inte på FV × 30 %

**Regelboken (§9.1):** "Fastighetspoäng (Fp) = (FV × 30 % × Energibonus)". Ordningen är: beräkna FV (utan energibonus), multiplicera med 30 %, multiplicera med energibonus.

**Koden ([husbyggspelet.py:3728–3736 och 4399–4402](Old/kategori5_2026-05/husbyggspelet.py:3728)):** `calc_fastighetsvarde()` returnerar `base_fv * modifier` (FV inklusive energibonus). Sedan i slutvärderingen: `fv_30 = fv * (1 - LOAN_RATIO)` där fv redan innehåller energibonusen. Resultatet är matematiskt ekvivalent (FV × EK-mod × 30 % = FV × 30 % × EK-mod) — men se B-SCORE-1: energibonusen slår igenom under hela spelet, inte bara i slutvärderingen.

**Avvikelse:** Matematiken i slutvärderingen ger rätt tal MEN energibonusen inbäddas i FV-värdet som används överallt (köp, sälj, statusvisning). Se B-SCORE-1 för fix.

**Status:** ⬜ (dubblettfynd av B-SCORE-1, men noterar Fp-strukturen specifikt)

---

## C – Spelmoment

*(inga fynd ännu)*

---

## D – Småfix

*(inga fynd ännu)*

---

## E – Oklart / Frågor till Niklas

### E-QUIZ-1. ❓ Quiz-termen i slutformeln — definition och implementation

**Fråga:** Slutformeln (§1.1 och §9.1) innehåller "+quiz" som sista term. Vad är quiz-poäng? Är det:
- Poäng från ett faktafråge-quiz som spelas utanför/efter spelomgången?
- En mekanik under spelet som inte ännu är implementerad?
- Alltid 0 och kan ignoreras tills vidare?

**Filen att notera svaret i:** REGELBOK_CHECKLIST.md, flytta E-QUIZ-1 till rätt sektion med Niklas bekräftelse-datum.

**Status:** ❓

---

## Logg

| Datum | ID | Händelse | Kommentar |
|-------|-----|----------|-----------|
| 2026-05-12 | B-SCORE-1 | upptäckt | Energibonus bäddas in i FV under hela spelet, ska bara gälla vid slutvärdering |
| 2026-05-12 | B-SCORE-2 | upptäckt | Energiklass E = 0.90 i kod, ska vara 0 per §9.1 |
| 2026-05-12 | B-SCORE-3 | upptäckt | EK-faktor 0.10/2.00 saknas helt i slutformel-implementation |
| 2026-05-12 | B-SCORE-4 | upptäckt | Moderbolagslån-avdrag logik behöver verifiering av indata |
| 2026-05-12 | B-SCORE-5 | upptäckt | Quiz-term i slutformeln saknas i koden — kräver Niklas-svar |
| 2026-05-12 | B-SCORE-6 | upptäckt | Sålda BRF:ers BTA räknas inte med i BTA-divisorn |
| 2026-05-12 | B-SCORE-7 | verifierat | FV-formel (driftnetto × 4 ÷ yield) korrekt i koden |
| 2026-05-12 | B-SCORE-8 | noterat | Fp-struktur matematiskt OK men se B-SCORE-1 |
| 2026-05-12 | E-QUIZ-1 | fråga | Quiz-term i slutformeln oklar — fråga till Niklas |

