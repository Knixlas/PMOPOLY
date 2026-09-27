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
- **Inga kort ger kostnader eller pengar, bara påverkan på driftnettot.** 26 kort i `kortdata/`
  (händelsekort 13, DD-kort 9, kvartalskort 4) har fått dolda plus- eller minusbrickor i stället för
  engångsbelopp; korttexterna med belopp är omskrivna. 400 partier: Förvaltningsstrategierna 22–27 %;
  FC *Bostadsveteranen* 34 % är nu starkast (nästa kandidat för justering), *Nätverkaren* 20 %.
  Tryckfilerna (tryck/ut) behöver byggas om innan korten trycks.
- **Projektekonomin i "A-läge"** (omräkning i `verktyg/bygg_pu_projekt_excel.py`, källan till
  `kortdata/PU_projekt.xlsx`): marknadsvärdet × 1,3 / 1,4 / 1,5 (fördelat i kortordning inom varje typ),
  ränta 2 % (minst 1 Mkr), lån 70 % av anskaffningen. Kort med 1,4 fick en motvikt och kort med 1,5 två:
  Q eller H +1, ett leverantörskrav nivå 2 till, eller energiklass C → D. Kolumnerna *MV-faktor* och
  *Motvikt* visar vad varje kort fick. Bostäder hamnar på 60–150 tkr/kvm. DN per fastighet: median 2 → 3,5
  Mkr/år. BRF är oförändrade (annars växer startkassan kraftigt).
- **Köp med nytt lån:** köparen lånar 70 % av marknadsvärdet och betalar resten ur kassan; vid tvångsbud
  betalas hela övervärdet (0,2 × MV) med kassa. Säljaren löser sitt lån.
- **F-poängens delare 15 → 25**, så att Förvaltningen väger lika mycket som förut (F median 8,5–9).
- **FC Nätverkaren får ha 8 kort på hand.** Skölden med 8 kort prövades också men hjälpte inte (13–17 %),
  inte heller skydd för fler typer eller två gånger per kvartal – Sköldens svaghet sitter någon annanstans.

  600 partier med allt ovan: Förvaltningsstrategierna 24–28 %. FC *Bostadsveteranen* 35 %, *Den lugna*
  32 % (hyresrätterna blev värdefullare), *Nätverkaren* 22–24 % (från 20 %), *Tekniska experten* 20–25 %,
  *Förhandlaren* 17–22 %, *Skölden* 13–17 %. FS 22–28 %. TG-median 4 → 1,7: motvikterna (högre Q och H)
  gör Genomförandet något svårare. Slutpoäng median 17–19.
- **Skölden är inte svag – den hamnar hos fel kvarter.** Utan moderbolagslån har Skölden-kvarteren lika
  hög F som de andra (13,9 mot 13,2–14,9), och förmågan är värd ungefär +1 F-poäng (samma partier med
  och utan skölden). Men hälften av Skölden-ägarna har moderbolagslån: lånets 95 Mkr räknas som kassa,
  så de väljer FC sist (9.2: minst kassa väljer först) och får det som blir över. Vinstandelen speglar
  alltså lånen, inte kortet. Större hand (8), skydd för fler typer eller två gånger per kvartal gav
  ingen skillnad. Förslag om det ska rättas: välj FC i ordning efter minst *eget kapital* (eller låt
  moderbolagslånets 95 Mkr inte räknas), så får de som lånat välja först.
- **Q- och H-kravet startar på 4 i stället för 6** (3.1, Detaljplanen). Moderbolagslån: 46 % → 29 % av
  kvarteren, TG-median 1,7 → 6,0. Start 3 gav samma lånandel (27 %), så 4 räcker. De lån som är kvar
  kommer främst från Skede 2-strategin *billig* (45 % lån – billiga val ger fler konsekvens- och
  garantikort) och små kvarter (*försiktig* 40 %), där fasta kostnader väger tungt mot en liten ABT.
- **F-poängens delare 25 → 30**, eftersom färre lån gav högre F (F-median 10,8).

  600 partier med allt ovan: Skede 1 *expansiv* 32 %, *försiktig* 19 % (jämnare än förut). Skede 2
  *balanserad* 38 %, *billig* 11 %. Förvaltningsstrategierna 23–28 %. FC *Bostadsveteranen* 35 %,
  övriga 21–27 %. FS 22–29 %. Slutpoäng median 25 (PU 15, TG 6, F 11).
- **Svårighetsgrader** (väljs när partiet startas): Detaljplanens startkrav för Q och H. 400 partier per nivå:

  | Nivå | Startkrav | Moderbolagslån | TG-median | Slutpoäng, median |
  |---|---|---|---|---|
  | Lätt | 3 | 23 % | 7,7 | 29 |
  | Normal | 4 | 31 % | 6,1 | 25 |
  | Svår | 6 (den tryckta scoreboarden) | 44 % | 2,3 | 17 |

  Att överaggressiva kvarter som pressar kassan får ta lån är avsiktligt (Niklas).
- **Skölden skyddar lokal, kontor och förskola redan som junior** (förut bara lokal; senior: alla typer
  som förut). 600 partier: Skölden väljs av 24 % av kvarteren (förut 7–8 %), vinstandel 22–23 % (förut
  17–21 %), och andelen Skölden-ägare med moderbolagslån sjönk från 50 % till 26 %. Förhandlaren väljs
  mer sällan (samma kontorskvarter) men vinner 23–25 %. Bostadsveteranen 35 % är nu den som sticker ut.
- **Bostadsveteranen är inte stark – hennes kvarter är det.** Med fastighetscheferna *slumpvis utdelade*
  (så att bara kortets förmåga räknas; 600 partier) vinner hon 21 %, lägst av alla: Skölden 30 %,
  Förhandlaren 27 %, Nätverkaren 27 %, Tekniska experten 24 %, Den lugna 21 % (brus ±3). Hennes 32–36 %
  när bottarna väljer kommer av att kvarter med många hyresrätter (54 % av portföljen) väljer henne, och de
  kvarteren är starka i hela spelet. Förmågan slår nästan aldrig till: av drygt 600 underhållsvarningar
  på 300 partier gav bara 3 en tredje varning på samma fastighet och ingen en fjärde, och seniorns
  "gratis att röja" gör inget sedan varningar bara tas bort med kort. Straff vid två varningar, eller
  −1 driftnetto per varning, ändrade inte hennes vinstandel.
- **Underhållsvarningar biter nästan aldrig.** 94 % av varningarna är den enda på fastigheten, och
  straffet kommer först vid tre. Varningen är i praktiken utan verkan.
- **Bostadsveteranens nya förmåga** (beslut): en gång per kvartal (senior två) blir ett negativt
  händelsekort på en hyresrätt en underhållsvarning i stället; straffet på hyresrätter kommer vid fyra
  som förut. Seniorns döda "gratis att röja" utgår. 800 partier med slumpvis utdelade FC: alla sex
  23–27 % (Bostadsveteranen 24 %, förut 21–22 %); förmågan används 0,9 gånger per parti. När bottarna
  väljer vinner hon fortfarande 36 % – det är hyresrättskvarterens styrka, inte kortets.
- **Bottbugg i Skede 1 rättad:** 6 % av kvarteren gick ur Skede 1 utan projekt. Botten tog Lokalen Kungen
  (fem rutor lång) som första projekt, men den ryms inte på 4 × 4 utan markexpansion, och botten expanderade
  inte – sedan fick inget annat heller plats. Nu väljer botten ett startprojekt som ryms och expanderar när
  projekten inte får plats. Efter rättningen: *expansiv* 28–33 %, *försiktig* 18–19 %, moderbolagslån 22 %.
- **Hyresrättskvarteren** (1 200 partier): kvarter där minst 35 % av projekten är hyresrätter vinner 31–33 %,
  kvarter utan hyresrätter 11–15 %. Rena bostadskvarter bygger bottarna nästan aldrig (4 av 4 000), så
  "is i magen"-vägen går inte att mäta med dem. Övertaget sitter i två delar:
  - *Förvaltningen* (mätt med slumpade portföljer, samma startkassa): F per fastighet hyresrätt +3,1,
    förskola +2,3, kontor +2,1, lokal +1,4. Marknadsvärdesfaktor hyresrätt −0,3 och lokal +0,3 jämnar ut
    till +2,2–2,5 för alla (inte infört – väntar på beslut; sänker hyresrätternas DN till 1–6).
  - *Genomförandet*: TG 10 mot 7 för hyresrättsrika kvarter. Inte förklarat av byggnadsytan (BYA/BTA är
    lika). Nästa steg: mät Skede 2 med påtvingade portföljer.
