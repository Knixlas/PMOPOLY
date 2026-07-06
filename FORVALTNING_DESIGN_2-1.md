# Förvaltning 2.1 — designdokument

*Resultat av designsessionen 2026-07. Detta är en omstart av förvaltningslogiken
(Skede 3) och ersätter de tidigare implementationshärledda texterna
(`FORVALTNING_REGLER.md`, `förvaltning 2-0.md` m.fl.). Beskriver övergripande logik —
korttexter, FC/FS-egenskaper och exakta balanssiffror tas fram separat.*

---

## 1. Bärande idé

Förvaltningen vilar på en enda strukturell insikt:

> **Driftnetto (DN) och energiklass (EK) är tyst fysik.** De driver upp och ner hela
> kvartalet — via kort, konsekvenser och uppgraderingar — men de kostar aldrig något
> förrän **marknaden**. Där, och bara där, prissätts allt på en gång.

Konsekvenserna:

- Under kvartalet flyttar man bara **DN-brickor och energiclips**. Plånboken är stängd.
  Marknadsvärde (MV) räknas *bara* i marknadsrutan.
- Det enda **tvingande** pengaflödet är marknaden. Intäkten är pengar in;
  energiuppgradering är frivillig. Allt tvång är samlat på ett förutsägbart ställe.
- Pedagogiken blir tydlig: *byggnaden står och lever sitt liv, men det är marknaden
  som dömer.* Belåning och slarv känns först vid avräkningen — precis som i verkligheten.

---

## 2. Centrala begrepp

- **DN (driftnetto)** — årligt netto i miljoner kronor (Mkr).
  - **Bas-DN** står på kortet. **Effektiv DN** = bas-DN + energiklass-modifier.
  - **Synlig DN** ser alla; **dold DN** (nedvända brickor) känner bara ägaren till.
- **Energiklass ↔ DN är linjärt:** varje steg = 1 DN, C är nollpunkten.

  | Klass | A | B | C | D | E |
  |---|---|---|---|---|---|
  | DN-modifier | +2 | +1 | 0 | −1 | −2 |

- **Yield** — marknadens avkastningskrav. Rör sig via omvärldskort. Bostäder start 4 %
  (spann 2–6 %), kommersiellt 5 % (spann 3–7 %). **Yieldbanan är synlig för alla
  kvartalen** men kan ändras av omvärldskort.
- **MV (marknadsvärde)** = effektiv DN ÷ yield. Slås upp i MV-tabellen (aldrig räknat
  för hand). Tre kolumner per ruta: **Tvång 0,7 / Normal 1,0 / Fientlig 1,2**, avrundat
  till närmaste 5 Mkr.
- **Lån** — se §3.
- **Eget kapital i en fastighet** = MV − lån. Flyter med MV.

---

## 3. Lånemodellen — motorn

- **Lån = 70 % av MV vid förvärvet**, avrundat till närmaste 10 Mkr, capat ≤ MV.
  Läses av i samma tabelluppslag som MV och **fryser** där. Ändras aldrig medan du äger.
- **Räntan är inbakad i DN** (grundspel). Lånet kostar alltså ingenting löpande. Det
  biter bara i **tre ögonblick:** när MV < lån (banken tar fastigheten), vid försäljning,
  och vid spelslut.
- **Tryckt lån = ursprungslån.** Det gäller din byggda portfölj och normala affärer.
  Bara en fastighet som gått genom banken bär en **lån-clip** med ett nedskrivet lån
  (§6). Nästan hela spelet använder alltså det tryckta talet.

**Hävstången är hela poängen.** Exempel — Kontoret in på MV 100, lån 70, eget kapital 30:

| Händelse | Utfall |
|---|---|
| Marknaden stiger, MV 130 | eget kapital 30 → **60** (lånet kvar 70) |
| Marknaden faller, MV 90 | eget kapital → **20** |
| MV 65 < lån 70 | **banken tar den** (§6) |

En 30-procentig MV-rörelse ger 100-procentig svängning i ditt ägande. Läser du
yieldbanan och vågar lagom mycket vinner du; maxar du lånet och blundar åker du ut.

---

## 4. Uppställning (”Kvartal 0”)

Per färdigbyggd fastighet från genomförandet:

1. **Kopplade kort följer med** — garanti- och konsekvenskort som hör till projektet.
2. **Sätt energiklass** ur H-poängen (H 9–10 = A, 6–8 = B, 4–5 = C, 2–3 = D, 0–1 = E).
3. **Justera DN efter energiklass** innan första varvet. En fastighet som kommer in på
   D börjar alltså −1 DN. Lägg rätt **DN-kort** (stor synlig siffra) under fastigheten.
4. **Lånet framgår på kortet** (70 % av entry-MV). *(Komponentkrav — saknas idag.)*
5. **Dra ett händelsekort per fastighet.**

Därefter, per spelare:

6. **Välj en FC och en FS.** Båda anställs, inga kostnader. Egenskaperna är passiva
   modifierare *(tas fram separat).*
7. **Ta tre personkort.** Får spelas när som helst, om inte kortet uttryckligen säger annat.
8. **Dra tre projekt till projektbanken** (marknadsutbudet).
9. **Lägg fram yieldbanan.**

---

## 5. Kvartalsloopen

Varje kvartal, i ordning:

1. **Marknad** — spelets enda avräkning (§6).
2. **Omvärldskort** — dra ett, gör det som står. Kan flytta yieldbanan, dela ut/dra in
   personkort, ge riskbuffert m.m. (makro, träffar alla).
3. **Driftnetto** — summera all DN (synlig + dold), dela med 4, avrunda nedåt.
   Resten blir **restkort** (§9). Räntan är redan inbakad i DN.
4. **Personal** — dra två personkort. (Ingen handspärr — du får bunkra.)
5. **Händelser per fastighet** — dra ett händelsekort per fastighet (§7).
6. **Kvartalskort** — dra ett. Som omvärldskort, men rör *aldrig* yield (tempo/resurs).
7. **Energiuppgraderingar** — frivilligt (§8). Max **3 / 2 / 1** fastigheter i Q1 / Q2 / Q3.
8. **Nytt varv** → tillbaka till marknaden. I **Q4** görs poängräkning istället (§10).

DN/EK-förändringar i steg 2–7 realiseras alltså först i *nästa* marknad — man ser dem
komma och kan agera (uppgradera, köpa skydd) innan domen.

---

## 6. Marknadssteget i detalj

Ordning i marknadsrutan:

### a) Balanskrav
**Varje fastighet du håller måste vara i balans: MV ≥ lån.** Slå upp MV för alla dina
fastigheter. Är någon under vatten (MV < lån) löses den nu:

- **Banken tar fastigheten.** Ägaren får **ingen kompensation** — men betalar heller
  ingen mellanskillnad. Straffet är att tillgången (och all dold uppsida) är borta.
- Fastigheten går till banken, som disponerar den (nedan).

### b) Bankens disposition av en tvångstagen fastighet
Två vägar:

- **Fynd:** banken **skriver ner lånet till 70 % av nuvarande (nedpressade) MV** och
  listar fastigheten på marknaden — nu med en lån-clip. Skadan (låg EK, minusbrickor)
  sitter kvar. En köpare betalar MV − nedskrivet lån och får en billig fixer-upper.
- **Saneringsuppdrag (workout):** se §6f.

### c) Förhandla om köp
Flera intresserade av samma fastighet ur banken/projektbanken → **förhandling:**
slå D20 med modifierare, **högst vinner**. Lika → den med **färst fastigheter** vinner.
*(FC-förturskort gäller vid vanligt köp, men inte vid tvångsbud eller tvångstagande.)*

### d) Köp
Köparen betalar **MV − lån** och tar över fastigheten med dess (tryckta eller
nedskrivna) lån. Ett DD-kort läggs dolt på nyförvärvet.

### e) Tvångsbud (fientligt)
Buda **1,2 × MV** på en motspelares fastighet. Hen måste sälja om hen inte spelar ett
stoppkort. Budgivaren betalar 1,2 × MV − lån; offret får 1,2 × MV − sitt lån (blir
alltså **överbetalt** — därför lägger man bud bara på strategiskt viktiga fastigheter).

### f) Saneringsuppdrag (distressed workout)
En spelare kan **åta sig** en tvångstagen fastighet i stället för att den blir ett fynd:

1. Banken betalar spelaren **(lån − MV)** i kassan. Fastigheten behåller sitt (höga) lån.
2. Spelaren försöker under kvartalet få **MV ≥ lån** (energiuppgradering, plus-/energikort,
   att yieldbanan håller).
3. **Vid nästa marknad avräknas den** (balanskravet):
   - **MV ≥ lån → räddad.** Fastigheten är din, med all uppsida däröver. Du behåller
     de mottagna pengarna minus det du lagt ner.
   - **MV < lån → du betalar (lån − MV då)** och fastigheten går tillbaka till banken.

**Nettot av att ta och lämna tillbaka = MV-rörelsen över kvartalet** ((lån − MV₀) −
(lån − MV₁) = MV₁ − MV₀). Att ”ta pengarna och gå” är alltså en blind hävstångsvad på
kvartalets MV — och eftersom ett omvärldskort dras under kvartalet är det en äkta risk,
ingen gratislunch.

> **Skulden följer dig.** Har du åtagit dig en fastighet är mellanskillnaden din skuld
> **tills den löses** — antingen genom att räddas (MV ≥ lån) eller betalas av när
> fastigheten lämnar dig, vid *varje* utgång (frivillig eller tvingad). Ingen bakväg.

*Exempel, räddat:* ta över (MV 100, lån 120) → +20. Lös EK E→D för 3 Mkr, DN +1, MV når
lånet. Behåll **fastigheten och 17 Mkr**.
*Exempel, svettigt:* samma start, men energin kräver flera slag à 3 Mkr, omvärldskortet
höjer yielden och du drar ett direkt −1 DN-kort. MV sjunker till 91 → betala 120 − 91 =
**29** vid nästa marknad. Rejält minus, och fastigheten är borta.

### g) Sälj och nya rundor
Efter köp/tvångsbud får spelare sälja fastigheter (till banken för Normal-MV, netto
MV − lån). En **ny förhandlingsrunda** hålls efter sålda fastigheter. Upprepa tills
ingen längre vill köpa.

### h) Likviditet
Måste du betala (saneringsskuld, tvångsbud du tvingas möta osv.) men kassan inte räcker
→ **sälj en fastighet till fullt MV** (du får dess eget kapital, MV − lån). Ingen
brandrea-rabatt; straffet är att du tappar tillgången. *(Denna regel ersätter
moderbolagslånet i grundspelet — moderbolagslån blir en ren expansion.)*

*Kant:* kan du inte täcka ens genom att sälja allt → du är i praktiken slut (sista plats
/ avskrivning). Sällsynt; detaljregel tas senare.

---

## 7. Korten

**Bärande uppdelning:** *händelsekort placeras ofrivilligt, personkort placeras
frivilligt.* Plus/minus-brickor ackumuleras på fastigheten oavsett källa.

### Händelsekort (per fastighet — ödet)
En lek per förvaltad typ: **Hyresrätt, Förskola, Lokal, Kontor.** Drar man ett kort
för en fastighet hamnar det på just den. Innehåll:

- **Plus- / minuskort (vanligast, dolda):** ackumulerar. **3 i netto → ±1 bas-DN**
  (eller ±1 energiklass, beroende på korttyp). Alla brickor kasseras då och siffran
  ändras permanent.
- **Varningskort:** 3 på samma fastighet → permanent −1 DN.
- **Energi-varningskort:** 3 på samma fastighet → −1 energiklass.
- **Direkt ±1 DN (ovanligt, ~1 per lek):** slår direkt och permanent. ”Skräpkortet”
  som kan sänka ett saneringsuppdrag.
- **Förköps- och stoppkort:** går till **handen** som reaktiva resurser.

*Komponentmodell:* händelsekort är en **återanvändbar drakortlek** — dra, läs, lägg en
generisk **+/− - eller energibricka** på fastigheten, korten tillbaka i leken. Fastigheten
bär brickor (och den stora DN-siffran), inte själva korten. Då kan leken dras hur många
gånger som helst i ett spotlight-kvartal.

### Personkort (på hand — agency)
En gemensam lek. Får spelas när som helst om inte kortet säger annat. Innehåll:

- Placera en **plus/minus- eller energibricka** på en fastighet du *själv* väljer.
- **Modifierare på energiuppgraderingsslag** (+1/+2/+3, spelas *efter* slaget).
- **Modifierare på förhandling** (spelas *innan* slaget), eller **auto-vunnen förhandling**.
- **Stoppkort** mot tvångsbud.
- **Dra / släng personkort**, **riskbuffert** m.m.

Ingen handspärr — man får **bunkra kort** för att kunna slå till på ett saneringsuppdrag
eller en vändning över tid. *(Om hamstring gör spelet segt: inför ett generöst tak eller
en årsskiftesrensning. Börja utan.)*

### DD-kort
Dras dolt vid övergången och vid varje nytt köp. **Intäkt = pluskort, Kostnad =
minuskort** — räknas i samma ackumulering som händelsekorten. Avslöjas för alla vid
försäljning eller tvångstagande.

### Konsekvens- och garantikort
Från genomförandet, kopplade till projekten. Kan justera energiklass/DN.

### Omvärlds- och kvartalskort
Två tydliga körfält:
- **Omvärldskort = makro:** yieldrörelser och effekter som träffar alla.
- **Kvartalskort = tempo/resurs:** dra/släng personkort, riskbuffert, extra runda —
  aldrig yield.

Båda kan innehålla t.ex. ”dra ett händelsekort per fastighet av en viss typ” (skapar
typ-kluster). *Öppen fråga:* namnger kortet typen, eller har varje kvartal en fokustyp?
*(Beslutas senare.)*

---

## 8. Energiuppgraderingar

Frivilligt, max 3 / 2 / 1 fastigheter i Q1 / Q2 / Q3. Eskalerande tärning:

1. Slå **1× D20 för 3 Mkr.** Över 10 (med modifierare) → **+1 energiklass (= +1 DN)**.
2. Miss? Slå igen för 3 Mkr, nu med **2× D20** — det räcker att *en* är över 10.
3. Miss igen? 3 Mkr, **3× D20**. Och så vidare — sannolikheten närmar sig säkerhet.
4. **Slår du en 20 är den rundan kostnadsfri.**

Förväntat ~1,6 försök (~5 Mkr) för en nära garanterad uppgradering, med spänning och
inbyggd ”pity”. **Personkort-modifierare spelas efter slaget; riskbuffert kan slå om.**
Energiklass kan inte gå förbi A.

---

## 9. Personal, riskbuffert, restkort

- **FC + FS:** båda anställs, inga kostnader; passiva egenskaper *(tas fram)*.
- **Riskbuffert = omslag av ett tärningsslag** (energiuppgradering eller förhandling).
  Kan **fås från alla korttyper** — omvärld, person, kvartal. En löpande valuta.
- **Restkort:** vid DN ÷ 4 blir resten restkort. **1 restkort = 0,25 Mkr; 4 restkort =
  1 Mkr.** Vi rör bara hela miljoner; restkorten bokför avrundningen. Sparas mellan kvartal.

---

## 10. Slutpoäng (Q4)

*Bärs över från tidigare modell — kalibreras om mot den här loopen.* Tre delpoäng,
vardera ~25 vid ett riktigt bra spel, summan × måluppfyllelse-faktor:

| Skede | Formel |
|---|---|
| 1 Utveckling | total anskaffning ÷ 100 |
| 2 Byggande | TG (täckningsgrad, %) |
| 3 Förvaltning | (fastighetsvärde obelånat + kassa) ÷ faktor |

där fastighetsvärde obelånat = Normal-MV − lån, summerat. **Slutpoäng = (S1 + S2 + S3) ×
måluppfyllelse.** Divisor/faktor sätts efter provspel.

---

## 11. Öppna frågor

1. **”Gällande typ i kvartalet”** — kort namnger typen, eller fokustyp per kvartal?
2. **FC/FS-egenskaper** — ta fram arketyp-set som passar loopen.
3. **Personkorts- och händelsekortstext** — författas (rätt fördelning plus/minus/varning/
   energivarning/direkt/förköp per lek).
4. **Balanssiffror** — tvångspris 0,7 och fientligt 1,2 är tunbara; likaså saneringens
   kanter (behåller man mottaget vid misslyckande — ja i nuläget) och slutformelns faktor.
5. **Konkurskanten** — vad händer när en spelare inte kan täcka ens genom att sälja allt.

---

## 12. Komponenter (översikt)

- Spelplan: MV-tabell (+ lånekolumn), yieldbana, marknadsyta, kvartalsspår.
- Fastighetskort **med tryckt lån**.
- DN-kort (stora synliga siffror) + energiclips A–E + **+/− - och energibrickor** + lån-clips (ex-bank).
- Händelsekort: 4 typleker (återanvändbara). Personkort: en lek (får bunkras).
- DD-kort, konsekvens-/garantikort, omvärldskort, kvartalskort.
- Restkort-markörer, riskbuffert-markörer.
- Tärningar: D20 (uppgradering + förhandling), ev. D10.

---

*Detta dokument fryser den övergripande logiken. Nästa steg är att ta fram innehåll
(FC/FS, kort) och därefter kalibrera siffror mot provspel.*
