"""
förbered_csv.py v3
Sorterar bas-CSV på plats efter ordning_bild så att rad-ordningen i
filen matchar tryckordningen för bildsidan. Inga separata _bildsida.csv
eller _textsida.csv genereras längre — master_kortproduktion.jsx (v19+)
sorterar bas-CSV om till ordning_text vid textsida-pass.

Detta skript är användbart om du vill rensa upp bas-CSV efter manuella
redigeringar så raderna ligger i en logisk ordning för läsning, eller
om du vill verifiera att alla CSV:er har giltiga ordning_bild-värden.

Anrop: python förbered_csv.py "C:\\väg\\till\\SPELET 2\\"
"""

import sys
import os
import csv


MAPPAR = {
    "PU_": "1. Projektutveckling",
    "PL_": "2. Planering",
    "GF_": "3. Genomförande",
    "F_":  "4. Förvaltning",
    "L_":  "0. Ledning",
}


def sortera_csv_på_plats(csv_path):
    """Läs, sortera efter ordning_bild, skriv tillbaka. Returnerar antal rader."""
    with open(csv_path, encoding="cp1252", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    if len(rows) < 2:
        return 0

    header = rows[0]
    if "ordning_bild" not in header:
        return -1

    idx = header.index("ordning_bild")

    def nyckel(rad):
        try:
            return (0, int(rad[idx]))
        except (ValueError, IndexError):
            return (1, 0)

    sorted_data = sorted(rows[1:], key=nyckel)

    with open(csv_path, "w", encoding="cp1252", newline="", errors="replace") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        writer.writerows(sorted_data)

    return len(sorted_data)


def behandla_mapp(mapp_path, prefix):
    if not os.path.isdir(mapp_path):
        print(f"  OBS: Mapp saknas: {mapp_path}")
        return 0

    ok = 0
    for fil in sorted(os.listdir(mapp_path)):
        if not fil.lower().endswith(".csv"):
            continue
        if "_bildsida.csv" in fil or "_textsida.csv" in fil or "_~temp" in fil:
            continue
        if fil.endswith(".bak"):
            continue
        if not fil.upper().startswith(prefix.upper()):
            continue

        csv_path = os.path.join(mapp_path, fil)
        try:
            n = sortera_csv_på_plats(csv_path)
            if n == -1:
                print(f"  - {fil} (saknar ordning_bild, oförändrad)")
            elif n == 0:
                print(f"  - {fil} (tom)")
            else:
                print(f"  OK: {fil} ({n} rader sorterade efter ordning_bild)")
                ok += 1
        except Exception as e:
            print(f"  FEL: {fil}: {e}")

    return ok


def main():
    rot = (sys.argv[1] if len(sys.argv) > 1 else os.getcwd()).rstrip("\\/")
    print(f"Sorterar CSV:er efter ordning_bild i: {rot}")
    totalt = 0
    for prefix, undermapp in MAPPAR.items():
        mapp_path = os.path.join(rot, undermapp)
        print(f"\n[{prefix}] {mapp_path}")
        totalt += behandla_mapp(mapp_path, prefix)

    print(f"\nKlart: {totalt} CSV-filer sorterade på plats.")


if __name__ == "__main__":
    main()

