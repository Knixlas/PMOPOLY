# -*- coding: utf-8 -*-
"""Genererar mockup-mottagardata för JV-paket DataMerge.

60 rader = 20 JV × 3 roller (CEO/COO/CFO).
Källor: 0. Ledning/L_JV.csv (för JV-namn).
Output: 0. Ledning/L_mottagare.csv (cp1252, semikolon-separerad).
"""
import csv
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDNING = ROOT / "0. Ledning"

ROLES = ["CEO", "COO", "CFO"]

FIRST_NAMES = [
    "Anna", "Erik", "Karin", "Lars", "Maria", "Johan", "Eva", "Mikael",
    "Lena", "Per", "Sofia", "Anders", "Helena", "Magnus", "Cecilia",
    "Fredrik", "Ingrid", "Stefan", "Birgitta", "Olof", "Margareta",
    "Henrik", "Susanne", "Niklas", "Camilla", "Patrik", "Annika",
    "Tomas", "Kristina", "Daniel", "Emma", "Jonas", "Therese",
    "Christer", "Elisabeth", "Marcus", "Monica", "Robert", "Charlotta",
    "Mats", "Jenny", "Andreas", "Linda", "Peter", "Sara",
    "Bengt", "Hanna", "Roger", "Pernilla", "Joakim", "Petra",
    "Martin", "Ulrika", "Björn", "Malin", "Staffan", "Åsa",
    "Gunnar", "Veronica", "Hans", "Marianne",
]

LAST_NAMES = [
    "Andersson", "Johansson", "Karlsson", "Nilsson", "Eriksson",
    "Larsson", "Olsson", "Persson", "Svensson", "Gustafsson",
    "Pettersson", "Jonsson", "Jansson", "Hansson", "Bengtsson",
    "Jönsson", "Lindberg", "Jakobsson", "Magnusson", "Olofsson",
    "Lindström", "Lindqvist", "Lindgren", "Berg", "Axelsson",
    "Bergström", "Lundberg", "Lundgren", "Lundqvist", "Mattsson",
    "Berglund", "Fredriksson", "Sandberg", "Henriksson", "Forsberg",
    "Sjöberg", "Wallin", "Engström", "Eklund", "Danielsson",
    "Holm", "Lindholm", "Samuelsson", "Fransson", "Bergman",
    "Wikström", "Isaksson", "Bergqvist", "Nyström", "Holmberg",
    "Arvidsson", "Löfgren", "Söderberg", "Nyberg", "Blomqvist",
    "Claesson", "Mårtensson", "Gunnarsson", "Hermansson", "Björk",
]

# Alla 20 JV-bolag får samma konferensdatum (mockup)
CONF_DATE = "2026-09-18"
CONF_PLATS = "Hotel Skansen, Båstad"
CONF_TID = "Fredag 13:00 – söndag 14:00"


def load_jv_names():
    """Läser JV-namn från L_JV.csv (kolumn 'Namn')."""
    path = LEDNING / "L_JV.csv"
    with open(path, encoding="cp1252") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [row["Namn"] for row in reader if row.get("Namn")]


def make_recipient_rows():
    random.seed(42)  # Stabilitet — samma mockup vid omkörning
    names_pool = [(fn, ln) for fn in FIRST_NAMES for ln in LAST_NAMES]
    random.shuffle(names_pool)

    rows = []
    jvs = load_jv_names()
    if len(jvs) < 20:
        raise ValueError(f"Förväntade ≥20 JV i L_JV.csv, fick {len(jvs)}")

    name_idx = 0
    for jv_idx, jv_namn in enumerate(jvs[:20], start=1):
        for role in ROLES:
            fn, ln = names_pool[name_idx]
            name_idx += 1
            full_name = f"{fn} {ln}"
            ref = f"JV{jv_idx:02d}-{role}"
            row = {
                "ID": f"M-{jv_idx:02d}-{role}",
                "Roll": role,
                "Namn": full_name,
                "JV_Namn": jv_namn,
                "Datum": CONF_DATE,
                "Plats": CONF_PLATS,
                "Tid": CONF_TID,
                "Ref": ref,
            }
            rows.append(row)
    return rows


def write_csv(rows, path):
    fieldnames = ["ID", "Roll", "Namn", "JV_Namn", "Datum", "Plats", "Tid", "Ref"]
    with open(path, "w", encoding="cp1252", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    rows = make_recipient_rows()
    out = LEDNING / "L_mottagare.csv"
    write_csv(rows, out)
    print(f"Skrev {len(rows)} rader till {out}")
    print(f"Roller: {', '.join(ROLES)}")
    print(f"JV-bolag: {len(set(r['JV_Namn'] for r in rows))}")


if __name__ == "__main__":
    main()

