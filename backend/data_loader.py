"""Load all game data from CSV/XLSX files."""
import csv
import json
import os
from typing import List, Dict, Tuple
from config import DATA_DIR, data_path
from models import (
    Project, PolitikDialogCard, SpecialCard, PlanningEventCard,
    Supplier, Organisation,
    PhaseCard, ExternalSupport, PenaltyCard, Staff, WorldEvent,
    ManagementEvent, DDCard, BYA_CLASSES, BTA_CLASSES,
)
import models


def detect_encoding(filepath: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(500)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"


def read_csv(filepath: str) -> List[dict]:
    enc = detect_encoding(filepath)
    with open(filepath, "r", encoding=enc) as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


def safe_int(val, default=0) -> int:
    if not val or str(val).strip() == "":
        return default
    try:
        return int(float(str(val).replace(",", ".").strip()))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0) -> float:
    if not val or str(val).strip() == "":
        return default
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return default


def safe_str(val, default="") -> str:
    if val is None:
        return default
    return str(val).strip()


# ── Projects ──

def load_projects() -> Dict[str, List[Project]]:
    """Load projects grouped by type."""
    rows = read_csv(data_path("projekt"))
    stacks: Dict[str, List[Project]] = {}
    counters: Dict[str, int] = {}

    supplier_cols = [
        "MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER",
        "STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"
    ]

    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        forekomst = safe_int(row.get("Förekomst", row.get("F\x94rekomst")), 1)
        namn = safe_str(row.get("Namn"))

        supplier_reqs = {}
        for col in supplier_cols:
            val = safe_str(row.get(col))
            if val:
                supplier_reqs[col] = val

        for i in range(forekomst):
            counters[typ] = counters.get(typ, 0) + 1
            pid = f"{typ[:3].upper()}-{counters[typ]}"
            p = Project(
                id=pid, namn=namn, typ=typ, forekomst=forekomst,
                kostnad=safe_int(row.get("Kostnad")),
                formfaktor=safe_int(row.get("Formfaktor")),
                bta=safe_int(row.get("BTA")),
                anskaffning=safe_int(row.get("Anskaffning")),
                marknadsvarde=safe_int(row.get("Marknadsvärde", row.get("Marknadsv\x84rde"))),
                rorlig_intakt=safe_str(row.get("Rörligt marknadsvärde", row.get("R\x94rligt marknadsv\x84rde")), "D6"),
                kvalitet=safe_int(row.get("Kvalitet")),
                hallbarhet=safe_int(row.get("Hållbarhet", row.get("H\x86llbarhet"))),
                tid=safe_int(row.get("Tid")),
                riskbuffert=safe_int(row.get("Riskbuffert")),
                antal_krav=safe_int(row.get("Antal krav")),
                namndbeslut=safe_int(row.get("Nämndbeslut", row.get("N\x84mndbeslut")), 1),
                energiklass=safe_str(row.get("Energiklass"), "C"),
                driftnetto=safe_float(row.get("Driftnetto")),
                supplier_reqs=supplier_reqs,
                led=safe_int(row.get("LED")),
                kom=safe_int(row.get("KOM")),
                sam=safe_int(row.get("SAM")),
                pro=safe_int(row.get("PRO")),
                abm=safe_int(row.get("ABM")),
            )
            stacks.setdefault(typ, []).append(p)

    # Shuffle each stack
    import random
    for stack in stacks.values():
        random.shuffle(stack)

    return stacks


# ── Politik/Dialog Cards ──

def load_politik_dialog() -> Tuple[List[PolitikDialogCard], List[PolitikDialogCard]]:
    rows = read_csv(data_path("poldia"))
    politik = []
    dialog = []

    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = {}
        # Columns: 1, 2-10, 11-15, 16-19, 20
        for key in ["1", "2-10", "11-15", "16-19", "20"]:
            val = safe_str(row.get(key))
            if val:
                effects[key] = val

        card = PolitikDialogCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            rubrik=safe_str(row.get("Rubrik")),
            text=safe_str(row.get("Text")),
            effects=effects,
        )
        if typ.lower().startswith("politik"):
            politik.append(card)
        else:
            dialog.append(card)

    return politik, dialog


def load_special_cards() -> List[SpecialCard]:
    fp = data_path("poldia_spec")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    cards = []
    for row in rows:
        cards.append(SpecialCard(
            typ=safe_str(row.get("Typ")),
            rubrik=safe_str(row.get("Rubrik")),
            poverkar=safe_str(row.get("Påverkar", row.get("P\x86verkar"))),
            effekt=safe_str(row.get("Effekt")),
        ))
    return cards


# ── Suppliers ──

def load_suppliers() -> Dict[str, List[Supplier]]:
    rows = read_csv(data_path("leverantorer"))
    suppliers: Dict[str, List[Supplier]] = {}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        klass_priser = {
            "A": safe_int(row.get("Klass_A")),
            "B": safe_int(row.get("Klass_B")),
            "C": safe_int(row.get("Klass_C")),
            "D": safe_int(row.get("Klass_D")),
        }
        kompetenser = {
            "LED": safe_int(row.get("LED")),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "PRO": safe_int(row.get("PRO")),
            "ABM": safe_int(row.get("ABM")),
        }
        s = Supplier(
            namn=namn, niva=safe_int(row.get("Nivå", row.get("Niv\x86")), 1),
            beskrivning=safe_str(row.get("Beskrivning")),
            beror_av=safe_str(row.get("Beror_av"), "BTA"),
            klass_priser=klass_priser,
            q=safe_int(row.get("Q")), h=safe_int(row.get("H")),
            t=safe_int(row.get("T_mån", row.get("T_m\x86n"))),
            erfarenhet=safe_int(row.get("erfarenhet")),
            kompetenser=kompetenser,
        )
        suppliers.setdefault(namn, []).append(s)

    # Sort each by level
    for key in suppliers:
        suppliers[key].sort(key=lambda x: x.niva)

    return suppliers


# ── Organisations ──

def load_organisations() -> Dict[str, List[Organisation]]:
    rows = read_csv(data_path("organisation"))
    orgs: Dict[str, List[Organisation]] = {}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        kompetenser = {
            "LED": safe_int(row.get("LED")),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "PRO": safe_int(row.get("PRO")),
            "ABM": safe_int(row.get("ABM")),
        }
        o = Organisation(
            namn=namn, niva=safe_int(row.get("Nivå", row.get("Niv\x86")), 1),
            kostnad_mkr=safe_int(row.get("Kostnad_Mkr")),
            q=safe_int(row.get("Q")), h=safe_int(row.get("H")),
            t=safe_int(row.get("T_mån", row.get("T_m\x86n"))),
            erfarenhet=safe_int(row.get("erfa", row.get("erfarenhet"))),
            riskbuffert=safe_int(row.get("Riskbuffert")),
            kompetenser=kompetenser,
        )
        orgs.setdefault(namn, []).append(o)

    for key in orgs:
        orgs[key].sort(key=lambda x: x.niva)

    return orgs


# ── Planning Event Cards ──

def load_planning_events() -> Dict[str, List[PlanningEventCard]]:
    """Load planning event cards grouped by kort_id.

    CSV columns: Kort_ID;ID;Namn;Typ;Fas;Svårighetsgrad;Beskrivning;Summering;
                 Trigger;Klassvillkor;Tröskel_1_5;Tröskel_6_17;Tröskel_18_20;Tröskel_21_plus
    """
    fp = data_path("handelsekort_pl")
    if not os.path.exists(fp):
        return {}

    enc = detect_encoding(fp)
    cards: Dict[str, List[PlanningEventCard]] = {}

    with open(fp, "r", encoding=enc) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        # Find threshold columns (indices 10-13 in 0-based)
        for cols in reader:
            if not cols[0].strip() or cols[0].strip().lower() == "tom":
                continue

            effects = [
                cols[10].strip() if len(cols) > 10 else "",
                cols[11].strip() if len(cols) > 11 else "",
                cols[12].strip() if len(cols) > 12 else "",
                cols[13].strip() if len(cols) > 13 else "",
            ]

            card = PlanningEventCard(
                kort_id=cols[0].strip(),
                id=safe_int(cols[1]) if len(cols) > 1 else 0,
                namn=cols[2].strip() if len(cols) > 2 else "",
                typ=cols[3].strip() if len(cols) > 3 else "",
                fas=cols[4].strip() if len(cols) > 4 else "",
                svarighetsgrad=cols[5].strip() if len(cols) > 5 else "",
                beskrivning=cols[6].strip() if len(cols) > 6 else "",
                summering=cols[7].strip() if len(cols) > 7 else "",
                trigger=cols[8].strip() if len(cols) > 8 else "Alla",
                klassvillkor=cols[9].strip() if len(cols) > 9 else "Alla",
                effects=effects,
            )

            kort_id = card.kort_id
            cards.setdefault(kort_id, []).append(card)

    return cards


def load_supplier_requirements() -> Dict[str, Dict[str, str]]:
    """Load project -> supplier requirement mappings from PU_projekt.csv.

    Returns: {supplier_type: {project_name: requirement_text}}
    """
    rows = read_csv(data_path("projekt"))
    supplier_cols = [
        "MARK", "HUSUNDERBYGGNAD", "STOMME", "YTTERTAK", "FASADER",
        "STOMKOMPLETTERING", "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN"
    ]
    reqs: Dict[str, Dict[str, str]] = {t: {} for t in supplier_cols}

    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        for col in supplier_cols:
            val = safe_str(row.get(col))
            if val:
                reqs[col][namn] = val

    return reqs


# ── External Support (Kultur) ──

def load_external_support() -> List[ExternalSupport]:
    rows = read_csv(data_path("kultur"))
    cards = []
    for row in rows:
        namn = safe_str(row.get("Namn"))
        if not namn:
            continue
        kompetenser = {
            "LED": safe_int(row.get("LED")),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "PRO": safe_int(row.get("PRO")),
            "ABM": safe_int(row.get("ABM")),
        }
        cards.append(ExternalSupport(
            id=safe_str(row.get("ID", "")),
            namn=namn, kompetenser=kompetenser,
        ))
    import random
    random.shuffle(cards)
    return cards


# ── Phase Cards (Faskort) ──

def load_phase_cards() -> Dict[int, List[PhaseCard]]:
    rows = read_csv(data_path("faskort"))
    cards: Dict[int, List[PhaseCard]] = {}

    for row in rows:
        pid = safe_str(row.get("ID"))
        steg = safe_int(row.get("Steg"))
        if not steg:
            continue

        levels = []
        for lvl_name, prefix in [("Negativt", "Negativt"), ("Neutralt", "Neutralt"),
                                   ("Positivt", "Positivt"), ("Bonus", "Bonus")]:
            levels.append({
                "name": lvl_name,
                "req_b": safe_str(row.get(f"{prefix} B")),
                "req_s": safe_str(row.get(f"{prefix} S")),
                "req_k": safe_str(row.get(f"{prefix} K")),
                "effect": safe_str(row.get(f"Effekt {lvl_name.lower()}", row.get(f"Effekt {prefix}"))),
            })

        card = PhaseCard(
            id=pid, steg=steg,
            namn=safe_str(row.get("Namn")),
            beskrivning=safe_str(row.get("Beskrivning")),
            levels=levels,
        )
        cards.setdefault(steg, []).append(card)

    return cards


# ── Penalty Cards ──

def _get_threshold_cols(row):
    """Find threshold column values, trying various encoding variants."""
    effects = []
    for suffix in ["_1_8", "_9_15", "_16_21", "_22_plus"]:
        val = ""
        for prefix in ["Troskel", "Tröskel", "Tr\xe4skel", "Tr\xf6skel"]:
            val = safe_str(row.get(f"{prefix}{suffix}"))
            if val:
                break
        effects.append(val)
    return effects


def load_penalty_cards() -> Dict[str, List[PenaltyCard]]:
    rows = read_csv(data_path("konsekvenskort"))
    cards: Dict[str, List[PenaltyCard]] = {}
    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = _get_threshold_cols(row)
        cards.setdefault(typ, []).append(PenaltyCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            namn=safe_str(row.get("Namn")),
            effects=effects,
            energiklass_projekt=safe_int(row.get("Energiklass_projekt")),
        ))
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


def load_garanti_cards() -> Dict[str, List[PenaltyCard]]:
    rows = read_csv(data_path("garantibesiktning"))
    cards: Dict[str, List[PenaltyCard]] = {}
    for row in rows:
        typ = safe_str(row.get("Typ"))
        if not typ:
            continue
        effects = _get_threshold_cols(row)
        cards.setdefault(typ, []).append(PenaltyCard(
            typ=typ, nr=safe_str(row.get("Nr")),
            namn=safe_str(row.get("Namn")),
            effects=effects,
        ))
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


# ── Phase 4 Data ──

def load_staff() -> List[Staff]:
    rows = read_csv(data_path("personal"))
    staff = []
    for row in rows:
        staff.append(Staff(
            roll=safe_str(row.get("Roll")),
            id=safe_str(row.get("ID")),
            namn=safe_str(row.get("Namn")),
            specialisering=safe_str(row.get("Specialisering")),
            kapacitet=safe_int(row.get("Kapacitet_proj"), 1),
            handelsemotstand=safe_str(row.get("Händelsemotstånd", row.get("H\x84ndelsemotst\x86nd"))),
            lon=safe_float(row.get("Lön_Mkr_per_kv", row.get("L\x94n_Mkr_per_kv"))),
            forhandling=safe_str(row.get("Förhandling", row.get("F\x94rhandling"))),
        ))
    return staff


def _parse_kompetenser(text: str) -> Dict[str, int]:
    """Parse competence string like 'LED:2, SAM:3' into dict."""
    result = {}
    if not text:
        return result
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            result[key.strip().upper()] = safe_int(val.strip())
    return result


def _parse_namnd_bonus(not_text: str) -> int:
    """Extract namnd bonus from Not field, e.g. 'nämndbonus +3' → 3."""
    import re
    m = re.search(r'n[äa]mndbonus\s*\+?\s*(\d+)', not_text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _parse_lindring(not_text: str) -> int:
    """Extract lindring bonus from Not field, e.g. 'Lindrar politikkort +2' → 2."""
    import re
    m = re.search(r'[Ll]indrar.*\+(\d+)', not_text)
    return int(m.group(1)) if m else 0


def _parse_erfarenhet(not_text: str) -> int:
    """Extract experience bonus from Not field, e.g. '+2 erfarenhet' → 2."""
    import re
    m = re.search(r'\+(\d+)\s*erfarenhet', not_text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def load_pc_ac_staff() -> Dict[str, list]:
    """Load PC and AC candidates from PU_PL_personal.csv."""
    fp = data_path("pu_pl_personal")
    if not os.path.exists(fp):
        return {"PC": [], "AC": []}
    rows = read_csv(fp)
    result = {"PC": [], "AC": []}
    for row in rows:
        roll = safe_str(row.get("Roll")).upper()
        if roll not in ("PC", "AC"):
            continue
        not_text = safe_str(row.get("Not"))
        kostnad_str = safe_str(row.get("Kostnad", row.get("Lön_Mkr_per_kv", "")))
        lon = safe_float(kostnad_str.replace(",", "."))

        kompetenser = {
            "LED": safe_int(row.get("LED")),
            "KOM": safe_int(row.get("KOM")),
            "SAM": safe_int(row.get("SAM")),
            "PRO": safe_int(row.get("PRO")),
            "ABM": safe_int(row.get("ABM")),
        }
        # Remove zero-value keys for cleaner display
        kompetenser = {k: v for k, v in kompetenser.items() if v > 0}

        entry = {
            "roll": roll,
            "id": safe_str(row.get("ID")),
            "namn": safe_str(row.get("Namn")),
            "specialisering": safe_str(row.get("Specialisering")),
            "handelsemotstand": safe_str(row.get("Händelsemotstand",
                                    row.get("Händelsemotstånd",
                                    row.get("H\x84ndelsemotst\x86nd", "")))),
            "lon": lon,
            "kompetenser": kompetenser,
            "not_text": not_text,
        }
        if roll == "PC":
            entry["namnd_bonus"] = _parse_namnd_bonus(not_text)
            entry["lindring"] = _parse_lindring(not_text)
        elif roll == "AC":
            entry["erfarenhet"] = _parse_erfarenhet(not_text)
        result[roll].append(entry)
    return result


def load_yield_cards() -> Dict[str, List[float]]:
    """Load yield change cards grouped by type (bostäder/kommersiellt)."""
    rows = read_csv(data_path("yield"))
    cards: Dict[str, List[float]] = {"bostader": [], "kommersiellt": []}
    for row in rows:
        titel = safe_str(row.get("Titel")).lower()
        # Ändring column may have % sign, e.g. "-1,50%"
        andring_str = safe_str(row.get("Ändring", row.get("\x84ndring", row.get("Ändring"))))
        andring_str = andring_str.replace("%", "").replace(",", ".").strip()
        try:
            andring = float(andring_str) if andring_str else 0.0
        except ValueError:
            andring = 0.0
        if "bost" in titel:
            cards["bostader"].append(andring)
        elif "kommersi" in titel:
            cards["kommersiellt"].append(andring)
    import random
    random.shuffle(cards["bostader"])
    random.shuffle(cards["kommersiellt"])
    return cards


def load_world_events() -> List[WorldEvent]:
    fp = data_path("omvarldskort")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    events = []
    for row in rows:
        events.append(WorldEvent(
            id=safe_str(row.get("ID")),
            rubrik=safe_str(row.get("Rubrik")),
            effekt_typ=safe_str(row.get("Effekt_typ")),
            effekt_mkr=safe_float(row.get("Effekt_Mkr")),
            poverkar=safe_str(row.get("Påverkar", row.get("P\x86verkar"))),
            beskrivning=safe_str(row.get("Beskrivning")),
        ))
    return events


def load_dd_cards() -> List[DDCard]:
    rows = read_csv(data_path("dd"))
    cards = []
    for row in rows:
        cards.append(DDCard(
            id=safe_str(row.get("ID")),
            typ=safe_str(row.get("Typ")),
            rubrik=safe_str(row.get("Rubrik")),
            effekt_mkr=safe_float(row.get("Effekt_Mkr")),
            beskrivning=safe_str(row.get("Beskrivning")),
        ))
    import random
    random.shuffle(cards)
    return cards


def load_mgmt_events() -> Dict[str, List[ManagementEvent]]:
    """Load management händelsekort grouped by type."""
    fp = data_path("handelsekort_forv")
    if not os.path.exists(fp):
        return {}
    enc = detect_encoding(fp)
    cards: Dict[str, List[ManagementEvent]] = {}
    with open(fp, "r", encoding=enc) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            eff_str = cols[3].strip().replace(",", ".") if len(cols) > 3 else "0"
            mild_eff_str = cols[6].strip().replace(",", ".") if len(cols) > 6 else "0"
            card = ManagementEvent(
                id=cols[0].strip(),
                typ=cols[1].strip(),
                rubrik=cols[2].strip(),
                effekt_mkr=float(eff_str) if eff_str else 0,
                mildring_roll=cols[4].strip() if len(cols) > 4 else "",
                mildring_spec=cols[5].strip() if len(cols) > 5 else "",
                mildring_effekt_mkr=float(mild_eff_str) if mild_eff_str else 0,
                trigger="Alla",
                beskrivning=cols[7].strip() if len(cols) > 7 else "",
            )
            cards.setdefault(card.typ, []).append(card)
    import random
    for pile in cards.values():
        random.shuffle(pile)
    return cards


# ── BYA/BTA Classification ──

def load_klass_table():
    """Load BYA/BTA class thresholds from CSV.

    CSV format: Klass;Typ;Kvm (e.g. "A;BTA;500-5000")
    Uses first set of 4 rows per type (BTA/BYA).
    """
    fp = data_path("btabya")
    if not os.path.exists(fp):
        models.BYA_CLASSES = [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]
        models.BTA_CLASSES = [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]
        return

    rows = read_csv(fp)
    bta_ranges = []
    bya_ranges = []
    bta_seen = set()
    bya_seen = set()

    for row in rows:
        klass = safe_str(row.get("Klass"))
        typ = safe_str(row.get("Typ")).upper()
        kvm_str = safe_str(row.get("Kvm"))
        if not klass or not kvm_str:
            continue

        # Only use first occurrence of each class per type
        if typ == "BTA" and klass not in bta_seen:
            bta_seen.add(klass)
            bta_ranges.append((klass, kvm_str))
        elif typ == "BYA" and klass not in bya_seen:
            bya_seen.add(klass)
            bya_ranges.append((klass, kvm_str))

    def parse_ranges(ranges):
        result = []
        for klass, range_str in ranges:
            range_str = range_str.replace(" ", "")
            if "-" in range_str and not range_str.startswith(">") and not range_str.startswith("<"):
                parts = range_str.split("-")
                try:
                    lo, hi = int(parts[0]), int(parts[1])
                    result.append((lo, hi, klass))
                except ValueError:
                    pass
            elif range_str.startswith(">"):
                try:
                    lo = int(range_str[1:]) + 1
                    result.append((lo, 999999, klass))
                except ValueError:
                    pass
            elif range_str.startswith("<"):
                try:
                    hi = int(range_str[1:])
                    result.append((0, hi, klass))
                except ValueError:
                    pass
        result.sort(key=lambda x: x[0])
        return result

    models.BTA_CLASSES = parse_ranges(bta_ranges) or [(0, 5000, "A"), (5001, 7000, "B"), (7001, 9000, "C"), (9001, 999999, "D")]
    models.BYA_CLASSES = parse_ranges(bya_ranges) or [(0, 6000, "A"), (6001, 8000, "B"), (8001, 10000, "C"), (10001, 999999, "D")]


# ── Puzzle Shapes ──

def load_shapes() -> Dict[str, List[List[int]]]:
    """Load polyomino shapes from shapes.json."""
    shapes_path = os.path.join(DATA_DIR, "shapes.json")
    if not os.path.exists(shapes_path):
        return {}
    with open(shapes_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Mark Expansion Pieces ──

def _generate_polyomino(n: int, rng=None) -> List[List[int]]:
    """Generate a random connected polyomino of n cells using random growth."""
    if rng is None:
        import random as rng
    cells = {(0, 0)}
    while len(cells) < n:
        # Find all neighbors of current cells
        neighbors = set()
        for r, c in cells:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (r + dr, c + dc)
                if nb not in cells:
                    neighbors.add(nb)
        # Pick a random neighbor
        chosen = rng.choice(list(neighbors))
        cells.add(chosen)
    # Normalize to origin
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return sorted([r - min_r, c - min_c] for r, c in cells)


def load_mark_expansions() -> List[dict]:
    """Load mark expansion piece definitions from CSV.
    Each piece has: {id, cell_count, cells: [[r,c],...]}.
    Generates random polyomino shapes since images don't exist yet.
    """
    fp = data_path("markexpansion")
    if not os.path.exists(fp):
        return []
    rows = read_csv(fp)
    import random
    rng = random.Random(42)  # Deterministic shapes
    pieces = []
    for i, row in enumerate(rows):
        n = safe_int(row.get("Antal rutor"), 3)
        pieces.append({
            "id": f"EXP-{i+1}",
            "cell_count": n,
            "cells": _generate_polyomino(n, rng),
        })
    rng.shuffle(pieces)
    return pieces


# ── Load All ──

class GameData:
    """Container for all loaded game data (read-only after init)."""

    def __init__(self):
        load_klass_table()
        self.projects = load_projects()
        self.politik, self.dialog = load_politik_dialog()
        self.special_cards = load_special_cards()
        self.suppliers = load_suppliers()
        self.organisations = load_organisations()
        self.planning_events = load_planning_events()
        self.supplier_requirements = load_supplier_requirements()
        self.external_support = load_external_support()
        self.phase_cards = load_phase_cards()
        self.penalty_cards = load_penalty_cards()
        self.garanti_cards = load_garanti_cards()
        self.staff = load_staff()
        _pc_ac = load_pc_ac_staff()
        self.pc_staff = _pc_ac["PC"]
        self.ac_staff = _pc_ac["AC"]
        self.yield_cards = load_yield_cards()
        self.world_events = load_world_events()
        self.dd_cards = load_dd_cards()
        self.mgmt_events = load_mgmt_events()
        self.shapes = load_shapes()
        self.mark_expansion_deck = load_mark_expansions()

        total_projects = sum(len(v) for v in self.projects.values())
        total_events = sum(len(v) for v in self.planning_events.values())
        total_phase_cards = sum(len(v) for v in self.phase_cards.values())
        total_penalty = sum(len(v) for v in self.penalty_cards.values())
        total_garanti = sum(len(v) for v in self.garanti_cards.values())
        total_mgmt = sum(len(v) for v in self.mgmt_events.values())
        total_yield = sum(len(v) for v in self.yield_cards.values())
        print(f"  Data loaded: {total_projects} projects, "
              f"{len(self.politik)} politik, {len(self.dialog)} dialog, "
              f"{sum(len(v) for v in self.suppliers.values())} suppliers, "
              f"{sum(len(v) for v in self.organisations.values())} orgs, "
              f"{total_events} planning events, "
              f"{total_phase_cards} faskort, {len(self.external_support)} kulturkort, "
              f"{total_penalty} konsekvenskort, {total_garanti} garantikort, "
              f"{len(self.staff)} personal, {total_yield} yield, "
              f"{len(self.world_events)} omvärld, {len(self.dd_cards)} DD, "
              f"{total_mgmt} händelsekort, "
              f"{len(self.shapes)} shapes")
