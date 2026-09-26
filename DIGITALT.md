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

## Framtid: "Spela och lär dig Åkes verksamhet" (Niklas, 2026-09-26)

Ett lager ovanpå det interaktiva spelet — och även för analogt spel — där man genom att spela lär
sig Åke Sundvalls verksamhet. Byggs på **ÅSA** (verksamhetssystemet) och **ÅKE** (utbildningspaketet),
särskilt prognoskursen med filmversion.

- Spelets moment kopplas till verkliga arbetsmoment, med **mockups av våra system**: hantera en faktura
  i **Rillion**, skriva de rapporter som krävs, göra inköpsplanen i **Levkollen**, osv.
- Tekniskt: motorns styrning (varje beslut, kort och tärning passerar den) är kroken. Ett lärlager
  kan läggas på vissa händelser — "nu ska fakturan hanteras" — utan att reglerna ändras.
- Analogt spel: samma lärmoment kan följa ett fysiskt parti via läge 2/3 (appen vet var ni är).
- **Välj roller:** man väljer vilka roller man "spelar" (t.ex. projektchef, inköpare, förvaltare — kopplat
  till spelets CEO/CFO/COO och personalkort) och får lärmomenten bara för dem; resten spelas som vanligt.
- Att göra när det blir aktuellt: gå igenom ÅSA/ÅKE och prognoskursen, välj de moment som passar
  spelets skeden (Skede 1 PU, Skede 2 planering/genomförande, Förvaltning), skissa en första mockup.

## Pusslet (regelboken 4.3, förtydligat)

- Tomten är 16×16; marken 4×4 är byggrätten. **Markexpansioner läggs kant i kant med befintlig mark.**
- **Bostäder** (BRF, hyresrätt) får ligga direkt på marken **eller** i andra lagret, ovanpå andra
  projekt, och ska då vila helt på underlag. **Övriga projekt** ligger bara direkt på marken.
- Inget får sticka ut utanför mark + expansioner eller överlappa i samma lager.
- Bitarna får roteras och speglas (8 lägen). Formerna finns i kortdatan (kolumnen "Form (rutor)" i `PU_projekt.xlsx` och `PU_markexpansion.xlsx`).
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

## Köra

```bash
python verktyg/exportera_webbdata.py     # speldata + testfall ur kortdata (efter ändrad Excel)
python -m unittest discover tester       # motorn, partiet och pusslet
cd spel/webb && npm install
npm run dev                              # http://localhost:5173 — kvarterspusslet
npm test                                 # webbens regler och lösare mot motorns facit
npm run artefakt                         # publicerbar sida: dist/artefakt.html + dist/bilder/
```

## Drift

- **Railway:** projektet `akepol-spel`, tjänsten `spel`, byggs från grenen med `spel/Dockerfile` (inställt på tjänsten; `railway.toml` i roten anger bara hälsokontroll och omstart)
  (webben byggs med Node, servern kör Python). Adress: https://spel-production.up.railway.app
  Partierna sparas på volymen `partier` (/data) och återskapas när tjänsten startar om.
  Den gamla appen ligger kvar i sitt eget projekt, orörd.
- **Lokalt:** `uvicorn spel.server.app:app --port 8000` (från roten, efter `npm run build` i
  `spel/webb`), eller `npm run dev` i `spel/webb` mot servern för utveckling.

## Steg

1. **Motorn som styrbar tillståndsmaskin** — *klart:* styrning, parti, logg, uppspelning,
   återupptagning, tester (`tester/test_parti.py`). All slump går via `Slump`; bottarna har egen
   slump; bottarna fattar bara beslut och utför inga spelhandlingar själva.
   *Kvar:* läge 2-slump (fråga spelaren om tärning och kort; Skede 1–2 drar i dag ur egna
   listor och behöver namngivna högar), frågor med läsbara alternativ för gränssnittet,
   tillståndsbild för klienten.
2. **Pusslet** som fristående sida med lösare — *första versionen klar:* `motor/pussel.py` (regler
   och lösare, facit), `spel/webb/` (Svelte: dra, vrid, spegla, två lager, ångra, "Går det?",
   "Visa en lösning"), markexpansionernas former i `PU_markexpansion.xlsx`, gemensamma testfall.
   *Klart även i motorn:* Skede 1 lägger pusslet på riktigt. Markexpansioner placeras kant i kant
   (beslut `placera_markexpansion`), 4.3 är ett beslut `placering` som motorn granskar, BYA är det
   faktiska fotavtrycket (lager 1). Bottarna tar bara projekt som får plats med formerna.
   *Simulerat (400 partier):* 4,2 projekt placerade och 0,2 oplacerade per kvarter, vinnarens
   PU-poäng 18 i median (19,7 när bara rutor räknades). Expansiv Skede 1-bott vinner oftare (40 %),
   eftersom marken nu är den verkliga begränsningen.
3. **Läge 2 och 3** (formulär; värde direkt vid fysiskt spel, motorn prövas mot riktiga partier).
   *Läge 2 klart i motorn:* `Parti(..., slump="inmatad")` frågar spelarna om varje tärning ("d20",
   "tarning": [min, max]) och varje draget kort ("dra": [högens namn, [kort-id kvar]]) — frågor med
   kanal "slump". Högar i okänd ordning (`InmatadHog`) frågar när ett kort dras eller när det översta
   visas. Loggen, uppspelningen och återupptagningen fungerar likadant. Ett parti ger ~110 kortfrågor
   och ~35 tärningsfrågor per kvarter — QR-koderna blir viktiga. *Kvar:* läge 3 (bara utfall),
   gränssnittet för båda.
4. **Läge 1 online:** brädor, kort, tärningar, animeringar.
   *Första spelbara versionen klar:* spelservern (`spel/server`: rum, WebSocket per kvarter,
   sparning och återskapning), läsbara frågor för alla beslut (`motor/fragor.py`), spelläget per
   skede (`motor/lage.py`) och klienten (nytt parti, en enhet per kvarter, bordet för tärningar och
   kort, pusslet vid 4.3, slutställning). Provat med hela partier i webbläsaren i båda lägena.
   *Kvar:* brädorna och korten som grafik i spelvyn, animeringar, tärningar på skärmen.
5. **Ljud, röster (ElevenLabs) och putsning.**
6. **Stadsdelar, topplistor, prognoser.**
