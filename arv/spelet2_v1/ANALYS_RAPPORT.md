# ANALYS_RAPPORT.md
## Slutformel-granskning: ÅKEPOL_Regelbok.docx vs implementation

**Datum:** 2026-05-12
**Granskad fil:** `Old/kategori5_2026-05/husbyggspelet.py`
**Regelboken:** `Spelinstruktioner/ÅKEPOL_Regelbok.docx` (via markdown-kopia i `0. Ledning/planer/ÅKEPOL_Regelbok_md/ÅKEPOL_Regelbok.md`)

---

## 1. Regelbokens slutformel (källa-sanning)

### §1.1 och §9.1 — Exakt citat

> **Slutformel**
>
> Fastighetspoäng (Fp) = (FV × 30 % × Energibonus)
>
> Måluppfyllnad (Mu) = ej uppfyllda mål ger avdrag i procent. Tabell finns i regelhäftet 9.2.
>
> Slutpoäng = Mu × (Fp + Eget kapital + TB) ÷ (BTA / 1000) + quiz

### §9.1 — Term-för-term-definitioner

| Term | Definition |
|------|-----------|
| FV | Summan av alla kvarterets fastigheters fastighetsvärde. FV per fastighet = (driftnetto (år) × 4) ÷ (yield/100). |
| × 30 % | Eget kapital i fastigheterna. 70 % av fastighetsvärdet antas vara lånefinansierat. |
| Energibonus | Multiplikator per energiklass. Tillämpas per fastighet vid slutsammanräkningen. A=1.10, B=1.05, C=1.00, D=0.95, E=0. |
| Eget kapital | Kvarvarande kassa minus moderbolagslån (100 Mkr per lån). Multipliceras med EK_faktor: 0.10 om EK >= 0, 2.00 om EK < 0. |
| TB | Täckningsbidrag = ABT-budget − faktisk ABT-kostnad. Sätts till 0 om ABT-budget var 0 eller negativ. |
| BTA | Summan av BTA från alla placerade projekt (inkl. sålda BRF) plus köpta fastigheter. Se §9.3. |
| quiz | Tilläggspoäng från quiz-moment (definition oklar, se E-QUIZ-1). |

### §9.1 — Energibonus-tabell

| Energiklass | Multiplikator |
|-------------|--------------|
| A | 1.10 |
| B | 1.05 |
| C | 1.00 |
| D | 0.95 |
| E | 0 (−100 %) |

### §9.1 — Viktigt om energibonusen

> "Energibonusen räknas in BARA vid slutsammanräkningen, inte i marknadsvärdet under Skede 3."

### §9.2 — Straffaktor (Mu) — tabell

| n (avvikelser) | Mu |
|----------------|-----|
| 0 | 100 % |
| 1 | 90 % |
| 2 | 82 % |
| 3 | 75 % |
| 4 | 70 % |
| 5 | 65 % |
| 6 | 61 % |
| 7 | 58 % |
| 8 | 55 % |
| 9 | 52 % |
| 10 | 50 % |
| n >= 11 | max(0, 50 − (n − 10)) % |

### §9.3 — BTA-divisorn

> "Vid slutvärderingen räknas total BTA som summan av alla projekt kvarteret PLACERAT på marken (inklusive expansioner), plus BRF som sålts efter Skede 2, plus eventuella fastigheter som köpts på sekundärmarknaden under Förvaltningen."

---

## 2. Vad varje implementation faktiskt gör

### 2.1 husbyggspelet.py (Old/kategori5_2026-05/)

#### Slutvärderingens kod (rad 4387–4442)

```
for prop in player.fastigheter:
    fv = calc_fastighetsvarde(prop, y, get_prop_ek(prop, player))  # FV MED energibonus
    fv_30 = fv * (1 - LOAN_RATIO)   # × 30 %
    total_fv += fv_30
    total_bta += prop.bta   # Bara förvaltade fastigheter — sålda BRF saknas

ek_verkligt = player.eget_kapital - loans_gross   # EK utan EK_faktor
score_abs = total_fv + ek_verkligt + tb
rapoang = (score_abs / total_bta * 1000)
score_per_kvm = rapoang * penalty   # Mu-faktor korrekt
```

#### Energibonus-konstanten (rad 3718)

```python
EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.90, "F": 0.00}
```

#### Straffaktor / Mu (rad 554–571)

```python
PENALTY_TABLE = [100, 90, 82, 75, 70, 65, 61, 58, 55, 52, 50]

def qht_penalty_factor(n: int) -> float:
    if n <= 10:
        return PENALTY_TABLE[n] / 100.0
    return max(0.0, (50 - (n - 10)) / 100.0)
```

#### FV-beräkning (rad 3728–3736)

```python
def calc_fastighetsvarde(prop, yield_pct, energiklass="C"):
    annual_dn = prop.driftnetto * 4
    base_fv = annual_dn / (yield_pct / 100.0)
    modifier = EK_FV_MODIFIER.get(energiklass, 1.0)
    return base_fv * modifier   # Energibonus ingår i returvärdet
```

### 2.2 simulering.py (Old/kategori5_2026-05/)

Samlar score-nyckeln från spelomgångarnas utdata. Ingen egen score-beräkning — delegerar till husbyggspelet.py. Alla avvikelser i husbyggspelet.py propagerar till simuleringen.

### 2.3 analys_abt.py (Old/kategori5_2026-05/)

Analyserar ABT-flödet, rapporterar TB och TG. Ingen slutformel-beräkning — fokuserar enbart på ABT-ekonomi. Ingen avvikelse identifierad.

### 2.4 Förvaltning-dokumenten (4. Förvaltning/Nya Förvaltning/)

`förvaltning 2-0.md` beskriver en alternativ slutformel i tre skeden (Anskaffning/TG/DN+kassa) som avviker kraftigt från regelbok-formeln. Detta är ett utkast-dokument, inte implementation. Ingen kod kopplar till denna formel. Notera att dokumentet kan skapa förvirring — det är inte regelbokens slutformel.

### 2.5 Companion-dokument

`Old/kategori5_2026-05/Companion_Husbyggspelet_Verksamhetssystem.docx` är binärt och inte sökbart med tillgängliga verktyg. Ingen granskning möjlig.

---

## 3. Avvikelser sorterade efter allvar

### KRITISK — Ändra koden

#### AVV-1: EK-faktor saknas (regelboken §9.1)

**Regelbok:** Eget kapital multipliceras med 0.10 (om EK >= 0) eller 2.00 (om EK < 0) i slutformeln.

**Koden:** EK adderas rakt, utan skalning.

**Konsekvens:** En kassa på 200 Mkr ska bidra med 20 Mkr till poängen — koden ger 200 Mkr. En skuld på −100 Mkr ska ge −200 Mkr — koden ger −100 Mkr. EK-termens vikt i slutformeln är 5–20× för stor vid positiv kassa och halvt för liten vid skuld. Rangordningen mellan spelare kan förändras dramatiskt.

**Rekommendation:** Ändra koden. Lägg till EK_factor-multiplikator i slutvärderingen. Se REGELBOK_CHECKLIST.md B-SCORE-3.

---

#### AVV-2: Energiklass E ger 0.90, ska ge 0 (regelboken §9.1)

**Regelbok:** Energiklass E = multiplikator 0 (−100 %).

**Koden:** `EK_FV_MODIFIER["E"] = 0.90`. E-klassade fastigheter bidrar med 90 % av baspoängen.

**Konsekvens:** En fastighet med energiklass E ska nolla ut sitt Fp-bidrag helt. Koden ger istället 90 % av normalt värde. En stor E-klassad portfölj kan vinna trots regelbok-avsikten. Notera: bekräftad avvikelse B4 i hierarkin säger "E = 0 — regelboken uppdaterad", vilket innebär att regelbokens nuvarande text (E = 0) är rätt och koden fortfarande har gamla värdet.

**Rekommendation:** Ändra koden. `EK_FV_MODIFIER["E"] = 0.00`. Ta bort "F"-nyckeln. Se REGELBOK_CHECKLIST.md B-SCORE-2.

---

#### AVV-3: Energibonus appliceras under hela spelet, inte bara vid slutvärdering (regelboken §9.1)

**Regelbok:** "Energibonusen räknas in BARA vid slutsammanräkningen, inte i marknadsvärdet under Skede 3."

**Koden:** `calc_fastighetsvarde()` inkluderar alltid energibonusen. Funktionen anropas vid köp, sälj, statusvisning och slutvärdering.

**Konsekvens:** Energiuppgraderingar under Skede 3 ändrar omedelbart marknadsvärdet (FV), vilket påverkar köp-/säljbeslut. Regelboken menar att FV under Skede 3 är "rent" (utan energibonus) och att energibonusen bara premieras vid sluträkning. Det missgynnar spelare som gör sena uppgraderingar och gynnar tidiga uppgraderingar felaktigt.

**Rekommendation:** Ändra koden. Separera FV-beräkning i en ren variant (utan energibonus) för löpande bruk, och applicera energibonus i slutvärderingen. Se REGELBOK_CHECKLIST.md B-SCORE-1.

---

#### AVV-4: Sålda BRF-projekts BTA räknas inte i divisorn (regelboken §9.3)

**Regelbok:** Sålda BRF-projekts BTA ska ingå i BTA-divisorn vid slutvärderingen.

**Koden:** BTA-divisorn summerar bara `player.fastigheter` (förvaltade fastigheter). Sålda BRF-projekts BTA lagras inte.

**Konsekvens:** Spelare som säljer BRF-projekt under spelet får en artificiellt liten BTA-divisor, vilket ökar deras poäng per kvm orättvist. BRF-kassastrategin blir övervärdesatt.

**Rekommendation:** Ändra koden. Lägg till fält `sold_brf_bta` på Player, uppdatera vid BRF-försäljning, och inkludera i BTA-divisorn. Se REGELBOK_CHECKLIST.md B-SCORE-6.

---

### MEDEL — Kräver Niklas-beslut

#### AVV-5: Quiz-term saknas i slutformeln (regelboken §1.1 och §9.1)

**Regelbok:** Slutpoäng = Mu × (...) ÷ (BTA/1000) + quiz. Termen "+quiz" finns explicit i formeln.

**Koden:** Ingen quiz-variabel eller quiz-beräkning finns.

**Konsekvens:** Om quiz-poäng är avsedda att vara icke-triviala (t.ex. 10–50 poäng) kan de påverka rankingen. Om quiz alltid är 0 är avvikelsen kosmetisk.

**Rekommendation:** Fråga Niklas om quiz-termens betydelse och implementering. Se REGELBOK_CHECKLIST.md E-QUIZ-1.

---

### KOSMETISK — Dokumentera, lägre prioritet

#### AVV-6: Moderbolagslån-avdrag — indirekt korrekt men otydlig kod (regelboken §6.2 och §9.1)

**Regelbok:** "Vid slutvärderingen dras hela det nominella beloppet (100 Mkr) från eget kapital."

**Koden:** `loans_gross = abt_loans_net + abt_borrow_cost`. Om `abt_loans_net = 95` och `abt_borrow_cost = 5` per lån är summan 100 — korrekt. Men beräkningen är indirekt och beroende av att variablerna sätts rätt under spelet. Kräver verifiering av att `abt_loans_net` verkligen sätts till 95 (nettoutbetalt) per lån.

**Rekommendation:** Verifiera att lånets bokföring är konsistent. Lägg gärna till en kommentar i koden som explicit kopplar logiken till §6.2.

---

#### AVV-7: Alternativ slutformel i förvaltningsutkastet (förvaltning 2-0.md)

**Regelboken:** Slutpoäng = Mu × (Fp + EK + TB) ÷ (BTA/1000) + quiz.

**förvaltning 2-0.md:** Beskriver en treskedsformel (Anskaffning/TG/DN+kassa) som ett designutkast, utan koppling till regelbok-formeln.

**Konsekvens:** Dokumentet skapar förvirring men är inte implementation. Ingen kod kopplar till den alternativa formeln. Markera dokumentet som "utkast, ej gällande" om det ska behållas.

---

## 4. Sammanfattning

| Avvikelse | ID | Allvar | Åtgärd |
|-----------|-----|--------|--------|
| EK-faktor 0.10/2.00 saknas | B-SCORE-3 | KRITISK | Ändra koden |
| Energiklass E = 0.90, ska 0 | B-SCORE-2 | KRITISK | Ändra koden |
| Energibonus i FV under hela spelet | B-SCORE-1 | KRITISK | Ändra koden |
| Sålda BRF-BTA saknas i divisorn | B-SCORE-6 | KRITISK | Ändra koden |
| Quiz-term saknas | E-QUIZ-1 | MEDEL | Fråga Niklas |
| Moderbolagslån-avdrag indirekt logik | B-SCORE-4 | KOSMETISK | Verifiera indata |
| Alternativ formel i utkastdokument | — | KOSMETISK | Märk som utkast |

**FV-beräkningens grundformel (driftnetto × 4 ÷ yield) och Mu-tabellen (PENALTY_TABLE) stämmer mot regelboken.**

Tre kritiska fel (EK-faktor, E-klassens multiplikator, energibonus-timing) kan tillsammans förändra relativ ranking mellan spelare. Det fjärde kritiska felet (BRF-BTA) gynnar BRF-säljstrategier orättvist. Alla fyra behöver åtgärdas innan spelet kan användas för rättvisa poängjämförelser.

