#!/bin/bash
# Sync CSV files from SPELET 2 (source of truth) to PMOPOLY/data/.
# SPELET 2 always wins.
#
# Tunn wrapper kring sync_csv.py, som hanterar att källan har splittat två
# filer (PU_BTA + PU_BYA, PU_personal + PL_personal) — Python-versionen
# kombinerar dem till de filnamn appen läser.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$SCRIPT_DIR/sync_csv.py" "$@"
