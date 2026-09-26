# Omstart — styrdokument (utkast)

*Inför konferensen i maj 2026 växte spelet snabbt och blev rörigt. Det här dokumentet
beskriver hur vi samlar ihop det och bygger om — regler, kort, grafik, tryck och kod —
från en gemensam grund. Utkast: öppna frågor längst ner.*

---

## 1. Grundproblemet

Samma regel finns i dag på flera ställen:

- `ÅKEPOL_Regelbok.docx` (OneDrive)
- CSV-filer i SPELET 2 (OneDrive), synkade hit med `sync_csv.py`
- Implementationen i `backend/engine.py` (~4800 rader)
- Companion-texterna i `data/companion_texts.json`
- Grafiken — t.ex. härleds projektens former *ur PNG-bilderna* (`tools/extract_shapes.py`)

`REGELBOK_CHECKLIST.md` och `ANALYS_RAPPORT.md` existerar i praktiken för att hålla reda
på var de säger emot varandra.

**Omstartens kärna: en källa för varje sak, och allt annat genereras ur den.**

### Excel-filerna är motorn

En Excel per korttyp (`kortdata/`) är **den enda källan** för allt kortinnehåll. Ur dem genereras:
- **tryck** (printfiler via mallar/skript),
- **onlinespelet** (motorn läser samma data),
- **vidareutveckling** (ändringar görs i Excel — aldrig direkt i kod, CSV eller InDesign).

### Prioritet vid återskapandet av kortdata

1. **Ledning (L), Skede 1 (PU), Skede 2 (PL, GF)** — återskapas fullständigt och verifieras mot tryck.
2. **Skede 3 (F)** — görs om ordentligt: baksidorna blir i princip helt nya och fler kort tillkommer.
   Nuvarande F-korts baksidor återskapas **inte**; framsidor/grafik noteras bara som referens.
   Obs: projektkortens baksida (`PU_projekt`) har en sektion *KÖP OCH SÄLJ FÖRVALTNING*
   (driftnetto, energiklass, 80 %-bud, 30 % kontantinsats) som hör till Skede 3. **Den görs om.**
   **Beslut:** alla 45 projektkort trycks om (även BRF, för enhetlighet) × 8 spel = **360 kort**.
   Värdena ses också över: små justeringar (några Mkr) så att **driftnetto och marknadsvärde matchar**
   (jfr yield). Görs i `kortdata/PU_projekt.xlsx`; de nya korten trycks ur den.

### Regelboken följer trycket

Där regelbok, CSV eller kod säger emot det tryckta materialet gäller **trycket** — även för
tärningsintervall, klassgränser och etiketter. Regelboken skrivs om efter korten, inte tvärtom.

### Beslutade regeländringar

#### R1. Nämnden — ett gemensamt slag, fler tärningar per försök (2026-09-26)

1. Summera **"Passera nämnden"** på alla projekt man tar med (tryckt på projektkorten som "> N").
2. Dra av projektchefens **nämndslag** (PU_personal; projektchefer utan nämndslag drar av 0).
3. **Försök 1:** slå 1 D20 — resultatet måste vara **över** summan.
4. **Miss:** välj **antingen**
   - **+1 på Q- eller H-kravet**, **eller**
   - **ta bort ett projekt** — summan sjunker med projektets nämndvärde, och kraven sjunker med
     projektets bidrag till Q/H.
5. **Nästa försök** slås med **en tärning mer** än förra (försök 2: 2 D20, försök 3: 3 D20 …).
   Det räcker att en tärning är över summan.
6. Upprepa tills man lyckas.

**Allt måste genom nämnden:** projekt som tas i efterhand (komplettering efter nämnden, 4.2) prövas med samma
regler för de nya projekten.

**Tak:** man får inte ta med fler projekt än att nämnden **går** att klara — summan (efter nämndslag)
måste vara högst 19. Är den högre måste projekt tas bort innan första slaget.

Kräver inget omtryck: projektkortens "> N" och personalkortens nämndslag används som de är.

Chans att lyckas per försök (slå över summan): summa 6 → 70 % / 91 % / 97 %; summa 10 → 50 % / 75 % / 88 %;
summa 14 → 30 % / 51 % / 66 % (1 / 2 / 3 tärningar).

### Slutmål: exakt rätt filer — varken mer eller mindre

När omstarten är klar innehåller repot **exakt** de filer som behövs för att
1. **trycka spelet** (kortdata, mallar, grafik, printskript),
2. **spela det online** (motor, gränssnitt, drift),
3. **vidareutveckla det** (regelböcker, testspelare, verktyg, dokumentation).

Allt annat tas bort. `arv/` är ett **tillfälligt** referenslager under omstarten — varje fil därifrån
förs antingen över till sin slutliga plats (och rensas/anpassas) eller lämnas, och mappen raderas när
omstarten är klar. Samma gäller nuvarande `backend/`, `frontend/`, `data/` och rot-dokumenten: de
ersätts, inte kompletteras. Git-historiken finns kvar som arkiv.

### Grundbeslut: det fysiska spelet är huvudprodukten

- **Det tryckta materialet är facit** för Skede 1 och 2. Vi ändrar så lite som möjligt där,
  för att slippa trycka nytt. Koden och de digitala verktygen anpassas efter det tryckta spelet — inte tvärtom.
- **Skede 3 (Förvaltning) får göras om** (jfr `FORVALTNING_DESIGN_2-1.md`) och får nytt tryck.
- **Spelplanerna ändras med klistermärken**, inte omtryck.
- **Allt byggs jungfruligt.** Kortdatan läses tillbaka ur tryckfilerna till **nya Excel-filer, en per korttyp**,
  som blir den nya källan. Befintliga CSV:er, `ÅKEPOL_alla_kortdata.xlsx`, kod och dokument är bara referens.
  Det enda som tas med från det gamla är **grafiken** (tryckfilerna).
- Varje föreslagen ändring i Skede 1–2 måste motivera sig: *vad måste tryckas om?*
  Regeländringar som bara påverkar regelboken är billiga; ändringar på kort och brickor är dyra.

```
  Regler (md) ──┐
                ├──► Motor ──► Online-spel
  Kortdata ─────┤         └──► Spellogg (fysiskt spel)
  (effektspråk) │         └──► Testspelare (bottar)
                │
  Mallar ───────┴──► Printfiler (kort, spelplaner, regelbok)
                 └──► Onlinegrafik
```

---

## 2. Arbetsområden

### A. Grund
- **Syfte och målgrupp** — vem spelar, hur länge, hur många, spelledarens roll, vad ska man lära sig.
- **Designprinciper per skede** — en "bärande idé" per skede, som Förvaltning 2.1:s
  *"DN och EK är tyst fysik — marknaden dömer"*. Avgör tvister längre fram.
- **Källsanning** — var regler och data bor (se öppen fråga 1 och 3).

### B. Regler
- **Uppstart** — CEO/CFO/COO, dotterbolag, projektchef.
- **Skede 1 — Projektutveckling**
- **Skede 2 — Planering (2.1) + Genomförande (2.2)**
- **Skede 3 — Förvaltning** (utgår från `FORVALTNING_DESIGN_2-1.md`)
- **Övergångar mellan skeden** — exakt vad som följer med (T, Q, H, EK, kassa, lån, fastigheter).
  Definieras *först*, så att skedena kan arbetas med parallellt.
- **Ekonomi och slutvärdering** — genomgående, eget område.

### C. Kort
- **Logik — ett effektspråk.** Ett litet, fast ordförråd av effekter (`DN -1`, `T +1`,
  `slå D6: 1–2 → …`). Kort blir data som motorn tolkar; nya kort kräver ingen ny kod.
- **Innehåll** — texter, siffror, balans.
- **Grafik** — kortmallar per korttyp, fylls från kortdatan.

### D. Spelplaner
- **Befintliga brädor** (Skede 1–2) behålls; ändringar görs som **klistermärken** — printfiler för dessa.
- **Nya brädor** för Skede 3 (t.ex. förvaltningens marknadskarta) — full mall.
- Former och rutnät som **data** (t.ex. `shapes.json` som källa), grafiken ritas ur dem — inte tvärtom.

### E. Printfiler
- Omfattning: **Skede 3-material** (nytt), **klistermärken** till befintliga brädor,
  eventuella **ersättningskort** i Skede 1–2 (hålls till ett minimum), och regelböckerna.
- Genereras automatiskt ur kortdata + mallar, så tryck och online alltid stämmer.
- **Kortark** med utfall och skärmärken, baksidor, rätt antal exemplar per kort.
- **Spelplaner** i skala, ev. uppdelade i delar.
- **Regelböcker i HTML med printfunktion** (print-CSS: sidbrytningar, marginaler, sidhuvud) —
  samma fil läses på skärm och skrivs ut/sparas som PDF. Ingen Word-källa.
- **Komponentlista** genereras ur datan (jfr `FORVALTNING_KOMPONENTER.md`).
- Tryckeriets krav: format, utfall, färgprofil (CMYK), upplösning — fastställs med tryckeriet.
- Varje utskrift märks med **regelversion**.

### F. Motor — samma för onlinespelet och spelloggen
- Ren tillståndsmaskin: *tillstånd + handling → nytt tillstånd*.
- Enda skillnaden mellan lägena är **varifrån slumpen kommer**:
  - *Online* — motorn slår tärningar och drar kort.
  - *Spellogg* — spelaren anger "jag slog 4" / "jag drog HR-7".
- Varje parti sparas som en logg av handlingar som kan spelas upp igen → felsökning.
- Loggen vet vilken regelversion den spelades med.

### G. Testspelare
- **Bottar** som spelar tusentals partier: fastnar logiken någonstans? Dominerar en strategi?
  Poängspridning, speltid, hur ofta varje kort spelar roll.
- **Människor** — ett enkelt provspelsprotokoll: vad man tittar efter, hur man rapporterar.
- Bottarna kan börja så fort motorn finns, före gränssnittet.

### H. Gränssnitt och drift
- Onlinespel, spellogg/companion, spelledarens dashboard.
- Deploy (Railway), rum, återanslutning.

---

## 3. Ordning

1. **Grund** — syfte, principer, källsanning (A)
2. **Gränssnitt mellan skeden** + ekonomimodellen (B)
3. **Regler per skede**, parallellt (B)
4. **Effektspråket** för kort (C)
5. **Motor + bottar** samtidigt — bottarna testar reglerna så fort de finns (F, G)
6. **Kortinnehåll och balans**, styrt av bottarnas resultat (C)
7. **Mallar, grafik och printfiler** — mallarna kan påbörjas tidigt (C, D, E)
8. **Gränssnitt** (H)

Varje område blir en naturlig tråd/session med tydlig ägare.

---

## 4. Utgångsläge för reglerna

**Beslut:** Alla befintliga regelböcker är mer eller mindre inaktuella. Vi läser oss fram
till vad som är korrekt. **Den version som till slut printades inför konferensen är mest
korrekt** och blir baslinjen; avvikelser mot kod, data och senare dokument prövas mot den.

### Det tryckta spelet — facit

Dropbox: `Åkepol tryckfiler/` (mappen `Mentorsprogram` hör inte till spelet).

| Mapp | Innehåll | Upplaga |
|---|---|---|
| `regelhäfte - 8 ex/` | `ÅKEPOL_Regelbok.pdf` | 8 ex |
| `Spelbräden - 8 ex/` | `PU_spelbräde2.pdf`, `PL_GF_spelbräde2.pdf`, `F_spelbräde2.pdf`, `scoreboard.pdf` | 8 ex |
| `Kort/` | 32 tryckfiler, se nedan | — |
| `plandokument - 1 ex av varje/` | Verksamhetsplan, Projektledningsplan, Projektplan, Förvaltningsplan — personaliserade för vart och ett av 20 dotterbolag (80 filer) | 1 ex/bolag |
| `tetrisfigurer/` | 45 projektbrickor (9 per typ: BRF, Förskola, Hyresrätt, Kontor, Lokal), 16 markexpansioner, markbitar (12 rutor), tomtrutor | — |

**Kort per skede:**
- *Ledning:* `L_personal`
- *Skede 1 (PU):* `PU_projekt`, `PU_BTA`, `PU_BYA`, `PU_markexpansion`, `PU_personal`, `PU_poldia`, `PU_poldia_spec`
- *Skede 2.1 (PL):* `PL_personal`, `PL_Händelsekort_S1–S4`, `PL_leverantörer_S1–S4`, `PL_organisation_S1–S4`
- *Skede 2.2 (GF):* `GF_faskort`, `GF_Konsekvenskort`, `GF_garantibesiktning`, `GF_kultur`
- *Skede 3 (F):* `F_DD`, `F_händelsekort`, `F_kvartal`, `F_moderbolagslån`, `F_omvärldskort`, `F_personal`, `F_yield`

**Iakttagelser:**
- Skede 3 trycktes enligt **Förvaltning v1** (`data/4_forvaltning/`), inte v2/2.1. Eftersom Skede 3 görs om spelar det mindre roll,
  men v1-korten är det spelarna faktiskt har.
- Plandokumenten är **genererade per bolag** ur en mall (pipeline i OneDrive `SPELET 2/0. Ledning/planer/`). Det är mallen som är regelinnehållet.
- `PL_*_S1–S4` — fyra identiska uppsättningar, märkta 1–4 för sortering efter spel.

### Hur korten producerades — och vilken data som trycktes

Kedjan (Dropbox `SPELET 2 - version 1 Åkepol/`, fryst 2026-05-13; se dess `AUTOMATISERING.md`, `CLAUDE.md`):

```
färgschema.xlsx → uppdatera_färger.py → CSV per korttyp (+ bildsida/textsida-sortering)
  → InDesign Data Merge (master_kortproduktion.jsx, tryckeri_58x88/88x88/88x146.jsx)
  → farglagg_projektkort.jsx → PDF → splitta_tryckeri.py → Åkepol tryckfiler/Kort/*_tryckeri.pdf
```

- InDesign-mallarna har **ingen fast länk** till en CSV — skriptet väljer `{PREFIX}_{KORTTYP}.csv` i samma mapp vid körning.
- Tryckfilerna exporterades **2026-04-27 ca 22:14 UTC**. CSV:er ändrade före dess är det som trycktes.
- **Ändrade efter tryck — lita inte på CSV:n, läs tryckfilen:** `PU_projekt.csv` (2026-05-02), `L_personal.csv` (2026-04-29).
- Alla övriga kort-CSV:er i `version 1` (PU, PL, GF, F) är daterade 2026-04-26/27, före tryck.
- **Statisk text finns i InDesign-mallen, inte i CSV:n** — t.ex. moderbolagslånets "MINNESKORT" och
  "BEHÅLL KORTET TILLS LÅNET ÄR ÅTERBETALT". Den måste läsas ur tryckfilen (en gång per korttyp).
- `S1–S4` på PL-korten är **sorteringsmärken**: fyra identiska uppsättningar, märkta 1–4 enbart för att korten ska gå att
  sortera tillbaka efter spel. Ingen spelmässig betydelse — i Excel blir det ett kort × 4 exemplar, och märkningen hör till
  produktionen, inte spelet.
- CSV-format: semikolon, cp1252, kolumnerna `fill_color`, `line_color`, `ordning_bild`, `ordning_text`, `@bild` m.fl. är
  produktionsdata; resten är kortinnehåll.

### JSON-filer att behålla och bygga vidare på

Produktionsdata från tryckkörningen (`version 1/PDF/Tryckbara/_tryckeri_temp/` m.fl.):

| Fil | Innehåll | Användning framåt |
|---|---|---|
| `*_layout.json` (en per korttyp och sida) | Kortformat (58×88, 88×88, 88×146 mm) och varje korts position per tryckark | Mall för nya printfiler, klistermärken och ersättningskort |
| `manifest_{format}.json` | Kopplingen tryckfil ↔ **exakt CSV-sökväg** ↔ bild-/textsida ↔ exemplarnr | Bevis för vilken data som trycktes (täcker bara senaste körningen per format) |
| `exemplar_map.json`, `Bilder/utskrift_config.json` | Antal exemplar per korttyp (t.ex. PL-korten och BTA/BYA ×4) | Antal kort i nya Excel |
| `Old/byggartefakter_2026-05/skede_config.json`, `typsnitt_config.json` | Skedesfärger och typsnitt | Grafisk profil |

I detta repo: `data/shapes.json` (projektbrickornas former), `data/companion_texts.json` (stegtexter),
`data/quiz_questions.json`.

### Python- och skriptkod att behålla och bygga vidare på

Dropbox `SPELET 2 - version 1 Åkepol/` (35 .py + InDesign-skript .jsx):

| Område | Filer | Användning framåt |
|---|---|---|
| **Tryckkedjan** | `förbered_csv.py`, `excel_till_config.py`, `Bilder/uppdatera_färger.py`, `skapa_tryckark.py`, `Mallar Indesign/splitta_tryckeri.py`, `interfoliera_pdf.py`, `provkort_ark.py` + `master_kortproduktion.jsx`, `master_tryckbart.jsx`, `tryckeri_58x88/88x88/88x146.jsx`, `farglagg_projektkort.jsx` | Grunden för nya printfiler (Skede 3, ersättningskort). Ska läsa de nya Excel-filerna |
| **IDML-generering** | `_dev/idml_builder.py`, `_dev/build_jvpaket_idml.py` | Bygger InDesign-dokument från kod — t.ex. klistermärken utan handarbete |
| **Former och bilder** | `1. Projektutveckling/generate_forms_v2.py`, `generate_svg.py` (Cricut), `konvertera_former_till_png.py`, `Bilder/shape_mask.py`, `Bilder/generate_images_v6.py`, `big_bang_skriv_om_prompter.py`, `patch_excel_testprompter.py` | Projektbrickornas former och kortbilder |
| **Regelböcker/planer** | `0. Ledning/planer/docx_to_markdown.py`, `markdown_to_pdf.py`, `splitta_planer.py`, `applicera_omslag.py`, `_dev/generate_mottagardata.py` | Utgångspunkt för HTML-regelböckerna med printfunktion |
| **Motor och testspelare** | `Old/kategori5_2026-05/husbyggspelet.py` (~180 kB), `simulering.py`, `spelare_optimal/forsiktig/aggressiv/kvalitet/kassabyggare.py`, `analys_abt.py` | **Testspelarna finns redan** — fem AI-strategier och batch-simulering. Referens för nya motorn och bottarna |

Obs: skripten har hårdkodade Windows-sökvägar (`C:\Users\niklas.sviden\OneDrive…\SPELET 2\`) och InDesign-stegen
kräver InDesign. Den delen körs på din dator — i ett projekt som en tråd "på din dator" via Remote Control.

### Metod för de nya Excel-filerna

1. Läs CSV:n från `version 1` (kortinnehåll + antal rader = antal tryckta kort).
2. Läs tryckfilens text för att fånga mallens statiska text och bekräfta att innehållet stämmer.
3. För `PU_projekt` och `L_personal`: tryckfilen är facit, CSV:n är bara hjälp.
4. Skriv en ny Excel per korttyp: en rad per unikt kort + antal exemplar; innehåll och produktionsdata på separata flikar.

### Övrigt källmaterial (OneDrive `SPELET 2/`)

| Dokument | Datum | Roll |
|---|---|---|
| `0. Ledning/planer/` — Word/markdown-källor + PDF-pipeline för regelbok och planer | 2026-05-03 | Källor till det tryckta |
| `ÅKEPOL_alla_kortdata.xlsx` | 2026-05-18 | All kortdata samlad (efter tryck — kan avvika) |
| `detaljerat spelflöde Åkepol.xlsx` | 2026-04-28 | Steg-för-steg-flöde |
| `Att göra.docx` | 2026-05-21 | Lärdomar efter konferensen (nedan) |
| `FORVALTNING_DESIGN_2-1.md` (detta repo) | 2026-07 | Omstart av Skede 3 |

### Lärdomar efter konferensen (`Att göra.docx`)

- Segerpoängen ska minska om man tagit moderbolagslån
- Hyresrätter och Lokaler behöver färger som går att skilja åt
- Tryck på båda sidor av projektbrickorna
- Regelboken måste bli lättare att följa
- Kulturvärdesrutan på samma höjd på alla kort (AC-, leverantörskort m.fl.)
- Tydligare instruktionstext längst ner på korten (mer mättad färg)
- Faskorten måste skickas runt/fotograferas — behöver en lösning
- Segerpoäng även i slutet av Skede 1 och 2
- Regler för nya projektuppsättningar inför runda 2 och 3
- Vissa PU-brickor: välj en av två projekttyper
- Illustrationer: beställa, hus sett ovanifrån på projektbrickorna
- Kommentarer i regelhäftet om hur reglerna motsvarar verkligheten

*Med grundbeslutet sorteras dessa: regelboks-/poängändringar och Skede 3 — gör; färger, dubbelsidiga
brickor och kortlayout — kräver omtryck, prövas ett i taget; illustrationer — senare.*

---

## 5. Vad vi behåller som referens

Allt byggs nytt; bara grafiken återanvänds. Nuvarande kod, data och dokument
(`REGELBOK_CHECKLIST.md`, `ANALYS_RAPPORT.md`, `FUTURE_UPGRADES.md`, `FORVALTNING_DESIGN_2-1.md`,
`PROMPT_FORSLAG.md`) är underlag och facit för vad som redan är bestämt och varför.

---

## 5b. Status kortdata (Ledning, Skede 1–2)

Alla 16 korttyper finns i `kortdata/`, byggda av `verktyg/bygg_*_excel.py` och verifierade kort för kort
mot tryckfilerna (utläst text i `arv/tryckt_text/`). Avvikelser mot CSV har lösts till tryckets fördel.

| Korttyp | Unika kort | Ex/spel | Format |
|---|---|---|---|
| L_personal | 18 | 1 | 58×88 |
| PU_projekt | 45 | 1 | 88×146 |
| PU_personal | 10 | 1 | 58×88 |
| PU_poldia | 40 | 1 | 58×88 |
| PU_poldia_spec | 12 | 1 | 58×88 |
| PU_markexpansion | 16 | 1 | 58×88 |
| PU_BTA / PU_BYA | 4 + 4 | 4 | 58×88 |
| PL_personal | 10 | 1 | 58×88 |
| PL_organisation | 16 | 4 (S1–S4) | 58×88 |
| PL_leverantörer | 36 | 4 (S1–S4) | 58×88 |
| PL_Händelsekort | 54 | 4 (S1–S4) | 58×88 |
| GF_faskort | 31 | 1 | 88×88 |
| GF_Konsekvenskort | 30 | 1 | 58×88 |
| GF_garantibesiktning | 44 | 1 | 58×88 |
| GF_kultur | 80 | 1 | 58×88 |

### Beslut om korten

**Korten gäller alltid först — så att vi slipper omtryck.** Text- och namnfel på tryckta kort rättas inte
för sig; de rättas bara om kortet ändå trycks om. Regelbok, Excel och kod anpassas efter korten.

| Fråga | Beslut |
|---|---|
| K1 Gamla namn i L-texterna (Riktningsgivaren, Maskinrumsmästaren) | Står kvar — **personalkorten trycks inte om** |
| K2 "MINSKAR KRAVEN…" vs "FÖRBÄTTRAR KRAVUPPFYLLNADEN…" | **Medvetet** — se *Krav och kravuppfyllnad* nedan |
| K3 PC-6 | **Hållbarhetsivraren** är korrekt; bildfilens namn "Hållbarhetschefen" är fel (bara produktion) |
| K5 Faskort: kulturkostnad steg 1 = 2 Mkr | **Avsiktligt** — "andra chans" till samma kostnad när man förstått logiken |
| K6 Avkortade faskortsnamn | **De fulla namnen är de rätta** (tryckets avkortning står kvar tills ev. omtryck) |
| K7 B/S/K på faskorten | **Bostad / Special / Komplex** — tidigare indelning, samma logik |
| K8 "ARB" vs "ABM" | Står kvar som tryckt |
| K9 "erfa" | Står kvar som tryckt |
| K11 Dubbla id "STO - 1…4" | Står kvar som tryckt |

| K4 Ändring i L_personal.csv 2026-04-29 | Okänd — korten gäller |

#### Krav och kravuppfyllnad (regelbegrepp)

- **Skede 1:** alla ökningar/minskningar gäller **kravet** (Q/T/H). Slutsumman är det som ska uppnås i Skede 2.
  Därför *minskar* projektchefen (PU_personal) **kravet**.
- **Skede 2:** arbetschefen (PL_personal) *ökar* **kravuppfyllnaden**.
- På den fysiska scoreboarden är **kravet den svarta kuben** och **uppfyllnaden de färgade kuberna**.

| K10 Blanka kort (8 PL-händelsekort, 2 GF-konsekvenskort) | Trycktes av misstag — **tas bort ur spelet**, ingår inte i kortdatan |

## 5c. Status regelbok

`regler/regelbok.html` — en fil, läses på skärm och skrivs ut i A4 (knappen "Skriv ut").
- **1.0** (git-historik): ordagrant som tryckt 2026-05-03, verifierad ord för ord mot tryck-PDF:en.
- **2.0** (nu): rättad mot korten — nämnden R1 (4.1), krav/kravuppfyllnad (3.3, 3.8, 6.1), D20-skalor per
  korttyp (3.5, 11.1), komponentantal (1.5), kapitel omnumrerade (Planering var också "5") med rättade
  hänvisningar, Förvaltningen (9) och slutvärderingen (10) markerade som under omarbetning.
  Ändringar märkta "Ändrat i 2.0"; sammanfattning i rutan "Nytt i version 2.0".
- Saknas: regelbokens 12 bilder (hämtas när nätverket för Dropbox är öppet).

## 5d. Skede 3 (Förvaltning 2.1) — status och implementationsplan

Underlag på main: `FORVALTNING_DESIGN_2-1.md` (logiken), `FORVALTNING_KORTSPEC.md` (effektkoder och
frekvenser), `data/forvaltning_2-1/F2-1_*.csv` — 256 kort i fem lekar + 6 FC + 4 FS, med text.

### Designluckor att stänga innan bottarna (F0)
- **Konsekvens-/garantikort finns bara i Kvartal 0**, men FC-4 Nätverkaren (svaghet), FC-5 Skölden och
  FS-4 Besiktningsgeniet verkar "per varv" på dem. Antingen dras sådana kort i loopen, eller så måste de
  tre egenskaperna skrivas om — annars är Skölden nästan värdelös.
- **FC saknar typ.** Alla sex är generella (förhandling/energi/resurs). Pokémon-delen finns i lekarnas
  typkaraktär men inte i personalen. Beslut: behåll generella, eller ge FC en typ?
- **FS-2 Kvalitetsoptimeraren** (+1 dolt DN per varv) blir +1 bas-DN efter tre kvartal — misstänkt
  starkast. Bottarna får avgöra.
- **Tio öppna loopfrågor** från den andra tråden (villkorskort, bankens ordning, påfyllning, omvärld vs
  yieldbana, FS-förmågor, 3-i-netto, fokustyp, uppgraderingskostnad, konsekvenskortens plats, konkurs).

### Plan
| Fas | Innehåll | Resultat |
|---|---|---|
| F0 | Stäng designluckorna ovan | Beslut i designdokumentet |
| F1 ✅ | Kortdata: `kortdata/F_*.xlsx` (8 filer, ~350 kort) byggda med `verktyg/bygg_f_excel.py` — effektkoder mot kortspecen, antal, unika ID:n och korttext kontrollerade. Excel är nu källan; `data/forvaltning_2-1/` utgår när grenarna slagits ihop. | 8 Excel-filer |
| F2 ✅ | Motor för Skede 3: `motor/` (tillstånd, kortladdning ur `kortdata/`, utbytbar slump, hela kvartalsloopen, slutavräkning). Antaganden samlade i `Parametrar`. Tester i `tester/`. | `motor/` + tester |
| F3 ▶ | Bottar: fem strategier (balanserad, försiktig, hävstång, aggressiv, energi), `python -m motor.simulera`. Första resultat nedan. | Balansrapport |
| F4 | Kalibrering ur F3: 0,7/1,2-faktorer, fördelningar, slutformelns faktor, FC/FS. | Justerade Excel |
| F5 | Regelbok kapitel 9 skrivs om efter låst loop; kapitel 10 (slutvärdering) efter kalibrering. | Regelbok 3.0 |
| F6 | Tryck: nya F-kort, MV-tabell, yieldbana, kvartalsspår, brickor/clips, stora DN-kort. **Projektkortens nya baksida** (tryckt lån + ny förvaltningssektion) samordnas med omtrycket av alla 45 projektkort. | Printfiler |
| F7 | Online/spellogg ovanpå motorn — när Skede 1–2 också finns i motorn. | App |

### Första bottresultat (4000 partier, 2026-09-26)

- **Marknaden är nästan död med lån 70 %:** banken tar 0,08 fastigheter per parti, 1,9 köp, 0,02 tvångsbud.
  Med ±0,5-steg i yield krävs ~3 steg nedåt innan MV < lån. Känslighet: lån 80 % → 0,36 bank/parti,
  85 % → 0,77, 90 % → 2,4. *Kalibreringsfråga: lånenivå (eller DN/MV-skalan när projektkorten görs om).*
- **Energiuppgradering är för billig:** ~23 per parti (nästan maxtaket 6 per spelare), 74 % lyckas per försök.
  +1 energiklass = +1 DN ≈ +20–25 Mkr MV för ~4 Mkr. Vid 8 Mkr/försök: 14 per parti.
- **Strategierna vinner lika ofta (24–26 %)** — startportföljen (3–5 fastigheter) avgör mer än besluten.
- **Plus-visning tvingande eller valfri: ingen skillnad** i utfall → tvingande åt båda håll räcker (enklast).
- **FC:** Bostadsveteranen och Den lugna ~30 % vinst, Skölden 18 %. **FS:** jämna (23–26 %).
- **Typkaraktären fungerar:** DN-drift per parti hyresrätt +1,6, förskola +1,3, lokal +0,4, kontor −0,7.
- **Motorantaganden att bekräfta:** brickor = 1/3 DN i intäkten (Anna-exemplet räknade 1), startkassa 20,
  fokustyp i fast rotation, villkorskort tolkade ur texten.

## 6. Öppna frågor

1. **Facit** — ~~är Word-regelboken facit?~~ Besvarat: den printade versionen är baslinje.
   Tryckfilerna finns i Dropbox `Åkepol tryckfiler/` (se §4). `S1–S4` = sorteringsmärken, korten är identiska (se §4).
2. ~~**Huvudprodukt**~~ Besvarat: det fysiska spelet. Minimala ändringar i Skede 1–2, Skede 3 görs om, brädor fixas med klistermärken.
3. **Var** — omstart i det här repot med ny struktur, eller ett nytt repo?
4. **Källsanning** — regelböckerna blir HTML i repot (beslutat). Flyttar även kortdatan in i repot, eller förblir SPELET 2 källan?
5. ~~Projektkortens förvaltningssektion~~ Besvarat: alla 45 projektkort trycks om.
6. **Tryck** — vilket tryckeri/format? Finns företagsmall/grafisk profil (ÅKEPOL) att utgå från?
