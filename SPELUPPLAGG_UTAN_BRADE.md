# Åkepol – Kvarteret
### Förslag på spelupplägg: interaktivt Åkepol utan spelplaner

*Förslag, 2026-10-27. Inget är byggt än.*

---

## 1. Grundidé

Spelbrädena i Åkepol gör fyra saker:

| Bräde | Vad det egentligen gör | Ersätts av |
|---|---|---|
| PU-brädet (slå och flytta) | Slump i vilka projekt och kort du får, plus en klocka (SBK två varv) | **Beslutsrundor med handlingskort** och en synlig **planklocka** |
| Tomten (pusslet) | Begränsar hur mycket du kan bygga | **Byggrättsmätare**: BYA-tak 4 000 kvm + markexpansioner |
| PL/GF-brädet | Ordning på 13 upphandlingar och 8 utförandefaser | **Tidslinje** på storskärmen, ett kort i taget |
| Scoreboard | Q/H/T mot krav, kassa, riskbuffert | **Bolagspanelen** i varje lags mobil/dator |
| Förvaltningsspiralen | Kvartalsräknare och marknad | **Fyra kvartalsrundor** med fast agenda + budgivning |

Det är alltså inte brädet som är spelet, det är **besluten**. Kvarteret behåller
alla kort, all ekonomi och slutformeln, men låter varje skede bli en serie
tydliga beslut som alla lag fattar **samtidigt**, och som sedan **avslöjas
tillsammans** på storskärmen.

**Format:** 2–6 lag (2–4 personer per lag), en storskärm, en enhet per lag,
en spelledare (GM). Speltid ca 90–120 min. Fungerar på konferens och i
utbildning, men också på distans (ingen fysisk utrustning alls).

**Spelrytmen i varje runda:**

> **Läge → Beslut (dolt) → Avslöjande → Utfall (tärning/kort) → Konsekvens**

Det samtidiga, dolda beslutet är kärnan: inga lag väntar på varandra, och
avslöjandet på storskärmen ger samtalet ("varför valde ni den billiga
gräventreprenören?!").

---

## 2. Upplägget skede för skede

### Akt 0 – Ledningen (5 min)
- Lagen draftar **CEO, CFO, COO** (L_personal) i ormordning: 1-2-3-3-2-1.
- Ordningen avgörs av ett snabbt **uppvärmningsquiz** (quiz_questions.json) i
  stället för D6. Bra start: alla är igång direkt.

### Akt 1 – Projektutveckling: "Byggrätten" (25 min)
Ersätter PU-brädet och pusslet.

**Projektmarknaden.** På storskärmen ligger de översta korten i fem
projekthögar (PU_projekt), alltid synliga.

**Planklockan.** Akten har **6 rundor** (motsvarar "tills någon passerar SBK
andra gången"). Klockan syns hela tiden; vissa händelser flyttar den ±1.

**Varje runda väljer varje lag dolt ett handlingskort** ur en egen hand:

| Handlingskort | Effekt (kopplad till befintlig data) |
|---|---|
| **Ta projekt** | Ta ett projekt från marknaden. Krocka två lag om samma projekt: budgivning i utvecklingskostnad |
| **Medborgardialog** | Dra ett dialogkort (PU_poldia) |
| **Politisk förankring** | Dra ett politikkort (PU_poldia); kan ge +1 på nämndslag |
| **Riskbuffert** | Ta en riskbuffert |
| **Markexpansion** | Köp markexpansion (5 Mkr), höjer BYA-taket |
| **Projektbanken** | Parkera ett projekt för senare |

Varje handlingskort används en gång och kommer tillbaka först när handen är
tom. Det tvingar fram prioriteringar, precis som rutorna på brädet gjorde
fast utan att tärningen bestämmer vart du hamnar.

**Projektchefen** (PU_PL_personal) ger ett extra handlingskort eller en
specialförmåga (t.ex. Politikern: ett gratis politikkort).

**Nämnden.** När klockan är slut: dramatiserat nämndslag per projekt på
storskärmen, ett lag i taget.

**Byggrätten** (i stället för pusslet). Bolagspanelen visar en mätare:
- BYA använd / BYA tillgänglig (4 000 kvm + expansioner)
- BTA total → BTA-klass och BYA-klass beräknas direkt
- Bostäder i övre lager tillåts om ett annat projekt bär dem (en kryssruta per
  par), så "staplingsregeln" lever kvar som beslut i stället för form.

Avslut som i dag: anskaffning, 15 % EK, mark, tomt, utvecklingskostnad. Allt
räknas automatiskt och visas som en **balansräkning per lag**.

### Akt 2 – Planering: "Upphandlingen" (20 min)
Ersätter PL-brädet.

- Tidslinjen på storskärmen visar de **13 upphandlingarna** i ordning.
- För varje steg ser varje lag **fyra anbud (nivå 1–4)** från PL_Leverantörer /
  PL_Organisation, med pris, Q/H/T och erfarenhet. Leverantörer som projekten
  förbjuder är gråade.
- Alla lag väljer **samtidigt och dolt** → avslöjande → panelen uppdaterar
  Q/H/T mot krav.
- Därefter löses ett **händelsekort** (PL_Händelsekort) med D20 + erfarenhet.
  Tärningen slås digitalt med animation, eller fysiskt om GM vill.
- **Arbetschefen** väljs först, lägst ABT-kostnad först, som i dag.

För att hålla tempot kan GM slå ihop steg två och två ("mark + grund").

### Akt 3 – Genomförande: "Bygget" (25 min)
Ersätter GF-brädet. Här blir spelet ett **handpussel**.

- Varje lag har en **kompetenshand**: sina personal-, organisations- och
  leverantörskort med STA/KOM/SAM/NOG/INN/ABM.
- Storskärmen vänder **ett faskort per fas** (GF_Faskort_utforande, 8 faser),
  samma för alla.
- Lagen väljer dolt vilka kort de **offrar** för att nå Negativt / Neutralt /
  Positivt / Bonus. Ett kort används en gång, ingen växel. Det är samma regel
  som i dag, men nu syns valet som en ren avvägning: *spara mitt starka
  SAM-kort till stommen, eller ta bonusen nu?*
- **Kulturkort** (GF_kultur) köps före varje fas: en liten butik på skärmen.
- D20 + samlad erfarenhet → utfall på faskortets skala.
  **Riskbuffert = ett omslag**, max ett per fas.
- Efter fas 8: konsekvenskort T/Q/H och garantibesiktning dras automatiskt per
  saknat steg och per nivå 1–2-leverantör, med en kort förklaring av *varför*
  just den missen kostade.
- Slut: TB och TG visas per lag. BRF:er säljs (marknadsvärde − anskaffning +
  rörlig tärning).

### Akt 4 – Förvaltning: "Året" (25 min)
Ersätter förvaltningsspiralen.

- **Fyra kvartalsrundor** med samma agenda, som en checklista på storskärmen:
  1. Omvärldskort (F_omvärldskort), samma för alla
  2. Driftnetto in, personal ut (F_personal)
  3. Ett händelsekort per fastighet (F_händelsekort)
  4. Kvartalskort (F_kvartal)
  5. **Beslut (dolt):** energiuppgradera? sälja? anställa FS?
  6. Yield ändras (F_yield)
  7. **Marknaden:** 3/2/1/0 nya fastigheter. Budgivning live på storskärmen;
     köp ger DD-kort (F_DD). Moderbolagslån finns som nödutgång.
- Fastighetschef väljs först, lägst marknadsvärde först.

### Finalen – Kvarteret (5–10 min)
- Slutresultat: **(FV × 30 % + EK + TB) / BTA × 1 000 = kr/kvm**, plus
  eventuella quizpoäng.
- **Lärdomsskärmen:** för varje lag visas deras tre dyraste beslut och var de
  fattades ("Mark nivå 1 i Akt 2 → 2 garantikort → −9 Mkr"). Det gör
  lärandemålet *första missen kostar mest* synligt i stället för underförstått.

---

## 3. Det som gör det interaktivt

1. **Dolda, samtidiga beslut + gemensamt avslöjande.** Ingen väntar på sin tur.
2. **Bolagspanelen** per lag: Q/H/T-mätare mot krav, kassa, EK, riskbuffertar,
   hand med kort. Ersätter scoreboard och papper.
3. **Storskärmen** är "bordet": marknad, tidslinje, faskort, omvärld, budgivning,
   topplista.
4. **Diskussionstimer** (t.ex. 90 s) per beslut; GM kan pausa och fråga ett lag
   varför.
5. **Quizfrågor som krydda** mellan akterna, inte som eget spel.
6. **Tärningar** digitalt som standard, fysiskt valbart: den som vill ha
   tärningskänslan kvar kan behålla den.

---

## 4. Teknisk ansats (om vi bygger det)

- **Nytt läge i companion-spåret**, inte i online-motorn: companion har redan
  rum, GM-vy, kortdragning, quiz, budgivning och dashboards. Förslag:
  `backend/kvarteret.py` + `frontend/kvarteret.html` (lag) +
  `frontend/kvarteret-skarm.html` (storskärm).
- **Läser befintliga CSV:er via `GameData`** – inga kopior av kortdata
  (Vakten §1). Det enda nya data är handlingskorten i Akt 1, som kan ligga i
  `data/companion_texts.json` eller en egen liten JSON.
- **Spellogg** per beslut (lag, vad, när, före/efter) till `data/game_logs/`.
  Behövs ändå för lärdomsskärmen, och följer Vakten §3.
- Ingen byggkedja, vanliga ES-moduler, som resten.

**Byggordning (förslag):**
1. Akt 3 (Bygget): mest kort och minst nytt regelarbete. Bra prototyp för
   "dolt beslut → avslöjande".
2. Akt 2 (Upphandlingen): samma mönster.
3. Akt 4 (Året): återanvänd companions budgivning.
4. Akt 1 (Byggrätten): kräver mest ny design (handlingskort, byggrättsmätare).
5. Finalen + lärdomsskärmen.

---

## 5. Det som går förlorat – och öppna frågor

- **Pusslet.** Att passa in former är kul och lär ut BYA. Byggrättsmätaren är
  enklare men torrare. *Alternativ:* behåll formerna som en liten digital
  "kvartersvy" som bara visualiserar, utan att vara ett bräde man spelar på.
- **Turordningens spänning** i PU (att någon tar "ditt" projekt) ersätts av
  krockbudgivning. Behöver speltestas.
- **Hur många lag?** 2–6 är förslaget. Fler än 4 kräver att Akt 1 har fler
  projekt på marknaden än fem högar.
- **Speltid:** räcker 6 rundor i Akt 1, eller blir det för få projekt?
- **Ska man kunna spela solo** mot en "standardbolags"-bot?
