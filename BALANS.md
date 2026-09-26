# Balansen — läget och förslag (natten till 2026-09-27)

Mätt med bottarna i motorn (`python -m motor.simulera`), 600–1 000 partier med 4 kvarter, med
riktig pusselgeometri i Skede 1. Bottarna är inte perfekta spelare, så siffrorna säger mest om vilka
*vägar* som bär, inte exakt hur starka de är.

## Sammanfattning

| Del | Läge | Bedömning |
|---|---|---|
| Förvaltning, strategier | 23–27 % vinst (förväntat 25 %) | **Välbalanserat** |
| Förvaltning, FS-kort | 22–29 % | **Välbalanserat** |
| Förvaltning, FC-kort | Bostadsveteranen 30–34 %, övriga 20–29 % | Nästan; Skölden varierar 14–22 % (väljs sällan) |
| Skede 1 | *expansiv* 38–40 %, *försiktig* 14–15 % | **Obalanserat: fler projekt lönar sig nästan alltid** |
| Skede 2 | *balanserad* 34–40 %, *kvalitet* 28–36 %, *billig* 11–13 % | **Billigt är en fälla** — ingen fungerande lågbudgetväg |
| Vem vinner | vinnaren ledde i TG 69 %, F 65 %, PU 48 % av partierna | Inget skede avgör ensamt, TG väger tyngst |
| Marginal | median 12 poäng (10–90 %: 2–34) | Stora marginaler: tidiga övertag växer |

Slutpoäng: median 22 (10–90 %: −14 till 46). PU median 14, TG 4, F 9, Mu 0,8.

## Skede 1: varför vinner "expansiv"?

Den som tar flest projekt vinner i alla delar samtidigt: PU 18 (mot 14), TG 9 (mot 4), F 15 (mot 8).
Mu sjunker bara till 0,72 (mot 0,82). Fler projekt ger mer ABT, större kvarter och fler fastigheter
i Förvaltningen — och risken biter för lite:

- **Nämnden (4.1)** släpper igenom nästan allt till slut. Varje miss höjer kraven ett steg och ger en
  tärning till, så man kan fortsätta tills det går.
- **Markexpansionens pris** spelar nästan ingen roll: 5 → 10 Mkr ändrar expansiv från 40 % till 40 %.

**Förslag att pröva (regelboken 4.1 — ditt beslut):**
1. ~~Högst ett eller två omförsök med höjda krav.~~ Prövat: ingen effekt (expansiv 39–40 %), nämnden
   avgörs nästan alltid på första eller andra försöket.
2. Alternativt: varje projekt över fem höjer nämndsumman med +1 ("stora mixar granskas hårdare").

## Skede 2: varför är billigt en fälla?

Nivå 1 hos leverantörer och organisation missar kvalitets- och hållbarhetskraven. Det straffas tre
gånger: konsekvenskort (8.1–8.3), garantikort för varje nivå 1–2-leverantör (8.4) och Mu. Resultat:
TG ≈ 0 och Mu ≈ 0,5, slutpoäng 8–10 mot 26–29. En smartare "sparsam" bott (nivå 1 bara när kraven
ligger i fas) klarade sig ännu sämre. Budskapet "kvalitet lönar sig" går fram — men spelet har bara
två vägar i Skede 2.

**Förslag att pröva:** nivå 1 ger en tydligare prisfördel, eller garantikort bara för nivå 1 (inte 2).

## Förvaltningen

Bra som den är. Bostadsveteranen är fortfarande något stark (försvagad en gång tidigare);
Skölden väljs sällan och varierar mellan körningar, en bredare Sköld hjälpte inte i simuleringen.
Motorn har nu parametrar för Skölden (`skold_typer`, `skold_per_kvartal`) om du vill pröva.

## Nya mätverktyg

- `python -m motor.simulera` visar nu också hur ofta vinnaren ledde i PU/TG/F och vinstmarginalen.
- `motor.pu.PUParametrar.namnd_hoj_max` begränsar omförsöken i nämnden (standard: obegränsat = som idag).
