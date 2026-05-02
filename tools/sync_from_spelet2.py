#!/usr/bin/env python
"""Sync CSV-data och bilder från SPELET 2 (källa-sanning) till PMOPOLY.

SPELET 2 vinner alltid på konflikter. Flödet är ENVÄGS: SPELET 2 → PMOPOLY.

Användning:
    python tools/sync_from_spelet2.py [--dry-run]

Notes:
- Använder rätt encoding (cp1252 → utf-8) för CSV:er, eftersom SPELET 2
  exporterar Windows-1252 men PMOPOLY-loadern föredrar UTF-8.
- PU_personal.csv + PL_personal.csv kombineras till data/PU_PL_personal.csv
  (PROJEKTCHEF + ARBETSCHEF i samma fil eftersom data_loader läser båda).
- PU_BTABYA.csv är delad i två filer (PU_BTA + PU_BYA) i SPELET 2 men
  våra loaders använder fortfarande den gamla strukturen — kombinerar dem.
- Kopierar även Spelbräde-bilder till frontend/img/steps/ för stödbilder.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

# Tvinga UTF-8 på stdout/stderr så åäö och pilar inte kraschar Windows-konsolen
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
SPELET2 = Path("C:/Users/niklas.sviden/OneDrive - Åke Sundvalls Byggnads AB/SPELET 2")
DATA = REPO / "data"
IMG_STEPS = REPO / "frontend" / "img" / "steps"

# (källa-relativ, destination-absolut)
CSV_FILES = [
    # 0. Ledning
    ("0. Ledning/L_dotterbolag.csv",        DATA / "0_ledning" / "L_dotterbolag.csv"),
    ("0. Ledning/L_personal.csv",           DATA / "0_ledning" / "L_personal.csv"),
    # 1. Projektutveckling — enskilda
    ("1. Projektutveckling/PU_poldia.csv",        DATA / "1_projektutveckling" / "PU_poldia.csv"),
    ("1. Projektutveckling/PU_poldia_spec.csv",   DATA / "1_projektutveckling" / "PU_poldia_spec.csv"),
    ("1. Projektutveckling/PU_projekt.csv",       DATA / "1_projektutveckling" / "PU_projekt.csv"),
    ("1. Projektutveckling/PU_markexpansion.csv", DATA / "1_projektutveckling" / "PU_markepansion.csv"),  # typo bevarad
    # 2. Planering
    ("2. Planering/PL_Händelsekort.csv",   DATA / "2_planering" / "PL_Händelsekort.csv"),
    ("2. Planering/PL_Leverantörer.csv",   DATA / "2_planering" / "PL_Leverantörer.csv"),
    ("2. Planering/PL_Organisation.csv",   DATA / "2_planering" / "PL_Organisation.csv"),
    # 3. Genomförande
    ("3. Genomförande/GF_faskort.csv",              DATA / "3_genomforande" / "GF_Faskort_utforande.csv"),
    ("3. Genomförande/GF_garantibesiktning.csv",    DATA / "3_genomforande" / "GF_garantibesiktning.csv"),
    ("3. Genomförande/GF_konsekvenskort.csv",       DATA / "3_genomforande" / "GF_konsekvenskort.csv"),
    ("3. Genomförande/GF_kultur.csv",               DATA / "3_genomforande" / "GF_kultur.csv"),
    # 4. Förvaltning
    ("4. Förvaltning/F_DD.csv",            DATA / "4_forvaltning" / "F_DD.csv"),
    ("4. Förvaltning/F_händelsekort.csv",  DATA / "4_forvaltning" / "F_händelsekort.csv"),
    ("4. Förvaltning/F_kvartal.csv",       DATA / "4_forvaltning" / "F_kvartal.csv"),
    ("4. Förvaltning/F_moderbolagslån.csv", DATA / "4_forvaltning" / "F_moderbolagslån.csv"),
    ("4. Förvaltning/F_omvärldskort.csv",  DATA / "4_forvaltning" / "F_omvärldskort.csv"),
    ("4. Förvaltning/F_personal.csv",      DATA / "4_forvaltning" / "F_personal.csv"),
    ("4. Förvaltning/F_yield.csv",         DATA / "4_forvaltning" / "F_yield.csv"),
]

# Bilder — kopieras direkt utan encoding-konvertering
IMG_PATTERNS = [
    ("Bilder/Spelbräde", IMG_STEPS),
]


def convert_cp1252_to_utf8(src: Path, dst: Path, dry: bool) -> bool:
    """Läs cp1252, skriv utf-8 (no BOM). Bevarar åäö korrekt."""
    if not src.exists():
        print(f"  SKIP (saknas): {src.name}")
        return False
    if dry:
        print(f"  [dry] {src.name} -> {dst.relative_to(REPO)}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = src.read_bytes()
    try:
        text = raw.decode("cp1252")
    except UnicodeDecodeError:
        # Fallback: prova UTF-8 om filen redan är konverterad
        text = raw.decode("utf-8", errors="replace")
    dst.write_text(text, encoding="utf-8", newline="\r\n")
    return True


def combine_personal(dry: bool) -> bool:
    """Kombinera PU_personal.csv + PL_personal.csv → PU_PL_personal.csv."""
    pu = SPELET2 / "1. Projektutveckling" / "PU_personal.csv"
    pl = SPELET2 / "2. Planering" / "PL_personal.csv"
    dst = DATA / "PU_PL_personal.csv"
    if not pu.exists() or not pl.exists():
        print(f"  SKIP combine_personal (saknas: PU_personal={pu.exists()}, PL_personal={pl.exists()})")
        return False
    if dry:
        print(f"  [dry] PU_personal + PL_personal -> {dst.relative_to(REPO)}")
        return True
    pu_text = pu.read_bytes().decode("cp1252")
    pl_text = pl.read_bytes().decode("cp1252")
    pu_lines = pu_text.splitlines()
    pl_lines = pl_text.splitlines()
    combined = pu_lines + pl_lines[1:]  # skip header in second file
    dst.write_text("\r\n".join(combined), encoding="utf-8", newline="")
    return True


def combine_btabya(dry: bool) -> bool:
    """SPELET 2 har PU_BTA.csv + PU_BYA.csv (split). PMOPOLY använder PU_BTABYA.csv.
    Kombinera till en fil för bakåtkompatibilitet."""
    bta = SPELET2 / "1. Projektutveckling" / "PU_BTA.csv"
    bya = SPELET2 / "1. Projektutveckling" / "PU_BYA.csv"
    dst = DATA / "1_projektutveckling" / "PU_BTABYA.csv"
    if not bta.exists() or not bya.exists():
        print(f"  SKIP combine_btabya (saknas: BTA={bta.exists()}, BYA={bya.exists()})")
        return False
    if dry:
        print(f"  [dry] PU_BTA + PU_BYA -> {dst.relative_to(REPO)}")
        return True
    bta_text = bta.read_bytes().decode("cp1252")
    bya_text = bya.read_bytes().decode("cp1252")
    bta_lines = bta_text.splitlines()
    bya_lines = bya_text.splitlines()
    combined = bta_lines + bya_lines[1:]
    dst.write_text("\r\n".join(combined), encoding="utf-8", newline="")
    return True


def sync_images(dry: bool) -> int:
    """Kopiera step-stödbilder från SPELET 2/Bilder/Spelbräde/ till frontend/img/steps/."""
    src = SPELET2 / "Bilder" / "Spelbräde"
    if not src.exists():
        print(f"  SKIP sync_images: {src} saknas")
        return 0
    if not dry:
        IMG_STEPS.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src.iterdir():
        if not f.is_file() or f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        dst = IMG_STEPS / f.name
        if dry:
            print(f"  [dry] image {f.name}")
        else:
            shutil.copy2(f, dst)
        count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="visa vad som skulle göras")
    args = ap.parse_args()

    if not SPELET2.exists():
        print(f"ERROR: SPELET 2 hittas inte: {SPELET2}", file=sys.stderr)
        sys.exit(1)

    print(f"Sync från {SPELET2}")
    print(f"Sync till   {REPO}")
    print()

    print("=== CSV-filer (cp1252 → utf-8) ===")
    ok = fail = 0
    for rel, dst in CSV_FILES:
        src = SPELET2 / rel
        if convert_cp1252_to_utf8(src, dst, args.dry_run):
            ok += 1
        else:
            fail += 1

    print("\n=== Kombinerade filer ===")
    if combine_personal(args.dry_run):
        ok += 1
    if combine_btabya(args.dry_run):
        ok += 1

    print("\n=== Stödbilder (Bilder/Spelbräde/) ===")
    img_count = sync_images(args.dry_run)
    print(f"  {img_count} bilder synkade")

    print(f"\nKlart: {ok} OK, {fail} skippade.")


if __name__ == "__main__":
    main()
