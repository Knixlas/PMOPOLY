# Framtida uppgraderingar — efter konferensen

Saker som identifierats men medvetet skjutits framåt. Inte blockerande för konferens fre 2026-05-?? — kan komma senare när huvudfokus skiftat.

---

## Spel-mekanik

### C9. Sekundärmarknad — full budgivning + bank-tillbakaköp

**Status:** Förenklad i full-game mode. I companion-mode räknar GM:n manuellt så det är inte kritiskt.

**Vad som saknas (regelboken §8.6):**
1. **Budgivning** — köparen lägger ett bud mellan 80 % och valfri övre nivå av marknadsvärdet, säljaren kan acceptera eller avvisa.
2. **Bank tillbakaköp** — säljaren kan alltid garanteras kunna sälja för 80 % av MV (banken som backstop).

**Koden idag** ([`engine.py:3504`](backend/engine.py:3504)): fast pris = MV, köparen betalar 30 % av MV, säljaren får 30 % av MV. Ingen flexibilitet.

**Påverkan:** Tar bort en strategisk dimension (förhandling). Medveten förenkling för spelflödets skull.

**Implementeringsförslag (när det är dags):**
- Nytt action: `f4_market_bid` med `bid_pct` (0.80–1.20)
- Säljaren får `accept` / `reject` / `bank_sell` (banken garanterar 80 %)
- DD-kort dras fortfarande vid varje genomfört köp

---

## Arkitektur

### A1 (resten). Fullständig refaktor `phase1-4` → `skede1-3`

**Status:** Bara UI-text bytt (Paket 3). Interna identifierare kvar.

**Vad som saknas:** Database/state-migrering, event-namn, save/load, alla `phase1_*`-strängar i backend och routing.

**Påverkan:** Stor refaktor — många filer rörs samtidigt. Hög risk om vi gör det innan konferensen.

**När:** Efter konferensen, om/när vi har tid och saknar konkret nytta. UI:n är redan korrekt så detta är mest "städning".

---

## Companion-funktioner

### Visa CEO/CFO/COO + PC i GM-dashboard

**Status:** Synligt i player-vyn, inte i GM-dashboard.

**Bekräftat med dig:** "Vald ledning och PC behöver inte visas i dashboard - det är ganska irrelevant för spelet" — men "när vi fått till att alla ändringar är inne kommer jag återkomma om vad jag vill ska visas var".

**När:** Efter konferensen.

---

## Regelbok-uppdateringar att göra

Saker där koden är källa-sanning men regelboken/SSOT inte matchar:

### E3. Yield-mekanik — tydliggör att Q1 är startvärde
**Status:** Bekräftat med dig att Q1 = startvärdet (4 % bostäder, 5 % kommersiellt). Yieldkort dras i slutet av Q1, Q2, Q3 för att sätta nästa kvartals värde.
**Att göra:** Lägg till en mening i regelboken §8.5 eller §8.11.

### E2. EK-faktor 0.10/2.00 i slutformeln
**Status:** Bekräftat med dig att asymmetrin (0.10 vid positiv EK, 2.00 vid negativ) är medveten — förhindrar "sälj-allt-för-stor-kassa"-strategin och straffar moderbolagslån hårt.
**Att göra:** Uppdatera regelboken §9.1 + Excel SSOT med rätt formel:
- `Råpoäng = (FV × 30 % × Energibonus + EK_factor × Eget kapital + TB) ÷ (BTA / 1000)`
- `EK_factor = 0.10 om EK ≥ 0, annars 2.00`

---

## Utforskningar

Saker värda att tänka på, inte nödvändigt att implementera:

- **F-klass i energi:** Borttagen helt nu. Om man vill ha "mycket dålig" som finare gradering än E=0, kan man lägga till tillbaka.
- **Plandokument:** Spelordning.docx är inaktuell — Excel SSOT är källa. Bör tas bort eller markeras "DEPRECATED".
- **Quiz-system:** Implementerat men inte i regelboken. Eventuellt dokumentera som "valfritt tillägg under middag".
