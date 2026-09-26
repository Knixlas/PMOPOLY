"""
uppdatera_färger.py – v5
Läser färgschema.xlsx (Färger + CSV-mappning + Skede-mappning) och skriver
fill_color / line_color / skede_color till alla CSV:er.

FÄRGKONVENTION:
  fill_color  = TEXT        — mörk variant av kategori-färg
  line_color  = KATEGORI    — ljus identitetsfärg (matchar bilder.xlsx)
  skede_color = FAS-MARKÖR  — färg som identifierar Fas 1-4 (PU/PL/GF/F)

Placering: SPELET 2\\
Kör: python uppdatera_färger.py
"""

import os, csv, json, shutil, tempfile, sys

try:
    import openpyxl
except ImportError:
    print("Saknas: pip install openpyxl")
    sys.exit(1)

# Skriptet ligger i SPELET 2\Bilder\ — config-filer ligger här,
# men CSV:erna ligger en nivå upp i SPELET 2\{1,2,3,4}. <fasmapp>\
BILDER_ROT    = os.path.dirname(os.path.abspath(__file__))
SPELET_ROT    = os.path.dirname(BILDER_ROT)
FARG_XLSX     = os.path.join(BILDER_ROT, "färgschema.xlsx")
TYPSNITT_JSON = os.path.join(BILDER_ROT, "typsnitt_config.json")
UTSKRIFT_JSON = os.path.join(BILDER_ROT, "utskrift_config.json")
SKEDE_JSON    = os.path.join(BILDER_ROT, "skede_config.json")

MAPPAR = {
    "PU_": os.path.join(SPELET_ROT, "1. Projektutveckling"),
    "PL_": os.path.join(SPELET_ROT, "2. Planering"),
    "GF_": os.path.join(SPELET_ROT, "3. Genomförande"),
    "F_":  os.path.join(SPELET_ROT, "4. Förvaltning"),
}

# ═══════════════════════════════════════════════════════════════════════
#  Textsidans bakgrund — gemensam för alla kort utom listan nedan
# ═══════════════════════════════════════════════════════════════════════
# bakgrund_color skrivs lika i alla CSV:er utom de som listas här.
# De undantagna filerna behåller den fas-/kategori-baserade bakgrundsfärgen
# som beräknas via paletten (10%-tint av kategorifärgen).
TEXTSIDA_BAKGRUND = "#FCF6EF"
BAKGRUND_EXKLUDERADE = {
    "PU_projekt",       # projektkort har egen typ-baserad bakgrund per fastighet
    "PU_BTA",           # BTA-klassningskort
    "PU_BYA",           # BYA-klassningskort
    "F_moderbolagslån", # moderbolagslån har särskild visuell behandling
}


# ═══════════════════════════════════════════════════════════════════════
#  Läs färgschema.xlsx
# ═══════════════════════════════════════════════════════════════════════

import re
_HEX_MONSTER = re.compile(r"^#[0-9A-Fa-f]{6}$")

def ar_giltig_hex(s):
    """Returnerar True om strängen är ett giltigt hex-värde (#RRGGBB)."""
    return bool(s and _HEX_MONSTER.match(s.strip()))


def berakna_tint(hex_str, tint, papper=(255, 255, 255)):
    """Beräkna hex som motsvarar att lägga hex_str vid tint-opacitet
    på angivet pappersfärg. Returnerar t.ex. #F3EFE9 för 10% #7A2020 på vitt."""
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    pR, pG, pB = papper
    nR = round((1 - tint) * pR + tint * r)
    nG = round((1 - tint) * pG + tint * g)
    nB = round((1 - tint) * pB + tint * b)
    return f"#{nR:02X}{nG:02X}{nB:02X}"


def hitta_kolumn_index(header_row, *namnvarianter):
    """Sök efter kolumn vars header matchar någon av namnvarianterna (case-insensitive, whitespace strippad)."""
    if not header_row:
        return -1
    for i, cell in enumerate(header_row):
        if cell is None:
            continue
        cell_str = str(cell).strip().lower()
        for variant in namnvarianter:
            if cell_str == variant.lower():
                return i
    return -1


def las_fargschema(path):
    """Returns (palett, csv_mappning, skede_mappning, typsnitt, utskrift)."""
    # Copy to temp (OneDrive lock workaround)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy2(path, tmp.name)
    wb = openpyxl.load_workbook(tmp.name, data_only=True)
    os.unlink(tmp.name)

    # ── Färger ─────────────────────────────────────────────────────────
    # Sheet-kolumner: Kategori | Färgnamn | Hex | Mörk variant | Hex (mörk)
    #                 [| ... | Hex (bakgrund) | ...]
    # Bakgrund-hex är VALFRI — om kolumnen "Hex (bakgrund)" saknas eller är
    # tom/ogiltig beräknas värdet automatiskt som 10%-tint av ljus-hex
    # på vitt papper (matchar farglagg-overlay).
    palett = {}  # namn -> (hex_ljus, hex_mork, hex_bakgrund)
    if "Färger" in wb.sheetnames:
        sheet = wb["Färger"]
        # Leta efter bakgrund-kolumnen via rubrik (tolerant mot ordning)
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        bg_col = hitta_kolumn_index(
            header_row,
            "Hex (bakgrund)",
            "Hex bakgrund",
            "Bakgrund hex",
            "Hex (bg)"
        )

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or not row[1] or not row[2]:
                continue
            namn = str(row[1]).strip()
            hex_ljus = str(row[2]).strip()
            # Normalisera hex som saknar #-prefix (t.ex. "8d519b" → "#8D519B")
            if hex_ljus and not hex_ljus.startswith("#"):
                if re.fullmatch(r"[0-9A-Fa-f]{6}", hex_ljus):
                    hex_ljus = "#" + hex_ljus
            # Hoppa över rader utan giltig hex (t.ex. dupliceringar av CSV-mappning,
            # rubrikrader eller färger som inte skrivits klart)
            if not ar_giltig_hex(hex_ljus):
                continue
            hex_mork = str(row[4]).strip() if len(row) > 4 and row[4] else ""
            if hex_mork and not ar_giltig_hex(hex_mork):
                hex_mork = ""
            hex_bakgrund = ""
            if bg_col >= 0 and bg_col < len(row) and row[bg_col]:
                kandidat = str(row[bg_col]).strip()
                if ar_giltig_hex(kandidat):
                    hex_bakgrund = kandidat
            if not hex_mork:
                hex_mork = hex_ljus  # fallback
            if not hex_bakgrund:
                hex_bakgrund = berakna_tint(hex_ljus, 0.10)  # 10% på vitt
            palett[namn] = (hex_ljus, hex_mork, hex_bakgrund)
    else:
        print("  VARNING: Bladet 'Färger' saknas!")

    # ── CSV-mappning ───────────────────────────────────────────────────
    # Sheet: Fil-pattern | Typ-värde | Färgnamn | Bakskede (front) | Fill (text) |
    #        Bakgrund (textsida) | Namn | Kommentar
    # De tre hex-kolumnerna är VALFRIA — om de saknas eller är tomma fallback
    # till uppslagning via Färgnamn i palett. Om de finns skriver de över
    # palettens värden för just den raden (per fil + typ).
    csv_map = []  # list of (pattern, typ, fargnamn, override_dict)
    if "CSV-mappning" in wb.sheetnames:
        sh = wb["CSV-mappning"]
        header_row = next(sh.iter_rows(min_row=1, max_row=1, values_only=True), None)
        bsk_col = hitta_kolumn_index(header_row, "Bakskede (front)", "Bakskede front", "Bakskede")
        fill_col = hitta_kolumn_index(header_row, "Fill (text)", "Fill text", "Fill")
        bg_col2 = hitta_kolumn_index(header_row, "Bakgrund (textsida)", "Bakgrund textsida", "Bakgrund")
        for row in sh.iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not row[2]:
                continue
            pattern = str(row[0]).strip()
            typ = str(row[1]).strip() if row[1] else "*"
            fargnamn = str(row[2]).strip()
            override = {}
            for key, idx in (("bakskede", bsk_col), ("fill", fill_col), ("bakgrund", bg_col2)):
                if idx >= 0 and idx < len(row) and row[idx]:
                    kand = str(row[idx]).strip()
                    if ar_giltig_hex(kand):
                        override[key] = kand
            csv_map.append((pattern, typ, fargnamn, override))
    else:
        print("  VARNING: Bladet 'CSV-mappning' saknas!")

    # ── Skede-mappning ─────────────────────────────────────────────────
    # Sheet: Skede | CSV-prefix | Färgnamn | Bakskede hex (valfri) | Kommentar
    # Bakskede-hex är VALFRI — om kolumnen saknas eller är tom beräknas
    # värdet automatiskt som 15%-tint av skedesfärgen på vitt papper.
    skede_map = {}          # prefix -> fargnamn
    skede_bakskede = {}     # prefix -> bakskede_hex (eller "" för auto)
    if "Skede-mappning" in wb.sheetnames:
        sh = wb["Skede-mappning"]
        header_row = next(sh.iter_rows(min_row=1, max_row=1, values_only=True), None)
        bs_col = hitta_kolumn_index(
            header_row,
            "Bakskede hex",
            "Bakskede-hex",
            "Bakskede",
            "Hex (bakskede)"
        )
        for row in sh.iter_rows(min_row=2, values_only=True):
            if not row or not row[1] or not row[2]:
                continue
            prefix = str(row[1]).strip()
            fargnamn = str(row[2]).strip()
            skede_map[prefix] = fargnamn
            bs_hex = ""
            if bs_col >= 0 and bs_col < len(row) and row[bs_col]:
                kandidat = str(row[bs_col]).strip()
                if ar_giltig_hex(kandidat):
                    bs_hex = kandidat
            skede_bakskede[prefix] = bs_hex
    else:
        print("  VARNING: Bladet 'Skede-mappning' saknas!")

    # ── Typsnitt ───────────────────────────────────────────────────────
    typsnitt = {
        "rubrik_font": "Minion Pro", "rubrik_style": "Bold",
        "brodtext_font": "Minion Pro", "brodtext_style": "Regular",
        "storlek_troskel": 14,
    }
    if "Typsnitt" in wb.sheetnames:
        for row in wb["Typsnitt"].iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            roll = str(row[0]).strip().lower()
            font = str(row[1]).strip() if row[1] else ""
            stil = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            if "rubrik" in roll and font:
                typsnitt["rubrik_font"] = font
                typsnitt["rubrik_style"] = stil
            elif ("bröd" in roll or "brod" in roll) and font:
                typsnitt["brodtext_font"] = font
                typsnitt["brodtext_style"] = stil
            if ("tröskel" in roll or "troskel" in roll):
                try:
                    size = row[3] if len(row) > 3 else None
                    if size:
                        typsnitt["storlek_troskel"] = float(size)
                except (ValueError, TypeError):
                    pass

    # ── Utskrift ───────────────────────────────────────────────────────
    utskrift = {}
    if "Utskrift" in wb.sheetnames:
        for row in wb["Utskrift"].iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            pdfnamn = str(row[1]).strip().replace(".pdf", "")
            exemplar = int(row[2]) if len(row) > 2 and row[2] and str(row[2]).strip().isdigit() else 1
            utskrift[pdfnamn] = exemplar

    return palett, csv_map, skede_map, typsnitt, utskrift, skede_bakskede


def skriv_json(data, path, etikett):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {etikett}")


# ═══════════════════════════════════════════════════════════════════════
#  Färgval per rad
# ═══════════════════════════════════════════════════════════════════════

def bestam_kategori_farg(filnamn, rad, csv_map, palett):
    """Returnerar (fill_color, line_color, bakgrund_color, override_bakskede)
    baserat på (fil, typ)-mappning.

    Om CSV-mappning har explicita hex-värden i kolumnerna 'Bakskede (front)',
    'Fill (text)' eller 'Bakgrund (textsida)' används dessa istället för
    palettens uppslag. override_bakskede returneras separat för att
    bestam_skede_farg ska kunna prioritera typ-specifik bakskede.
    """
    fn_low = filnamn.lower()
    typ = ""
    for k in ("Typ", "typ", "TYP", "Type"):
        if k in rad and rad[k]:
            typ = str(rad[k]).strip()
            break

    # Hitta första matchande mappning
    best_match = None  # (score, fargnamn, override)
    for entry in csv_map:
        # Stöd både 3-tupel (gamla) och 4-tupel (nya med override)
        if len(entry) == 4:
            pattern, typ_val, fargnamn, override = entry
        else:
            pattern, typ_val, fargnamn = entry
            override = {}
        if pattern.lower() not in fn_low:
            continue
        if typ_val == "*" or typ_val.lower() == typ.lower():
            score = len(pattern) * 10 + (5 if typ_val != "*" else 0)
            if best_match is None or score > best_match[0]:
                best_match = (score, fargnamn, override)

    if best_match is None:
        fargnamn = "Åke Sundvall Mörkgrå"
        override = {}
    else:
        fargnamn = best_match[1]
        override = best_match[2]

    if fargnamn not in palett:
        # Om override har alla tre värden (fill, bakskede, bakgrund) räcker det
        # — palett behövs då inte. Annars varna och fall tillbaka till Mörkgrå.
        if not (override.get("fill") and override.get("bakskede") and override.get("bakgrund")):
            print(f"    VARNING: Färg '{fargnamn}' saknas i paletten — använder Mörkgrå")
            fargnamn = "Åke Sundvall Mörkgrå"

    default = ("#605951", "#605951", berakna_tint("#605951", 0.10))
    hex_ljus, hex_mork, hex_bakgrund = palett.get(fargnamn, default)

    # Override per CSV-mappning (om explicita hex finns)
    fill_color = override.get("fill", hex_mork)         # mörk text
    line_color = override.get("bakskede", hex_ljus)     # ljus accent (line = bakskede)
    bakgrund_color = override.get("bakgrund", hex_bakgrund)
    override_bakskede = override.get("bakskede", "")    # för typ-specifik bakskede

    return fill_color, line_color, bakgrund_color, override_bakskede


def bestam_skede_farg(filnamn, skede_map, palett, skede_bakskede=None):
    """Returnerar (skede_hex, bakskede_hex) för filens skede.

    skede_hex   = ljus variant av skedesfärgen (för accent/kontur)
    bakskede_hex = ljus tint av skedesfärgen (för bakgrund på framsida)
                   Om explicit värde finns i Skede-mappning används det,
                   annars beräknas 15%-tint på vitt automatiskt.
    """
    bn = os.path.basename(filnamn).lower()
    for prefix in sorted(skede_map.keys(), key=len, reverse=True):
        if bn.startswith(prefix.lower()):
            fargnamn = skede_map[prefix]
            if fargnamn in palett:
                skede_hex = palett[fargnamn][0]  # ljus variant
                # Bakskede: explicit från Excel, annars beräkna 15%-tint
                bakskede_hex = ""
                if skede_bakskede:
                    bakskede_hex = skede_bakskede.get(prefix, "")
                if not bakskede_hex:
                    bakskede_hex = berakna_tint(skede_hex, 0.15)
                return skede_hex, bakskede_hex
    return "#605951", berakna_tint("#605951", 0.15)  # fallback


# ═══════════════════════════════════════════════════════════════════════
#  Encoding-detektering (CSV-filerna varierar)
# ═══════════════════════════════════════════════════════════════════════

def detektera_encoding(path):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


# ═══════════════════════════════════════════════════════════════════════
#  Uppdatera en CSV-fil
# ═══════════════════════════════════════════════════════════════════════

def uppdatera_csv(csvpath, palett, csv_map, skede_map, skede_bakskede=None):
    enc = detektera_encoding(csvpath)
    raw = open(csvpath, "rb").read()
    if not raw.strip():
        return False

    text = raw.decode(enc, errors="replace")
    lines = text.splitlines()
    if not lines:
        return False
    sep = ";" if lines[0].count(";") >= lines[0].count(",") else ","

    reader = csv.DictReader(lines, delimiter=sep)
    headers = list(reader.fieldnames or [])
    rows = list(reader)
    if not rows:
        return False

    changed = False
    for col in ("fill_color", "line_color", "skede_color", "bakgrund_color", "bakskede"):
        if col not in headers:
            headers.append(col)
            changed = True

    filnamn = os.path.basename(csvpath)
    skede_hex, fas_bakskede_hex = bestam_skede_farg(filnamn, skede_map, palett, skede_bakskede)

    # Avgör om denna fil ska få den gemensamma textsidesbakgrunden eller
    # behålla sin fas-/kategori-baserade bakgrundsfärg.
    fil_stam = os.path.splitext(filnamn)[0]
    anvand_gemensam_bakgrund = fil_stam not in BAKGRUND_EXKLUDERADE

    uppdaterade = 0
    for rad in rows:
        fill, line, kategori_bakgrund, override_bakskede = bestam_kategori_farg(
            filnamn, rad, csv_map, palett
        )
        bakgrund = TEXTSIDA_BAKGRUND if anvand_gemensam_bakgrund else kategori_bakgrund
        # Typ-specifik bakskede har företräde över fas-bakskede (för t.ex. PU_projekt)
        bakskede_hex = override_bakskede if override_bakskede else fas_bakskede_hex
        if (rad.get("fill_color") != fill
            or rad.get("line_color") != line
            or rad.get("skede_color") != skede_hex
            or rad.get("bakgrund_color") != bakgrund
            or rad.get("bakskede") != bakskede_hex):
            rad["fill_color"] = fill
            rad["line_color"] = line
            rad["skede_color"] = skede_hex
            rad["bakgrund_color"] = bakgrund
            rad["bakskede"] = bakskede_hex
            uppdaterade += 1
            changed = True

    if not changed:
        return False

    # Skriv alltid som CP1252 (funkar i både Excel och InDesign Data Merge)
    with open(csvpath, "w", encoding="cp1252", errors="replace", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, delimiter=sep, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    if os.path.getsize(csvpath) < 20:
        print(f"    VARNING: {filnamn} verkar tom!")
        return False
    return uppdaterade


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    if not os.path.exists(FARG_XLSX):
        print(f"Hittar inte: {FARG_XLSX}")
        return

    print("Läser färgschema.xlsx...")
    palett, csv_map, skede_map, typsnitt, utskrift, skede_bakskede = las_fargschema(FARG_XLSX)
    print(f"  {len(palett)} färger i paletten")
    print(f"  {len(csv_map)} CSV-mappningsregler")
    print(f"  {len(skede_map)} skede-mappningar")
    skriv_json(typsnitt, TYPSNITT_JSON, "typsnitt_config.json")
    skriv_json(utskrift, UTSKRIFT_JSON, f"utskrift_config.json ({len(utskrift)} filer)")

    # Skede-config: filprefix -> hex, för InDesign-jsx att läsa
    skede_config = {}
    for prefix, fargnamn in skede_map.items():
        if fargnamn in palett:
            skede_config[prefix] = palett[fargnamn][0]  # ljus variant
    skriv_json(skede_config, SKEDE_JSON, f"skede_config.json ({len(skede_config)} skeden)")
    print()

    totalt_filer = 0
    totalt_rader = 0
    for prefix, mapp in MAPPAR.items():
        if not os.path.isdir(mapp):
            print(f"  Mapp saknas: {mapp}")
            continue
        print(f"[{prefix}] {os.path.basename(mapp)}")
        for f in sorted(os.listdir(mapp)):
            if not f.lower().endswith(".csv"):
                continue
            path = os.path.join(mapp, f)
            result = uppdatera_csv(path, palett, csv_map, skede_map, skede_bakskede)
            if result is False:
                print(f"    – {f} (oförändrad)")
            else:
                print(f"    [OK] {f} ({result} rader)")
                totalt_filer += 1
                totalt_rader += result

    print(f"\nKlart! {totalt_filer} CSV-filer uppdaterade ({totalt_rader} rader totalt).")


if __name__ == "__main__":
    main()

