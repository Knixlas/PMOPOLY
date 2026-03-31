#!/bin/bash
# Sync CSV files from SPELET 2 (source of truth) to PMOPOLY/data/
# SPELET 2 always wins.

SPELET2="/c/Users/niklas.sviden/OneDrive - Åke Sundvalls Byggnads AB/SPELET 2"
PMOPOLY="/c/PMOPOLY/data"

echo "Syncing CSV files from SPELET 2 -> PMOPOLY/data..."

# Phase 1: Projektutveckling
cp "$SPELET2/1. Projektutveckling/PU_BTABYA.csv"        "$PMOPOLY/1_projektutveckling/PU_BTABYA.csv"
cp "$SPELET2/1. Projektutveckling/PU_poldia.csv"         "$PMOPOLY/1_projektutveckling/PU_poldia.csv"
cp "$SPELET2/1. Projektutveckling/PU_poldia_spec.csv"    "$PMOPOLY/1_projektutveckling/PU_poldia_spec.csv"
cp "$SPELET2/1. Projektutveckling/PU_projekt.csv"        "$PMOPOLY/1_projektutveckling/PU_projekt.csv"
cp "$SPELET2/1. Projektutveckling/PU_markexpansion.csv"  "$PMOPOLY/1_projektutveckling/PU_markepansion.csv"
cp "$SPELET2/1. Projektutveckling/PU_PL_personal.csv"    "$PMOPOLY/PU_PL_personal.csv"

# Phase 2: Planering
cp "$SPELET2/2. Planering/PL_Händelsekort.csv"  "$PMOPOLY/2_planering/PL_Händelsekort.csv"
cp "$SPELET2/2. Planering/PL_Leverantörer.csv"  "$PMOPOLY/2_planering/PL_Leverantörer.csv"
cp "$SPELET2/2. Planering/PL_Organisation.csv"  "$PMOPOLY/2_planering/PL_Organisation.csv"

# Phase 3: Genomförande
cp "$SPELET2/3. Genomförande/GF_faskort.csv"             "$PMOPOLY/3_genomforande/GF_Faskort_utforande.csv"
cp "$SPELET2/3. Genomförande/GF_garantibesiktning.csv"   "$PMOPOLY/3_genomforande/GF_garantibesiktning.csv"
cp "$SPELET2/3. Genomförande/GF_konsekvenskort.csv"      "$PMOPOLY/3_genomforande/GF_konsekvenskort.csv"
cp "$SPELET2/3. Genomförande/GF_kultur.csv"              "$PMOPOLY/3_genomforande/GF_kultur.csv"

# Phase 4: Förvaltning
cp "$SPELET2/4. Förvaltning/F_DD.csv"              "$PMOPOLY/4_forvaltning/F_DD.csv"
cp "$SPELET2/4. Förvaltning/F_händelsekort.csv"    "$PMOPOLY/4_forvaltning/F_händelsekort.csv"
cp "$SPELET2/4. Förvaltning/F_kvartal.csv"         "$PMOPOLY/4_forvaltning/F_kvartal.csv"
cp "$SPELET2/4. Förvaltning/F_moderbolagslån.csv"  "$PMOPOLY/4_forvaltning/F_moderbolagslån.csv"
cp "$SPELET2/4. Förvaltning/F_omvärldskort.csv"    "$PMOPOLY/4_forvaltning/F_omvärldskort.csv"
cp "$SPELET2/4. Förvaltning/F_personal.csv"        "$PMOPOLY/4_forvaltning/F_personal.csv"
cp "$SPELET2/4. Förvaltning/F_yield.csv"           "$PMOPOLY/4_forvaltning/F_yield.csv"

echo "Done! All 20 CSV files synced."
