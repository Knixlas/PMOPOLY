#!/usr/bin/env python3
"""
Sync CSV files from SPELET 2 (source of truth) to PMOPOLY/data/.

SPELET 2 always wins. Hanterar att källan har splittat två filer:
- PU_BTABYA.csv (kombinerad)  ←  PU_BTA.csv + PU_BYA.csv
- PU_PL_personal.csv (PC+AC)  ←  1.Projektutveckling/PU_personal.csv + 2.Planering/PL_personal.csv

Använder utf-8 inläsning + cp1252-fallback eftersom källan ibland sparas
som Windows-1252. Skriver alltid utf-8 utan BOM så data_loader.py kan
lita på en stabil encoding.
"""
import os
import sys

SPELET2 = r"C:\Users\niklas.sviden\OneDrive - Åke Sundvalls Byggnads AB\SPELET 2"
# Relativt skriptets plats — funkar både från main checkout och git-worktrees.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PMOPOLY = os.path.join(_SCRIPT_DIR, "data")

# (src_relpath, dst_relpath)  — direktkopior
DIRECT = [
    ("1. Projektutveckling/PU_poldia.csv",         "1_projektutveckling/PU_poldia.csv"),
    ("1. Projektutveckling/PU_poldia_spec.csv",    "1_projektutveckling/PU_poldia_spec.csv"),
    ("1. Projektutveckling/PU_projekt.csv",        "1_projektutveckling/PU_projekt.csv"),
    ("1. Projektutveckling/PU_markexpansion.csv",  "1_projektutveckling/PU_markepansion.csv"),
    ("2. Planering/PL_Händelsekort.csv",           "2_planering/PL_Händelsekort.csv"),
    ("2. Planering/PL_Leverantörer.csv",           "2_planering/PL_Leverantörer.csv"),
    ("2. Planering/PL_Organisation.csv",           "2_planering/PL_Organisation.csv"),
    ("3. Genomförande/GF_faskort.csv",             "3_genomforande/GF_Faskort_utforande.csv"),
    ("3. Genomförande/GF_garantibesiktning.csv",   "3_genomforande/GF_garantibesiktning.csv"),
    ("3. Genomförande/GF_konsekvenskort.csv",      "3_genomforande/GF_konsekvenskort.csv"),
    ("3. Genomförande/GF_kultur.csv",              "3_genomforande/GF_kultur.csv"),
    ("4. Förvaltning/F_DD.csv",                    "4_forvaltning/F_DD.csv"),
    ("4. Förvaltning/F_händelsekort.csv",          "4_forvaltning/F_händelsekort.csv"),
    ("4. Förvaltning/F_kvartal.csv",               "4_forvaltning/F_kvartal.csv"),
    ("4. Förvaltning/F_moderbolagslån.csv",        "4_forvaltning/F_moderbolagslån.csv"),
    ("4. Förvaltning/F_omvärldskort.csv",          "4_forvaltning/F_omvärldskort.csv"),
    ("4. Förvaltning/F_personal.csv",              "4_forvaltning/F_personal.csv"),
    ("4. Förvaltning/F_yield.csv",                 "4_forvaltning/F_yield.csv"),
    # Nya Förvaltning 2.0 – designdokument 2026-05-09 (fastigheter centrum, MV-tabell, FC/FS-arketyper).
    ("4. Förvaltning/Nya Förvaltning/F2_fastighetskort.csv", "4_forvaltning_v2/F2_fastighetskort.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_DD.csv",             "4_forvaltning_v2/F2_DD.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_FC_personal.csv",    "4_forvaltning_v2/F2_FC_personal.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_FS_personal.csv",    "4_forvaltning_v2/F2_FS_personal.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_garantikort.csv",    "4_forvaltning_v2/F2_garantikort.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_konsekvenskort.csv", "4_forvaltning_v2/F2_konsekvenskort.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_kvartal.csv",        "4_forvaltning_v2/F2_kvartal.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_omvärldskort.csv",   "4_forvaltning_v2/F2_omvärldskort.csv"),
    ("4. Förvaltning/Nya Förvaltning/F2_händelsekort.csv",   "4_forvaltning_v2/F2_händelsekort.csv"),
]

# (src1, src2, dst) — slå ihop två CSV-filer (en header från första)
COMBINE = [
    (
        "1. Projektutveckling/PU_BTA.csv",
        "1. Projektutveckling/PU_BYA.csv",
        "1_projektutveckling/PU_BTABYA.csv",
    ),
    (
        "1. Projektutveckling/PU_personal.csv",
        "2. Planering/PL_personal.csv",
        "PU_PL_personal.csv",
    ),
]


def read_text(path: str) -> str:
    """Läs CSV som text. Försöker utf-8/utf-8-sig/cp1252/latin-1."""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def sync():
    copied = 0
    combined = 0
    missing = []

    for src_rel, dst_rel in DIRECT:
        src = os.path.join(SPELET2, src_rel.replace("/", os.sep))
        dst = os.path.join(PMOPOLY, dst_rel.replace("/", os.sep))
        if not os.path.exists(src):
            missing.append(src_rel)
            continue
        write_text(dst, read_text(src))
        copied += 1
        print(f"  copy: {src_rel} -> {dst_rel}")

    for src1_rel, src2_rel, dst_rel in COMBINE:
        src1 = os.path.join(SPELET2, src1_rel.replace("/", os.sep))
        src2 = os.path.join(SPELET2, src2_rel.replace("/", os.sep))
        dst = os.path.join(PMOPOLY, dst_rel.replace("/", os.sep))
        if not os.path.exists(src1):
            missing.append(src1_rel)
            continue
        if not os.path.exists(src2):
            missing.append(src2_rel)
            continue
        text1 = read_text(src1).rstrip("\n").rstrip("\r")
        text2 = read_text(src2)
        # Hoppa över andra filens header
        lines2 = text2.splitlines(keepends=True)
        body2 = "".join(lines2[1:]) if len(lines2) > 1 else ""
        combined_text = text1 + "\n" + body2
        write_text(dst, combined_text)
        combined += 1
        print(f"  combine: {src1_rel} + {src2_rel} -> {dst_rel}")

    print()
    print(f"Klart: {copied} kopierade, {combined} kombinerade.")
    if missing:
        print()
        print("VARNING — saknade källfiler:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"Syncar SPELET 2 -> PMOPOLY/data ...")
    print(f"  src: {SPELET2}")
    print(f"  dst: {PMOPOLY}")
    print()
    sync()
