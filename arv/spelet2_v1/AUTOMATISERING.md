# Kortautomatisering — hur flödet hänger ihop

Senast uppdaterad i samband med `farglagg_projektkort.jsx` v14 och
`uppdatera_färger.py` v5.

## Datapath — från din redigering till färdig PDF

```
  färgschema.xlsx           ← EDIT HÄR
         │
         ▼ python uppdatera_färger.py
  ┌──────┴─────────────────────────────────────┐
  │ CSV:er i 1./2./3./4.-mapparna               │
  │   fill_color, line_color, skede_color       │
  │ typsnitt_config.json                        │
  │ utskrift_config.json                        │
  │ skede_config.json                           │
  └──────┬─────────────────────────────────────┘
         │
         ▼ master_kortproduktion.jsx (i InDesign)
  InDesign Data Merge → farglagg_projektkort.jsx
         │                          │
         │                          ├─ Sätter _fillcolor & _linecolor hex
         │                          ├─ Sätter _skede_color hex (om templaten har den)
         │                          ├─ Applicerar typsnitt från typsnitt_config
         │                          └─ Applicerar fas-färg på _skede_* element
         │
         ▼
  PDF-mappen  →  interfoliera_pdf.py  →  utskriftsklara ark
```

## Vad händer automatiskt

| Du ändrar | Kör | Effekt |
|---|---|---|
| Kategorifärg (Färger-bladet) | `uppdatera_färger.py` + kör `master_kortproduktion.jsx` i InDesign | Alla kortens fill/line byts |
| Typsnitt (Typsnitt-bladet) | Samma | Alla rubriker/brödtexter byts |
| Antal exemplar (Utskrift-bladet) | Samma | PDF-exporten använder rätt antal |
| Skede-färg (Skede-mappning-bladet) | Samma | Fas-färg ändras på alla `_skede_*`-element |
| CSV-mappning (fil/typ → färgnamn) | Samma | Rätt kategori får rätt färg |
| Korttext (CSV Beskrivning/Text/Rubrik) | Samma | Data Merge plockar upp nya texter |

Allt styrs från **färgschema.xlsx** + **CSV-filerna**. Du behöver aldrig
redigera hex-koder eller font-namn i `.jsx`-skript eller `.indd`-filer.

## Vad du gör en gång i InDesign (för att få full effekt)

Placeholders som InDesign Data Merge redan känner igen finns troligen
(`_fillcolor`, `_linecolor`). Det som `v14` av färglaggsskriptet dessutom
kan hantera är fas-markering via `_skede_*`-namn.

### För att få Banshaft/Typsnitt-ändringar att fungera

Ingenting behövs i templaten! Skriptet `v14` läser `typsnitt_config.json`
och applicerar fonten per textram baserat på teckenstorlek (rubrik = ≥14pt,
brödtext = <14pt).

**Förutsättning**: Banshaft-fonten måste vara installerad på datorn som
kör InDesign. Om den inte finns så ignoreras ändringen tyst och tidigare
font behålls.

### För att få fas-färg (skede_color) att synas på korten

Du har två alternativ för varje template (.indd-fil):

**Alternativ A — platshållartext (rekommenderat)**

1. Öppna en template, t.ex. `PU_projekt_bildsida.indd`
2. Skapa en liten textram någonstans på kortet (syns inte på utskrift —
   den plockas bort automatiskt av `master_kortproduktion.jsx`)
3. Öppna panelen `Fönster > Namn` (eller välj ramen och tryck F2) och
   döp ramen till `_skede_color`
4. Öppna panelen `Fönster > Verktyg > Data-sammanfogning`
5. Placera `<<skede_color>>`-fältet i textramen
6. Spara

Sen plockas det rätta hex-värdet automatiskt från CSV:en vid varje merge.
Detta ger dig flexibilitet att override:a fas-färgen per rad om du vill.

**Alternativ B — hardcoded fallback (ingen templateändring)**

Om du hoppar över A så använder skriptet fallback-logik: det tittar
på `.indd`-filens namn (`PU_…` → brun, `PL_…` → blå, osv.) och hämtar
hex från `skede_config.json`. Fungerar ut ur lådan.

### För att få fas-färgen att synas visuellt

Skriptet applicerar fas-färgen på element **namngivna** enligt dessa regler:

| Elementnamn | Vad som händer |
|---|---|
| `_skede_stripe` | Fylls med fas-färgen |
| `_skede_bar` | Fylls med fas-färgen |
| `_skede_badge` | Fylls med fas-färgen |
| `_skede_frame` (innehåller "frame") | Stroke sätts till fas-färgen |
| `_skede_text` (textram) | Alla tecken får fas-färgen |

För att lägga till en fas-rand i en template, en gång per `.indd`:

1. Öppna templaten
2. Rita en smal rektangel (t.ex. 4 mm bred, full höjd på kanten av kortet)
3. Välj ramen, tryck F2 och döp den till `_skede_stripe`
4. Lämna fyllningsfärgen på default (skriptet sätter den vid körning)
5. Spara

Gör samma sak för alla templates som hör till samma fas (eller kopiera ramen
mellan filer). Från och med nästa merge får alla kort i den fasen en färgrand.

## Filer som är del av systemet

| Fil | Roll |
|---|---|
| `färgschema.xlsx` | Källa till sanning — alla färger, fonts, utskrift, mappningar |
| `uppdatera_färger.py` | Läser xlsx → skriver CSV-färger + JSON-configs |
| `typsnitt_config.json` | Auto-genererad — font för rubrik/brödtext |
| `utskrift_config.json` | Auto-genererad — antal exemplar per PDF |
| `skede_config.json` | Auto-genererad — fas-färg per prefix (NY) |
| `Mallar Indesign/master_kortproduktion.jsx` | Orkestrerar merge + export |
| `Mallar Indesign/farglagg_projektkort.jsx` v14 | Färgsätter + typsnitter + skede |
| `Mallar Indesign/typsnitt_block.jsx` | **OBSOLET** — integrerad i färglaggsskriptet, kan raderas |
| `Mallar Indesign/diagnostik_*.jsx` | Felsökning |
| `interfoliera_pdf.py` | Slår ihop PDF:er för utskrift |

## Felsökning

**"Banshaft applicerades inte"**: 
- Är fonten installerad på datorn? Kontrollera i Typkatalogen/Font Book.
- Har du sparat `färgschema.xlsx`?
- Har du kört `python uppdatera_färger.py` *efter* sparningen?
- Kolla `typsnitt_config.json` — innehåller den "Banshaft"?

**"Fas-färgen syns inte på korten"**:
- Har templaten ett element namngivet `_skede_stripe` (eller liknande)?
- Om inte → se Alternativ B ovan, men notera att ingen visuell element
  får färgen automatiskt utan att du lägger till ett namngivet element.

**"Kategori-färgen är fel"**:
- Kolla `CSV-mappning`-bladet i färgschema.xlsx — finns rätt (fil, typ)-rad?
- Kolla att färgnamnet du refererar till finns i `Färger`-bladet.
- Kör `uppdatera_färger.py` igen och bekräfta att rätt hex hamnar i CSV:en.

**"Loggfil för InDesign-körning"**:
`kortproduktion_logg.txt` i SPELET 2-roten skrivs av
`master_kortproduktion.jsx` vid varje körning.

