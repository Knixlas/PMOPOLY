"""
excel_till_config.py
Läser SPELET 2\\Bilder\\färgschema.xlsx (fliken 'Utskrift') och skriver
en färsk utskrift_config.json i SPELET 2\\-roten.

Normaliserar nycklar så de matchar de faktiska PDF-filerna som JSX-skriptet
producerar (t.ex. PU_BYA_BTA_klass → PU_BTABYA_bildsida + PU_BTABYA_textsida).

Excel-kolumner som förväntas:
  A: Mapp          (t.ex. "1. Projektutveckling")
  B: PDF-filnamn   (t.ex. "PU_Projekt_bildsida.pdf")
  C: Exemplar      (heltal)
  D: Kommentar     (valfritt, ignoreras)

Anrop: python excel_till_config.py "C:\\...\\SPELET 2"
Kräver: pip install openpyxl
"""

import sys
import os
import json
import re
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    print("FEL: openpyxl saknas. Kör: pip install openpyxl")
    sys.exit(1)


# ── Alias-map för nycklar som inte matchar filnamnen direkt ─────────────
# Key = det som står i Excel (lowercase, utan .pdf), Value = verkligt basnamn
# Lagt till varje gång vi upptäcker en ny miss i Excel-arket.
ALIAS = {
    "pu_bya_bta_klass": "PU_BTABYA",
    "pu_poldia-speckort": "PU_poldia_spec",
    "pu_poldia": "PU_poldia",
    "pu_projekt": "PU_projekt",
    "pl_leverantörer": "PL_leverantörer",
    "pl_organisation": "PL_organisation",
    "pl_händelsekort": "PL_Händelsekort",
    "gf_garantibesiktning": "GF_garantibesiktning",
    "gf_faskort": "GF_faskort",
    "gf_konsekvenskort": "GF_Konsekvenskort",
    "gf_kultur": "GF_kultur",
    "f_dd": "F_DD",
    "f_händelsekort": "F_händelsekort",
    "f_kvartal": "F_kvartal",
    "f_kort_moderbolagslån": "F_moderbolagslån",
    "f_moderbolagslån": "F_moderbolagslån",
    "f_omvärldskort": "F_omvärldskort",
    "f_personal": "F_personal",
    "f_yield": "F_yield",
}


def las_mapp_filer(spelet2_rot: Path) -> set:
    """Samla alla faktiska .indd-basnamn från alla fasmappar."""
    mappar = [
        "1. Projektutveckling",
        "2. Planering",
        "3. Genomförande",
        "4. Förvaltning",
    ]
    basnamn = set()
    for mapp in mappar:
        p = spelet2_rot / mapp
        if not p.is_dir():
            continue
        for f in p.glob("*.indd"):
            basnamn.add(f.stem)  # utan .indd
    return basnamn


def normalisera_nyckel(raw: str, faktiska_basnamn: set) -> list:
    """
    Från en rad i Excel (t.ex. "PU_BYA_BTA_klass.pdf") → lista av riktiga
    basnamn som ska få samma värde i utskrift_config.json.

    - Strippa .pdf
    - Om namnet redan har _bildsida/_textsida → använd som-är
    - Annars expandera till BÅDE _bildsida och _textsida om de finns
    - Använd ALIAS-map för icke-matchande namn
    """
    namn = raw.strip()
    namn = re.sub(r"\.pdf$", "", namn, flags=re.IGNORECASE)

    # Redan explicit _bildsida eller _textsida?
    m = re.match(r"^(.+)_(bildsida|textsida)$", namn, re.IGNORECASE)
    if m:
        bas = m.group(1)
        sida = m.group(2).lower()
        # Hantera stavfel som "bildsida" → "bildsida" (ok) och alias på bas
        bas_alias = ALIAS.get(bas.lower(), bas)
        kandidat = f"{bas_alias}_{sida}"
        if kandidat in faktiska_basnamn:
            return [kandidat]
        # Testa exakt nyckelmatch case-insensitive
        for fn in faktiska_basnamn:
            if fn.lower() == kandidat.lower():
                return [fn]
        return []  # ingen träff

    # Inget suffix – expandera till bild+text
    bas = namn
    # Kolla alias
    bas_alias = ALIAS.get(bas.lower(), bas)

    resultat = []
    for sida in ("bildsida", "textsida"):
        kandidat = f"{bas_alias}_{sida}"
        if kandidat in faktiska_basnamn:
            resultat.append(kandidat)
        else:
            # Case-insensitive sökning
            for fn in faktiska_basnamn:
                if fn.lower() == kandidat.lower():
                    resultat.append(fn)
                    break
    return resultat


def konvertera(spelet2_rot: Path) -> None:
    xlsx_path = spelet2_rot / "Bilder" / "färgschema.xlsx"
    config_path = spelet2_rot / "utskrift_config.json"
    logg_path = spelet2_rot / "excel_till_config_logg.txt"

    logg = []

    def log(rad):
        logg.append(rad)
        print(rad)

    log(f"=== excel_till_config.py ===")
    log(f"Excel: {xlsx_path}")
    log(f"Output: {config_path}")

    if not xlsx_path.is_file():
        log(f"FEL: Excel-filen finns inte")
        sys.exit(1)

    # Samla alla faktiska indd-basnamn
    faktiska = las_mapp_filer(spelet2_rot)
    log(f"Hittade {len(faktiska)} indd-filer i fasmapparna")

    # Öppna Excel
    try:
        wb = load_workbook(xlsx_path, data_only=True)
    except Exception as e:
        log(f"FEL vid läsning av Excel: {e}")
        sys.exit(1)

    if "Utskrift" not in wb.sheetnames:
        log(f"FEL: Fliken 'Utskrift' finns inte. Flikar: {wb.sheetnames}")
        sys.exit(1)

    ws = wb["Utskrift"]

    config = {}
    omappade = []   # Excel-rader som inte matchar några indd-filer
    anvanda_indd = set()

    # Hoppa över rubrikraden (rad 1), läs tills vi hittar tom rad
    for rad_idx, rad in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not rad or rad[0] is None:
            continue
        mapp = rad[0]
        pdf_namn = rad[1]
        exemplar = rad[2]

        if not pdf_namn or exemplar is None:
            continue

        try:
            exemplar_int = int(exemplar)
        except (ValueError, TypeError):
            log(f"  VARNING rad {rad_idx}: kunde inte tolka exemplar='{exemplar}'")
            continue

        nycklar = normalisera_nyckel(str(pdf_namn), faktiska)

        if not nycklar:
            omappade.append(f"rad {rad_idx}: '{pdf_namn}' (x{exemplar_int})")
            continue

        for nyckel in nycklar:
            if nyckel in config and config[nyckel] != exemplar_int:
                log(f"  VARNING: '{nyckel}' finns redan med värde {config[nyckel]}, "
                    f"överskrivs med {exemplar_int} från rad {rad_idx}")
            config[nyckel] = exemplar_int
            anvanda_indd.add(nyckel)

    # Indd-filer som INTE hittades i Excel → varna, default 1
    saknas_i_excel = faktiska - anvanda_indd
    for basnamn in sorted(saknas_i_excel):
        log(f"  OBS: {basnamn}.indd saknas i Excel – sätter 1 ex")
        config[basnamn] = 1

    # Varna om rader i Excel som inte matchar någon fil
    if omappade:
        log(f"\n⚠️  {len(omappade)} Excel-rader matchar INGA indd-filer:")
        for rad in omappade:
            log(f"    {rad}")
        log(f"   Lägg till dessa namn i ALIAS-mappen i excel_till_config.py,")
        log(f"   eller rätta namnen i Excel.")

    # Skriv JSON
    # Sortera med samma fasordning som JSX:en använder
    fas_prio = {"PU": 1, "PL": 2, "GF": 3, "F_": 4}
    def fas_key(k):
        for pfx, prio in fas_prio.items():
            if k.startswith(pfx):
                return (prio, k)
        return (9, k)

    sorterad = dict(sorted(config.items(), key=lambda kv: fas_key(kv[0])))

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sorterad, f, ensure_ascii=False, indent=2)
        f.write("\n")

    log(f"\nSkrev {len(sorterad)} poster till {config_path.name}")

    # Sammanfattning av antal exemplar
    log(f"\nExemplar-fördelning:")
    antal_per_exemplar = {}
    for v in sorterad.values():
        antal_per_exemplar[v] = antal_per_exemplar.get(v, 0) + 1
    for ex in sorted(antal_per_exemplar.keys()):
        log(f"  {antal_per_exemplar[ex]} filer får {ex} ex")

    # Skriv logg
    with open(logg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(logg))


if __name__ == "__main__":
    rot = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    konvertera(rot)

