# CLAUDE.md – ÅKEPOL

## Projektöversikt

ÅKEPOL (tidigare PMOpoly / Husbyggspelet) är ett utbildningsspel om fastighetsutveckling och projektledning. Det finns som:

- **Digitalt spel** – Python-baserat (husbyggspelet.py) med AI-motståndare och simuleringsstöd
- **Fysiskt brädspel** – Kort, spelbrädor och tokens producerade via CSV → InDesign → PDF-pipeline

Spelet har fyra faser som speglar en fastighets livscykel:

1. **Projektutveckling** (Fas 1) – Markförvärv, projektval, politisk dialog, nämndbeslut
2. **Projektplanering** (Fas 2) – Leverantörsval, organisation, planeringshändelser
3. **Projektgenomförande** (Fas 3) – 8 utförandefaser, kompetenskort, konsekvenser
4. **Fastighetsförvaltning** (Fas 4) – Personal, drift, yield, omvärldshändelser

---

## Mappstruktur

```
SPELET 2/
├── husbyggspelet.py              # Huvudsaklig spelmotor (~4600 rader)
├── simulering.py                 # Batch-simulering av 5 AI-strategier
├── analys_abt.py                 # Kostnadsanalys efter spelomgång
├── förbered_csv.py               # Genererar bildsida/textsida-CSV:er
├── uppdatera_färger.py           # Uppdaterar färger i alla CSV:er + config
├── interfoliera_pdf.py           # Kombinerar PDF:er för dubbelsidig utskrift
├── spelare_*.py                  # AI-strategier (optimal, försiktig, aggressiv, kvalitet, kassabyggare)
├── typsnitt_config.json          # Typsnittsval (Minion Pro)
├── utskrift_config.json          # Kort per rad per fas-prefix
├── PMOpoly_ekonomisk_modell.xlsx # Ekonomisk modell (filnamn pending byte → ÅKEPOL_ekonomisk_modell.xlsx)
├── färgschema.xlsx               # Färgpalett (ljus/mörk hex per fas)
│
├── 1. Projektutveckling/         # Fas 1: kort-CSV:er, InDesign-mallar, spelbrädor
│   ├── PU_projekt.csv            # Projektkort (typ, BTA, kostnad, Q/H/T)
│   ├── PU_poldia.csv             # Politik/Dialog-kort
│   ├── PU_BTABYA.csv             # BTA/BYA-klassificering
│   ├── PU_markexpansion.csv      # Markexpansionskort
│   ├── PU_PL_personal.csv        # PC/AC-kort (Projektchef/Arbetschef)
│   ├── generate_forms_v2.py      # Genererar projektformbilder (PNG)
│   ├── generate_svg.py           # Cricut-ready SVG-export
│   └── *.indd                    # InDesign-mallar
│
├── 2. Planering/                 # Fas 2
│   ├── PL_Leverantörer.csv       # Leverantörskort (typ, nivå, kompetenser)
│   ├── PL_Organisation.csv       # Organisationskort
│   └── PL_Händelsekort.csv       # Planeringshändelsekort
│
├── 3. Genomförande/              # Fas 3
│   ├── GF_faskort.csv            # Faskort (8 utförandefaser)
│   ├── GF_konsekvenskort.csv     # Konsekvenskort (T/Q/H-straff)
│   ├── GF_garantibesiktning.csv  # Garantibesiktningskort
│   └── GF_kultur.csv             # Företagskulturkort (externt stöd)
│
├── 4. Förvaltning/               # Fas 4
│   ├── F_personal.csv            # Personalkort (FC/FS)
│   ├── F_händelsekort.csv        # Förvaltningshändelsekort
│   ├── F_DD.csv                  # Due Diligence-kort
│   ├── F_omvärldskort.csv        # Omvärldskort (påverkar alla)
│   ├── F_kvartal.csv             # Kvartalsprogressionskort
│   ├── F_yield.csv               # Yieldberäkning
│   └── F_moderbolagslån.csv      # Moderbolagslån
│
├── Spelinstruktioner/            # Regeldokument (docx)
├── Companion/                    # Verksamhetssystem-referens
├── Bilder/                       # Bildtillgångar + genereringsskript
├── Mallar Indesign/              # InDesign-huvudmallar
├── PDF/                          # Exporterade PDF:er
└── Old/                          # Arkiverade versioner
```

---

## Namnkonventioner

### Fas-prefix

| Prefix | Fas | Mapp |
|--------|-----|------|
| `PU_`  | 1. Projektutveckling | `1. Projektutveckling/` |
| `PL_`  | 2. Planering | `2. Planering/` |
| `GF_`  | 3. Genomförande | `3. Genomförande/` |
| `F_`   | 4. Förvaltning | `4. Förvaltning/` |

### Filnamnsmönster för kort

- `{PREFIX}_{KORTTYP}.csv` – Basdata
- `{PREFIX}_{KORTTYP}_bildsida.csv` – Sorterad för bildsida (InDesign)
- `{PREFIX}_{KORTTYP}_textsida.csv` – Spegelvänd radordning för textsida
- `{PREFIX}_{KORTTYP}_bildsida.indd` – InDesign-mall (datamerge från CSV)
- `{PREFIX}_{KORTTYP}_textsida.indd` – InDesign-mall (baksida)

### Bildsida vs Textsida

Bildsida = framsida av kortet (bild), textsida = baksida (text). Vid dubbelsidig utskrift spegelvänds radordningen så att framsida och baksida hamnar rätt. `förbered_csv.py` genererar dessa par automatiskt.

---

## CSV-format

- **Encoding:** cp1252 (Windows), skripten autodetekterar (utf-8-sig → utf-8 → cp1252 → latin-1)
- **Delimiter:** semikolon (`;`)
- **Gemensamma kolumner:** `fill_color` (mörk hex, WCAG AAA), `line_color` (ljus hex), `@bildsida`, `@textsida`, `ordning_bild`, `ordning_text`
- **Kort per rad:** PU=3, PL=4, GF=3, F=3 (styrs av `utskrift_config.json`)

---

## Centrala spelbegrepp

| Begrepp | Förklaring |
|---------|-----------|
| **BTA** | Bruttototalarea (kvm) – summa av alla projekts area |
| **BYA** | Byggnadsarea – beräknas som formfaktor × 250 per projekt |
| **Q** | Kvalitet – målvärde som sätts i Fas 2, påverkas av leverantörer/organisation |
| **H** | Hållbarhet – samma logik som Q |
| **T** | Byggtid (månader) – base 12, min 8, påverkas av val |
| **ABT** | Arbetsbudget – 85% av (Anskaffning + intäkter - Fas 1-kostnader) |
| **EK** | Eget kapital – spelarens totala ekonomi |
| **TG** | Saldo-% – kvarvarande ABT som % av ursprunglig ABT-budget |
| **FV** | Fastighetsvärde – marknadsvärde × (1 + energiklassbonus) |
| **D20** | Tärningskast 1-20, trösklar: ≤5 / 6-17 / 18-20 / 21+ (med erfarenhetsbonus) |
| **Riskbuffert** | Auto-success vid dåligt tärningskast (kommer från PC/AC-val) |
| **Kompetenser** | STA, KOM, SAM, NOG, INN, ABM – sex kompetensparametrar |
| **Trigger** | BOSTÄDER ⊂ STAPLAD ⊂ KOMPLEX – hierarkisk matchning av projektmix |
| **Moderbolagstillskott** | Nödlån: 100 Mkr per block, 5 Mkr avgift (dras från EK) |

---

## Arbetsflöden

### Kortproduktion (CSV → tryckfärdiga kort)

```
färgschema.xlsx
    ↓
uppdatera_färger.py  →  Uppdaterar fill_color/line_color i alla CSV:er
    ↓                    + genererar typsnitt_config.json & utskrift_config.json
förbered_csv.py      →  Skapar *_bildsida.csv och *_textsida.csv
    ↓
InDesign (datamerge) →  Exportera till PDF
    ↓
interfoliera_pdf.py  →  Kombinerar bild+text-PDF:er för dubbelsidig utskrift
```

### Simulering och analys

```
husbyggspelet.py     →  Enskild spelomgång (mänsklig spelare + AI)
simulering.py        →  Batch-körning av 5 strategier × N iterationer
analys_abt.py        →  Detaljerad kostnadsuppföljning per fas
```

### Bildgenerering

```
generate_forms_v2.py →  Projektform-PNG (rutnätsbaserade, seedade från namn)
generate_svg.py      →  Cricut-ready SVG med alla former
Bilder/generate_images_v2.py → Kortbilder
```

---

## Python-kodbas

### Krav

- Python 3.8+
- `openpyxl` (pip install openpyxl)
- Standardbibliotek: csv, random, os, sys, re, dataclasses, platform

### Arkitektur (husbyggspelet.py)

Huvudklasser:
- `Project` – Ett fastighetsprojekt med alla parametrar
- `Player` – Spelarens tillstånd (projekt, ekonomi, personal, kompetenser)
- `GameState` – Hela spelets tillstånd
- `Supplier`, `Organisation` – Fas 2-val med kompetenser och kostnader
- `PlanningEventCard`, `PhaseCard`, `PenaltyCard` – Korttyper
- `Staff`, `ManagementEvent`, `WorldEvent`, `DDCard` – Fas 4-komponenter

Fasernas funktioner:
- `phase_mark_och_tomt()` → `phase_board_game()` → `phase_namndbeslut()` → `phase_placement()` → `phase_ekonomi()`
- `phase_planering()` → `phase_genomforande()` → `phase_forvaltning()`

AI-moduler (spelare_*.py):
- `AIBrain`-klass med strategispecifik beslutslogik
- Patchar `input()`/`print()` för automatisk spelkörning
- Strategier: optimal, försiktig, aggressiv, kvalitet, kassabyggare

### Dataflöde

Alla speldata laddas från CSV-filer vid start. `DATA_DIR` pekar på OneDrive-rotmappen (`SPELET 2/`). Filsökvägar definieras i `DATA_FILES`-dict med relativa sökvägar under respektive fas-mapp.

---

## Viktigt att veta vid ändringar

- **CSV-ändringar** kräver att `förbered_csv.py` körs om för att generera nya bildsida/textsida-filer
- **Färgändringar** görs i `färgschema.xlsx` och propageras med `uppdatera_färger.py`
- **Nya korttyper** kräver: ny CSV, ny loader i husbyggspelet.py, ny InDesign-mall
- **Tröskelvärden** (D20-systemet) är hårdkodade som `[5, 17, 20, 9999]` i koden
- **Formfaktor** 1-8 styr projektformens komplexitet (används av generate_forms_v2.py)
- **Encoding:** Håll cp1252 för CSV:er som ska till InDesign på Windows

