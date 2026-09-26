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
- **Grafik** — en mall per bräde (PU-brädet, planerings-/genomförandebrädet, förvaltningens marknadskarta m.m.).
- Former och rutnät som **data** (t.ex. `shapes.json` som källa), grafiken ritas ur dem — inte tvärtom.

### E. Printfiler
- Genereras automatiskt ur kortdata + mallar, så tryck och online alltid stämmer.
- **Kortark** med utfall och skärmärken, baksidor, rätt antal exemplar per kort.
- **Spelplaner** i skala, ev. uppdelade i delar.
- **Regelbok** som PDF (och .docx vid behov) ur markdown-källan.
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

## 4. Vad vi behåller som referens

Omstart betyder inte att kasta bort: nuvarande kod, data och dokument
(`REGELBOK_CHECKLIST.md`, `ANALYS_RAPPORT.md`, `FUTURE_UPGRADES.md`, `FORVALTNING_DESIGN_2-1.md`,
`PROMPT_FORSLAG.md`) är underlag och facit för vad som redan är bestämt och varför.

---

## 5. Öppna frågor

1. **Facit** — är `ÅKEPOL_Regelbok.docx` fortfarande facit, och är Förvaltning 2.1 det senaste för Skede 3?
2. **Huvudprodukt** — är det fysiska spelet huvudprodukten med det digitala som stöd, eller tvärtom?
3. **Var** — omstart i det här repot med ny struktur, eller ett nytt repo?
4. **Källsanning** — flyttar regler (som markdown) och kortdata in i repot, med Word och tryckfiler genererade? Eller förblir OneDrive/SPELET 2 källan?
5. **Tryck** — vilket tryckeri/format? Finns företagsmall/grafisk profil (ÅKEPOL) att utgå från?
