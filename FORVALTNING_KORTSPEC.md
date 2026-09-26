# Förvaltning 2.1 — kortspecifikation

*Ritningen för alla kortlekar i Skede 3 (Förvaltning 2.1). Bygger på
`FORVALTNING_DESIGN_2-1.md` och definierar effekt-vokabulär, attribut-schema och
frekvenser per lek. Scaffold-filer (en rad per kort, mekanik ifylld, text att
författa) ligger i `data/forvaltning_2-1/`.*

---

## 1. Effekt-vokabulär

Alla korts egenskaper är effekter ur en gemensam lista. Koderna nedan används i
`Effekt`-kolumnen i CSV:erna och blir kontraktet mot den kommande motorn.

### A. Fastighetseffekter (hamnar på en fastighet)
| Kod | Synlig | Verkan |
|---|---|---|
| `dolt_plus_dn` | nej | ackumulerar; 3 i netto → **+1 bas-DN** |
| `dolt_minus_dn` | nej | ackumulerar; 3 i netto → **−1 bas-DN** |
| `energi_plus` | nej | ackumulerar; 3 → **+1 energiklass** |
| `energi_minus` | nej | ackumulerar; 3 i netto → **−1 energiklass** (energi hanteras i tredjedelar precis som DN) |
| `direkt_dn_plus` | ja | **+1 bas-DN direkt** & permanent (sällsynt) |
| `direkt_dn_minus` | ja | **−1 bas-DN direkt** & permanent (sällsynt) |
| `underhallsvarning` | ja | betala `Värde` Mkr i marknaden för att röja; 3 oåtgärdade → −1 DN **+ uppgraderingsstopp** tills röjt |
| `villkorskort` | ja | effekt beror på tillstånd (t.ex. ”om EK ≤ D → −1 DN”, ”äger du 3+ av typen → −1 DN på alla”) |
| `engangskassa_plus` / `engangskassa_minus` | ja | vid nästa marknad: ± `Värde` Mkr (engångs) |
| `forkop` | — | går till **handen**; ger förstaval vid köp av matchande typ |
| `utveckling` | ja | lägg en **utvecklingsbricka** på din FC om fastigheten har FC:s typ, annars på din FS (se §5) |
| `riskbuffert` | ja | ta en riskbuffert (se designdokumentet §9) |

Plus/minus är **dolda och tysta**; varning är **synlig och åtgärdbar**;
energi plus/minus är dolda brickor som DN — se visningsregeln i §6.

### B. Handeffekter (personkort)
| Kod | Timing | Verkan |
|---|---|---|
| `forhandling_mod` | före slag | +1/+2/+3 på förhandlingsslag (`Värde`) |
| `forhandling_auto` | före slag | vinner förhandlingen automatiskt |
| `energi_mod` | efter slag | +1/+2/+3 på energiuppgraderingsslag (`Värde`) |
| `lagg_dn_plus_egen` | när som helst | lägg en dold +1 DN-bricka på **egen** fastighet |
| `lagg_energi_plus_egen` | när som helst | lägg en dold energiplusbricka på **egen** fastighet |
| `direkt_dn_plus_egen` | när som helst | **+1 bas-DN direkt** och permanent på egen fastighet (sällsynt joker) |
| `stada` | när som helst | ta bort ett minus- eller varningskort från egen fastighet |
| `stopp` | reaktivt | avvärj ett tvångsbud |
| `kika` | när som helst | titta på ett dolt kort hos en motståndare |
| `hyresgastvarvning` | när som helst | kräver egen fastighet av samma typ som motspelarens: **+1 dold plusbricka på din, +1 dold minusbricka på motspelarens** (konkurrens om hyresgäster — lagligt, inte sabotage) |
| `headhunting` | när som helst | ta ett **slumpvis personkort** från en motspelares hand |
| `utveckling` | när som helst | lägg en utvecklingsbricka på din FC eller FS |
| `dra_personkort` | när som helst | dra ett personkort |
| `riskbuffert` | när som helst | ta en riskbuffert |

### C. Däckeffekter (omvärld/kvartal)
| Kod | Var | Verkan |
|---|---|---|
| `yield_ersatt` | omvärld | **Gäller nu:** lägg omvärldskortet på nästa plats på `Påverkar`-spåret i yieldbanan; dess `Värde` (± pp) gäller i stället för yieldkortet där |
| `yield_byt` | omvärld | **Byt ut:** ersätt nästa yieldkort på `Påverkar`-spåret (eller båda) med översta kortet ur yieldleken |
| `bords_dn` | omvärld | ±1 DN på alla fastigheter av en typ |
| `resurs` | båda | riskbuffert till alla / dra personkort |
| `personalrotation` | omvärld | alla drar ett slumpvis personkort från spelaren till vänster |
| `yield_byt_alla` | omvärld | byt ut **alla kvarvarande** yieldkort på `Påverkar`-spåret mot nya ur yieldleken |
| `energistod` | omvärld | varje spelare höjer energiklassen ett steg på en valfri egen fastighet |
| `slang_personkort` | omvärld | varje spelare slänger ett valfritt personkort |
| `inget` | kvartal | inget händer |
| `kvartal_dd` | kvartal | alla med fokustypen drar ett DD-kort dolt på en av sina fastigheter av typen |
| `kvartal_kassa_minus` | kvartal | varje ägare av fokustypen betalar `Värde` Mkr **vid nästa marknad** (plånboken stängd) |
| `typbred_dn_plus` / `typbred_dn_minus` | kvartal | ±1 DN på **allas** fastigheter av fokustypen |
| `typbred_ek_plus` / `typbred_ek_minus` | kvartal | ±1 energiklass på allas fastigheter av fokustypen |
| `spotlight` | kvartal | alla drar ett extra händelsekort för fokustypen |
| `villkorat` | kvartal | typbrett villkorskort |

---

## 2. Lekar, attribut och frekvens

### Händelsekort — `F2-1_händelsekort.csv` (106)
Fyra typleker (Hyresrätt, Förskola, Lokal, Kontor). **Återanvändbar lek:** dra, lös
(lägg bricka / applicera), lägg tillbaka. Förköp går till handen.
Kolumner: `ID;Typ;Effekt;Synlig;Värde;Rubrik;Beskrivning`

| Effekt | Hyresrätt | Förskola | Lokal | Kontor |
|---|---|---|---|---|
| dolt_plus_dn | 6 | 6 | 5 | 4 |
| dolt_minus_dn | 3 | 3 | 6 | 6 |
| energi_plus | 2 | 2 | 1 | 1 |
| energi_minus | 1 | 1 | 2 | 2 |
| direkt_dn_plus | 1 | 1 | 1 | 1 |
| direkt_dn_minus | – | – | 1 | 2 |
| underhallsvarning | 3 | 3 | 2 | 2 |
| villkorskort | 2 | 2 | 2 | 3 |
| engangskassa_plus / minus | 2/1 | 3/– | 2/2 | 1/2 |
| forkop | 2 | 2 | 2 | 2 |
| utveckling | 1 | 1 | 1 | 1 |
| riskbuffert | 1 | 1 | 1 | 1 |
| **Summa** | **25** | **25** | **28** | **28** |

Karaktär: stabila typer plus-lean utan direkta minus (men enstaka windfall + fler
underhållsvarningar); volatila typer minus-övervikt med båda direktchockerna, mer
energiminus och villkor.

### Kvartalskort — `F2-1_kvartalskort.csv` (46)
Fyra typleker. Varje kvartal är en **fokustyp** aktiv; dess kvartalskort träffar allas
fastigheter av typen. Kolumner: `ID;Typ;Effekt;Värde;Rubrik;Beskrivning`
Förskola, Lokal, Kontor (12 st var): typbred_dn_plus 1, typbred_dn_minus 2, typbred_ek_plus 1,
typbred_ek_minus 1, spotlight 2, resurs 1, villkorat 1, inget 1, kvartal_dd 1, kvartal_kassa_minus 1
(2 Mkr förskola, 5 Mkr lokal/kontor).
**Hyresrätt (10 st) drabbas aldrig av typbrett minus** — i stället inget 2, kvartal_dd 1; plus
typbred_dn_plus 1, typbred_ek_plus 1, spotlight 2, resurs 1, villkorat 1, kvartal_kassa_minus 1 (2 Mkr).

### Personkort — `F2-1_personkort.csv` (73)
En förbrukningslek, blandas om. Kolumner: `ID;Effekt;Timing;Värde;Rubrik;Beskrivning`
forhandling_mod 10, forhandling_auto 3, energi_mod 10, lagg_dn_plus_egen 8, stada 6,
stopp 5, kika 4, hyresgastvarvning 6, headhunting 3, dra_personkort 5, riskbuffert 4, utveckling 3,
lagg_energi_plus_egen 5, direkt_dn_plus_egen 1.

### Omvärldskort — `F2-1_omvärldskort.csv` (31)
Kolumner: `ID;Effekt;Värde;Påverkar;Rubrik;Beskrivning`
yield_ersatt 15 (alla ±0,5 pp), yield_byt 4, yield_byt_alla 2, bords_dn 3, resurs 3, personalrotation 1,
energistod 1, slang_personkort 2.

### Yieldkort — `F2-1_yieldkort.csv` (24)
Två lekar, 16 per spår (bostäder, kommersiellt). Innehållet är det **tryckta yieldkortet från
version 1** (`F_yield`) utom de åtta korten med ±1,0 — **bara ±0,5-steg** (beslut 2026-09-26).
De tryckta korten kan återanvändas; ±1,0-korten plockas bort.
Kolumner: `ID;Spår;Ändring;Rubrik`. Fördelning bostäder: −0,5 ×5, 0 ×2, +0,5 ×5;
kommersiellt: −0,5 ×6, 0 ×2, +0,5 ×4 (lutar mot sjunkande yield = stigande MV — kontrolleras av bottarna).

**Yieldbanan** har fyra platser per spår: **Q2, Q3, Q4, Slut**. Vid uppställningen läggs fyra yieldkort
öppet per spår. Q1:s marknad sker på startyield (bostäder 4 %, kommersiellt 5 %). Vid varje följande
marknad (och vid slutavräkningen) flyttas yieldpekaren med kortet på den platsen, inom spannet
(bostäder 2–6 %, kommersiellt 3–7 %). Omvärldskortet som dras i kvartal *n* påverkar plats *n+1*.

### DD — `F2-1_DD.csv` (36)
Dolt vid övergång + köp; räknas i samma ackumulering som händelsekort; avslöjas vid
försäljning/tvångstagande. Kolumner: `ID;Effekt;Rubrik;Beskrivning`
dd_plus (Intäkt) 16, dd_minus (Kostnad) 18, dd_ek 2.

### FC / FS-arketyper — `F2-1_FC.csv` (6), `F2-1_FS.csv` (6)
Omgjorda 2026-09-26, se §5. FC har **typ** och lutar mot marknad/slag; FS lutar mot fastighetsnivå.
Alla kort är **dubbelsidiga: junior / senior**.

## 3. Komponentöversikt (nya/uppdaterade kort)

| Lek | Antal |
|---|---|
| Händelsekort (4 typleker) | 106 |
| Kvartalskort (4 typleker) | 46 |
| Personkort | 73 |
| Omvärldskort | 31 |
| Yieldkort (återanvänds från version 1, utan ±1,0) | 24 |
| DD | 36 |
| Fastighetskort (uppdaterad baksida: tryckt lån) | 45 |
| FC + FS-arketyper (dubbelsidiga) | 12 |
| **Summa** | **~351** |

Brickor: utvecklingsbrickor, DN-siffror, energiclips A–E, +/− - och energibrickor, riskbuffert, restkort,
lån-clips (ex-bank).

---

## 4. Att författa (fas 3)

- **Rubrik + Beskrivning** är tomma i scaffolden — texten skrivs per kort (svenska,
  byggbransch; `korttextforfattare`). Där en befintlig framsida finns återanvänds namnet;
  nya slots får ny framsida + text.
- **Värde-fält** sätts vid författning: engångskassa (Mkr), underhållsvarningens
  röjkostnad, yield-rörelsernas pp.
- **`kort-balansör`** körs som kontroll när texten är på plats — verifierar att
  fördelningarna stämmer och flaggar outliers.
- **Fastighetskortens baksida:** tryck lån (70 % av entry-MV, avrundat 10). Räntekolumn
  utgår (inbakad i DN).

---

## 5. FC och FS — typ och utveckling

- **FC har en typ:** HYRESRÄTT, FÖRSKOLA, LOKAL, KONTOR, eller en bred typ — BOSTÄDER (hyresrätt +
  förskola) eller KOMMERSIELLT (lokal + kontor), samma uppdelning som yieldspåren. Specialisten är stark
  på sin typ; den breda svagare men på två.
- **Dubbelsidiga kort.** Alla börjar som **junior**. Med **två utvecklingsbrickor** vänds kortet till
  **senior**: starkare version plus en ny egenskap (se filerna). Brickorna tas bort.
- **Utvecklingsbrickor** kommer från händelsekort (`utveckling`, 1 per typlek) och personkort
  (`utveckling`, 3 st). Från ett händelsekort går brickan till **FC om fastigheten har FC:s typ**,
  annars till FS — FC växer alltså med den portfölj den passar.
- **FC-3 Skölden** blockerar händelsekort (inte konsekvenskort, som bara förekommer i Kvartal 0).

---

## 6. Dolda brickor och visning (DN och energi)

DN och energi hanteras **på samma sätt, i tredjedelar**: plus- och minusbrickor läggs dolt på fastigheten
när de dras eller spelas. Vid **netto 3** åt något håll ändras bas-DN respektive energiklass permanent och
brickorna kasseras.

**Visningsregel:**
- **Netto −3 visas direkt** — tvingande (beslut 2026-09-26).
- **Netto +3:** *öppet — testas med bottarna.* Antingen tvingande visning även här (enklast), eller
  valfri tidpunkt (plus hjälper först när det visas, men ett minus kan hinna sänka nettot till +2).

---

*Denna spec fryser innehållsritningen. Scaffold-CSV:erna i `data/forvaltning_2-1/` är
skelettet; nästa steg är att fylla i texten lek för lek.*
