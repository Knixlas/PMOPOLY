# Komponentlista — Skede 3: Förvaltning

*Vad som behöver produceras för att spela förvaltningsdelen manuellt vid bordet.
Antal utgår från nuvarande CSV-data i `data/4_forvaltning_v2/`.*

---

## Spelplan (1)

En spelplan med:

- **Marknadskarta — två yield-spår** med pekare:
  - Bostäder: start 4 %, spann 2–6 %, steg 0,5 pp
  - Kommersiellt: start 5 %, spann 3–7 %, steg 0,5 pp
- **Yield-kö** — 3 platser för uppvända omvärldskort framför kartan (tre kvartal framåt)
- **MV-tabell** — tryckt, yield i kolumn × effektiv DN i rad, tre värden per cell:
  Tvång (0,7×) / Normal (1,0×) / Fientlig (1,2×), avrundat till närmaste 5 Mkr
- **Marknadsyta** — för nya fastigheter (Q1: 3, Q2: 2, Q3: 1, Q4: 0)
- **Kvartalsspår** Q1–Q4
- **Spelarytor** för korthögar och kassa

---

## Fastighetskort (45)

9 kort per typ. Förtryckt på varje kort: namn, typ, anskaffning, **bas-DN**,
**lånebelopp**, **räntekostnad/kvartal**, marknadsvärde.

| Typ | Antal | Bas-DN-spann |
|---|---|---|
| BRF | 9 | (säljs vid övergången) |
| Förskola | 9 | 3–9 |
| Lokal | 9 | 2–9 |
| Kontor | 9 | 4–11 |
| Hyresrätt | 9 | 3–7 |

*BRF förvaltas inte i Skede 3 — de säljs till föreningen vid övergången (MV + 10 Mkr).*

---

## Markörer på fastigheterna

| Komponent | Antal (ca) | Not |
|---|---|---|
| DN-kort 1–15 | ~80 | Ett per fastighet, byts när DN ändras. Flera av varje siffra. |
| Energiklass-clips A–E | ~40 | Ett per fastighet, byts vid uppgradering/degradering |
| Röda markörer (risk för tvångsförsäljning) | ~15 | Läggs när MV < lån nästa kvartal |

---

## Personal — arketyper

| Lek | Antal | Innehåll |
|---|---|---|
| FC-arketyper | 6 | Förhandlaren, Skölden, Generalisten, Nätverkaren, Den lugna, Tekniska experten |
| FS-arketyper | 4 | Margareta "Rivaren", Per "Kvalitetsoptimeraren", Lars "Spionen", Sara "Besiktningsgeniet" |

Varje spelare väljer **en FC + en FS** vid övergången. Inga kostnader, inga kapacitetstak.

---

## Personkort (rekommenderat ~20 + ~20)

Engångskort som dras till handen. CSV:n (`F2_FCkort`, `F2_FSkort`) har 80 tomma
kortplatser vardera — nuvarande spellogik använder **20 FC + 20 FS** med definierade
effekter. Rekommendation: tryck 20 av varje att börja med.

Effekttyper (direkta och permanenta när de spelas):
- +5 / +3 Mkr till kassan
- +1 bas-DN permanent
- −10 Mkr lån permanent
- +2 / +3 på hyresförhandling
- auto-success energiuppgradering
- blockera konsekvenskort / annullera minuskort / kasta 3 minuskort
- (reaktiva: förköpsrätt, kika på motståndarkort)

**Dragning:** 2 FC + 2 FS vid start, sedan 1 FC + 1 FS per kvartal. Max 6 på hand.

---

## Händelsekort per typ (31)

En lek per förvaltad fastighetstyp — varje lek matchar sin typ direkt.

| Lek | Antal | Riskprofil | Innehåll (7 kort) |
|---|---|---|---|
| Hyresrätt (HR) | 7 | stabil, milda utslag | 2 plus, 2 minus, 1 varning, 1 energivarning, 1 förköp |
| Förskola (FS) | 7 | trygg samhällsfastighet | 2 plus, 2 minus, 1 varning, 1 energivarning, 1 förköp |
| Lokal (LO) | 7 | trendkänslig | 2 plus, 2 minus, 1 varning, 1 energivarning, 1 förköp |
| Kontor (KO) | 7 | cyklisk | 2 plus, 2 minus, 1 varning, 1 energivarning, 1 förköp |
| Stoppkort (ST) | 3 | reaktiva | avvärjer fientligt bud (en per HR/Kontor/Lokal) |

**Dragning:** 1 kort per fastighet vid övergången och varje kvartal, ur leken som
matchar fastighetens typ. Plus/minus läggs dolt; 3 i netto → ±1 bas-DN. Stopp- och
förköp­skort → till handen.

---

## Övriga kortlekar

| Lek | Antal | Not |
|---|---|---|
| DD-kort | 10 | Dolda. Intäkt = pluskort, Kostnad = minuskort. Dras vid övergång + köp. |
| Omvärldskort | 10 | Yield-rörelser + bordseffekter. Effekter i hela Mkr. |
| Kvartalskort | 4 | Q1–Q4-specifika |
| Konsekvenskort | 8 | Från Skede 2.2, länkade till garantikort |
| Garantikort | 8 | Länkade par med konsekvenskort |

---

## Restkort och tärningar

| Komponent | Antal | Not |
|---|---|---|
| Restkort (markörer) | ~15 | 1 per överbliven DN-enhet; 4 → 1 Mkr cash |
| Moderbolagslån-markörer | ~15 | Nödknapp vid likviditetskris (100 Mkr/block, 5 Mkr avgift) |
| Tärning D10 | 1 | Förstaval vid nya fastigheter |
| Tärning D20 | 1 | Energiuppgraderingar (≥ 10 = lyckas) |

---

## Sammanställning

| Kategori | Ungefärligt antal fysiska bitar |
|---|---|
| Fastighetskort | 45 |
| DN-kort + energiclips + röda markörer | ~135 |
| Personal-arketyper (FC+FS) | 10 |
| Personkort (FC+FS) | ~40 |
| Händelsekort (typ + stopp) | 31 |
| DD / omvärld / kvartal / konsekvens / garanti | 40 |
| Restkort + lånemarkörer | ~30 |
| Tärningar | 2 |
| Spelplan | 1 |
| **Totalt** | **~330 kort/bitar + spelplan** |

---

## Vad som är digitalt-bara (inte fysiska komponenter)

Följande finns i provspelsappen men behövs inte för det manuella spelet:
- AI-motspelare (för solo-läge)
- Preset "Starta i Skede 2/3" (hoppar över tidigare skeden)
- Live-poängtavla och yield-utvecklingsgraf
- Automatisk restkort-bokföring och margin-call-avläsning

I det manuella spelet gör spelledaren/spelarna dessa moment för hand.
