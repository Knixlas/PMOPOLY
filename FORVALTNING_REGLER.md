# Regelhäfte — Skede 3: Förvaltning

*Version från provspel-implementationen (2026-07). Denna text beskriver spelet så
som det faktiskt fungerar i den digitala provspelsversionen — den ersätter tidigare
`Regelhäfte Förvaltning.md`, som hann bli inaktuell under iterationerna.*

---

## 1. Översikt

Du har byggt färdigt dina fastigheter. Nu ska de förvaltas under ett år — fyra
kvartal, Q1 till Q4. Varje kvartal samlar du in driftnetto, hanterar händelser,
uppgraderar, köper och säljer. Vid årets slut räknas vinnaren fram.

Det finns ingen enda rätt strategi. En bred portfölj med många fastigheter kan
vinna, liksom några få välskötta premiumfastigheter. Det viktiga är helheten:
driftnetto, kassa och hur väl du undviker tvångsförsäljningar.

**Mål:** högsta slutpoäng. Slutpoängen väger tre skeden lika (utveckling, byggande,
förvaltning) och multipliceras med en måluppfyllelse-faktor.

---

## 2. Centrala begrepp

**DN (driftnetto)** — det årliga nettot från en fastighet, i miljoner kronor (Mkr).
En fastighet med DN 5 ger 5 Mkr per år.

- **Bas-DN** står förtryckt på fastighetskortet.
- **Effektiv DN** = bas-DN + energiklass-modifier (se §6). Det är effektiv DN som
  gäller för allt — intäkt, värdering och risk.
- **Synlig DN** ser alla vid bordet. **Dold DN** (från dolda kort) känner bara
  ägaren till, tills korten avslöjas.

**MV (marknadsvärde)** — vad fastigheten är värd just nu. MV = effektiv DN ÷ yield.
Du slår alltid upp MV i MV-tabellen på spelplanen — du räknar aldrig själv.

**Yield** — marknadens avkastningskrav. Rör sig under spelet via omvärldskort.
Lägre yield = högre MV (samma DN blir mer värd). Högre yield = lägre MV.
Bostäder startar på 4 % (spann 2–6 %), kommersiellt på 5 % (spann 3–7 %).

**Lån och ränta** — förtryckta på fastighetskortet (70 % av MV vid förvärv, ränta 4 %).
Räntan dras varje kvartal. Ingen valmöjlighet — det är vad kortet säger.

**Kvartalscash** — den kontanta intäkten varje kvartal = total effektiv DN ÷ 4
(avrundat nedåt). Resten hanteras med restkort (se §5c).

---

## 3. Övergången till förvaltning ("Kvartal 0")

Innan Q1 sätter ni upp varje spelares portfölj. Gör i ordning, per fastighet:

### a) Sätt energiklass
Utifrån H-poängen (Hållbarhet) fastigheten fick i byggandet:

| H-poäng | 0–1 | 2–3 | 4–5 | 6–8 | 9–10 |
|---|---|---|---|---|---|
| Energiklass | E | D | C | B | A |

Placera rätt energiklass-clip på fastigheten.

### b) Bestäm effektiv DN
Effektiv DN = bas-DN + energiklass-modifier:

| Klass | A | B | C | D | E |
|---|---|---|---|---|---|
| DN-modifier | +2 | +1 | 0 | −1 | −2 |

Lägg DN-kortet med rätt siffra under fastigheten. *Exempel: bas-DN 4, klass B → effektiv DN 5.*

### c) Lånebelopp
Lånebelopp och räntekostnad står förtryckta på kortet. Du har inget val.
Olika fastigheter får olika faktisk belåningsgrad (oftast 60–75 %) — vissa är
naturligt känsligare för yieldhöjningar än andra.

### d) Övergångsekonomi (lös byggnadskreditivet)
Räkna ut din startkassa:

> **Startkassa = TB + BRF-intäkt + summa nya lån − byggnadskreditiv**

- **TB** (täckningsbidrag) förs över från byggandet.
- **BRF säljs** direkt till föreningen: MV + 10 Mkr per BRF. BRF förvaltas inte i
  Skede 3 och tar inga kort.
- **Nya lån** = summan av lånebeloppen på dina förvaltade fastigheter.
- **Byggnadskreditiv** = din totala anskaffning.

Räcker inte kassan att lösa kreditivet måste du sälja fastigheter direkt. Hård
läxa: att bygga inom budget är livsavgörande.

### e) Dra kort på fastigheterna
Per förvaltad fastighet (ej BRF):

- **1 DD-kort** — läggs **dolt**. Intäkt-DD = pluskort, Kostnad-DD = minuskort (se §7).
- **1 händelsekort** — från typleken som matchar fastigheten (se §7).

### f) Anställ personal
Välj **en Fastighetschef (FC)** och **en Fastighetsspecialist (FS)** ur arketyperna.
Båda måste anställas. Det kostar ingenting — varje arketyp har istället egenskaper
som påverkar spelet (se §8). Valet gäller hela året.

### g) Dra personkort
Dra **2 FC-personkort och 2 FS-personkort** till din hand. Max 6 på hand totalt.

---

## 4. Kvartalsflödet (Q1–Q4)

Varje kvartal körs i denna ordning:

1. **Yield låses.** Vänd kvartalets omvärldskort i kön framför marknadskartan och
   flytta yield-pekaren enligt kortet.

2. **Risk-check.** För varje fastighet: titta på nästa kvartals yield (första kortet
   i kön) och slå upp MV vid den yielden. Är **MV lägre än lånet** — lägg en **röd
   markör**: fastigheten *riskerar tvångsförsäljning nästa kvartal* (se §9).

3. **Dra kort.** Per fastighet: 1 händelsekort och 1 DD-kort (första kvartalet redan
   gjort i övergången — gäller därefter varje kvartal). Dessutom **1 FC- + 1 FS-personkort**
   till handen (max 6 på hand).

4. **Omvärld.** Dra ett omvärldskort. Effekten är direkt (yield-rörelse, bordseffekt
   på en typ, eller liknande).

5. **Intäktsfas.** Se §5.

6. **Kvartalskort.** Dra kvartalskortet för aktuellt Q (bordsövergripande händelse
   eller tilldelning).

7. **Energiuppgradering.** Se §6.

8. **Marknad.** Se §9 (auto-tvångsförsäljning av röda fastigheter, sedan köp/sälj).

Personkort får spelas löpande när det passar (se §8).

---

## 5. Intäktsfasen

**a) Summera total effektiv DN** över alla dina fastigheter — synlig + dold. Räkna i
huvudet; andra ser bara den synliga summan.

**b) Dela med 4, avrunda nedåt.** Det är kvartalets cash i Mkr.

**c) Hantera residualen med restkort.** Det som "blir över" när DN inte är jämnt
delbart med 4 blir restkort — **1 restkort per överbliven DN-enhet** (varje enhet =
0,25 Mkr). När du samlat **4 restkort omvandlas de automatiskt till 1 Mkr cash**.
Restkort sparas mellan kvartal.

> *Exempel: total DN 19. 19 ÷ 4 = 4 Mkr cash, rest 3 → +3 restkort. Hade du 1 restkort
> sedan tidigare har du nu 4 → omvandla till +1 Mkr. Kvartalscash blir 5 Mkr.*

**d) Dra räntekostnaden** — summan av räntekostnad/kvartal från dina fastighetskort.

**e) Cash flow** = kvartalscash − ränta. Läggs till (eller dras från) din kassa.

**Q2 – hyresförhandling.** I Q2 förhandlar du om hyresnivån på dina hyresrätter. Ett
tärningsslag plus din FC:s förhandlingsvärde avgör höjningen. Personkort kan ge extra
bonus på slaget.

---

## 6. Energiklass och uppgraderingar

Energiklassen påverkar bara DN (och därmed MV via tabellen). Ingen separat
MV-justering.

Varje kvartal kan du köpa energiuppgraderingar:

- **Kostnad:** 5 Mkr per steg.
- **Tärningsslag:** D20 ≥ 10 för att lyckas.
- **Vid lyckat slag:** +1 energiklass (byt clip) och +1 effektiv DN (byt DN-kort).
- **Vid misslyckat slag:** kostnaden är ändå spenderad — men **nästa försök på samma
  fastighet lyckas automatiskt** (spara en garanti-markör).
- **Modifierare:** FC *Tekniska experten* ger +3 på slaget. Vissa personkort ger
  auto-success.

Energiklass kan inte gå förbi A. Antal fastigheter du får uppgradera per kvartal:
**Q1 = 3, Q2 = 2, Q3 = 1, Q4 = 0.** (Samma fastighet flera steg räknas som en.)

**Effektiv DN cap:** en fastighet kan max fördubbla sin bas-DN (bas × 2), absolut
maxtak 15.

---

## 7. Korten på fastigheterna

### Plus- och minuskort (dolda)
De flesta händelsekort och alla DD-kort är **plus- eller minuskort** som läggs
**dolt** på fastigheten. De ger ingen effekt direkt. När du har **3 i netto** på
samma fastighet — 3 fler plus än minus, eller tvärtom — **avslöjas alla, kasseras,
och bas-DN ändras permanent ±1.** DD-kort räknas i samma hög som händelsekorten.

> Detta är kärnan i den dolda ekonomin: du bär på risk och potential som andra inte
> ser, tills det tippar över.

### Varningskort
Ger ingen DN-effekt direkt. **Tre varningskort på samma fastighet** → fastigheten får
permanent −1 DN (offentligt). Kan inte tas bort efter att de utlösts.

### Energi-varningskort
**Tre energi-varningar på samma fastighet** → energiklassen sänks ett steg
automatiskt (−1 DN + nytt clip).

### Direkta DN-kort
Enstaka kort (industri) ger **+1 eller −1 bas-DN direkt och permanent**. Sällsynta —
högst omkring 10 % av leken.

### DD-kort (Due Diligence)
Dras dolt vid övergången och vid varje nytt köp. Fungerar som plus/minus-kort men
avslöjas **för alla** när fastigheten säljs eller tvångsförsäljs.

### Stoppkort och förköpsrätt-kort
Dras till **handen** (inte på fastigheten) som reaktiva resurser:
- **Stoppkort** — avvärjer ett fientligt bud.
- **Förköpsrätt** — ger förstaval när en matchande fastighetstyp kommer ut på marknaden.

### Typlekar
Händelsekort finns i fyra lekar — en per förvaltad fastighetstyp, med olika
riskprofil:

- **Hyresrätt** — stabil, milda utslag.
- **Förskola** — trygg samhällsfastighet med långa kommunala avtal.
- **Lokal** — trendkänslig (omsättningshyror, konkurser, e-handel).
- **Kontor** — cyklisk (uppsägningar, storbolag, omorganisationer).

Du drar ur den lek som matchar fastighetens typ.

---

## 8. Personal och personkort

### FC-arketyper (välj en)
| Arketyp | Förhandling | Motstånd konsekvens | Specialeffekt |
|---|---|---|---|
| Förhandlaren | +3 | −1 | – |
| Skölden | −1 | +3 | – |
| Generalisten | +1 | +1 | – |
| Nätverkaren | +1 | 0 | drar 1 extra typ-händelsekort/kvartal |
| Den lugna | 0 | +2 | −1 Mkr räntedrag/kvartal |
| Tekniska experten | 0 | 0 | +3 på alla energiuppgraderingsslag |

### FS-arketyper (välj en)
| Arketyp | Specialeffekt |
|---|---|
| Margareta "Rivaren" | tar bort 1 konsekvenskort per omgång |
| Per "Kvalitetsoptimeraren" | +1 DN på fastighet med högst kvalitet |
| Lars "Spionen" | får titta på 1 motståndarkort per omgång |
| Sara "Besiktningsgeniet" | ignorerar första garantibesiktningen per fastighet |

### Personkort (på hand)
Taktiska engångskort. **Effekten är direkt och permanent när du spelar kortet** — det
finns inga "detta kvartal"-effekter. Undantag: plus/minuskort (som läggs på en
fastighet) och reaktiva kort (som spelas i rätt ögonblick, men även då är effekten
direkt). Exempel på effekter:

- +5 / +3 Mkr direkt till kassan
- +1 bas-DN permanent på en fastighet
- sänk en fastighets lån med 10 Mkr permanent
- +2 / +3 på en hyresförhandling
- auto-success på en energiuppgradering
- blockera ett konsekvenskort / annullera ett minuskort
- kasta tre minuskort från en fastighet

Max **6 personkort på hand**. Blir handen full måste du välja vilka du behåller.

---

## 9. Risk för tvångsförsäljning

När nästa kvartals yield skulle pressa **MV under lånet** får fastigheten en **röd
markör** — en tydlig varning ett kvartal i förväg. Markören syns för alla.

**Vid marknadsfasen** tvångsförsäljs varje röd fastighet automatiskt till
**tvångspris = 0,7 × MV**. Räcker inte det för att täcka lånet dras mellanskillnaden
från kassan (och i värsta fall via moderbolagstillskott). Dolda kort på fastigheten
avslöjas för alla.

**Så undviker du det:** läs yield-kön (tre kvartal framåt), sälj frivilligt i tid för
fullt MV, uppgradera för att höja DN — eller avslöja dold DN som höjer effektiv DN och
därmed MV.

---

## 10. Marknad — köp och sälj

- **Frivillig försäljning:** sälj en fastighet till banken för normal MV. Lånet löses,
  resten går till kassan.
- **Köp:** nya fastigheter kommer ut på marknaden (Q1: 3, Q2: 2, Q3: 1, Q4: 0). Du
  betalar förvärvspriset och tar över det förtryckta lånet. Ett DD-kort läggs dolt på
  den nya fastigheten.
- **Fientligt bud** (flerspelarläge): buda 1,2 × MV på en motståndares fastighet.
  Mottagaren måste sälja om hen inte spelar ett stoppkort.

---

## 11. Slutet av året — slutpoäng

Efter Q4:

1. **Avslöja alla dolda kort** (DD + dolda händelsekort).
2. **Lös lånen** — dras från kassan.
3. **Räkna slutpoängen.** Tre delpoäng, vardera ~25 vid ett riktigt bra spel:

| Skede | Formel | "Superbra" = 25 |
|---|---|---|
| 1 Utveckling | total anskaffning ÷ 100 | vid 2 500 Mkr förvärv |
| 2 Byggande | TG (täckningsgrad, %) | vid TG 25 % |
| 3 Förvaltning | (fastighetsvärde obelånat + kassa) ÷ 30 | vid ~750 Mkr fritt kapital |

där *fastighetsvärde obelånat* = säljvärde (normal MV) − utestående lån.

> **Slutpoäng = (Skede 1 + Skede 2 + Skede 3) × måluppfyllelse-faktor**

Måluppfyllelse-faktorn (baserad på Q/H/T-avvikelse) sänker poängen om du inte höll
dina mål. Högsta slutpoäng vinner.

---

*Balanssiffror (yield-spann, kostnader, trösklar) är kalibrerbara och kan justeras
efter provspel. Se `FORVALTNING_KOMPONENTER.md` för fullständig komponentlista.*
