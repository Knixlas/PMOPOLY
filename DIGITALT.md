# ÅKEPOL digitalt — plan och beslut

Det digitala spelet byggs nytt. Den gamla appen (`backend/`, `frontend/`) används inte som grund,
får ligga kvar på Railway, och det nya spelet blir en egen tjänst.

## Beslut (Niklas, 2026-09-26)

- **Grafiken är densamma som på brädor och kort.** Brädornas PDF:er (`tryck/brada/`) och
  kortmallarna (`tryck/kortmallar.py`) är källan, så skärm och tryck alltid stämmer.
- **Tre sätt att spela, en motor:**
  1. *Online* — motorn slår och drar, med animeringar, ljud och röster.
  2. *Bräde + logg* — ni spelar fysiskt och anger vilka kort ni drog och vad tärningen visade.
  3. *Bräde + utfall* — ni anger bara vad som hände; appen loggar och räknar.
- **Varje kvarter har en egen enhet** (mobil/surfplatta).
- **Ingen inloggning** än så länge.
- **Röster** via ElevenLabs (Niklas har API).
- **QR-koder på korten** vid nästa tryck, så att läge 2 kan skanna kortet i stället för att skriva ID.
- **Senare:** stadsdelar (spelplan med 1–4 kvarter), topplistor och prognoser över vem som ligger bäst till.

## Pusslet (regelboken 4.3, förtydligat)

- Tomten är 16×16; marken 4×4 är byggrätten. **Markexpansioner läggs kant i kant med befintlig mark.**
- **Bostäder** (BRF, hyresrätt) får ligga direkt på marken **eller** i andra lagret, ovanpå andra
  projekt, och ska då vila helt på underlag. **Övriga projekt** ligger bara direkt på marken.
- Inget får sticka ut utanför mark + expansioner eller överlappa i samma lager.
- Bitarna får roteras och speglas (8 lägen). Formerna finns i `data/shapes.json`.
- Samma regelfunktion på servern (facit) och i webbläsaren (direkt återkoppling), med gemensamma testfall.
- En lösare (backtracking) svarar på "går det att få in?" — ledtråd, bättre bottar, lägen 2–3.

## Arkitektur

- **Motorn** (`motor/`) är facit för reglerna. Den körs oförändrad; allt den behöver utifrån går
  genom **styrningen** (`motor/styrning.py`):
  - *beslut*: varje anrop till ett kvarters strategi — en bott svarar, en människa tillfrågas,
    eller svaret läses ur loggen;
  - *slump*: tärningar och kort — digitalt, inmatat (fysiskt spel) eller ur loggen.
- **Partiet** (`motor/parti.py`) kör hela spelet (Skede 1 → 2 → Förvaltning) i en egen tråd och
  stannar vid varje fråga till en människa. Allt loggas som JSON; loggen + regelversionen räcker för
  att spela upp partiet igen eller återuppta det efter en omstart.
- **Server:** Python/FastAPI, WebSocket per parti, servern bestämmer. Partiloggar i databas.
- **Klient:** TypeScript + Svelte + Vite, brädor och pussel i SVG, kort ur kortmallarna.
- **Prognoser** (senare): bottarna spelar klart från nuläget några hundra gånger → vinstchans per kvarter.

## Steg

1. **Motorn som styrbar tillståndsmaskin** — *klart:* styrning, parti, logg, uppspelning,
   återupptagning, tester (`tester/test_parti.py`). All slump går via `Slump`; bottarna har egen
   slump; bottarna fattar bara beslut och utför inga spelhandlingar själva.
   *Kvar:* läge 2-slump (fråga spelaren om tärning och kort; Skede 1–2 drar i dag ur egna
   listor och behöver namngivna högar), frågor med läsbara alternativ för gränssnittet,
   tillståndsbild för klienten.
2. **Pusslet** som fristående sida med lösare — du provar det tidigt. Motorn går från att räkna
   rutor till riktig geometri.
3. **Läge 2 och 3** (formulär; värde direkt vid fysiskt spel, motorn prövas mot riktiga partier).
4. **Läge 1 online:** brädor, kort, tärningar, animeringar.
5. **Ljud, röster (ElevenLabs) och putsning.**
6. **Stadsdelar, topplistor, prognoser.**
