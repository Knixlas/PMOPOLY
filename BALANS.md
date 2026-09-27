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

Prövat i simuleringen (600 partier per variant), utan att ändra reglerna:

| Ändring | expansiv | försiktig |
|---|---|---|
| Som idag | 40 % | 14 % |
| Markexpansion 8 Mkr / 10 Mkr (i stället för 5) | 37 % / 40 % | 15 % / 15 % |
| Nämnden: högst 1–2 omförsök med höjda krav | 39–40 % | 14–15 % |
| Nämnden: +1 per projekt över 4 / över 5 | 39 % / 39 % | 14 % / 15 % |

| Nya nämndsiffror efter storlek, bottarna oförändrade (t.ex. 750 kvm: 1 … 2000 kvm: 4) | 46 % | 5–10 % |
| Samma nya siffror, bottarnas nämndgräns skalad i samma takt (rättvis jämförelse) | 37–39 % | 14–16 % |

Nämndsiffrorna per projekt (2026-09-27, inför omtrycket): fyra varianter prövade — ⌈BTA/500⌉,
BTA/250 − 2, en trappa 1–4 efter BTA och en trappa 0–4 där de minsta projekten går fritt. Höjs bara
siffrorna för stora projekt blir *expansiv* ännu starkare, eftersom den försiktiga spelaren då får
nästan inga projekt inom sin riskgräns. Anpassar spelarna sin riskgräns efter siffrorna (vilket
riktiga spelare gör) blir balansen densamma som i dag. Skälet: ett misslyckat nämndförsök kostar för
lite (ett steg högre krav och ett nytt försök med en tärning till), så nämndsumman begränsar aldrig
storleken på riktigt. **Nya nämndsiffror ensamma räcker alltså inte**; de behöver kombineras med en
dyrare miss i nämnden eller en kostnad som växer med storleken (se nedan). Siffrorna kan ändå
justeras vid omtrycket av andra skäl — balansen påverkas inte åt något håll.

**Slutsats:** övertaget är strukturellt. Storlek lönar sig i alla tre skedena, och små justeringar i
nämnden eller markpriset rubbar det inte. En verklig motvikt behöver en kostnad som *växer* med
storleken, till exempel:

1. brantare priser per BTA-klass i Skede 2 (större kvarter = dyrare planering och genomförande),
2. avtagande avkastning i slutpoängen (t.ex. F-poängen räknad per fastighet över en viss nivå), eller
3. att riskbufferten/tidskravet påverkas av antalet projekt.

Det är regel- och kortfrågor för dig. Motorn har parametrarna för att pröva dem snabbt. Om det är
avsikten att stora kvarter ska vinna ("bostäder är ofta bästa valet"), kan det också få stå.

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

## Regeländringar 2026-09-27 (Niklas) och deras effekt

- **Händelsekort när man tackar nej till ett draget projekt eller lämnar tillbaka ett vid Stadshuset.**
  Skede 1 i stort sett oförändrat (500 partier: expansiv 36 %, försiktig 16 %).
- **Underhållsvarningar går inte att köpa bort, bara ta bort med kort** (städning, förvaltningsstödet
  Rivaren). 400 partier: Förvaltningsstrategierna 23–29 %; FC *Den lugna* 31 % och *Bostadsveteranen*
  30 % (något starkare än förut), *Nätverkaren* 19 %. Bostadsveteranens rabatt på röjning har ingen
  verkan längre; hens tröskel (varningsstraff först vid 4 på hyresrätter) gäller fortfarande.
