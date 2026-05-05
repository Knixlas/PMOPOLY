"""Importerar steg-prompts från Stegprompts.xlsx till data/companion_texts.json.

Användning:
    python tools/import_prompts_xlsx.py                    # importera & skriv
    python tools/import_prompts_xlsx.py --dry-run          # visa diff utan att skriva
    python tools/import_prompts_xlsx.py --xlsx min.xlsx    # annan källfil

Excel-formatet (flikken "Stegprompts"):
    A: phase_id      (lås — t.ex. phase1)
    B: step_id       (lås — t.ex. choose_pc)
    C: order         (heltal, sorterar inom fas)
    D: name          (rubrik)
    E: image         (filnamn i frontend/img/steps/, valfritt)
    F: lead          (inledning)
    G: actions       (en åtgärd per rad — Alt+Enter)
    H: meaning       (vad det betyder i verkligheten)
    I: tip           (strategitips)
    J: regelbok      (t.ex. §3.8)

Skriver JSON med samma struktur som data/companion_texts.json. Kör
`python tools/validate_prompts.py` efteråt för att verifiera.
"""
import argparse
import json
import os
import sys
from collections import OrderedDict

try:
    from openpyxl import load_workbook
except ImportError:
    print("FEL: openpyxl saknas. Kör: pip install openpyxl", file=sys.stderr)
    sys.exit(2)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XLSX = os.path.join(ROOT, "Stegprompts.xlsx")
JSON_PATH = os.path.join(ROOT, "data", "companion_texts.json")
PHASE_NAMES = {
    "phase1": "Skede 1: Projektutveckling",
    "phase2": "Skede 2.1: Planering",
    "phase3": "Skede 2.2: Genomförande",
    "phase4": "Skede 3: Förvaltning",
}
COL_ORDER = ["phase_id", "step_id", "order", "name", "image", "lead",
             "actions", "meaning", "tip", "regelbok"]


def parse_actions(raw):
    """Splittra en cells text till en lista av åtgärder.

    Behåller indragna fortsättningsrader (de börjar med två blanksteg) som
    fortsättning på föregående punkt — det matchar JSON-strukturen där t.ex.
    'Companion summerar automatiskt:' följs av indenterade undermeningar.
    """
    if not raw:
        return []
    lines = str(raw).splitlines()
    items = []
    for line in lines:
        if not line.strip():
            continue
        # Strip ledande punktsymboler vi själva la in när vi exporterade
        stripped = line.lstrip()
        for prefix in ("• ", "- ", "* "):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
                break
        # Bevara ev. ledande blanksteg (indrag)
        leading = line[:len(line) - len(line.lstrip())]
        items.append(leading + stripped)
    return items


def read_xlsx(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Hittar inte {path}")
    wb = load_workbook(path, data_only=True)
    if "Stegprompts" not in wb.sheetnames:
        raise ValueError(f"{path}: saknar flikken 'Stegprompts'")
    ws = wb["Stegprompts"]

    # Verifiera headerraden
    header = [(ws.cell(row=1, column=i + 1).value or "").strip().lower()
              if ws.cell(row=1, column=i + 1).value else ""
              for i in range(len(COL_ORDER))]

    rows = []
    for r in range(2, ws.max_row + 1):
        record = {}
        for i, key in enumerate(COL_ORDER):
            val = ws.cell(row=r, column=i + 1).value
            record[key] = val
        # Hoppa över helt tomma rader
        if not any(v for v in record.values()):
            continue
        rows.append((r, record))
    return rows


def validate_rows(rows):
    errors = []
    seen = set()
    for r, rec in rows:
        pid = rec.get("phase_id")
        sid = rec.get("step_id")
        if not pid or not sid:
            errors.append(f"Rad {r}: phase_id och step_id krävs")
            continue
        if pid not in PHASE_NAMES:
            errors.append(f"Rad {r}: okänt phase_id '{pid}' (förväntat: {sorted(PHASE_NAMES)})")
        key = (pid, sid)
        if key in seen:
            errors.append(f"Rad {r}: duplicerad ({pid}, {sid})")
        seen.add(key)
        for req in ("name", "lead"):
            if not rec.get(req) or not str(rec[req]).strip():
                errors.append(f"Rad {r} ({pid}/{sid}): saknar '{req}'")
        if not parse_actions(rec.get("actions")):
            errors.append(f"Rad {r} ({pid}/{sid}): 'actions' är tom — minst en åtgärd krävs")
    return errors


def build_phases(rows):
    by_phase = {pid: [] for pid in PHASE_NAMES}
    for _, rec in rows:
        pid = rec["phase_id"]
        if pid not in by_phase:
            continue  # validation rapporterar redan
        order = rec.get("order")
        try:
            order_val = int(order) if order is not None else 9999
        except (TypeError, ValueError):
            order_val = 9999
        by_phase[pid].append((order_val, rec))

    phases_out = []
    for pid in ("phase1", "phase2", "phase3", "phase4"):
        items = sorted(by_phase[pid], key=lambda x: x[0])
        steps = []
        for _, rec in items:
            step = OrderedDict()
            step["id"] = str(rec["step_id"]).strip()
            step["name"] = str(rec["name"]).strip()
            if rec.get("image") and str(rec["image"]).strip():
                step["image"] = str(rec["image"]).strip()
            step["lead"] = str(rec["lead"]).strip()
            step["actions"] = parse_actions(rec.get("actions"))
            if rec.get("meaning") and str(rec["meaning"]).strip():
                step["meaning"] = str(rec["meaning"]).strip()
            if rec.get("tip") and str(rec["tip"]).strip():
                step["tip"] = str(rec["tip"]).strip()
            if rec.get("regelbok") and str(rec["regelbok"]).strip():
                step["regelbok"] = str(rec["regelbok"]).strip()
            steps.append(step)
        phases_out.append({"id": pid, "name": PHASE_NAMES[pid], "steps": steps})
    return phases_out


def diff_summary(old_phases, new_phases):
    """Skriv ut en kort diff av step-id:n och vilka fält som ändrats."""
    old_idx = {(p["id"], s["id"]): s for p in old_phases for s in p.get("steps", [])}
    new_idx = {(p["id"], s["id"]): s for p in new_phases for s in p.get("steps", [])}

    added = sorted(set(new_idx) - set(old_idx))
    removed = sorted(set(old_idx) - set(new_idx))
    common = sorted(set(old_idx) & set(new_idx))

    changed_steps = []
    for key in common:
        o, n = old_idx[key], new_idx[key]
        diffs = []
        for field in ("name", "image", "lead", "actions", "meaning", "tip", "regelbok"):
            if o.get(field) != n.get(field):
                diffs.append(field)
        if diffs:
            changed_steps.append((key, diffs))

    print(f"  Tillagda steg:    {len(added)}")
    for k in added:
        print(f"    + {k[0]}/{k[1]}")
    print(f"  Borttagna steg:   {len(removed)}")
    for k in removed:
        print(f"    - {k[0]}/{k[1]}")
    print(f"  Ändrade steg:     {len(changed_steps)}")
    for key, diffs in changed_steps:
        print(f"    ~ {key[0]}/{key[1]}: {', '.join(diffs)}")

    # Reordering check
    for pid in ("phase1", "phase2", "phase3", "phase4"):
        old_ids = [s["id"] for p in old_phases if p["id"] == pid for s in p.get("steps", [])]
        new_ids = [s["id"] for p in new_phases if p["id"] == pid for s in p.get("steps", [])]
        if [i for i in old_ids if i in new_ids] != [i for i in new_ids if i in old_ids]:
            print(f"  {pid}: ordning ändrad")
            print(f"    från: {old_ids}")
            print(f"    till: {new_ids}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=DEFAULT_XLSX,
                    help=f"Sökväg till excelfilen (standard: {DEFAULT_XLSX})")
    ap.add_argument("--out", default=JSON_PATH,
                    help=f"JSON att skriva (standard: {JSON_PATH})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Visa diff utan att skriva")
    args = ap.parse_args()

    print(f"Läser {args.xlsx}...")
    rows = read_xlsx(args.xlsx)
    print(f"  {len(rows)} rader hittade")

    errors = validate_rows(rows)
    if errors:
        print("\nFEL i indata:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    new_phases = build_phases(rows)

    # Läs befintlig JSON för diff
    old_data = {"phases": []}
    if os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as f:
            old_data = json.load(f)

    print("\nDiff mot nuvarande JSON:")
    diff_summary(old_data.get("phases", []), new_phases)

    new_data = {"phases": new_phases}

    if args.dry_run:
        print("\n[DRY-RUN] Skriver inget. Kör utan --dry-run för att applicera.")
        return

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nSkrev {args.out}")
    print("Tips: kör 'python tools/validate_prompts.py' för att verifiera.")


if __name__ == "__main__":
    main()
