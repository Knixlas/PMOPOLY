# Prompt-förslag — Companion

> Texter + trigger-mappning för companion-prompts. Baserat på **Spelflöde_SSOT.xlsx** (auktoritativt flöde) och **ÅKEPOL_Regelbok.docx** (paragrafhänvisningar). PowerPoint är källa till "Vad det betyder"-raderna men hänvisas inte direkt.

## Översikt

**18 prompts** (mot dagens 16). Tre nya step-IDs: `welcome`, `setup_skede1`, `transition_skede2`. Sju behåller sina ID:n men får helt nytt innehåll.

**När en prompt visas:** GM klickar "Nästa steg" → alla spelare i alla kvarter får exakt samma prompt → kan stängas individuellt med **"Förstått"**.

## Design

**Layout (mobile-first, eftersom 28 spelare på telefoner):**

```
┌─────────────────────────────────────┐
│ [eyebrow] SKEDE 1 · STEG 3          │
│                                     │
│ # Välj Projektchef                  │
│                                     │
│ Varje kvarter väljer en av 10       │
│ projektchefer. PC:n leder projektet │
│ genom utvecklingen…                 │  ← Lead (serif)
│                                     │
│ ─── Stegen ni gör nu ───            │
│ • Klicka "Välj Projektchef"         │
│ • Jämför attribut: Rb, Lindring…    │
│ • Diskutera och välj gemensamt      │  ← Bullets (mono-caps label, serif body)
│                                     │
│ ─── Vad det betyder ───             │
│ Hög lindring = bra på PU-brädet…    │  ← Italic serif (alltid synlig)
│                                     │
│ ─── 💡 Tips ───  [ Dölj tips ▽ ]    │  ← Endast om tips-toggle är PÅ
│ Hög Rb = mer flexibilitet senare.   │
│                                     │
│ Regelbok §3.8                       │  ← Discreet footer, mono-caps
│                                     │
│         [ FÖRSTÅTT ]                │
└─────────────────────────────────────┘
```

**Tips-toggle:** En liten knapp i player-headern (bredvid "Lämna"): `💡 Tips: [PÅ ▾]` / `💡 Tips: [AV ▸]`. Persistas i `localStorage`. Default PÅ för förstagångsspelare. Påverkar bara digitala companion (i fysiska spelet är tips ointressant — där sköter ni allt fysiskt).

**Existerande nivåsystem rensas:** dagens tre tutorial-nivåer ("all" / "rules" / "none") från [`instructions.js`](frontend/js/instructions.js) blir överflödiga eftersom strukturen är fast. "Vad det betyder" visas alltid; Tips kan togglas.

**Format per prompt:**
- Titel (rubrik)
- Lead (1–2 meningar — momentets sammanhang)
- Stegen ni gör nu (punktlista)
- Vad det betyder (1 mening — alltid synlig)
- 💡 Tips (1 mening — om toggle:n är PÅ)
- Regelbok §X.Y (footer)

---

## Skede 1 — Projektutveckling

### 1. `welcome` (NY) — Välkommen till Åkepol
**Trigger:** När första spelaren går med i ett kvarter (eller GM klickar "Starta")
**Lead:** Idag spelar vi ett spel som speglar hela kedjan: från projektutveckling, genom planering och byggnation, till att äga och förvalta fastigheter inom ert kvarter. Som par bildar ni ett kvarter; tre andra par i samma stadsdel är era konkurrenter. Spelet har **3 skeden**.
**Stegen ni gör nu:**
- Skriv in stadsdelskoden ni fått av spelledaren
- Skriv in ert företagsnamn (kvarterets namn)
- Välj er företagsledning: 1 CEO, 1 CFO, 1 COO (kosmetiskt, ger lagrollerna karaktär)
**Vad det betyder:** Ni leder ett dotterbolag till Holiday House Holding — moderbolaget garanterar byggnadskreditiv men styr inte projektet. Strategin lägger ni.
**Tips:** CEO/CFO/COO påverkar inte poängen — välj efter personlighet, inte siffror.
**Källa:** Regelbok §1, §2.3

---

### 2. `setup_skede1` (NY) — Sätt upp Projektutvecklingen
**Trigger:** GM klickar "Starta Skede 1" i sin GM-vy
**Lead:** Vi börjar Skede 1: Projektutveckling. Här tar ni fram projekt och sätter de krav (Q, H, T) som ska uppfyllas senare.
**Stegen ni gör nu:**
- Lägg fram PU-brädet (det stora bruna)
- Plocka tärningar: D4, D6, D8, D10, D12, D20
- Sätt svarta krav-markörer på Q=6 och H=6 (Detaljplanens grundvärde)
- Sätt T=12 (utgångskravet, rör sig först i Skede 2.1)
- Slå D6 om vem som börjar — högst slag börjar, sedan medsols
**Vad det betyder:** Q=Kvalitet, H=Hållbarhet, T=Byggtid (månader). Riskbuffertar (Rb) ger er chansen att slå om dåliga slag.
**Tips:** Q och H rör sig UPPÅT under hela Skede 1 (svårare krav att möta). Rb-stjärnorna kan rädda er senare — samla dem.
**Källa:** Regelbok §3.1, §1.7

---

### 3. `choose_pc` — Välj Projektchef
**Trigger:** GM klickar "Välj PC" (efter setup)
**Lead:** Varje kvarter väljer en av 10 projektchefer (PC). PC:n leder projektet genom utvecklingen — i verkligheten ansvarig för budget, nämndkontakt och riskhantering.
**Stegen ni gör nu:**
- Klicka "Välj Projektchef" i companion
- Jämför attribut: Riskbuffertar (Rb), Lindring (politik/dialog-bonus), Nämndbonus (D20 vid nämndbeslut), Q/H/T-bonus, Kompetens
- Diskutera i kvarteret och välj en gemensam PC
**Vad det betyder:** PC är en av kvarterets viktigaste resurser. Erfarenhet och kontaktnät spelar stor roll.
**Tips:** Hög lindring = bra på PU-brädet. Hög nämndbonus = tryggare med BRF. Hög Rb = mer flexibilitet senare.
**Källa:** Regelbok §3.8

---

### 4. `projects` — Projektval & PU-brädet
**Trigger:** GM klickar "Välj startprojekt + spela brädet"
**Lead:** Nu rör ni er runt PU-brädet i två varv. På varje runda får ni välja projekt, hantera politik/dialog-händelser, eller utöka tomten. Brädet har 24 rutor, fyra hörnrutor är specialfall.
**Stegen ni gör nu:**
- Klicka "Välj första projekt" — ett projekt sätter Q-/H-krav och utvecklingskostnad
- Slå D6 och flytta medsols (på er tur)
- På varje ruta:
  - **Projekt-ruta:** ta projektet eller lägg i projektbanken
  - **Stjärna:** +1 riskbuffert
  - **Dialog/Politik:** dra kort, slå D20 + PC-lindring
  - **Stadsbyggnadskontoret:** dra markexpansion (5 Mkr/styck)
  - **Stadshuset:** ta, byt eller lämna projekt
  - **Länsstyrelsen:** +2 på valfritt krav (Q eller H) — du väljer
  - **Skönhetsrådet:** −2 på valfritt krav (Q eller H) — du väljer
- Justera Q/H/Rb i companion efterhand
- När första kvarteret passerar Stadsbyggnadskontoret för **andra** gången → fas avbryts, övriga avslutar pågående drag
**Vad det betyder:** Mer projekt = mer intäkter, men också svårare krav att uppfylla i Skede 2. Kvartertypen (Bostäder / Bostäder+1 / Övriga) styr hur snälla händelsekorten blir senare.
**Tips:** Ta fler projekt än ni får rum med — utvecklingskostnaden betalas ändå, så strategin "redundans + sortera bort i pusslet" kan löna sig.
**Källa:** Regelbok §3.2–§3.7, §4.4

---

### 5. `namndbeslut` — Nämndbeslut
**Trigger:** Första kvarteret passerar SBK andra gången
**Lead:** Innan ni får placera projekten måste nämnden godkänna dem. För varje projekt med nämndkrav slår ni D20 + PC:s nämndbonus (erfarenhet räknas **inte**).
**Stegen ni gör nu:**
- Slå D20 + nämndbonus per projekt
- Resultat ≥ nämndkravet = godkänt
- Misslyckat: använd 1 Rb för omslag, eller ta bort projektet (✕-knappen)
- **Utvecklingskostnaden är redan betald** även för underkända projekt
- Köp ev. nya projekt från projektbanken till **3× utvecklingskostnad** (i tur och ordning enligt spelordning)
**Vad det betyder:** I verkligheten är nämndprocessen den första riktiga risken — fel typ av projekt på fel mark = avslag.
**Tips:** Rb är värt mer på dyra projekt än billiga. Sätt också spelregeln: ni kan slå om EN gång per slag — ingen tredje serve.
**Källa:** Regelbok §4.1, §4.2

---

### 6. `placement` (NY/utbygge av befintlig) — Placera projekt på marken
**Trigger:** GM klickar "Placera projekt" (efter nämnd)
**Lead:** Lägg pussel: alla godkända projekt ska rymmas på er mark (4×4 = 16 celler) plus markexpansioner. Bostäder (BRF/Hyresrätt) får läggas i ett övre lager — men hela bostadsformen måste vila på underliggande projekt (inga "hål").
**Stegen ni gör nu:**
- Passa in projektformerna fysiskt på er tomt
- Inget projekt får sticka ut utanför mark + expansioner
- Övre lager: bara bostäder, måste täckas helt av projekt under
- Justera tillbaka Q-/H-krav om ni inte placerade ett projekt (det räknas inte längre)
- Lägg ej placerade projekt i projektbanken (kostnaden är ändå betald)
**Vad det betyder:** I verkligheten är detta byggrättsligt komplicerat — staplade lager symboliserar flerskiktade kvarter (oftast inte tillåtet i verkligheten).
**Tips:** Bostäder ovanpå kontor/lokaler är spelets mest BTA-effektiva strategi — använd det om ni passar in formerna.
**Källa:** Regelbok §4.3, §4.4

---

### 7. `anskaffning` (NY) — Anskaffning & ABT-budget
**Trigger:** GM klickar "Räkna anskaffning"
**Lead:** Nu räknas ekonomin ihop. Anskaffningen är er totala budget — det som blir kvar efter tomt, expansioner och utveckling är **ABT-budgeten** ni har att röra er med i Skede 2.
**Stegen ni gör nu:**
- Companion summerar automatiskt:
  - Anskaffning (intäkt från projekten)
  - − 15 Mkr för tomten
  - − 5 Mkr per markexpansion
  - − Utvecklingskostnad för **alla** projekt (även ej placerade)
  - = ABT-budget
- Notera kvarterstyp på scoreboard: Bostäder / Bostäder+1 / Övriga
- Notera BTA-klass och BYA-klass (A–D, baserat på storlek)
**Vad det betyder:** ABT är er kassa under produktionen. Det som blir över när bygget är klart är ert täckningsbidrag (TB). Moderbolaget förväntar sig ett TB.
**Tips:** Negativ ABT-budget tvingar fram moderbolagslån — undvik om möjligt, lånet straffar er hårt i Skede 3.
**Källa:** Regelbok §5.1, §1.7

---

### 8. `rb_invest` — Sänk era krav (om ni vill)
**Trigger:** GM klickar "Sista justering Skede 1"
**Lead:** Sista chansen i Skede 1: använd era kvarvarande riskbuffertar för att sänka Q-, H- eller T-kravet. 1 Rb = 1 steg. Resterande Rb sparas till Skede 2.2 (omslag på dåliga slag).
**Stegen ni gör nu:**
- Använd ± knappar för att fördela Rb:
  - −1 Q-krav per Rb
  - −1 H-krav per Rb
  - −1 T per Rb
- Golv: T ≥ 8, Q-krav ≥ 0, H-krav ≥ 0
**Vad det betyder:** Det är sista chansen att flytta målstolparna. Sparade Rb fungerar som omslag-försäkring i Skede 2.2 istället.
**Tips:** T-sänkning är ovanligt värdefull eftersom T-överskridande också drar med sig Q- och H-straff via konsekvenskorten.
**Källa:** Regelbok §3.6, §5.2

---

## Övergång → Skede 2

### 9. `transition_skede2` (NY) — Skede 1 är klart
**Trigger:** GM klickar "Avsluta Skede 1"
**Lead:** Skede 1 är klart! Vi pausar nu, sen byter vi bräde till PL/GF-brädet och börjar Skede 2.1 Planering.
**Stegen ni gör nu:**
- Plocka undan PU-kort, PU-bräde, PU-personal — läggs i spelboxen
- BEHÅLL alla projektkort (placerade + godkända som inte placerades). Ej godkända BRF kan läggas tillbaka eftersom BRF inte används i förvaltningen.
- Lägg fram Skede 2-brädet (Planering + Genomförande använder samma)
- Sätt T-utfall (färgad kub) = 12 + högsta projektets T (max 14)
- Färgade Q-, H-utfallskuber börjar på samma värde som kraven
**Vad det betyder:** Bygget startar i T-utfallet — högsta projekt drar upp tiden direkt. T-utfallet kan röra sig i Skede 2.2, aldrig under 8.
**Tips:** Q- och H-utfallskuberna börjar på krav-värdet och rör sig endast nedåt i Skede 2 — målet är att inte tappa för många steg.
**Källa:** Regelbok §5.1, §5.2

---

## Skede 2.1 — Planering

### 10. `choose_ac` — Välj Arbetschef
**Trigger:** GM klickar "Välj AC"
**Lead:** Varje kvarter väljer en arbetschef (AC). Kvarteret med **lägst ABT-kostnad** väljer först. AC ger erfarenhetsbonus på alla händelsekort i Skede 2 + 3.
**Stegen ni gör nu:**
- Klicka "Välj Arbetschef" i companion
- Jämför: Rb, Erfarenhet (taket är 12, regelbok §10), Kompetens (STA/KOM/SAM/NOG/INN/ABM), Q/H/T-bonus
- Lägst ABT-kostnad väljer först — companion visar turordning
**Vad det betyder:** +1 erfarenhet = +1 på alla D20-slag i Skede 2 + 3 (max +12). Mycket värdefullt eftersom det lindrar händelsekort. Kompetenser används i Skede 2.2 för att betala FAS-kort.
**Tips:** En AC med +2 erfarenhet är ofta bättre än en med spridda kompetenser — bonusen på alla slag rätar ut värsta utfallen.
**Källa:** Regelbok §5.4, §10

---

### 11. `planning` — De 13 planeringsstegen
**Trigger:** GM klickar "Starta planering"
**Lead:** 13 steg i fast ordning. Vid varje steg ligger fyra alternativ uppe — alla kvarter har samma fyra och får välja samma som varandra (en leverantör jobbar ofta åt flera). Efter varje val drar ni ett händelsekort.
**Stegen ni gör nu (per steg):**
1. Välj ett av fyra alternativ (leverantör nivå 1–4 eller organisation)
2. Betala kostnaden från ABT-budget (BYA/BTA-klass styr priset)
3. Justera Q, H, T, erfarenhet enligt valet
4. Dra händelsekort: D20 + erfarenhet → utför kortets effekt
5. Notera: leverantörer **nivå 1 eller 2** sparas på scoreboard (de drar garanti-kort i 7.4)

**Ordning (13 steg):** Stödfunktioner → Mark → Husunderbyggnad → Digitalisering → Stomme → Installationer → Operativt team → Gemensamma arbeten → Yttertak → Fasader → Marknadsteam → Stomkomplettering → Inv. ytskikt

**Vad det betyder:** I verkligheten är planeringen där projekt vinner eller förlorar. De flesta byggproblem kan spåras tillbaka till planeringen.
**Tips:** Billiga leverantörer = lägre Q/H men sparar ABT till Skede 2.2 — riskar dock fler garantibesiktningar i §7.4. Balansera medvetet.
**Källa:** Regelbok §5.3, §5.5

---

### 12. `planning_summary` — Sammanfattning Skede 2.1
**Trigger:** Efter alla 13 steg
**Lead:** 13 steg klara. Kontrollera era värden innan ni går in i Skede 2.2 — det är så här det ser ut när byggstart sker.
**Stegen ni gör nu:**
- Q-utfall vs Q-krav — uppfyllt redan?
- H-utfall vs H-krav — uppfyllt redan?
- T-utfall (mål: 12)
- ABT-budget kvar — finns marginal till Genomförandet?
- Erfarenhet (max 12, gäller hela Skede 2)
- Alla leverantörs- och organisationskort sparas som **kompetenskort** för Skede 2.2 (kan spelas en gång var)
**Vad det betyder:** Skede 2.2 är där ni "betalar med kompetens" för att klara FAS-korten. Spridda kompetenser = bredare verktygslåda.
**Tips:** Räkna kompetenspoäng per kategori (STA/KOM/SAM/NOG/INN/ABM) innan Skede 2.2 — saknar ni en kategori helt blir vissa FAS-kort omöjliga utan kulturkort.
**Källa:** Regelbok §5.6, §6.5

---

## Skede 2.2 — Genomförande

### 13. `transition_skede3` (NY/`gf_byggfaser` start) — Sätt upp Genomförandet
**Trigger:** GM klickar "Starta Genomförande"
**Lead:** Samma bräde som 2.1, men nu byggs projekten. 8 utförandefaser. Ni betalar med kompetens (eller tar konsekvensen). Riskbuffertar är värdefulla nu.
**Stegen ni gör nu:**
- Plocka fram alla GF-kort (gröna): FAS-kort, konsekvenskort (Q/H/T), garantibesiktning, kulturkort
- Sätt scoreboarden: Q-, H-, T-utfallskuberna är där 2.1 lämnade dem
- Sparade leverantörer nivå 1–2 ska ligga i sin ruta på scoreboarden
**Vad det betyder:** Företagskultur (kulturkorten) är "extraenergi" — det lilla extra hela teamet kan ge utöver normalnivå. Begränsad mängd, först till kvarn (80 kort delas av alla kvarter).
**Tips:** Köp kulturkort tidigt om ni planerar dem — de blir dyrare för varje fas (2 → 7 Mkr).
**Källa:** Regelbok §6.1, §6.3

---

### 14. `gf_byggfaser` — De 8 utförandefaserna
**Trigger:** GM klickar "Vänd första FAS-kortet"
**Lead:** Per fas: vänd FAS-kortet → 4 utfallsnivåer (Röd / Gul / Grön / Mörkgrön) → välj nivå genom att betala kompetens. Sen händelsekort.
**Stegen ni gör nu (per fas):**
1. **Köp ev. kulturkort** (frivilligt, kostar 2–7 Mkr beroende på fas) — ger kompetenspoäng
2. **Vänd FAS-kortet** — välj kolumn baserat på er kvarterstyp (Bostäder / Bostäder+1 / Övriga)
3. **Välj utfallsnivå:**
   - **Röd (negativ):** ingen kostnad i kompetens, straff i Q/H/T eller ABT
   - **Gul:** lägre kompetenskrav, sparar pengar och tid
   - **Grön (ingen effekt):** moderat kompetenskrav, neutralt
   - **Mörkgrön (bonus):** högsta kompetenskrav, kan ge tidsvinst, Q-bonus eller B-ÄTA-intäkt
4. **Spela kompetenskort** tills sammanlagda summan möter eller överstiger kravet (överskott räknas inte; hela kortet förbrukas)
5. **Dra händelsekort** ur er egen hög: D20 + erfarenhet → utför kortets effekt
6. Justera scoreboard, lägg använda kort i spelboxen (utom leverantörer nivå 1–2 som sparas)

**Upprepa för alla 8 utförandefaser.**

**B-ÄTA — beställarinitierad ändring:** Vinst på beställarens ändring. Läggs **direkt till kassan**, inte till TB/TG.

**Vad det betyder:** Ambitionsnivån är en riskavvägning — det är inte alltid värt att gå för Mörkgrön. Mörkgrön = högsta krav, men kan ge B-ÄTA-vinst direkt till kassan.
**Tips:** Planera över alla 8 faser. Spela inte alla kompetenskort på fas 1–3 — de senare faserna har högre krav och kostnader. Och tänk på att ej använda kompetenser ger inga pengar tillbaka.
**Källa:** Regelbok §6.4, §6.5, §6.6, §6.7

---

### 15. `gf_konsekvens` — Konsekvenser (Tid, Kvalitet, Hållbarhet)
**Trigger:** GM klickar "Konsekvenskort" (efter alla 8 faser)
**Lead:** Nu jämförs era utfall mot kraven. Avvikelser ger konsekvenskort som drar er nedåt.
**Stegen ni gör nu (i ordning T → Q → H):**
1. **Tid:** för varje månad er T överstiger 12, dra ett konsekvenskort-Tid → utför, lägg tillbaka, blanda mellan kvarter
2. **Kvalitet:** för varje steg ert Q-utfall understiger Q-kravet, dra konsekvenskort-Kvalitet
3. **Hållbarhet:** för varje steg ert H-utfall understiger H-kravet, dra konsekvenskort-Hållbarhet
- Per kort: slå D20 + erfarenhet, effekt = ABT-kostnad
- Q/H-loopen kan rulla på (vissa kort sänker utfallet ytterligare → fler kort)
- **CFO antecknar antalet dragna konsekvenskort** — påverkar antal garantikort i nästa steg
**Vad det betyder:** Avvikelser från Q/H/T-mål påverkar slutpoängen via **f(n) straffaktorn** (1 fel → 90 %, 4 fel → 70 %, 10 fel → 50 %, sen linjärt till 0).
**Tips:** En enstaka avvikelse tar 10 % av råpoängen — håll målen om ni kan. Förebyggande arbete i Skede 2 är billigare än konsekvenser här.
**Källa:** Regelbok §7.1–§7.3, §9.2

---

### 16. `gf_garanti` — Garantibesiktning
**Trigger:** GM klickar "Garantibesiktning"
**Lead:** 5 år efter färdigställande besiktigas byggnaden. Dolda fel dyker upp — leverantörers kvalitet avgör hur många.
**Stegen ni gör nu:**
- Antal kort = (antal konsekvenskort dragna) + (antal sparade leverantörer nivå 1–2)
- Per kort: slå D20, effekt = ABT-kostnad (alltid ≤ 0)
- Om garanti-högen tar slut: blanda om använda kort, dra igen
**Vad det betyder:** Lågnivå-leverantörer (nivå 1–2) ger garantiavsättningar. Här syns straffet för att ha sparat in på leverantörsval i Skede 2.1.
**Tips:** Garantikorten är ALLTID ≤ 0 — det är ren kostnad. Bara att svälja och föra in i ABT.
**Källa:** Regelbok §7.4

---

### 17. `gf_abt_ek` — Ekonomisk uppgörelse + BRF-försäljning
**Trigger:** GM klickar "Räkna TB + sälj BRF"
**Lead:** Bygget är klart. Nu summeras Skede 2-resultatet och BRF-projekten säljs av innan förvaltningen.
**Stegen ni gör nu:**
- **TB (Täckningsbidrag):** ABT-budget − faktisk ABT-kostnad
- **TG (Täckningsgrad):** TB ÷ ABT-budget (procentmått)
- Om moderbolagslån har tagits: 100 Mkr per lån dras från eget kapital
- Kvarvarande medel → kassan (följer med till Skede 3)
- **BRF-försäljning:** Marknadsvärde − Anskaffning + rörlig intäkt (slå projektkortets tärning) → kassan
- Behåll BRF-projektkorten i separat hög (BTA räknas i slutet)
- B-ÄTA-intäkter ligger separat på kassan, **inte** i TB/TG
- Räkna avvikelser (n) **innan** scoreboarden plockas bort: spara n stycken kort i en hög hos kvarteret som markörer för slutvärderingen
**Vad det betyder:** TB är ert mått på hur väl ni höll budgeten — del av slutpoängen och tillskott till kassan. n styr f(n)-straffaktorn på slutpoängen.
**Tips:** Spara avvikelse-högen synligt — n läses av direkt ur den vid slutvärderingen. BRF-projektkorten behövs för BTA-divisorn även om de är sålda.
**Källa:** Regelbok §7.5, §7.6, §7.7

---

## Skede 3 — Förvaltning

### 18. `f4_forbered` — Sätt upp förvaltningen + anställ personal
**Trigger:** GM klickar "Starta Skede 3"
**Lead:** Bygget är klart, nu förvaltar ni i 4 kvartal. Projekten heter nu **fastigheter**. Marknaden har också utbud (fastigheter byggda av andra aktörer) som ni kan köpa.
**Stegen ni gör nu:**
- Plocka undan Skede 2-brädet, plocka fram Skede 3-brädet (stadsdelens marknad)
- Era fastigheter ligger framför er (ej på brädet)
- Övriga aktörers fastigheter (ej BRF) ligger på brädet — kan köpas
- Plocka fram röda kort (F): personal, händelsekort per fastighetstyp, omvärldskort, DD-kort, kvartalskort, yieldkort
- **Anställ FC (Fastighetschef)** — minst 1 krävs. Lägst marknadsvärde väljer först.
- **Anställ ev. FS (Fastighetsskötare)** så samlade kapacitet ≥ antalet fastigheter ni äger
- Personalstyrkan kan **inte** minskas under skedet, även vid övertalighet
**Vad det betyder:** I verkligheten är förvaltningskostnaden över 50 år större än byggkostnaden. Rätt personal = lägre driftskostnader.
**Tips:** Personalstyrkan kan inte minskas — anställ inte fler än ni säkert behöver. FC har strategiskt fokus, FS sköter daglig drift.
**Källa:** Regelbok §8.1, §8.2

---

### 19. `f4_q1` / `f4_q2` / `f4_q3` / `f4_q4` — Kvartalsspiralen
**Trigger:** GM klickar "Starta Kvartal N"
**Lead:** Kvartalet följer en fast spiral. Marknadsvärdet uppdateras varje kvartal pga yield-förändringar.
**Stegen ni gör nu (per kvartal):**
1. **Sälj fastigheter** om ni vill (tvångsförsäljning sker här om kassan är negativ)
2. **Utöka marknaden:** Q1: 3 nya, Q2: 2, Q3: 1, Q4: 0
3. **Budgivning:** köp på sekundärmarknaden — start på marknadsvärde, lägsta accepterade bud 80 %, banken köper alltid tillbaka för 80 %, ni betalar bara **30 % kontant** (70 % är lånefinansiering)
4. **Dra DD-kort** (Due Diligence) per fastighet ni köper — kan vara kostnad, neutralt eller övervärde
5. **Anställ ev. ny FS** för att täcka antal fastigheter
6. **Summera driftnetto** på era ägda fastigheter → intäkt till kassan
7. **Dra omvärldskort** (samma för alla kvarter)
8. **Betala personalkostnad** (FC + FS-löner)
9. **Dra händelsekort** av rätt typ per ägd fastighet (HR / KON / LOK / FÖR — lägg tillbaka och blanda mellan varje kvarter)
10. **Dra kvartalskort** (kvartalets händelse)
11. **Energiuppgraderingar** (frivilligt, 3 Mkr per steg, A–E)
12. **Dra yieldkort** och justera marknadsyielden (sker i Q1–Q3, inte Q4)

**Moderbolagslån-konsekvenser** (om sådana togs i Skede 2):
- Säljkrav till **1** fastighet
- Köpstopp på sekundärmarknaden
- Uppgraderingsstopp för energiklass

**Vad det betyder:** Yield-förändringar är makro-risken ni inte kan kontrollera — den vänder hela värderingen. Banken stabiliserar med 80 %-golv. Energiklass A = +10 % FV-bonus, klass E = osäljbar (0).
**Tips:** Energiuppgraderingar (3 Mkr/steg) lönar sig nästan alltid på fastigheter ni planerar att behålla. På fastigheter ni ska sälja: räkna på köparens incitament istället.
**Källa:** Regelbok §6.2 (lån-konsekvenser), §8.3–§8.11

---

### 20. `f4_slut` — Slutvärdering
**Trigger:** GM klickar "Avsluta spelet" (efter Q4)
**Lead:** Förvaltningen är klar. Nu räknas slutpoängen — det jämförelsetal som avgör vinnaren.
**Stegen ni gör nu (companion räknar automatiskt):**

**Råpoäng = (FV × 30 % × Energibonus + Eget kapital + TB) ÷ (BTA / 1000)**

- FV per fastighet = (driftnetto × 4) ÷ (yield/100), summerad över portföljen
- × 30 % = ert ägarkapital (70 % är banklån)
- Energibonus per fastighet: A=1.10, B=1.05, C=1.00, D=0.95, **E=0** (osäljbar)
- Eget kapital = kassa − moderbolagslån (100 Mkr per lån)
- TB = ABT-budget − faktisk ABT-kostnad (sätts till 0 om ABT var negativt)
- BTA = placerade projekt + sålda BRF + köpta fastigheter

**Slutpoäng = Råpoäng × f(n)** där n = Q-, H- och T-avvikelser (mätt vid Skede 2-avslut)
- n=0 → 100 %, n=1 → 90 %, n=4 → 70 %, n=10 → 50 %, sen linjärt till 0 vid n=60

**Den med högst slutpoäng vinner.** Vid lika poäng: högst förvaltad BTA vinner.

**Vad det betyder:** Inte bara "mest pengar" — det handlar om bäst förvaltad portfölj per kvm. Den som byggt kvalitet från start har fördel i förvaltningen.
**Tips:** Vid lika poäng vinner högst förvaltad BTA. Ett tätt slut kan avgöras av om ni köpte en till fastighet på sekundärmarknaden.
**Källa:** Regelbok §9.1, §9.2, §9.3

---

## Implementering — så här syncas detta i kod

**Beslut (2026-05-01):**
- Tider och PPT-hänvisningar borttagna ✓
- "Vad det betyder" alltid synlig ✓
- Tips: rad i varje prompt + toggle `💡 Tips: PÅ/AV` i companion-headern ✓
- Layout: linjär mobile-first (skissad ovan) ✓

**Filer som ändras:**
1. `data/companion_texts.json` — utbyts mot ny version med 18 prompts (overrider `PHASES` i `backend/companion.py`)
2. `backend/companion.py` `PHASES` fallback-dict — uppdateras till samma struktur (för säkerhets skull om JSON saknas)
3. `frontend/companion.html` — ny prompt-renderingskomponent som:
   - Visar Lead, Stegen, Vad det betyder alltid
   - Visar Tips bara när toggle:n är PÅ
   - Visar Regelbok-footer i mono-caps
4. `frontend/companion.html` — ny tips-toggle i player-header (bredvid "Lämna"-knappen), persistas i `localStorage`
5. **Borttaget:** `frontend/js/instructions.js` `INSTRUCTIONS`-dict + tutorial-nivåsystemet ("all" / "rules" / "none") — ersätts av nya systemet. Existerande `showInstruction(step_id)` i full-game mode (huvudappen) får antingen samma toggle eller en separat lösning.

**Nya step-IDs i `PHASES`:**
- `welcome` (hela kvarteret innan Skede 1)
- `setup_skede1` (efter företagsval, innan PC-val)
- `transition_skede2` (mellan Skede 1 och 2.1)
- `transition_skede3` (mellan Skede 2.1 och 2.2 — eller integrera i `gf_byggfaser`)
- `placement` (mellan namndbeslut och anskaffning)
- `anskaffning` (efter placement, innan rb_invest)

**Trigger-koppling:**
- Ändras inte. I companion-mode triggas prompten av GM:s "Nästa steg"-knapp som flyttar `current_step_id`. I full-game mode (huvudappen) triggas av backend phase-machine.

---

Säg till om någon av de 18 prompts känns fel/saknad/överlapp, eller om du vill att jag bara kör på och implementerar — jag har specat tillräckligt för att börja koda.
