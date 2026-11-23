#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HUSBYGGSPELET – Fas 1 & 2: Projektutveckling & Projektplanering
Ett utbildningsspel om fastighetsutveckling och projektledning.
"""

import random
import csv
import os
import sys
import re
import platform
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ── Windows compatibility ──
if platform.system() == "Windows":
    # Enable UTF-8 output on Windows console
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass
    # Enable ANSI/Unicode in Windows terminal
    os.system("")

# Detect file encoding: try utf-8 first, fall back to cp1252
def detect_csv_encoding(filepath: str) -> str:
    """Try to detect encoding of a CSV file."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(500)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"

try:
    import openpyxl
except ImportError:
    print("Kräver openpyxl: pip install openpyxl")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
MARK_TOMT_KOSTNAD = 15  # Mkr for mark + tomt together
EXPANSION_KOSTNAD = 5   # Mkr per expansion
TOMT_CELLS = 16         # 4x4 grid
EXPANSION_MIN = 3
EXPANSION_MAX = 5
MAX_PROJECTS = 9        # Tetris-begränsning: max antal projekt
MAX_BTA = 12500         # Max BTA i kvm (fysisk tomtbegränsning)
START_Q_KRAV = 4
START_H_KRAV = 4
MIN_T = 8  # T (byggtid) kan aldrig gå under 8 månader

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = None  # Set at startup to OneDrive root

# Mapping: original filenames in their subfolders
DATA_FILES = {
    "projekt":         os.path.join("1. Projektutveckling", "PU_projekt.csv"),
    "politik_dialog":  os.path.join("1. Projektutveckling", "PU_politik_dialog.csv"),
    "special":         os.path.join("1. Projektutveckling", "PU_PolDia-speckort.csv"),
    "bradet":          os.path.join("1. Projektutveckling", "PU_Projektutvecklingsbrädet.xlsx"),
    "klass":           os.path.join("1. Projektutveckling", "PU_BYA_BTA_klass.xlsx"),
    "pc_ac_personal":  os.path.join("1. Projektutveckling", "PU_PL_personal.csv"),
    "leverantorer":    os.path.join("2. Planering", "PL_Leverantörer.csv"),
    "organisation":    os.path.join("2. Planering", "PL_Organisation.csv"),
    "handelsekort_pl": os.path.join("2. Planering", "PL_Händelsekort_planering.csv"),
    "faskort":         os.path.join("3. Genomförande", "GF_Faskort_utforande.csv"),
    "externstod":      os.path.join("3. Genomförande", "GF_kultur.csv"),
    "konsekvenskort":      os.path.join("3. Genomförande", "GF_konsekvenskort.csv"),
    "garantibesiktning": os.path.join("3. Genomförande", "GF_Garantibesiktning.csv"),
    # Phase 4: Förvaltning
    "personal":          os.path.join("4. Förvaltning", "F_personal.csv"),
    "yield":             os.path.join("4. Förvaltning", "F_yield.csv"),
    "dd":                os.path.join("4. Förvaltning", "F_DD.csv"),
    "omvarldskort":      os.path.join("4. Förvaltning", "F_omvärldskort.csv"),
    "handelsekort_forv": os.path.join("4. Förvaltning", "F_händelsekort.csv"),
    "hyreshojningar":    os.path.join("4. Förvaltning", "F_hyreshöjningar.csv"),
    "energiuppgradering": os.path.join("4. Förvaltning", "F_energiuppgradering.csv"),
}


def data_path(key: str) -> str:
    """Get full path to a data file by key."""
    return os.path.join(DATA_DIR, DATA_FILES[key])


# ─────────────────────────────────────────────
# BYA / BTA CLASS TABLE (loaded from Excel)
# ─────────────────────────────────────────────
# Each entry: (min_value, max_value, class_letter)
# Loaded dynamically at startup from PU_BYA_BTA_klass.xlsx
BYA_CLASSES: List[Tuple[int, int, str]] = []
BTA_CLASSES: List[Tuple[int, int, str]] = []


def safe_open_xlsx(filepath: str):
    """Open an xlsx file, copying to temp first if locked (OneDrive/Excel)."""
    import tempfile
    import shutil
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True)
        return wb
    except PermissionError:
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        shutil.copy2(filepath, tmp.name)
        wb = openpyxl.load_workbook(tmp.name, read_only=True)
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return wb


def safe_open_csv(filepath: str):
    """Open a CSV file for reading, copying to temp first if locked."""
    import tempfile
    import shutil
    enc = detect_csv_encoding(filepath)
    try:
        return open(filepath, "r", encoding=enc)
    except PermissionError:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w",
                                          encoding=enc)
        tmp.close()
        shutil.copy2(filepath, tmp.name)
        return open(tmp.name, "r", encoding=enc)


def load_klass_table() -> None:
    """Load BYA/BTA class thresholds from Excel.
    
    Parses ranges like '500-6000', '6001-8000', '>10000', '<10000'.
    Stores as sorted list of (min, max, class_letter) tuples.
    """
    global BYA_CLASSES, BTA_CLASSES

    filepath = data_path("klass")
    wb = safe_open_xlsx(filepath)
    ws = wb.active

    bya_ranges = []
    bta_ranges = []

    rows = list(ws.iter_rows(values_only=True))
    # Skip header row
    for row in rows[1:]:
        if not row[0]:
            continue
        klass = str(row[0]).strip()
        bya_str = str(row[1]).strip()
        bta_str = str(row[2]).strip()

        bya_ranges.append((klass, bya_str))
        bta_ranges.append((klass, bta_str))

    wb.close()

    def parse_ranges(ranges):
        result = []
        for klass, range_str in ranges:
            range_str = range_str.replace(" ", "")
            if "-" in range_str and not range_str.startswith(">") and not range_str.startswith("<"):
                parts = range_str.split("-")
                lo, hi = int(parts[0]), int(parts[1])
                result.append((lo, hi, klass))
            elif range_str.startswith(">"):
                lo = int(range_str[1:]) + 1
                result.append((lo, 999999, klass))
            elif range_str.startswith("<"):
                # Interpret '<X' as meaning everything below the lowest defined range
                # is already covered, so this must mean '>X'
                hi = int(range_str[1:])
                result.append((hi + 1, 999999, klass))
            else:
                try:
                    val = int(range_str)
                    result.append((val, val, klass))
                except ValueError:
                    pass
        # Sort by lower bound
        result.sort(key=lambda x: x[0])
        return result

    BYA_CLASSES = parse_ranges(bya_ranges)
    BTA_CLASSES = parse_ranges(bta_ranges)


def classify(value: int, table: List[Tuple[int, int, str]]) -> str:
    """Look up a value in a class table. Returns class letter."""
    for lo, hi, klass in table:
        if lo <= value <= hi:
            return klass
    # Below minimum → lowest class
    if table:
        return table[0][2]
    return "D"

DICE_MAP = {"D4": 4, "D6": 6, "D8": 8, "D10": 10, "D12": 12, "D20": 20}

PROJECT_TYPES = ["BRF", "FÖRSKOLOR", "LOKAL", "KONTOR", "Hyresrätt"]
TYPE_CODES = {"BRF": "B", "FÖRSKOLOR": "F", "LOKAL": "L", "KONTOR": "K", "Hyresrätt": "H"}
CODE_TO_TYPES = {
    "B": ["BRF"], "F": ["FÖRSKOLOR"], "L": ["LOKAL"],
    "K": ["KONTOR"], "H": ["Hyresrätt"],
}

# ─────────────────────────────────────────────
# DYNAMIC D20 THRESHOLDS
# ─────────────────────────────────────────────
# Parsed from CSV column headers like "Tröskel_1_8", "Tröskel_9_15", "Tröskel_22_plus"
# Stored as list of upper bounds: e.g. [8, 15, 21, 9999]
# Default matches original: [5, 17, 20, 9999]
D20_THRESHOLDS: List[int] = [5, 17, 20, 9999]


def parse_threshold_headers(headers: List[str]) -> List[int]:
    """Parse threshold columns from CSV headers to extract upper bounds.

    Handles formats like:
      Tröskel_1_5, Tröskel_6_17, Tröskel_18_20, Tröskel_21_plus
      Tröskel_1_8, Tröskel_9_15, Tröskel_16_21, Tröskel_22_plus
    Returns: [5, 17, 20, 9999] or [8, 15, 21, 9999] etc.
    """
    threshold_cols = [h for h in headers if h.lower().startswith("tröskel") or
                      h.lower().startswith("troskel") or
                      h.lower().startswith("troeskel")]
    if len(threshold_cols) < 4:
        return D20_THRESHOLDS  # fallback

    bounds = []
    for col in threshold_cols:
        # Extract numbers from name like "Tröskel_1_8" or "Tröskel_22_plus"
        parts = col.split("_")
        if "plus" in parts[-1].lower():
            bounds.append(9999)
        elif len(parts) >= 3:
            try:
                bounds.append(int(parts[-1]))
            except ValueError:
                bounds.append(9999)
        else:
            bounds.append(9999)

    return bounds


def threshold_lookup(value: int, effects: List[str]) -> str:
    """Look up which effect applies for a given D20+exp value."""
    for i, upper in enumerate(D20_THRESHOLDS):
        if value <= upper and i < len(effects):
            return effects[i]
    # Above all thresholds → last effect
    return effects[-1] if effects else ""


# ─────────────────────────────────────────────
# DICE
# ─────────────────────────────────────────────
def roll(die: str) -> int:
    """Roll a die like 'D6' or 'D12'. Returns integer result."""
    sides = DICE_MAP.get(die.upper().strip())
    if not sides:
        raise ValueError(f"Okänd tärning: {die}")
    return random.randint(1, sides)


def roll_display(die: str, label: str = "") -> int:
    """Roll a die and display the result."""
    result = roll(die)
    prefix = f"{label}: " if label else ""
    print(f"  🎲 {prefix}Slår {die} → {result}")
    return result


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────
@dataclass
class Project:
    id: str
    namn: str
    typ: str
    forekomst: int
    kostnad: int        # Programkostnad, Mkr
    formfaktor: int
    bta: int            # kvm
    anskaffning: int    # Mkr (Anskaffningskostnad)
    rorlig_intakt: str  # e.g. "D12"
    kvalitet: int
    hallbarhet: int
    tid: int
    riskbuffert: int
    antal_krav: int
    namndbeslut: int    # Must roll >= this on D20
    energiklass: str
    driftnetto: float   # Mkr/kvartal
    marknadsvarde: int  # Mkr

    def display_short(self) -> str:
        return (f"{self.namn} ({self.typ}) | BTA:{self.bta} kvm | "
                f"Kostnad:{self.kostnad} Mkr | Anskaff:{self.anskaffning} MV:{self.marknadsvarde} Mkr | "
                f"Q:{self.kvalitet} H:{self.hallbarhet} T:{self.tid} | "
                f"Nämnd:≥{self.namndbeslut} | Form:{self.formfaktor}")

    def display_full(self) -> str:
        lines = [
            f"  ┌─ {self.namn} ({self.id}) ─────────────────",
            f"  │ Typ: {self.typ}",
            f"  │ Programkostnad: {self.kostnad} Mkr",
            f"  │ Anskaffning: {self.anskaffning} Mkr | Marknadsvärde: {self.marknadsvarde} Mkr",
            f"  │ Q: {self.kvalitet}  H: {self.hallbarhet}  T: {self.tid}",
            f"  │ BTA: {self.bta} kvm  Formfaktor: {self.formfaktor}",
            f"  │ Nämnd: ≥{self.namndbeslut}  Riskbuffert: {self.riskbuffert}",
            f"  │ Energiklass: {self.energiklass}",
            f"  │ Driftnetto: {self.driftnetto} Mkr/kvartal",
            f"  │ Marknadsvärde: {self.marknadsvarde} Mkr",
            f"  └──────────────────────────────────",
        ]
        return "\n".join(lines)


@dataclass
class BoardSquare:
    nr: int
    ruta: str
    handelse: str


@dataclass
class PolitikDialogCard:
    typ: str         # "Politik" or "Dialog"
    nr: str
    rubrik: str
    text: str
    effects: Dict[str, str]  # range -> effect text
    is_special: bool = False
    special_target: str = ""
    special_effect: str = ""


@dataclass
class Supplier:
    """A leverantör card (e.g. MARK nivå 2)."""
    namn: str           # e.g. "MARK"
    niva: int           # 1-4
    beskrivning: str    # e.g. "Betong etablerat" - matches project requirements
    beror_av: str       # "BYA" or "BTA"
    klass_priser: Dict[str, int]  # {"A": 10, "B": 14, ...}
    q: int
    h: int
    t: int              # T_mån
    erfarenhet: int
    kompetenser: Dict[str, int]   # STA, KOM, SAM, NOG, INN, ABM

    def kostnad(self, klass: str) -> int:
        """Get cost for a given BYA/BTA class."""
        return self.klass_priser.get(klass, 0)

    def display(self, klass: str) -> str:
        pris = self.kostnad(klass)
        komp_str = ", ".join(f"{k}:{v}" for k, v in self.kompetenser.items() if v > 0)
        return (f"Nivå {self.niva}: {self.beskrivning} | "
                f"Pris: {pris} Mkr ({self.beror_av}-klass {klass}) | "
                f"Q:{self.q:+d} H:{self.h:+d} T:{self.t:+d} | "
                f"Erf:{self.erfarenhet:+d} | {komp_str}")


@dataclass
class Organisation:
    """An organisation card (e.g. Operativt team nivå 3)."""
    namn: str
    niva: int
    kostnad_mkr: int
    q: int
    h: int
    t: int
    erfarenhet: int
    riskbuffert: int
    kompetenser: Dict[str, int]

    def display(self) -> str:
        komp_str = ", ".join(f"{k}:{v}" for k, v in self.kompetenser.items() if v > 0)
        rb_str = f" | Rb:{self.riskbuffert}" if self.riskbuffert else ""
        return (f"Nivå {self.niva} | Kostnad: {self.kostnad_mkr} Mkr | "
                f"Q:{self.q:+d} H:{self.h:+d} T:{self.t:+d} | "
                f"Erf:{self.erfarenhet:+d}{rb_str} | {komp_str}")


@dataclass
class PlanningEventCard:
    """A händelsekort for the planning phase."""
    kort_id: str        # e.g. "MARK", "OPERATIVT TEAM"
    namn: str
    typ: str            # "Negativt", "Neutralt", "Positivt", "Positivt (B)ÄTA"
    fas: str
    svarighetsgrad: str
    beskrivning: str
    summering: str       # Which cards contribute experience
    trigger: str         # "Alla", "STAPLAD", "KOMPLEX", "BOSTÄDER", combinations
    klassvillkor: str    # "Alla", "Skalad", "Skalad (BYA)", "Skalad (BTA)", "BTA Klass C+"
    effects: List[str] = field(default_factory=list)  # 4 effect texts, ordered worst→best

    def get_effect(self, roll_plus_exp: int) -> str:
        """Get effect text based on D20 + experience, using dynamic thresholds."""
        return threshold_lookup(roll_plus_exp, self.effects)

    def display_short(self) -> str:
        return f"[{self.typ}] {self.namn}: {self.beskrivning[:60]}"


@dataclass
class PhaseCard:
    """A faskort for the execution phase (Fas 1-8 of genomförande)."""
    id: str             # e.g. "PG_01_A"
    steg: int           # 1-8
    namn: str
    beskrivning: str
    # Four levels, each with requirements per trigger (B/S/K) and an effect
    # Levels: 0=Negativt, 1=Neutralt, 2=Positivt, 3=Bonus
    levels: List[Dict]  # [{req_b, req_s, req_k, effect}, ...]

    def display_for_trigger(self, trigger: str) -> None:
        """Display the card's levels for a given trigger type."""
        col = {"BOSTÄDER": "req_b", "STAPLAD": "req_s", "KOMPLEX": "req_k"}[trigger]
        level_names = ["Negativt", "Neutralt", "Positivt", "Bonus"]
        for i, level in enumerate(self.levels):
            req = level[col]
            effect = level["effect"]
            skip = req.strip() == "— (skippa)" or req.strip() == ""
            if skip:
                continue
            if req.strip() == "—":
                req_display = "(ingen insats krävs)"
            else:
                req_display = req
            print(f"    {i + 1}. [{level_names[i]}] Krav: {req_display} → Effekt: {effect}")


@dataclass
class ExternalSupport:
    """An företagskultur card with multiple competency values.
    Total points = 6, max 4 per parameter."""
    kort_id: str
    namn: str
    kompetenser: Dict[str, int]  # STA, KOM, SAM, NOG, INN, ABM values

    def display(self) -> str:
        vals = ", ".join(f"{k}:{v}" for k, v in self.kompetenser.items() if v > 0)
        return f"{self.namn} ({vals})"


@dataclass
class PenaltyCard:
    """A konsekvenskort (T/Q/H penalty) – resolved with D20 + experience."""
    typ: str            # T, Q, H
    nr: str
    namn: str
    effects: List[str]  # 4 effect texts matching D20_THRESHOLDS
    energiklass_projekt: int  # Number of projects to downgrade (on worst outcome)

    def get_effect(self, roll_plus_exp: int) -> Tuple[str, int]:
        """Get effect text and energy class downgrades for a roll.
        Energy class downgrade only on worst tier (tier 0).
        """
        for i, upper in enumerate(D20_THRESHOLDS):
            if roll_plus_exp <= upper and i < len(self.effects):
                ek_down = self.energiklass_projekt if i == 0 else 0
                return self.effects[i], ek_down
        return self.effects[-1] if self.effects else "", 0


# ── Phase 4: Förvaltning data classes ──

@dataclass
class Staff:
    """A staff member (FC = Fastighetschef, FS = Fastighetsskötare)."""
    roll: str           # FC or FS
    id: str
    namn: str
    specialisering: str  # Bostäder, Kommersiellt, Samhälle, Teknisk, Generalist
    kapacitet: int       # Number of properties they can manage
    handelsemotstand: str  # Types of events they can mitigate
    lon_mkr_kv: float    # Salary per quarter
    forhandling: str     # Dice for rent negotiation (FC only), e.g. "D8"


@dataclass
class ManagementEvent:
    """A händelsekort for property management phase."""
    id: str
    typ: str            # HR, FSK, LOK, KON, ALLA
    rubrik: str
    effekt_mkr: float
    mildring_roll: str   # FC or FS (empty = no mitigation)
    mildring_spec: str   # Specialisering required
    mildring_effekt_mkr: float
    trigger: str         # Alla, KOMPLEX, STAPLAD, BTA_C+, EK_DEF, EK_ABC
    beskrivning: str


@dataclass
class WorldEvent:
    """An omvärldskort for the management phase."""
    id: str
    rubrik: str
    effekt_typ: str      # kostnad_alla, intäkt_alla, kostnad_per_ek, etc.
    effekt_mkr: float
    paverkar: str
    beskrivning: str


@dataclass
class DDCard:
    """A Due Diligence card for property acquisitions."""
    id: str
    typ: str
    rubrik: str
    effekt_mkr: float
    beskrivning: str


# Mapping from project type to event card type
PROJECT_TYPE_TO_EVENT = {
    "Hyresrätt": "HR",
    "FÖRSKOLOR": "FSK",
    "LOKAL": "LOK",
    "KONTOR": "KON",
}

# Mapping from event card type to project types
EVENT_TYPE_TO_PROJECTS = {
    "HR": ["Hyresrätt"],
    "FSK": ["FÖRSKOLOR"],
    "LOK": ["LOKAL"],
    "KON": ["KONTOR"],
    "ALLA": ["Hyresrätt", "FÖRSKOLOR", "LOKAL", "KONTOR"],
}

YIELD_START_BOSTADER = 4.0   # %
YIELD_START_KOMMERSIELLT = 5.0  # %
LOAN_RATIO = 0.70  # 70% lån

# ── Straffaktor för Q/H/T-avvikelser vid Skede 2-slut ──
# n = q-avvikelse + h-avvikelse + t-avvikelse, multiplikatorn appliceras på slutpoängen.
# Tabell för n = 0..10, sedan -1 procentenhet per ytterligare avvikelse (golv 0).
PENALTY_TABLE = [100, 90, 82, 75, 70, 65, 61, 58, 55, 52, 50]
T_KRAV = 12

def qht_penalty_n(player) -> int:
    """Antal steg avvikelse från Q-, H- och T-kraven vid Skede 2:s slut.
    Mäts som summan av Q-avvikelse + H-avvikelse + T-avvikelse, alla räknade
    bara som missar (0 om kravet uppfylls eller överträffas)."""
    q_dev = max(0, player.q_krav - player.snap_exec_q)
    h_dev = max(0, player.h_krav - player.snap_exec_h)
    t_dev = max(0, player.snap_exec_t - T_KRAV)
    return q_dev + h_dev + t_dev

def qht_penalty_factor(n: int) -> float:
    """Multiplikator (0..1) som appliceras på slutpoängen.
    n=0 → 1.00, n=10 → 0.50, sedan -0.01 per ytterligare avvikelse, golv 0."""
    if n <= 10:
        return PENALTY_TABLE[n] / 100.0
    return max(0.0, (50 - (n - 10)) / 100.0)

# Which project types are "bostäder" vs "kommersiellt" for yield
BOSTADER_TYPES = ["Hyresrätt"]
KOMMERSIELLT_TYPES = ["FÖRSKOLOR", "LOKAL", "KONTOR"]


@dataclass
class ProjektArbetschef:
    """Projektchef (PC) or Arbetschef (AC)."""
    roll: str           # "PC" or "AC"
    id: str             # "PC-1", "AC-3" etc.
    namn: str
    specialisering: str
    bonus: int          # PC: lindring +N på kort. AC: +N erfarenhet
    motstand: str       # Vad de lindrar (display text)
    kostnad: float      # Mkr (0 = gratis)
    forhandling: str    # PC: nämndbonus. AC: kompetenspoäng
    not_text: str
    # Parsed fields:
    kompetenser: Dict[str, int] = field(default_factory=dict)  # STA, KOM, SAM, NOG, INN, ABM
    namnd_bonus: int = 0  # PC only: bonus on nämnd D20
    q_bonus: int = 0      # +Q from this person
    h_bonus: int = 0      # +H from this person
    t_bonus: int = 0      # -T from this person (positive = months saved)
    rb_bonus: int = 2     # Riskbuffertar (always 2)

    def display(self) -> str:
        parts = [f"{self.namn} ({self.specialisering})"]
        if self.roll == "PC":
            parts.append(f"Lindring +{self.bonus}")
            if self.namnd_bonus > 0:
                parts.append(f"Nämnd +{self.namnd_bonus}")
            bonuses = []
            if self.q_bonus: bonuses.append(f"+{self.q_bonus} Q")
            if self.h_bonus: bonuses.append(f"+{self.h_bonus} H")
            if self.t_bonus: bonuses.append(f"-{self.t_bonus} T")
            if bonuses: parts.append(", ".join(bonuses))
            komp = ", ".join(f"{k}:{v}" for k, v in self.kompetenser.items() if v > 0)
            if komp: parts.append(komp)
        else:
            parts.append(f"+{self.bonus} erf")
            komp = ", ".join(f"{k}:{v}" for k, v in self.kompetenser.items() if v > 0)
            if komp: parts.append(komp)
            bonuses = []
            if self.q_bonus: bonuses.append(f"+{self.q_bonus} Q")
            if self.h_bonus: bonuses.append(f"+{self.h_bonus} H")
            if self.t_bonus: bonuses.append(f"-{self.t_bonus} T")
            if bonuses: parts.append(", ".join(bonuses))
        parts.append(f"{self.rb_bonus} Rb")
        return " | ".join(parts)


@dataclass
class Player:
    name: str
    position: int = 1
    laps: int = 0
    projects: List[Project] = field(default_factory=list)
    riskbuffertar: int = 0
    pending_riskbuffertar: int = 0   # From projects, released after nämndbeslut
    q_krav: int = START_Q_KRAV
    h_krav: int = START_H_KRAV
    t_bonus: int = 0             # Months bonus from Rb spending (reduces pl_t)
    eget_kapital: float = 0.0
    abt_budget: float = 0.0     # ABT contract budget (85% of net after Fas 1 costs)
    abt_start: float = 0.0      # Initial ABT budget (for TG calculation)
    abt_overflow: float = 0.0   # Total ABT overflow to EK (tracks overspend)
    abt_borrowing_cost: float = 0.0  # Total cost of moderbolagstillskott (5 Mkr per 100)
    abt_loans_net: float = 0.0       # Total net loan money that went into ABT
    mark_expansions: int = 0       # total cells from expansions
    expansion_events: int = 0       # number of expansion events (each costs 5 Mkr)
    has_mark_tomt: bool = False
    total_revenue: float = 0.0
    projektchef: "ProjektArbetschef" = None      # PC chosen in Fas 1a
    arbetschef: "ProjektArbetschef" = None        # AC chosen in Fas 2

    # ── Phase 2: Projektplanering ──
    pl_q: int = 0               # Quality achieved in planning
    pl_h: int = 0               # Sustainability achieved in planning
    pl_t: int = 0               # Time (months), target ≤ 12
    pl_kostnad: float = 0.0     # Total planning costs (Mkr)
    pl_suppliers: Dict[str, "Supplier"] = field(default_factory=dict)   # chosen suppliers by type
    pl_orgs: Dict[str, "Organisation"] = field(default_factory=dict)    # chosen orgs by type

    # ── Phase 3: Projektgenomförande ──
    used_supplier_keys: List[str] = field(default_factory=list)  # supplier types already played as cards
    used_org_keys: List[str] = field(default_factory=list)       # org types already played as cards
    external_hand: List["ExternalSupport"] = field(default_factory=list)  # bought external support
    used_external: List["ExternalSupport"] = field(default_factory=list)  # played external support
    projekt_energiklass: Dict[str, str] = field(default_factory=dict)  # project namn -> current energiklass

    # ── Snapshots for reporting ──
    snap_plan_q: int = 0      # Q after planning
    snap_plan_h: int = 0      # H after planning
    snap_plan_t: int = 0      # T after planning
    snap_exec_q: int = 0      # Q after execution
    snap_exec_h: int = 0      # H after execution
    snap_exec_t: int = 0      # T after execution

    # ── Phase 4: Förvaltning ──
    staff: List["Staff"] = field(default_factory=list)       # hired staff
    fastigheter: List["Project"] = field(default_factory=list)  # managed properties (non-BRF)
    driftnetto_bonus: Dict[str, float] = field(default_factory=dict)  # per-property bonus from events

    @property
    def total_bta(self) -> int:
        return sum(p.bta for p in self.projects)

    @property
    def total_bya(self) -> int:
        return sum(p.formfaktor * 250 for p in self.projects)

    @property
    def total_formfaktor(self) -> int:
        return sum(p.formfaktor for p in self.projects)

    @property
    def available_cells(self) -> int:
        base = TOMT_CELLS
        return base + self.mark_expansions

    @property
    def krav_summa(self) -> int:
        return self.q_krav + self.h_krav

    def bta_klass(self) -> str:
        return classify(self.total_bta, BTA_CLASSES)

    def bya_klass(self) -> str:
        return classify(self.total_bya, BYA_CLASSES)

    def total_erfarenhet(self) -> int:
        """Sum experience from all chosen suppliers and organisations."""
        exp = sum(s.erfarenhet for s in self.pl_suppliers.values())
        exp += sum(o.erfarenhet for o in self.pl_orgs.values())
        return exp

    def relevant_erfarenhet(self, summering: str) -> int:
        """Calculate experience from only relevant cards based on summering text."""
        exp = 0
        summering_upper = summering.upper()

        # Check each chosen supplier
        for namn, s in self.pl_suppliers.items():
            # Direct match or partial match
            if namn.upper() in summering_upper:
                exp += s.erfarenhet
            # Handle "(om vald)" references
            elif f"{namn.upper()} (OM VALD)" in summering_upper:
                exp += s.erfarenhet

        # Check each chosen organisation
        for namn, o in self.pl_orgs.items():
            if namn.lower() in summering.lower():
                exp += o.erfarenhet

        # Arbetschef ger permanent erfarenhetsbonus
        if self.arbetschef:
            exp += self.arbetschef.bonus

        return exp

    def kvarter_trigger(self) -> str:
        """Determine trigger type based on project composition.
        
        BOSTÄDER: only housing (BRF, Hyresrätt)
        STAPLAD: housing + one other type
        KOMPLEX: housing + two or more other types
        """
        typer = set(p.typ for p in self.projects)
        bostader = typer & {"BRF", "Hyresrätt"}
        andra = typer - {"BRF", "Hyresrätt"}

        if not bostader:
            # No housing at all - count as STAPLAD if mixed, else base
            return "STAPLAD" if len(andra) >= 2 else "STAPLAD" if len(andra) > 0 else "BOSTÄDER"
        if len(andra) == 0:
            return "BOSTÄDER"
        elif len(andra) == 1:
            return "STAPLAD"
        else:
            return "KOMPLEX"

    def card_is_eligible(self, card: "PlanningEventCard") -> bool:
        """Check if a planning event card's trigger matches this player's kvarter."""
        trigger = card.trigger.upper()
        if trigger == "ALLA":
            return True

        player_trigger = self.kvarter_trigger()
        triggers = [t.strip() for t in trigger.split(",")]

        # Card activates if player's trigger matches any of the card's triggers
        for t in triggers:
            if t == player_trigger:
                return True
            # KOMPLEX includes STAPLAD cards too
            if t == "STAPLAD" and player_trigger == "KOMPLEX":
                return True

        return False


# ─────────────────────────────────────────────
# ABT OVERFLOW – Moderbolagstillskott
# ─────────────────────────────────────────────
BORROWING_CHUNK = 100    # Mkr per lån
BORROWING_COST = 5       # Mkr kostnad per lån (5% av 100)
BORROWING_NET = BORROWING_CHUNK - BORROWING_COST  # 95 Mkr netto per lån

def handle_abt_overflow(player: Player, verbose: bool = True) -> float:
    """Om ABT < 0, låna i steg om 100 Mkr med 5 Mkr kostnad per steg.
    
    Mekaniken: Du lånar 100, betalar 5 i avgift, får 95 netto.
    Den netto-summan går in i ABT-budgeten för att täcka underskottet.
    Avgiften belastar EK.
    
    Returnerar totalt lånat belopp (brutto).
    """
    if player.abt_budget >= 0:
        return 0.0

    deficit = abs(player.abt_budget)
    # Antal lån: tillräckligt många netto-95 för att täcka underskottet
    import math
    n_loans = math.ceil(deficit / BORROWING_NET)
    gross = n_loans * BORROWING_CHUNK
    cost = n_loans * BORROWING_COST
    net = n_loans * BORROWING_NET            # Vad som faktiskt kommer in

    # Bokför
    player.abt_overflow += deficit            # Spåra verklig överförbrukning
    player.abt_borrowing_cost += cost         # Spåra lånekostnader
    player.abt_loans_net += net               # Spåra netto lån i ABT
    player.abt_budget = net - deficit         # Kvar i ABT efter att täcka underskott
    player.eget_kapital -= cost               # EK betalar BARA avgiften (5 per 100)

    if verbose:
        print(f"      ⚠ ABT slut! Moderbolagstillskott: {n_loans}×{BORROWING_CHUNK} Mkr "
              f"(avgift {cost} Mkr, netto {net} Mkr)")
        print(f"        ABT: {player.abt_budget:.1f} Mkr | EK: {player.eget_kapital:.1f} Mkr")

    return gross


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
def load_projects() -> Dict[str, List[Project]]:
    """Load projects from CSV and organize into stacks by type.

    Uses header-based column lookup for robustness against column reordering.
    """
    filepath = data_path("projekt")
    stacks: Dict[str, List[Project]] = {t: [] for t in PROJECT_TYPES}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(reader)]

        # Build column index map from header names
        col = {name: i for i, name in enumerate(header)}

        for cols in reader:
            if len(cols) < 15 or not cols[0].strip():
                continue

            namn = cols[col["Namn"]].strip()
            typ = cols[col["Typ"]].strip()
            proj_id = cols[col.get("Namn2", 1)].strip()  # Namn2 used as project ID

            if typ not in PROJECT_TYPES:
                continue

            def safe_int(idx, default=0):
                try:
                    return int(float(cols[idx].strip().replace(",", ".")))
                except (ValueError, IndexError):
                    return default

            def safe_float(idx, default=0.0):
                try:
                    return float(cols[idx].strip().replace(",", "."))
                except (ValueError, IndexError):
                    return default

            forekomst = safe_int(col.get("Förekomst", 4), 1)

            project = Project(
                id=proj_id,
                namn=namn,
                typ=typ,
                forekomst=forekomst,
                kostnad=safe_int(col.get("Kostnad", 5)),
                formfaktor=safe_int(col.get("Formfaktor", 6), 1),
                bta=safe_int(col.get("BTA", 8)),
                anskaffning=safe_int(col.get("Anskaffning", 9)),
                rorlig_intakt=cols[col.get("Rörligt marknadsvärde", 11)].strip() if len(cols) > col.get("Rörligt marknadsvärde", 11) else "D6",
                kvalitet=safe_int(col.get("Kvalitet", 12)),
                hallbarhet=safe_int(col.get("Hållbarhet", 13)),
                tid=safe_int(col.get("Tid", 14)),
                riskbuffert=safe_int(col.get("Riskbuffert", 15)),
                antal_krav=safe_int(col.get("Antal krav", 16)),
                namndbeslut=safe_int(col.get("Nämndbeslut", 17), 1),
                energiklass=cols[col.get("Energiklass", 33)].strip() if len(cols) > col.get("Energiklass", 33) else "C",
                driftnetto=safe_float(col.get("Driftnetto", 35)),
                marknadsvarde=safe_int(col.get("Marknadsvärde", 10)),
            )

            # Create copies based on förekomst
            for _ in range(forekomst):
                stacks[typ].append(Project(**vars(project)))

    # Shuffle each stack
    for typ in stacks:
        random.shuffle(stacks[typ])

    return stacks


def load_pc_ac() -> Dict[str, List[ProjektArbetschef]]:
    """Load Projektchef (PC) and Arbetschef (AC) from CSV.

    Columns: Roll;ID;Namn;Specialisering;Rb;Lindring;Händelsemotstand;Nämnd;
             Q;H;T;Erfarenhet;STA;KOM;SAM;NOG;INN;ABM;Beskrivning;...
    """
    filepath = data_path("pc_ac_personal")
    result = {"PC": [], "AC": []}

    try:
        with safe_open_csv(filepath) as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader)

            for cols in reader:
                if len(cols) < 17 or not cols[0].strip():
                    continue

                roll = cols[0].strip()
                if roll not in ("PC", "AC"):
                    continue

                def si(idx, default=0):
                    try: return int(float(cols[idx].strip().replace(",", ".")))
                    except (ValueError, IndexError): return default

                kompetenser = {}
                for k, idx in [("STA", 12), ("KOM", 13), ("SAM", 14), ("NOG", 15), ("INN", 16), ("ABM", 17)]:
                    v = si(idx)
                    if v > 0:
                        kompetenser[k] = v

                person = ProjektArbetschef(
                    roll=roll,
                    id=cols[1].strip(),
                    namn=cols[2].strip(),
                    specialisering=cols[3].strip(),
                    bonus=si(5) if roll == "PC" else si(11),  # Lindring (PC) / Erfarenhet (AC)
                    motstand=cols[6].strip() if len(cols) > 6 else "",
                    kostnad=0,
                    forhandling="",
                    not_text=cols[18].strip() if len(cols) > 18 else "",
                    kompetenser=kompetenser,
                    namnd_bonus=si(7),
                    q_bonus=si(8),
                    h_bonus=si(9),
                    t_bonus=si(10),
                    rb_bonus=si(4),
                )
                result[roll].append(person)
    except FileNotFoundError:
        pass  # Optional file - game works without it

    return result


def load_board() -> List[BoardSquare]:
    """Load board squares from Excel data (hardcoded from file)."""
    squares = [
        BoardSquare(1, "Stadsbyggnadskontoret", "Ta eller byt markexpansion."),
        BoardSquare(2, "Stjärna", "Ta en riskbuffert"),
        BoardSquare(3, "F", "Ta ett förskoleprojekt."),
        BoardSquare(4, "Glödlampa", "Dra ett dialogkort"),
        BoardSquare(5, "Frågetecken", "Dra ett Politikkort"),
        BoardSquare(6, "H", "Ta ett HR-projekt."),
        BoardSquare(7, "Stadshuset", "Ta, lämna tillbaka eller byt ett projekt"),
        BoardSquare(8, "B", "Ta ett BRF-projekt."),
        BoardSquare(9, "Glödlampa", "Dra ett dialogkort"),
        BoardSquare(10, "L", "Ta ett lokalprojekt."),
        BoardSquare(11, "Stjärna", "Ta en riskbuffert"),
        BoardSquare(12, "K", "Ta ett kontorsprojekt."),
        BoardSquare(13, "Länsstyrelsen", "Minska hållbarhetskravet med 2"),
        BoardSquare(14, "F", "Ta ett förskoleprojekt."),
        BoardSquare(15, "Frågetecken", "Dra ett Politikkort"),
        BoardSquare(16, "Glödlampa", "Dra ett dialogkort"),
        BoardSquare(17, "H", "Ta ett HR-projekt."),
        BoardSquare(18, "B, K", "Ta en av projekttyperna (BRF eller Kontor)."),
        BoardSquare(19, "Skönhetsrådet", "Minska kvalitetskravet med 2"),
        BoardSquare(20, "L, H", "Ta en av projekttyperna (Lokal eller Hyresrätt)."),
        BoardSquare(21, "Frågetecken", "Dra ett Politikkort"),
        BoardSquare(22, "K, B", "Ta en av projekttyperna (Kontor eller BRF)."),
        BoardSquare(23, "Stjärna", "Ta en riskbuffert"),
        BoardSquare(24, "L, F", "Ta en av projekttyperna (Lokal eller Förskola)."),
    ]
    return squares


def load_politik_dialog() -> Tuple[List[PolitikDialogCard], List[PolitikDialogCard]]:
    """Load Politik and Dialog card decks."""
    politik_deck = []
    dialog_deck = []

    # Regular cards
    filepath = data_path("politik_dialog")
    with safe_open_csv(filepath) as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            typ = row.get("Typ", "").strip()
            card = PolitikDialogCard(
                typ=typ,
                nr=row.get("Nr", "").strip(),
                rubrik=row.get("Rubrik", "").strip(),
                text=row.get("Text", "").strip(),
                effects={
                    "1": row.get("1", "").strip(),
                    "2-11": row.get("02-11", "").strip(),
                    "12-15": row.get("12-15", "").strip(),
                    "16-19": row.get("16-19", "").strip(),
                    "20": row.get("20", "").strip(),
                },
            )
            if typ == "Politik":
                politik_deck.append(card)
            elif typ == "Dialog":
                dialog_deck.append(card)

    # Special cards
    filepath = data_path("special")
    with safe_open_csv(filepath) as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            typ_raw = row.get("Typ", "").strip()
            card = PolitikDialogCard(
                typ="Politik" if "Politik" in typ_raw else "Dialog",
                nr=row.get("Nr", "").strip(),
                rubrik=row.get("Rubrik", "").strip(),
                text=row.get("Text", "").strip(),
                effects={},
                is_special=True,
                special_target=row.get("Påverkar", "").strip(),
                special_effect=row.get("Effekt", "").strip(),
            )
            if "Politik" in typ_raw:
                politik_deck.append(card)
            else:
                dialog_deck.append(card)

    random.shuffle(politik_deck)
    random.shuffle(dialog_deck)
    return politik_deck, dialog_deck


def load_suppliers() -> Dict[str, List[Supplier]]:
    """Load all supplier cards grouped by type."""
    filepath = data_path("leverantorer")
    suppliers: Dict[str, List[Supplier]] = {}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        for cols in reader:
            if not cols[0].strip():
                continue
            namn = cols[0].strip()

            def safe_int(idx, default=0):
                try:
                    return int(cols[idx].strip()) if cols[idx].strip() else default
                except (ValueError, IndexError):
                    return default

            kompetenser = {}
            for key, idx in [("STA", 12), ("KOM", 13), ("SAM", 14), ("NOG", 15), ("INN", 16), ("ABM", 17)]:
                v = safe_int(idx, 0)
                if v:
                    kompetenser[key] = v

            s = Supplier(
                namn=namn,
                niva=safe_int(1),
                beskrivning=cols[2].strip() if len(cols) > 2 else "",
                beror_av=cols[3].strip() if len(cols) > 3 else "BTA",
                klass_priser={
                    "A": safe_int(4), "B": safe_int(5),
                    "C": safe_int(6), "D": safe_int(7),
                },
                q=safe_int(8), h=safe_int(9), t=safe_int(10),
                erfarenhet=safe_int(11),
                kompetenser=kompetenser,
            )
            if namn not in suppliers:
                suppliers[namn] = []
            suppliers[namn].append(s)

    # Sort each group by nivå
    for namn in suppliers:
        suppliers[namn].sort(key=lambda x: x.niva)

    return suppliers


def load_organisations() -> Dict[str, List[Organisation]]:
    """Load all organisation cards grouped by type."""
    filepath = data_path("organisation")
    orgs: Dict[str, List[Organisation]] = {}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        for cols in reader:
            if not cols[0].strip():
                continue
            namn = cols[0].strip()

            def safe_int(idx, default=0):
                try:
                    return int(cols[idx].strip()) if cols[idx].strip() else default
                except (ValueError, IndexError):
                    return default

            kompetenser = {}
            for key, idx in [("STA", 8), ("KOM", 9), ("SAM", 10), ("NOG", 11), ("INN", 12), ("ABM", 13)]:
                v = safe_int(idx, 0)
                if v:
                    kompetenser[key] = v

            o = Organisation(
                namn=namn,
                niva=safe_int(1),
                kostnad_mkr=safe_int(2),
                q=safe_int(3), h=safe_int(4), t=safe_int(5),
                erfarenhet=safe_int(6),
                riskbuffert=safe_int(7),
                kompetenser=kompetenser,
            )
            if namn not in orgs:
                orgs[namn] = []
            orgs[namn].append(o)

    for namn in orgs:
        orgs[namn].sort(key=lambda x: x.niva)

    return orgs


def load_planning_events() -> Dict[str, List[PlanningEventCard]]:
    """Load planning event cards grouped by slot (kort_id)."""
    global D20_THRESHOLDS
    filepath = data_path("handelsekort_pl")
    cards: Dict[str, List[PlanningEventCard]] = {}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        # Parse thresholds from column headers (cols 9-12)
        if len(header) > 12:
            D20_THRESHOLDS = parse_threshold_headers(header[9:13])
            print(f"    D20-trösklar: {D20_THRESHOLDS}")

        for cols in reader:
            if not cols[0].strip():
                continue

            effects = [
                cols[9].strip() if len(cols) > 9 else "",
                cols[10].strip() if len(cols) > 10 else "",
                cols[11].strip() if len(cols) > 11 else "",
                cols[12].strip() if len(cols) > 12 else "",
            ]

            card = PlanningEventCard(
                kort_id=cols[0].strip(),
                namn=cols[1].strip(),
                typ=cols[2].strip(),
                fas=cols[3].strip() if len(cols) > 3 else "",
                svarighetsgrad=cols[4].strip() if len(cols) > 4 else "",
                beskrivning=cols[5].strip() if len(cols) > 5 else "",
                summering=cols[6].strip() if len(cols) > 6 else "",
                trigger=cols[7].strip() if len(cols) > 7 else "Alla",
                klassvillkor=cols[8].strip() if len(cols) > 8 else "Alla",
                effects=effects,
            )

            kort_id = card.kort_id
            if kort_id not in cards:
                cards[kort_id] = []
            cards[kort_id].append(card)

    return cards


# Mapping from planning slot names to event card kort_id values
SLOT_TO_CARD_IDS = {
    "MARK": ["MARK"],
    "HUSUNDERBYGGNAD": ["HUSUNDERBYGGNAD"],
    "STOMME": ["STOMME"],
    "YTTERTAK": ["YTTERTAK"],
    "FASADER": ["FASADER"],
    "STOMKOMPLETTERING": ["STOMKOMP"],
    "INV YTSKIKT": ["INV YTSKIKT"],
    "INSTALLATIONER": ["INSTALLATÖRER"],
    "GEMENSAMMA ARBETEN": ["GEM ARBETEN"],
    "Operativt team": ["OPERATIVT TEAM"],
    "Stödfunktioner": ["STÖDFUNKTIONER"],
    "Marknadsteam": ["MARKNADSTEAM"],
    "Digitalisering": ["DIGITALISERING"],
}

# The 13 planning steps in order (from the board layout image)
PLANNING_ORDER = [
    ("Stödfunktioner", "org"),
    ("MARK", "lev"),
    ("HUSUNDERBYGGNAD", "lev"),
    ("Digitalisering", "org"),
    ("STOMME", "lev"),
    ("INSTALLATIONER", "lev"),
    ("Operativt team", "org"),
    ("GEMENSAMMA ARBETEN", "lev"),
    ("YTTERTAK", "lev"),
    ("FASADER", "lev"),
    ("Marknadsteam", "org"),
    ("STOMKOMPLETTERING", "lev"),
    ("INV YTSKIKT", "lev"),
]

# Phase 3 constants
PHASE_COST = [2, 2, 3, 3, 4, 5, 6, 7]  # External support cost per phase (1-8)
ENERGY_CLASSES = ["A", "B", "C", "D", "E", "F"]
ENERGY_UPGRADE_COST_PER_STEP = 3.0  # Mkr per klassteg
ENERGY_UPGRADE_QUARTERLY_LIMITS = {1: 0, 2: 3, 3: 2, 4: 1}  # max förbättringar per kvartal


def load_phase_cards() -> Dict[int, List[PhaseCard]]:
    """Load faskort grouped by steg (1-8)."""
    filepath = data_path("faskort")
    cards: Dict[int, List[PhaseCard]] = {}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        for cols in reader:
            if not cols[0].strip():
                continue
            steg = int(cols[1].strip())
            levels = [
                {"req_b": cols[4].strip(), "req_s": cols[5].strip(),
                 "req_k": cols[6].strip(), "effect": cols[7].strip()},
                {"req_b": cols[8].strip(), "req_s": cols[9].strip(),
                 "req_k": cols[10].strip(), "effect": cols[11].strip()},
                {"req_b": cols[12].strip(), "req_s": cols[13].strip(),
                 "req_k": cols[14].strip(), "effect": cols[15].strip()},
                {"req_b": cols[16].strip(), "req_s": cols[17].strip(),
                 "req_k": cols[18].strip(), "effect": cols[19].strip()},
            ]
            card = PhaseCard(
                id=cols[0].strip(), steg=steg,
                namn=cols[2].strip(), beskrivning=cols[3].strip(),
                levels=levels,
            )
            if steg not in cards:
                cards[steg] = []
            cards[steg].append(card)

    return cards


def load_external_support() -> List[ExternalSupport]:
    """Load företagskultur cards (multi-parameter, 6 points total, max 4 per param)."""
    filepath = data_path("externstod")
    cards: List[ExternalSupport] = []

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # ID;Namn;STA;KOM;SAM;NOG;INN;ABM
        for cols in reader:
            if not cols[0].strip():
                continue
            kompetenser = {
                "STA": int(cols[2].strip()) if len(cols) > 2 and cols[2].strip() else 0,
                "KOM": int(cols[3].strip()) if len(cols) > 3 and cols[3].strip() else 0,
                "SAM": int(cols[4].strip()) if len(cols) > 4 and cols[4].strip() else 0,
                "NOG": int(cols[5].strip()) if len(cols) > 5 and cols[5].strip() else 0,
                "INN": int(cols[6].strip()) if len(cols) > 6 and cols[6].strip() else 0,
                "ABM": int(cols[7].strip()) if len(cols) > 7 and cols[7].strip() else 0,
            }
            cards.append(ExternalSupport(
                kort_id=cols[0].strip(),
                namn=cols[1].strip(),
                kompetenser=kompetenser,
            ))

    random.shuffle(cards)
    return cards


def load_penalty_cards() -> Dict[str, List[PenaltyCard]]:
    """Load konsekvenskort grouped by type (T/Q/H). Now with D20 threshold effects."""
    filepath = data_path("konsekvenskort")
    cards: Dict[str, List[PenaltyCard]] = {"T": [], "Q": [], "H": []}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # skip header

        for cols in reader:
            if not cols[0].strip():
                continue
            effects = [
                cols[4].strip() if len(cols) > 4 else "",
                cols[5].strip() if len(cols) > 5 else "",
                cols[6].strip() if len(cols) > 6 else "",
                cols[7].strip() if len(cols) > 7 else "",
            ]
            card = PenaltyCard(
                typ=cols[0].strip(),
                nr=cols[1].strip(),
                namn=cols[2].strip(),
                energiklass_projekt=int(cols[3].strip()) if cols[3].strip() else 0,
                effects=effects,
            )
            if card.typ in cards:
                cards[card.typ].append(card)

    for typ in cards:
        random.shuffle(cards[typ])
    return cards


def load_garanti_cards() -> Dict[str, List[PenaltyCard]]:
    """Load garantibesiktning cards grouped by type (T/Q/H/EK)."""
    filepath = data_path("garantibesiktning")
    cards: Dict[str, List[PenaltyCard]] = {"T": [], "Q": [], "H": [], "EK": []}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)

        for cols in reader:
            if not cols[0].strip():
                continue
            effects = [
                cols[3].strip() if len(cols) > 3 else "",
                cols[4].strip() if len(cols) > 4 else "",
                cols[5].strip() if len(cols) > 5 else "",
                cols[6].strip() if len(cols) > 6 else "",
            ]
            card = PenaltyCard(
                typ=cols[0].strip(),
                nr=cols[1].strip(),
                namn=cols[2].strip(),
                energiklass_projekt=0,
                effects=effects,
            )
            if card.typ in cards:
                cards[card.typ].append(card)

    for typ in cards:
        random.shuffle(cards[typ])
    return cards


# ─────────────────────────────────────────────
# PHASE 4 LOADERS
# ─────────────────────────────────────────────

def load_staff() -> List[Staff]:
    """Load personnel cards (FC and FS)."""
    filepath = data_path("personal")
    staff: List[Staff] = []
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            lon_str = cols[6].strip().replace(",", ".") if len(cols) > 6 else "0"
            staff.append(Staff(
                roll=cols[0].strip(),
                id=cols[1].strip(),
                namn=cols[2].strip(),
                specialisering=cols[3].strip() if len(cols) > 3 else "",
                kapacitet=int(cols[4].strip()) if len(cols) > 4 and cols[4].strip() else 1,
                handelsemotstand=cols[5].strip() if len(cols) > 5 else "",
                lon_mkr_kv=float(lon_str) if lon_str else 0,
                forhandling=cols[7].strip() if len(cols) > 7 else "",
            ))
    return staff


def load_yield_cards() -> Dict[str, List[float]]:
    """Load yield change cards. Returns {bostäder: [changes], kommersiellt: [changes]}."""
    filepath = data_path("yield")
    result: Dict[str, List[float]] = {"bostäder": [], "kommersiellt": []}
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            titel = cols[0].strip().lower()
            change_str = cols[2].strip().replace(",", ".").replace("%", "")
            change = float(change_str) if change_str else 0
            if "bostäd" in titel:
                result["bostäder"].append(change)
            elif "kommersiell" in titel:
                result["kommersiellt"].append(change)
    for k in result:
        random.shuffle(result[k])
    return result


def load_dd_cards() -> List[DDCard]:
    """Load Due Diligence cards."""
    filepath = data_path("dd")
    cards: List[DDCard] = []
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            eff_str = cols[3].strip().replace(",", ".") if len(cols) > 3 else "0"
            cards.append(DDCard(
                id=cols[0].strip(),
                typ=cols[1].strip(),
                rubrik=cols[2].strip(),
                effekt_mkr=float(eff_str) if eff_str else 0,
                beskrivning=cols[4].strip() if len(cols) > 4 else "",
            ))
    random.shuffle(cards)
    return cards


def load_world_events() -> List[WorldEvent]:
    """Load omvärldskort."""
    filepath = data_path("omvarldskort")
    cards: List[WorldEvent] = []
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            eff_str = cols[3].strip().replace(",", ".") if len(cols) > 3 else "0"
            cards.append(WorldEvent(
                id=cols[0].strip(),
                rubrik=cols[1].strip(),
                effekt_typ=cols[2].strip() if len(cols) > 2 else "",
                effekt_mkr=float(eff_str) if eff_str else 0,
                paverkar=cols[4].strip() if len(cols) > 4 else "",
                beskrivning=cols[5].strip() if len(cols) > 5 else "",
            ))
    random.shuffle(cards)
    return cards


def load_mgmt_events() -> Dict[str, List[ManagementEvent]]:
    """Load management händelsekort grouped by type."""
    filepath = data_path("handelsekort_forv")
    cards: Dict[str, List[ManagementEvent]] = {}
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        # Detect new format with Trigger column
        has_trigger = len(header) >= 9 and "trigger" in header[7].lower()
        for cols in reader:
            if not cols[0].strip():
                continue
            eff_str = cols[3].strip().replace(",", ".") if len(cols) > 3 else "0"
            mild_eff_str = cols[6].strip().replace(",", ".") if len(cols) > 6 else "0"
            if has_trigger:
                trigger = cols[7].strip() if len(cols) > 7 else "Alla"
                beskrivning = cols[8].strip() if len(cols) > 8 else ""
            else:
                trigger = "Alla"
                beskrivning = cols[7].strip() if len(cols) > 7 else ""
            card = ManagementEvent(
                id=cols[0].strip(),
                typ=cols[1].strip(),
                rubrik=cols[2].strip(),
                effekt_mkr=float(eff_str) if eff_str else 0,
                mildring_roll=cols[4].strip() if len(cols) > 4 else "",
                mildring_spec=cols[5].strip() if len(cols) > 5 else "",
                mildring_effekt_mkr=float(mild_eff_str) if mild_eff_str else 0,
                trigger=trigger,
                beskrivning=beskrivning,
            )
            if card.typ not in cards:
                cards[card.typ] = []
            cards[card.typ].append(card)
    for typ in cards:
        random.shuffle(cards[typ])
    return cards


def load_rent_scale() -> Dict[int, float]:
    """Load hyreshöjningar scale. Returns {netto_value: höjning_per_HR}."""
    filepath = data_path("hyreshojningar")
    scale: Dict[int, float] = {}
    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for cols in reader:
            if not cols[0].strip():
                continue
            netto = int(cols[0].strip())
            hojning = float(cols[1].strip().replace(",", "."))
            scale[netto] = hojning
    return scale


def input_int(prompt: str, min_val: int, max_val: int) -> int:
    """Get integer input within range."""
    while True:
        try:
            val = int(input(prompt).strip())
            if min_val <= val <= max_val:
                return val
            print(f"  Ange ett tal mellan {min_val} och {max_val}.")
        except ValueError:
            print("  Ange ett giltigt heltal.")


def input_choice(prompt: str, options: List[str]) -> str:
    """Get string input from a list of options."""
    opts_lower = [o.lower() for o in options]
    while True:
        val = input(prompt).strip().lower()
        if val in opts_lower:
            return val
        print(f"  Giltiga val: {', '.join(options)}")


def input_yes_no(prompt: str) -> bool:
    """Get yes/no input."""
    return input_choice(prompt + " (j/n): ", ["j", "n"]) == "j"


def pause():
    """Wait for user to press Enter."""
    input("  [Tryck Enter för att fortsätta...]")


# ─────────────────────────────────────────────
# EFFECT PARSING & APPLICATION
# ─────────────────────────────────────────────
def parse_and_apply_effect(effect_text: str, player: "Player",
                           game: "GameState") -> None:
    """Parse a card effect text and apply it to the player."""
    if not effect_text or effect_text.lower() == "ingen effekt":
        print("  → Ingen effekt.")
        return

    text = effect_text.strip()
    parts = [p.strip() for p in text.replace(" och ", ",").split(",")]

    for part in parts:
        part_low = part.lower().strip()

        # Return project with highest income
        if "lämna tillbaka" in part_low and "högst intäkt" in part_low:
            if player.projects:
                worst = max(player.projects, key=lambda p: p.anskaffning)
                print(f"  → Lämnar tillbaka: {worst.namn} (anskaffning {worst.anskaffning} Mkr)")
                player.projects.remove(worst)
                player.q_krav -= worst.kvalitet
                player.h_krav -= worst.hallbarhet
                game.return_project(worst)
            else:
                print("  → Inga projekt att lämna tillbaka.")

        # Increase Q krav
        elif "kvalitetskrav" in part_low:
            amount = 2 if "2" in part else 1
            if "-" in part_low or "minska" in part_low or part.startswith("-"):
                player.q_krav = max(0, player.q_krav - amount)
                print(f"  → Kvalitetskrav -{amount} (nu: {player.q_krav})")
            else:
                player.q_krav += amount
                print(f"  → Kvalitetskrav +{amount} (nu: {player.q_krav})")

        # Increase H krav
        elif "hållbarhetskrav" in part_low:
            amount = 2 if "2" in part else 1
            if "-" in part_low or "minska" in part_low or part.startswith("-"):
                player.h_krav = max(0, player.h_krav - amount)
                print(f"  → Hållbarhetskrav -{amount} (nu: {player.h_krav})")
            else:
                player.h_krav += amount
                print(f"  → Hållbarhetskrav +{amount} (nu: {player.h_krav})")

        # Risk buffers
        elif "riskbuffert" in part_low:
            amount = 2 if "2" in part else 1
            player.riskbuffertar += amount
            print(f"  → +{amount} riskbuffert(ar) (nu: {player.riskbuffertar})")

        # Tid
        elif "tid" in part_low:
            amount = 2 if "2" in part else 1
            if "-" in part or "minska" in part_low:
                print(f"  → Tid -{amount} (noterat för projektplanering)")
            else:
                print(f"  → Tid +{amount} (noterat för projektplanering)")

        # Swap project
        elif "byt projekt" in part_low:
            if input_yes_no("  Vill du byta ett projekt (samma typ)?"):
                handle_swap_project(player, game)

        # Take project from any stack
        elif "ta projekt från valfri hög" in part_low:
            if input_yes_no("  Vill du ta ett projekt från valfri hög?"):
                handle_take_any_project(player, game)

        # Mark expansion
        elif "markanvisning" in part_low or "markexpansion" in part_low:
            if input_yes_no("  Vill du dra en markanvisning (markexpansion)?"):
                cells = random.randint(EXPANSION_MIN, EXPANSION_MAX)
                player.mark_expansions += cells
                player.expansion_events += 1
                print(f"  → Markexpansion: +{cells} rutor (totalt tomtutrymme: {player.available_cells})")


def handle_swap_project(player: "Player", game: "GameState") -> None:
    """Let player swap a project for another of the same type."""
    if not player.projects:
        print("  Du har inga projekt att byta.")
        return

    print("  Dina projekt:")
    for i, p in enumerate(player.projects):
        print(f"    {i + 1}. {p.display_short()}")

    idx = input_int("  Vilket projekt vill du byta? (nummer): ", 1, len(player.projects)) - 1
    old_project = player.projects[idx]
    typ = old_project.typ

    available = game.get_available_projects(typ)
    if not available:
        print(f"  Inga tillgängliga {typ}-projekt att byta mot.")
        return

    print(f"  Tillgängliga {typ}-projekt:")
    for i, p in enumerate(available):
        print(f"    {i + 1}. {p.display_short()}")

    new_idx = input_int("  Vilket vill du ta? (nummer, 0 = avbryt): ", 0, len(available))
    if new_idx == 0:
        return

    new_project = available[new_idx - 1]
    player.projects[idx] = new_project
    game.take_project_from_available(new_project, typ)
    game.return_project(old_project)

    player.q_krav += new_project.kvalitet - old_project.kvalitet
    player.h_krav += new_project.hallbarhet - old_project.hallbarhet
    print(f"  → Bytte {old_project.namn} mot {new_project.namn}")


def handle_take_any_project(player: "Player", game: "GameState") -> None:
    """Let player take a project from any stack."""
    print("  Tillgängliga projekttyper:")
    available_types = []
    for typ in PROJECT_TYPES:
        avail = game.get_available_projects(typ)
        if avail:
            available_types.append(typ)
            print(f"    {len(available_types)}. {typ} ({len(avail)} tillgängliga)")

    if not available_types:
        print("  Inga projekt tillgängliga.")
        return

    choice = input_int("  Välj typ (nummer, 0 = avbryt): ", 0, len(available_types))
    if choice == 0:
        return

    typ = available_types[choice - 1]
    offer_project_from_type(player, game, typ)


# ─────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────
class GameState:
    def __init__(self, num_players: int):
        self.players: List[Player] = []
        self.project_stacks: Dict[str, List[Project]] = {}
        self.project_bank: Dict[str, List[Project]] = {t: [] for t in PROJECT_TYPES}
        self.board: List[BoardSquare] = []
        self.politik_deck: List[PolitikDialogCard] = []
        self.dialog_deck: List[PolitikDialogCard] = []
        self.politik_discard: List[PolitikDialogCard] = []
        self.dialog_discard: List[PolitikDialogCard] = []
        self.game_over: bool = False
        self.num_players = num_players
        # Per-player event card piles (persist from Fas 2 to Fas 3)
        self.pl_draw_piles: Dict[str, List[PlanningEventCard]] = {}
        self.pl_discard_piles: Dict[str, List[PlanningEventCard]] = {}
        # Phase 4 state
        self.no_trading: bool = False

    def setup(self):
        """Initialize the full game state."""
        print("\n" + "=" * 60)
        print("  HUSBYGGSPELET – Fas 1: Projektutveckling")
        print("=" * 60)

        # Create players
        for i in range(self.num_players):
            name = input(f"\n  Namn på spelare {i + 1}: ").strip()
            if not name:
                name = f"Spelare {i + 1}"
            self.players.append(Player(name=name))

        # Load data
        print("\n  Laddar speldata...")
        load_klass_table()
        print(f"    BYA-klasser: {', '.join(f'{k}: {lo}-{hi}' for lo, hi, k in BYA_CLASSES)}")
        print(f"    BTA-klasser: {', '.join(f'{k}: {lo}-{hi}' for lo, hi, k in BTA_CLASSES)}")
        self.project_stacks = load_projects()
        self.board = load_board()
        self.politik_deck, self.dialog_deck = load_politik_dialog()

        for typ, stack in self.project_stacks.items():
            print(f"    {typ}: {len(stack)} projektkort")
        print(f"    Politikkort: {len(self.politik_deck)}")
        print(f"    Dialogkort: {len(self.dialog_deck)}")

        # Determine starting player
        print("\n  ── Slår om vem som börjar ──")
        rolls = []
        for p in self.players:
            r = roll_display("D6", p.name)
            rolls.append(r)

        max_roll = max(rolls)
        starter_idx = rolls.index(max_roll)

        # Reorder players so starter is first
        self.players = self.players[starter_idx:] + self.players[:starter_idx]
        print(f"\n  🏁 {self.players[0].name} börjar! (slog {max_roll})")

    def get_available_projects(self, typ: str) -> List[Project]:
        """Get all available projects of a type (stack top + bank)."""
        available = []
        # Top of stack
        if self.project_stacks.get(typ):
            available.append(self.project_stacks[typ][-1])
        # Bank
        available.extend(self.project_bank.get(typ, []))
        return available

    def take_project_from_available(self, project: Project, typ: str) -> None:
        """Remove a project from available pool."""
        if self.project_stacks.get(typ) and self.project_stacks[typ][-1] is project:
            self.project_stacks[typ].pop()
        elif project in self.project_bank.get(typ, []):
            self.project_bank[typ].remove(project)

    def return_project(self, project: Project) -> None:
        """Return a project – goes to used pile (cannot be reused)."""
        if not hasattr(self, 'used_projects'):
            self.used_projects = []
        self.used_projects.append(project)
        print(f"    ({project.namn} läggs åt sidan – kan inte användas igen)")

    def draw_politik(self) -> Optional[PolitikDialogCard]:
        """Draw a politik card."""
        if not self.politik_deck:
            if self.politik_discard:
                self.politik_deck = self.politik_discard[:]
                self.politik_discard.clear()
                random.shuffle(self.politik_deck)
            else:
                return None
        card = self.politik_deck.pop(0)
        self.politik_discard.append(card)
        return card

    def draw_dialog(self) -> Optional[PolitikDialogCard]:
        """Draw a dialog card."""
        if not self.dialog_deck:
            if self.dialog_discard:
                self.dialog_deck = self.dialog_discard[:]
                self.dialog_discard.clear()
                random.shuffle(self.dialog_deck)
            else:
                return None
        card = self.dialog_deck.pop(0)
        self.dialog_discard.append(card)
        return card


# ─────────────────────────────────────────────
# SQUARE HANDLERS
# ─────────────────────────────────────────────
def offer_project_from_type(player: Player, game: GameState, typ: str) -> None:
    """Offer a player to take a project of a given type."""
    # ── Tetris-begränsning ──
    if len(player.projects) >= MAX_PROJECTS:
        print(f"  ⚠ Du har redan {len(player.projects)} projekt (max {MAX_PROJECTS}). "
              f"Tomten är full!")
        return
    if player.total_bta >= MAX_BTA:
        print(f"  ⚠ Du har redan {player.total_bta} kvm BTA (max {MAX_BTA}). "
              f"Tomten är full!")
        return

    available = game.get_available_projects(typ)
    if not available:
        print(f"  Inga {typ}-projekt tillgängliga.")
        return

    print(f"\n  Tillgängliga {typ}-projekt:")
    for i, p in enumerate(available):
        print(f"    {i + 1}. {p.display_short()}")

    choice = input_int(f"  Välj projekt (1-{len(available)}, 0 = passa): ",
                       0, len(available))
    if choice == 0:
        print("  Du passar.")
        return

    project = available[choice - 1]
    game.take_project_from_available(project, typ)
    player.projects.append(project)
    player.q_krav += project.kvalitet
    player.h_krav += project.hallbarhet
    msg = f"  ✓ Tog {project.namn}! Q-krav nu: {player.q_krav}, H-krav nu: {player.h_krav}"
    if project.riskbuffert > 0:
        player.pending_riskbuffertar += project.riskbuffert
        msg += f" | +{project.riskbuffert} riskbuffert (låst till efter nämnd)"
    print(msg)


def handle_square(square: BoardSquare, player: Player, game: GameState) -> None:
    """Resolve a board square's effect."""
    ruta = square.ruta

    print(f"\n  ╔══ Ruta {square.nr}: {ruta} ══╗")
    print(f"  ║ {square.handelse}")
    print(f"  ╚{'═' * 40}╝")

    # Stadsbyggnadskontoret - markexpansion
    if ruta == "Stadsbyggnadskontoret":
        if input_yes_no("  Vill du ta en markexpansion (kostnad 5 Mkr vid slutet)?"):
            cells = random.randint(EXPANSION_MIN, EXPANSION_MAX)
            player.mark_expansions += cells
            player.expansion_events += 1
            print(f"  → Markexpansion: +{cells} rutor (totalt tomtutrymme: {player.available_cells})")

    # Stjärna - riskbuffert
    elif ruta == "Stjärna":
        player.riskbuffertar += 1
        print(f"  → +1 riskbuffert (totalt: {player.riskbuffertar})")

    # Project squares
    elif ruta in ("F",):
        offer_project_from_type(player, game, "FÖRSKOLOR")
    elif ruta in ("H",):
        offer_project_from_type(player, game, "Hyresrätt")
    elif ruta in ("B",):
        offer_project_from_type(player, game, "BRF")
    elif ruta in ("L",):
        offer_project_from_type(player, game, "LOKAL")
    elif ruta in ("K",):
        offer_project_from_type(player, game, "KONTOR")

    # Multi-type squares
    elif ruta == "B, K":
        print("  Välj projekttyp:")
        print("    1. BRF")
        print("    2. Kontor")
        c = input_int("  Val (1-2, 0 = passa): ", 0, 2)
        if c == 1:
            offer_project_from_type(player, game, "BRF")
        elif c == 2:
            offer_project_from_type(player, game, "KONTOR")
    elif ruta == "K, B":
        print("  Välj projekttyp:")
        print("    1. Kontor")
        print("    2. BRF")
        c = input_int("  Val (1-2, 0 = passa): ", 0, 2)
        if c == 1:
            offer_project_from_type(player, game, "KONTOR")
        elif c == 2:
            offer_project_from_type(player, game, "BRF")
    elif ruta == "L, H":
        print("  Välj projekttyp:")
        print("    1. Lokal")
        print("    2. Hyresrätt")
        c = input_int("  Val (1-2, 0 = passa): ", 0, 2)
        if c == 1:
            offer_project_from_type(player, game, "LOKAL")
        elif c == 2:
            offer_project_from_type(player, game, "Hyresrätt")
    elif ruta == "L, F":
        print("  Välj projekttyp:")
        print("    1. Lokal")
        print("    2. Förskola")
        c = input_int("  Val (1-2, 0 = passa): ", 0, 2)
        if c == 1:
            offer_project_from_type(player, game, "LOKAL")
        elif c == 2:
            offer_project_from_type(player, game, "FÖRSKOLOR")

    # Dialog cards
    elif ruta == "Glödlampa":
        handle_dialog_card(player, game)

    # Politik cards
    elif ruta == "Frågetecken":
        handle_politik_card(player, game)

    # Stadshuset
    elif ruta == "Stadshuset":
        handle_stadshuset(player, game)

    # Länsstyrelsen
    elif ruta == "Länsstyrelsen":
        player.h_krav = max(0, player.h_krav - 2)
        print(f"  → Hållbarhetskrav -2 (nu: {player.h_krav})")

    # Skönhetsrådet
    elif ruta == "Skönhetsrådet":
        player.q_krav = max(0, player.q_krav - 2)
        print(f"  → Kvalitetskrav -2 (nu: {player.q_krav})")


def handle_dialog_card(player: Player, game: GameState) -> None:
    """Draw and resolve a dialog card."""
    card = game.draw_dialog()
    if not card:
        print("  Inga dialogkort kvar.")
        return

    print(f"\n  📋 DIALOGKORT: {card.rubrik}")
    print(f"     {card.text}")

    if card.is_special:
        print(f"\n  ⚡ SPECIALKORT!")
        print(f"     Påverkar: {card.special_target}")
        print(f"     Effekt: {card.special_effect}")
        handle_special_card(card, player, game)
    else:
        result = roll_display("D20", "Dialogkort")

        # Projektchef lindrar
        pc_bonus = 0
        if player.projektchef and "Dialogkort" in player.projektchef.motstand:
            pc_bonus = player.projektchef.bonus
            result += pc_bonus
            print(f"  → {player.projektchef.namn} lindrar +{pc_bonus} (totalt: {result})")

        # Determine effect range
        if result == 1:
            effect = card.effects.get("1", "Ingen effekt")
        elif result <= 11:
            effect = card.effects.get("2-11", "Ingen effekt")
        elif result <= 15:
            effect = card.effects.get("12-15", "Ingen effekt")
        elif result <= 19:
            effect = card.effects.get("16-19", "Ingen effekt")
        else:
            effect = card.effects.get("20", "Ingen effekt")

        print(f"  → Effekt: {effect}")

        # Offer reroll with riskbuffert
        if player.riskbuffertar > 0 and effect and "ingen effekt" not in effect.lower():
            if input_yes_no(f"  Använd riskbuffert för att slå om? ({player.riskbuffertar} kvar)"):
                player.riskbuffertar -= 1
                result = roll_display("D20", "Omslag")
                if result == 1:
                    effect = card.effects.get("1", "Ingen effekt")
                elif result <= 11:
                    effect = card.effects.get("2-11", "Ingen effekt")
                elif result <= 15:
                    effect = card.effects.get("12-15", "Ingen effekt")
                elif result <= 19:
                    effect = card.effects.get("16-19", "Ingen effekt")
                else:
                    effect = card.effects.get("20", "Ingen effekt")
                print(f"  → Ny effekt: {effect}")

        parse_and_apply_effect(effect, player, game)


def handle_politik_card(player: Player, game: GameState) -> None:
    """Draw and resolve a politik card."""
    card = game.draw_politik()
    if not card:
        print("  Inga politikkort kvar.")
        return

    print(f"\n  🏛️  POLITIKKORT: {card.rubrik}")
    print(f"     {card.text}")

    if card.is_special:
        print(f"\n  ⚡ SPECIALKORT!")
        print(f"     Påverkar: {card.special_target}")
        print(f"     Effekt: {card.special_effect}")
        handle_special_card(card, player, game)
    else:
        result = roll_display("D20", "Politikkort")

        # Projektchef lindrar
        pc_bonus = 0
        if player.projektchef and "Politikkort" in player.projektchef.motstand:
            pc_bonus = player.projektchef.bonus
            result += pc_bonus
            print(f"  → {player.projektchef.namn} lindrar +{pc_bonus} (totalt: {result})")

        if result == 1:
            effect = card.effects.get("1", "Ingen effekt")
        elif result <= 11:
            effect = card.effects.get("2-11", "Ingen effekt")
        elif result <= 15:
            effect = card.effects.get("12-15", "Ingen effekt")
        elif result <= 19:
            effect = card.effects.get("16-19", "Ingen effekt")
        else:
            effect = card.effects.get("20", "Ingen effekt")

        print(f"  → Effekt: {effect}")

        # Offer reroll with riskbuffert
        if player.riskbuffertar > 0 and "lämna tillbaka" in effect.lower():
            if input_yes_no(f"  Använd riskbuffert för att slå om? ({player.riskbuffertar} kvar)"):
                player.riskbuffertar -= 1
                result = roll_display("D20", "Omslag")
                if result == 1:
                    effect = card.effects.get("1", "Ingen effekt")
                elif result <= 11:
                    effect = card.effects.get("2-11", "Ingen effekt")
                elif result <= 15:
                    effect = card.effects.get("12-15", "Ingen effekt")
                elif result <= 19:
                    effect = card.effects.get("16-19", "Ingen effekt")
                else:
                    effect = card.effects.get("20", "Ingen effekt")
                print(f"  → Ny effekt: {effect}")

        parse_and_apply_effect(effect, player, game)


def handle_special_card(card: PolitikDialogCard, current_player: Player,
                        game: GameState) -> None:
    """Handle special Politik/Dialog cards that affect multiple players."""
    effect = card.special_effect
    target = card.special_target.upper()

    if "ALLA SPELARE" in target:
        players_affected = game.players
    elif "DIG" in target:
        players_affected = [current_player]
        # Find additional targets
        if "HÖGST KRAVSUMMA" in target:
            other = max((p for p in game.players if p != current_player),
                        key=lambda p: p.krav_summa, default=None)
            if other:
                players_affected.append(other)
        elif "LÄGSTA KRAVSUMMA" in target:
            other = min((p for p in game.players if p != current_player),
                        key=lambda p: p.krav_summa, default=None)
            if other:
                players_affected.append(other)
        elif "FLEST RISKBUFFERTAR" in target:
            other = max((p for p in game.players if p != current_player),
                        key=lambda p: p.riskbuffertar, default=None)
            if other:
                players_affected.append(other)
    elif "LÄGSTA KRAVSUMMA" in target:
        players_affected = [min(game.players, key=lambda p: p.krav_summa)]
    elif "HÖGST KRAVSUMMA" in target:
        players_affected = [max(game.players, key=lambda p: p.krav_summa)]
    else:
        players_affected = [current_player]

    print(f"  Påverkade spelare: {', '.join(p.name for p in players_affected)}")
    print(f"  Effekt: {effect}")

    # Apply the effect text as-is for complex special cards
    for p in players_affected:
        print(f"\n  Applicerar på {p.name}:")
        parse_and_apply_effect(effect, p, game)


def handle_stadshuset(player: Player, game: GameState) -> None:
    """Handle the Stadshuset square: take, return, or swap a project."""
    print("  Stadshuset – välj en åtgärd:")
    print("    1. Ta ett projekt (valfri typ)")
    print("    2. Lämna tillbaka ett projekt")
    print("    3. Byt ett projekt (samma kategori)")
    print("    0. Passa")

    choice = input_int("  Val: ", 0, 3)

    if choice == 0:
        print("  Du passar.")
    elif choice == 1:
        handle_take_any_project(player, game)
    elif choice == 2:
        if not player.projects:
            print("  Du har inga projekt att lämna tillbaka.")
            return
        print("  Dina projekt:")
        for i, p in enumerate(player.projects):
            print(f"    {i + 1}. {p.display_short()}")
        idx = input_int("  Vilket projekt lämnar du tillbaka? (nummer, 0 = avbryt): ",
                        0, len(player.projects))
        if idx > 0:
            project = player.projects.pop(idx - 1)
            player.q_krav -= project.kvalitet
            player.h_krav -= project.hallbarhet
            game.return_project(project)
            print(f"  → Lämnade tillbaka {project.namn}")
    elif choice == 3:
        handle_swap_project(player, game)


# ─────────────────────────────────────────────
# PLAYER STATUS DISPLAY
# ─────────────────────────────────────────────
def show_player_status(player: Player) -> None:
    """Display a player's current status."""
    print(f"\n  ┌─── {player.name} ───────────────────────────")
    print(f"  │ Position: ruta {player.position} | Varv: {player.laps}")
    print(f"  │ Projekt: {len(player.projects)} st | "
          f"Total BTA: {player.total_bta} kvm | Formfaktor: {player.total_formfaktor}/{player.available_cells}")
    print(f"  │ Q-krav: {player.q_krav} | H-krav: {player.h_krav} | "
          f"Riskbuffertar: {player.riskbuffertar}")
    if player.projects:
        print(f"  │ Projekt:")
        for p in player.projects:
            print(f"  │   • {p.namn} ({p.typ}) BTA:{p.bta} Q:{p.kvalitet} H:{p.hallbarhet}")
    print(f"  └{'─' * 45}")


# ─────────────────────────────────────────────
# PHASE 1: MAIN GAME LOOP
# ─────────────────────────────────────────────
def phase_mark_och_tomt(game: GameState) -> None:
    """Initial phase: each player takes mark and tomt."""
    print("\n" + "=" * 60)
    print("  FAS 1a: MARK OCH TOMT")
    print("=" * 60)
    print("  Varje spelare tar en markkvadrat (16×16 rutor à 250 kvm)")
    print("  och en tomtkvadrat (4×4 rutor = 16 celler).")
    print("  Kostnad: 15 Mkr totalt (betalas vid slutet).\n")

    for player in game.players:
        print(f"  {player.name} tar mark och tomt. ✓")
        player.has_mark_tomt = True

        # Välj projektchef
        pc_ac = load_pc_ac()
        pcs = pc_ac.get("PC", [])
        if pcs:
            print(f"\n  ── Välj Projektchef ──")
            for i, pc in enumerate(pcs, 1):
                print(f"    {i}. {pc.display()}")
            choice = input_int(f"  Välj projektchef (1-{len(pcs)}): ", 1, len(pcs))
            chosen_pc = pcs[choice - 1]
            player.projektchef = chosen_pc
            player.riskbuffertar += chosen_pc.rb_bonus
            extras = []
            if chosen_pc.q_bonus: extras.append(f"+{chosen_pc.q_bonus} Q")
            if chosen_pc.h_bonus: extras.append(f"+{chosen_pc.h_bonus} H")
            if chosen_pc.t_bonus: extras.append(f"-{chosen_pc.t_bonus} T")
            extras.append(f"+{chosen_pc.rb_bonus} Rb")
            print(f"  ✓ {chosen_pc.namn} ({chosen_pc.specialisering}) "
                  f"ansluter som projektchef ({', '.join(extras)})")

        # Startprojekt – varje spelare får välja ett projekt
        print(f"\n  {player.name} väljer sitt första projekt:")
        types = list(game.project_stacks.keys())
        for i, t in enumerate(types, 1):
            count = len(game.get_available_projects(t))
            print(f"    {i}. {t} ({count} tillgängliga)")
        choice = input_int(f"  Välj projekttyp (1-{len(types)}): ", 1, len(types))
        chosen_type = types[choice - 1]
        offer_project_from_type(player, game, chosen_type)

    pause()


def phase_board_game(game: GameState) -> None:
    """Main board game loop: players move around and resolve squares."""
    print("\n" + "=" * 60)
    print("  FAS 1b: PROJEKTUTVECKLINGSBRÄDET")
    print("=" * 60)
    print("  Spelarna rör sig runt brädet (24 rutor).")
    print("  Spelet slutar när första spelaren passerar")
    print("  Stadsbyggnadskontoret för andra gången.\n")

    turn_number = 0

    while not game.game_over:
        for player in game.players:
            if game.game_over:
                break

            turn_number += 1
            print(f"\n{'─' * 60}")
            print(f"  TUR {turn_number}: {player.name}")
            show_player_status(player)

            # Roll D6 and move
            steps = roll_display("D6", "Förflyttning")
            old_pos = player.position
            new_pos = old_pos + steps

            # Check if passing start (Stadsbyggnadskontoret)
            if new_pos > 24:
                new_pos = new_pos - 24
                player.laps += 1
                print(f"  → Passerar Stadsbyggnadskontoret! (varv {player.laps})")

                if player.laps >= 2:
                    print(f"\n  🏁 {player.name} har passerat start för andra gången!")
                    print("  Projektutvecklingen avslutas!")
                    game.game_over = True
                    player.position = new_pos
                    # Still resolve the square they land on
                    square = game.board[new_pos - 1]
                    handle_square(square, player, game)
                    break

            player.position = new_pos
            square = game.board[new_pos - 1]

            print(f"  → Flyttar från ruta {old_pos} → ruta {new_pos}")
            handle_square(square, player, game)

            pause()


def phase_namndbeslut(game: GameState) -> None:
    """Roll for nämnd decisions on all projects with nämnd > 1."""
    print("\n" + "=" * 60)
    print("  FAS 1c: NÄMNDBESLUT")
    print("=" * 60)
    print("  Alla projekt med nämndkrav > 1 måste klara ett D20-slag.\n")

    for player in game.players:
        projects_to_check = [p for p in player.projects if p.namndbeslut > 1]
        if not projects_to_check:
            print(f"  {player.name}: Inga projekt kräver nämndbeslut.")
            continue

        print(f"\n  {player.name} – nämndbeslut:")
        failed = []
        namnd_bonus = 0
        if player.projektchef and player.projektchef.namnd_bonus > 0:
            namnd_bonus = player.projektchef.namnd_bonus
            print(f"  {player.projektchef.namn} ger nämndbonus +{namnd_bonus}")
        for project in projects_to_check:
            result = roll_display("D20", f"{project.namn} (krav ≥{project.namndbeslut})")
            result += namnd_bonus
            if namnd_bonus > 0:
                print(f"  → +{namnd_bonus} nämndbonus = {result}")

            # Offer reroll with riskbuffert
            if result < project.namndbeslut and player.riskbuffertar > 0:
                if input_yes_no(f"  Misslyckat! Använd riskbuffert? ({player.riskbuffertar} kvar)"):
                    player.riskbuffertar -= 1
                    result = roll_display("D20", "Omslag")

            if result >= project.namndbeslut:
                print(f"  ✓ {project.namn} godkänt!")
            else:
                print(f"  ✗ {project.namn} AVSLAGET – lämnas tillbaka.")
                failed.append(project)

        for project in failed:
            player.projects.remove(project)
            player.q_krav -= project.kvalitet
            player.h_krav -= project.hallbarhet
            # Remove pending Rb from failed project
            if project.riskbuffert > 0:
                player.pending_riskbuffertar -= project.riskbuffert
            game.return_project(project)

    # Release pending riskbuffertar from projects
    for player in game.players:
        if player.pending_riskbuffertar > 0:
            player.riskbuffertar += player.pending_riskbuffertar
            print(f"\n  {player.name}: +{player.pending_riskbuffertar} riskbuffert(ar) "
                  f"från projekt frigivna (totalt: {player.riskbuffertar})")
            player.pending_riskbuffertar = 0

    pause()


def phase_placement(game: GameState) -> None:
    """Check project placement on tomt, remove excess projects."""
    print("\n" + "=" * 60)
    print("  FAS 1d: PLACERING PÅ TOMT")
    print("=" * 60)

    for player in game.players:
        total_form = player.total_formfaktor
        available = player.available_cells

        print(f"\n  {player.name}: {len(player.projects)} projekt | "
              f"BTA {player.total_bta} kvm | "
              f"Formfaktor {total_form}/{available} celler")

        # ── 1. Formfaktor-kontroll (befintlig) ──
        while player.total_formfaktor > player.available_cells:
            excess = player.total_formfaktor - player.available_cells
            print(f"  ⚠ Formfaktor-överskott: {excess} celler. Du måste lämna tillbaka projekt.")
            _force_return_project(player, game, "formfaktor")

        # ── 2. Max antal projekt ──
        while len(player.projects) > MAX_PROJECTS:
            print(f"  ⚠ {len(player.projects)} projekt (max {MAX_PROJECTS}). "
                  f"Du måste lämna tillbaka projekt.")
            _force_return_project(player, game, "antal")

        # ── 3. Max BTA ──
        while player.total_bta > MAX_BTA:
            print(f"  ⚠ BTA {player.total_bta} kvm (max {MAX_BTA}). "
                  f"Du måste lämna tillbaka projekt.")
            _force_return_project(player, game, "BTA")

        if player.projects:
            print(f"  ✓ Alla projekt ryms! ({len(player.projects)} st, "
                  f"{player.total_bta} kvm, "
                  f"{player.total_formfaktor}/{player.available_cells} celler)")
        else:
            print("  ⚠ Du har inga projekt!")

    pause()


def _force_return_project(player, game, reason: str) -> None:
    """Force player to return a project. Development cost already paid."""
    print("  Dina projekt:")
    for i, p in enumerate(player.projects):
        print(f"    {i + 1}. {p.display_short()}")

    idx = input_int("  Vilket projekt lämnar du tillbaka? ", 1, len(player.projects)) - 1
    project = player.projects.pop(idx)
    player.q_krav -= project.kvalitet
    player.h_krav -= project.hallbarhet
    game.return_project(project)
    print(f"  → Lämnade tillbaka {project.namn} (BTA:{project.bta}, form:{project.formfaktor}) "
          f"[{reason}] (utvecklingskostnad redan betald)")


def phase_ekonomi(game: GameState) -> None:
    """Final economic calculations for Phase 1."""
    print("\n" + "=" * 60)
    print("  FAS 1e: EKONOMISK SAMMANSTÄLLNING")
    print("=" * 60)

    for player in game.players:
        print(f"\n  {'═' * 50}")
        print(f"  {player.name} – Ekonomisk sammanställning")
        print(f"  {'═' * 50}")

        if not player.projects:
            print("  Inga projekt – ingen anskaffning.")
            continue

        # Sum fixed values (no dice roll - rörlig används vid förvaltningsstart)
        fast_summa = sum(p.anskaffning for p in player.projects)
        print(f"\n  Anskaffningskostnad: {fast_summa} Mkr")

        total_intakt = fast_summa
        print(f"  (Rörlig del avgörs vid förvaltningsstart)")

        # Fas 1 costs (deducted BEFORE EK/ABT split)
        mark_tomt_cost = MARK_TOMT_KOSTNAD if player.has_mark_tomt else 0
        expansion_cost = player.expansion_events * EXPANSION_KOSTNAD
        dev_cost = sum(p.kostnad for p in player.projects)

        print(f"\n  Fas 1-kostnader (dras före EK/ABT-uppdelning):")
        print(f"    Mark & tomt: {mark_tomt_cost} Mkr")
        if expansion_cost > 0:
            print(f"    Markexpansioner: {expansion_cost} Mkr")
        print(f"    Utvecklingskostnader: {dev_cost} Mkr")
        total_cost = mark_tomt_cost + expansion_cost + dev_cost
        print(f"    Totala Fas 1-kostnader: {total_cost} Mkr")

        # Net after Fas 1 costs
        netto = total_intakt - total_cost
        print(f"\n  Netto efter Fas 1-kostnader: {netto:.1f} Mkr")

        # EK = 0 vid start. Allt netto → ABT.
        # Förskott (tärning + BRF-bonus) betalas ut vid förvaltningsstart.
        ek = 0
        abt = netto
        player.eget_kapital = ek
        player.abt_budget = abt
        player.abt_start = abt
        player.total_revenue = total_intakt

        print(f"\n  Allt netto → ABT-budget (EK byggs upp via förskott vid förvaltningsstart)")
        print(f"    Eget kapital (EK): {ek:.1f} Mkr")
        print(f"    ABT-budget: {abt:.1f} Mkr")

        # BTA and BYA class
        print(f"\n  BTA-klass: {player.bta_klass()} (total BTA: {player.total_bta} kvm)")
        print(f"  BYA-klass: {player.bya_klass()} (total BYA: {player.total_bya} kvm)")

        # Show final project list
        print(f"\n  Kvarter ({len(player.projects)} projekt):")
        for p in player.projects:
            print(f"    • {p.namn} | BTA:{p.bta} | Anskaff:{p.anskaffning} MV:{p.marknadsvarde} | "
                  f"Q:{p.kvalitet} H:{p.hallbarhet} T:{p.tid}")

        print(f"\n  Q-krav: {player.q_krav} | H-krav: {player.h_krav}")
        print(f"  Riskbuffertar: {player.riskbuffertar}")

        # ── Riskbuffert-investering: sänk Q/H/T-krav ──
        if player.riskbuffertar > 0:
            print(f"\n  ── RISKBUFFERT-INVESTERING ──")
            print(f"  Du har {player.riskbuffertar} riskbuffert(ar).")
            print(f"  Varje Rb sänker Q-krav, H-krav eller T med 1.")
            print(f"  (Kvarvarande Rb sparas till genomförande.)")

            while player.riskbuffertar > 0:
                print(f"\n  Rb kvar: {player.riskbuffertar} | "
                      f"Q-krav: {player.q_krav} | H-krav: {player.h_krav} | "
                      f"T-bonus: {player.t_bonus} mån")
                print(f"    1. Sänk Q-krav (-1)")
                print(f"    2. Sänk H-krav (-1)")
                print(f"    3. Sänk T (-1 mån)")
                print(f"    0. Spara resterande Rb")
                choice = input_int("  Val: ", 0, 3)
                if choice == 0:
                    break
                elif choice == 1:
                    player.q_krav = max(0, player.q_krav - 1)
                    player.riskbuffertar -= 1
                    print(f"    → Q-krav sänkt till {player.q_krav}")
                elif choice == 2:
                    player.h_krav = max(0, player.h_krav - 1)
                    player.riskbuffertar -= 1
                    print(f"    → H-krav sänkt till {player.h_krav}")
                elif choice == 3:
                    player.t_bonus += 1
                    player.riskbuffertar -= 1
                    print(f"    → T-bonus: -{player.t_bonus} mån")

            print(f"\n  Slutliga krav: Q:{player.q_krav} H:{player.h_krav} "
                  f"T-bonus:-{player.t_bonus} mån | "
                  f"Rb kvar: {player.riskbuffertar}")

    pause()


def phase_summary(game: GameState) -> None:
    """Show final Phase 1 summary for all players."""
    print("\n" + "=" * 60)
    print("  SAMMANFATTNING – Fas 1: Projektutveckling")
    print("=" * 60)

    for player in game.players:
        print(f"\n  {player.name}:")
        print(f"    Projekt: {len(player.projects)} st")
        print(f"    Total BTA: {player.total_bta} kvm ({player.bta_klass()})")
        print(f"    Total BYA: {player.total_bya} kvm ({player.bya_klass()})")
        print(f"    Q-krav: {player.q_krav} | H-krav: {player.h_krav} | T-bonus: -{player.t_bonus} mån")
        print(f"    EK: {player.eget_kapital:.1f} Mkr | ABT: {player.abt_budget:.1f} Mkr")
        print(f"    Riskbuffertar: {player.riskbuffertar}")

    print("\n  ─── Fas 1 avslutad! ───")
    print("  Nästa steg: Fas 2 – Projektplanering")


# ─────────────────────────────────────────────
# PHASE 2: PROJEKTPLANERING
# ─────────────────────────────────────────────

def get_min_supplier_level(player: Player, supplier_type: str) -> int:
    """Determine minimum supplier level based on project requirements.

    Each project may specify a requirement text for a supplier type.
    That text matches a supplier's 'beskrivning' which determines its level.
    The strictest (highest level) requirement across all projects applies.
    """
    # Column indices for supplier requirements in project data
    # We stored projects as Project objects, but the requirement texts
    # are in the original CSV columns 20-28. We need to re-check the CSV.
    # Instead, let's store them on the project. For now, we use a lookup.
    # Actually, we need to load these from the CSV at startup.
    # This is handled via SUPPLIER_REQUIREMENTS loaded at game start.
    reqs = SUPPLIER_REQUIREMENTS.get(supplier_type, {})
    min_level = 1
    for proj in player.projects:
        req_text = reqs.get(proj.namn, "")
        if req_text:
            # Find which supplier level matches this requirement text
            suppliers = ALL_SUPPLIERS.get(supplier_type, [])
            for s in suppliers:
                if s.beskrivning.lower() == req_text.lower():
                    min_level = max(min_level, s.niva)
                    break
    return min_level


def load_supplier_requirements() -> Dict[str, Dict[str, str]]:
    """Load project -> supplier requirement mappings from PU_projekt.csv.

    Returns: {supplier_type: {project_name: requirement_text}}
    """
    filepath = data_path("projekt")
    # Supplier type columns in CSV (looked up by header name)
    supplier_col_names = [
        "MARK", "HUSUNDERBYGGNAD", "STOMME",
        "YTTERTAK", "FASADER", "STOMKOMPLETTERING",
        "INV YTSKIKT", "INSTALLATIONER", "GEMENSAMMA ARBETEN",
    ]
    reqs: Dict[str, Dict[str, str]] = {t: {} for t in supplier_col_names}

    with safe_open_csv(filepath) as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(reader)]
        col = {name: i for i, name in enumerate(header)}

        for cols in reader:
            if not cols[0].strip():
                continue
            proj_namn = cols[0].strip()
            for typ in supplier_col_names:
                idx = col.get(typ)
                if idx is not None and idx < len(cols) and cols[idx].strip():
                    reqs[typ][proj_namn] = cols[idx].strip()

    return reqs


# Global lookups populated at game start
SUPPLIER_REQUIREMENTS: Dict[str, Dict[str, str]] = {}
ALL_SUPPLIERS: Dict[str, List[Supplier]] = {}
ALL_ORGANISATIONS: Dict[str, List[Organisation]] = {}
ALL_PLANNING_EVENTS: Dict[str, List[PlanningEventCard]] = {}


def parse_planning_effect(effect_text: str, player: Player, bta_klass: str) -> None:
    """Parse and apply a planning event card effect.

    Effects look like:
    - "Stora förseningar: -8 Mkr, +2 mån"
    - "Klass A-B: -4 Mkr, +1 mån // Klass C-D: -8 Mkr, +1 mån"
    - "Förbättrad samordning: +1 Rb"
    - "+1 Q", "+1 H", "-1 mån"
    """
    if not effect_text or effect_text.lower() == "ingen effekt":
        print("    → Ingen effekt.")
        return

    text = effect_text

    # Handle scaled effects: pick the right branch based on BTA class
    if "//" in text:
        parts = text.split("//")
        klass_upper = bta_klass.upper()
        chosen = parts[0].strip()  # default to first
        for part in parts:
            part_stripped = part.strip()
            if klass_upper in ("A", "B") and "A-B" in part_stripped:
                chosen = part_stripped
                break
            elif klass_upper in ("C", "D") and "C-D" in part_stripped:
                chosen = part_stripped
                break
        text = chosen

    # Remove the label prefix (e.g., "Stora förseningar: ")
    if ":" in text:
        text = text.split(":", 1)[1].strip()

    print(f"    → {effect_text}")

    # Parse Mkr → deduct from ABT budget (falls back to EK if ABT runs out)
    mkr_matches = re.findall(r'([+-]?\d+)\s*Mkr', text)
    for m in mkr_matches:
        val = int(m)
        player.abt_budget += val
        if player.abt_budget < 0:
            handle_abt_overflow(player)
        else:
            print(f"      ABT {val:+d} Mkr (ABT: {player.abt_budget:.1f} Mkr)")

    # Parse months
    mon_matches = re.findall(r'([+-]?\d+)\s*mån', text)
    for m in mon_matches:
        val = int(m)
        player.pl_t = max(MIN_T, player.pl_t + val)
        print(f"      Tid {val:+d} mån (nu: {player.pl_t} mån)")

    # Parse Q
    q_matches = re.findall(r'([+-]?\d+)\s*Q', text)
    for m in q_matches:
        val = int(m)
        player.pl_q += val
        print(f"      Q {val:+d} (nu: {player.pl_q})")

    # Parse H
    h_matches = re.findall(r'([+-]?\d+)\s*H', text)
    for m in h_matches:
        val = int(m)
        player.pl_h += val
        print(f"      H {val:+d} (nu: {player.pl_h})")

    # Parse Riskbuffert
    rb_matches = re.findall(r'([+-]?\d+)\s*Rb', text)
    for m in rb_matches:
        val = int(m)
        player.riskbuffertar += val
        print(f"      Riskbuffert {val:+d} (nu: {player.riskbuffertar})")


def handle_planning_event(player: Player, draw_pile: List[PlanningEventCard],
                          discard_pile: List[PlanningEventCard]) -> None:
    """Draw and resolve one planning event card."""
    if not draw_pile:
        print("    Inga händelsekort kvar i draghögen.")
        return

    card = draw_pile.pop(0)
    discard_pile.append(card)

    print(f"\n    📋 HÄNDELSE: {card.namn}")
    print(f"       {card.beskrivning}")
    print(f"       Typ: {card.typ} | Trigger: {card.trigger}")
    print(f"       Erfarenhet räknas från: {card.summering}")

    # Check if card is eligible for this player
    if not player.card_is_eligible(card):
        print(f"    → Kortet aktiveras inte (kräver {card.trigger}, "
              f"du har {player.kvarter_trigger()}).")
        return

    # Calculate relevant experience
    exp = player.relevant_erfarenhet(card.summering)
    print(f"    Relevant erfarenhet: {exp}")

    # Roll D20 + experience
    d20 = roll_display("D20", "Händelsekort")
    total = d20 + exp
    print(f"    Totalt: {d20} + {exp} erfarenhet = {total}")

    # Offer reroll with riskbuffert
    if player.riskbuffertar > 0 and total <= 5:
        if input_yes_no(f"    Använd riskbuffert för att slå om? ({player.riskbuffertar} kvar)"):
            player.riskbuffertar -= 1
            d20 = roll_display("D20", "Omslag")
            total = d20 + exp
            print(f"    Nytt totalt: {d20} + {exp} = {total}")

    # Get effect
    effect = card.get_effect(total)

    # Determine BTA class for scaled effects
    bta_klass = player.bta_klass()

    parse_planning_effect(effect, player, bta_klass)


def show_planning_status(player: Player) -> None:
    """Show player's current planning status."""
    print(f"\n  ┌─── {player.name} – Planeringsstatus ─────────")
    print(f"  │ Kvarter: {player.kvarter_trigger()} | "
          f"BTA-klass: {player.bta_klass()} | BYA-klass: {player.bya_klass()}")
    print(f"  │ Q: {player.pl_q} (krav: {player.q_krav}) | "
          f"H: {player.pl_h} (krav: {player.h_krav}) | "
          f"T: {player.pl_t} mån (mål: ≤12)")
    # TG = (verklig ABT kvar - lånekostnader) / ABT start
    real_remaining = player.abt_budget - player.abt_loans_net
    tb = real_remaining - player.abt_borrowing_cost
    tg_real = (tb / player.abt_start * 100) if player.abt_start > 0 else 0
    print(f"  │ ABT-budget: {player.abt_budget:.1f} Mkr (start: {player.abt_start:.0f}) | "
          f"TG: {tg_real:.0f}% | "
          f"EK: {player.eget_kapital:.1f} Mkr | "
          f"Riskbuffertar: {player.riskbuffertar}")
    print(f"  │ Erfarenhet: {player.total_erfarenhet()}")

    if player.pl_suppliers:
        print(f"  │ Leverantörer:")
        for namn, s in player.pl_suppliers.items():
            print(f"  │   • {namn}: {s.beskrivning} (nivå {s.niva})")
    if player.pl_orgs:
        print(f"  │ Organisation:")
        for namn, o in player.pl_orgs.items():
            print(f"  │   • {namn}: nivå {o.niva}")
    print(f"  └{'─' * 50}")


def choose_supplier(player: Player, supplier_type: str, game: GameState) -> None:
    """Let player choose a supplier for a given type."""
    all_options = ALL_SUPPLIERS.get(supplier_type, [])
    if not all_options:
        print(f"  Inga leverantörer av typen {supplier_type}.")
        return

    # Determine BYA/BTA class
    beror_av = all_options[0].beror_av
    klass = player.bya_klass() if beror_av == "BYA" else player.bta_klass()

    # Filter by project requirements (minimum level)
    min_level = get_min_supplier_level(player, supplier_type)

    available = [s for s in all_options if s.niva >= min_level]
    if not available:
        print(f"  ⚠ Inga leverantörer uppfyller kraven (miniminivå {min_level}).")
        return

    # Check which ones player can afford without Q/H going below 0
    print(f"\n  ── {supplier_type} ({beror_av}-klass {klass}) ──")
    if min_level > 1:
        print(f"  Projektkrav: miniminivå {min_level}")

    for i, s in enumerate(available):
        # Check if choosing this would push Q or H below 0
        new_q = player.pl_q + s.q
        new_h = player.pl_h + s.h
        blocked = ""
        if new_q < 0 or new_h < 0:
            blocked = " ⛔ (Q eller H går under 0)"
        print(f"    {i + 1}. {s.display(klass)}{blocked}")

    while True:
        choice = input_int(f"  Välj leverantör (1-{len(available)}): ", 1, len(available))
        chosen = available[choice - 1]

        # Validate Q/H constraint
        new_q = player.pl_q + chosen.q
        new_h = player.pl_h + chosen.h
        if new_q < 0 or new_h < 0:
            print(f"  ⛔ Kan inte välja – Q ({player.pl_q}{chosen.q:+d}={new_q}) "
                  f"eller H ({player.pl_h}{chosen.h:+d}={new_h}) går under 0.")
            print(f"  Välj en annan.")
            continue
        break

    # Apply
    kostnad = chosen.kostnad(klass)
    player.pl_suppliers[supplier_type] = chosen
    player.pl_q += chosen.q
    player.pl_h += chosen.h
    player.pl_t = max(MIN_T, player.pl_t + chosen.t)
    player.pl_kostnad += kostnad
    player.abt_budget -= kostnad
    abt_warn = ""
    if player.abt_budget < 0:
        handle_abt_overflow(player)
        abt_warn = " ⚠ Moderbolagstillskott!"

    print(f"\n  ✓ Valde {chosen.beskrivning} (nivå {chosen.niva})")
    print(f"    Kostnad: {kostnad} Mkr | Q:{chosen.q:+d} H:{chosen.h:+d} T:{chosen.t:+d} | "
          f"Erfarenhet:{chosen.erfarenhet:+d}")
    print(f"    ABT kvar: {player.abt_budget:.1f} Mkr{abt_warn}")
    if chosen.riskbuffert if hasattr(chosen, 'riskbuffert') else False:
        player.riskbuffertar += chosen.riskbuffert
        print(f"    +{chosen.riskbuffert} riskbuffert")


def choose_organisation(player: Player, org_type: str, game: GameState) -> None:
    """Let player choose an organisation for a given type."""
    all_options = ALL_ORGANISATIONS.get(org_type, [])
    if not all_options:
        print(f"  Inga organisationer av typen {org_type}.")
        return

    print(f"\n  ── {org_type} ──")

    for i, o in enumerate(all_options):
        new_q = player.pl_q + o.q
        new_h = player.pl_h + o.h
        blocked = ""
        if new_q < 0 or new_h < 0:
            blocked = " ⛔ (Q eller H går under 0)"
        print(f"    {i + 1}. {o.display()}{blocked}")

    while True:
        choice = input_int(f"  Välj organisation (1-{len(all_options)}): ", 1, len(all_options))
        chosen = all_options[choice - 1]

        new_q = player.pl_q + chosen.q
        new_h = player.pl_h + chosen.h
        if new_q < 0 or new_h < 0:
            print(f"  ⛔ Kan inte välja – Q ({player.pl_q}{chosen.q:+d}={new_q}) "
                  f"eller H ({player.pl_h}{chosen.h:+d}={new_h}) går under 0.")
            print(f"  Välj en annan.")
            continue
        break

    # Apply
    player.pl_orgs[org_type] = chosen
    player.pl_q += chosen.q
    player.pl_h += chosen.h
    player.pl_t = max(MIN_T, player.pl_t + chosen.t)
    player.pl_kostnad += chosen.kostnad_mkr
    player.abt_budget -= chosen.kostnad_mkr
    abt_warn = ""
    if player.abt_budget < 0:
        handle_abt_overflow(player)
        abt_warn = " ⚠ Moderbolagstillskott!"
    if chosen.riskbuffert:
        player.riskbuffertar += chosen.riskbuffert

    print(f"\n  ✓ Valde {org_type} nivå {chosen.niva}")
    print(f"    Kostnad: {chosen.kostnad_mkr} Mkr | Q:{chosen.q:+d} H:{chosen.h:+d} T:{chosen.t:+d} | "
          f"Erfarenhet:{chosen.erfarenhet:+d}")
    print(f"    ABT kvar: {player.abt_budget:.1f} Mkr{abt_warn}")
    if chosen.riskbuffert:
        print(f"    +{chosen.riskbuffert} riskbuffert")


def offer_swap_supplier(player: Player, game: GameState) -> None:
    """Offer to swap a previously chosen supplier during planning."""
    if not player.pl_suppliers:
        return

    if not input_yes_no("\n  Vill du byta en leverantör?"):
        return

    print("  Dina leverantörer:")
    names = list(player.pl_suppliers.keys())
    for i, namn in enumerate(names):
        s = player.pl_suppliers[namn]
        beror_av = s.beror_av
        klass = player.bya_klass() if beror_av == "BYA" else player.bta_klass()
        print(f"    {i + 1}. {namn}: {s.display(klass)}")

    idx = input_int(f"  Vilken vill du byta? (1-{len(names)}, 0 = avbryt): ", 0, len(names))
    if idx == 0:
        return

    supplier_type = names[idx - 1]
    old = player.pl_suppliers[supplier_type]

    # Reverse old supplier's Q/H/T effects
    player.pl_q -= old.q
    player.pl_h -= old.h
    player.pl_t = max(MIN_T, player.pl_t - old.t)
    # Note: old cost is sunk - not refunded

    # Remove the old supplier temporarily
    del player.pl_suppliers[supplier_type]

    # Choose new one (pays full price)
    choose_supplier(player, supplier_type, game)

    if supplier_type not in player.pl_suppliers:
        # Player couldn't choose - restore old
        player.pl_suppliers[supplier_type] = old
        player.pl_q += old.q
        player.pl_h += old.h
        player.pl_t = max(MIN_T, player.pl_t + old.t)
        print("  Byte avbrutet, behåller gammal leverantör.")


def phase_planering(game: GameState) -> None:
    """Execute Phase 2: Projektplanering for all players."""
    global ALL_SUPPLIERS, ALL_ORGANISATIONS, ALL_PLANNING_EVENTS, SUPPLIER_REQUIREMENTS

    print("\n" + "=" * 60)
    print("  FAS 2: PROJEKTPLANERING")
    print("=" * 60)

    # Load Phase 2 data
    print("\n  Laddar planeringsdata...")
    ALL_SUPPLIERS = load_suppliers()
    ALL_ORGANISATIONS = load_organisations()
    ALL_PLANNING_EVENTS = load_planning_events()
    SUPPLIER_REQUIREMENTS = load_supplier_requirements()

    print(f"    Leverantörstyper: {len(ALL_SUPPLIERS)} "
          f"({sum(len(v) for v in ALL_SUPPLIERS.values())} kort)")
    print(f"    Organisationstyper: {len(ALL_ORGANISATIONS)} "
          f"({sum(len(v) for v in ALL_ORGANISATIONS.values())} kort)")
    print(f"    Händelsekort: {sum(len(v) for v in ALL_PLANNING_EVENTS.values())} st")

    # Each player does planning independently
    for player in game.players:
        print(f"\n{'═' * 60}")
        print(f"  {player.name} – PROJEKTPLANERING")
        print(f"{'═' * 60}")

        # Välj arbetschef
        pc_ac = load_pc_ac()
        acs = pc_ac.get("AC", [])
        if acs:
            print(f"\n  ── Välj Arbetschef ──")
            for i, ac in enumerate(acs, 1):
                print(f"    {i}. {ac.display()}")
            choice = input_int(f"  Välj arbetschef (1-{len(acs)}): ", 1, len(acs))
            chosen_ac = acs[choice - 1]
            player.arbetschef = chosen_ac
            player.riskbuffertar += chosen_ac.rb_bonus
            extras = []
            if chosen_ac.q_bonus: extras.append(f"+{chosen_ac.q_bonus} Q")
            if chosen_ac.h_bonus: extras.append(f"+{chosen_ac.h_bonus} H")
            if chosen_ac.t_bonus: extras.append(f"-{chosen_ac.t_bonus} T")
            extras.append(f"+{chosen_ac.rb_bonus} Rb")
            print(f"  ✓ {chosen_ac.namn} ({chosen_ac.specialisering}) "
                  f"ansluter som arbetschef ({', '.join(extras)})")

        # Initialize planning markers
        max_t = max((p.tid for p in player.projects), default=0)
        # Apply PC + AC Q/H/T bonuses
        pc_q = player.projektchef.q_bonus if player.projektchef else 0
        pc_h = player.projektchef.h_bonus if player.projektchef else 0
        pc_t = player.projektchef.t_bonus if player.projektchef else 0
        ac_q = player.arbetschef.q_bonus if player.arbetschef else 0
        ac_h = player.arbetschef.h_bonus if player.arbetschef else 0
        ac_t = player.arbetschef.t_bonus if player.arbetschef else 0
        start_q = pc_q + ac_q
        start_h = pc_h + ac_h
        start_t_bonus = player.t_bonus + pc_t + ac_t

        player.pl_q = start_q
        player.pl_h = start_h
        player.pl_t = 12 + max_t - start_t_bonus
        player.pl_kostnad = 0.0

        print(f"\n  Projektmål satta:")
        q_from = f" ({pc_q} PC + {ac_q} AC)" if start_q > 0 else ""
        h_from = f" ({pc_h} PC + {ac_h} AC)" if start_h > 0 else ""
        print(f"    Q: {start_q} (krav: {player.q_krav}){q_from}")
        print(f"    H: {start_h} (krav: {player.h_krav}){h_from}")
        t_parts = [f"12 + {max_t}"]
        if player.t_bonus > 0: t_parts.append(f"- {player.t_bonus} Rb")
        if pc_t + ac_t > 0: t_parts.append(f"- {pc_t + ac_t} PC/AC")
        print(f"    T: {player.pl_t} mån ({' '.join(t_parts)})")
        print(f"    Kvartertyp: {player.kvarter_trigger()}")

        # Build the shared draw pile for event cards
        # Start with all eligible cards, shuffled
        all_event_cards: List[PlanningEventCard] = []
        for card_list in ALL_PLANNING_EVENTS.values():
            for card in card_list:
                all_event_cards.append(card)

        draw_pile: List[PlanningEventCard] = []
        discard_pile: List[PlanningEventCard] = []

        # Process each step in order
        for step_idx, (slot_name, slot_type) in enumerate(PLANNING_ORDER):
            step_num = step_idx + 1
            print(f"\n{'─' * 60}")
            print(f"  STEG {step_num}/13: {slot_name} "
                  f"({'Organisation' if slot_type == 'org' else 'Leverantör'})")

            show_planning_status(player)

            # 1. Add this slot's event cards to the draw pile and shuffle
            card_ids = SLOT_TO_CARD_IDS.get(slot_name, [])
            new_cards = []
            for cid in card_ids:
                new_cards.extend(ALL_PLANNING_EVENTS.get(cid, []))

            if new_cards:
                draw_pile.extend(new_cards)
                random.shuffle(draw_pile)
                print(f"\n  +{len(new_cards)} händelsekort tillagda i draghögen "
                      f"(totalt: {len(draw_pile)})")

            # 2. Choose supplier or organisation
            if slot_type == "lev":
                choose_supplier(player, slot_name, game)
            else:
                choose_organisation(player, slot_name, game)

            # 3. Draw one event card
            print(f"\n  Drar händelsekort...")
            handle_planning_event(player, draw_pile, discard_pile)

            # 4. Leverantörsbyte borttaget

            pause()

        # Planning complete - save leftover event cards for Fas 3
        game.pl_draw_piles[player.name] = draw_pile
        game.pl_discard_piles[player.name] = discard_pile

        # Planning complete - show summary
        print(f"\n{'═' * 60}")
        print(f"  {player.name} – PLANERING KLAR")
        print(f"{'═' * 60}")
        show_planning_status(player)

        # Check targets
        q_ok = "✓" if player.pl_q >= player.q_krav else "✗"
        h_ok = "✓" if player.pl_h >= player.h_krav else "✗"
        t_ok = "✓" if player.pl_t <= 12 else "✗"

        print(f"\n  Resultat:")
        print(f"    {q_ok} Kvalitet: {player.pl_q} / {player.q_krav}")
        print(f"    {h_ok} Hållbarhet: {player.pl_h} / {player.h_krav}")
        print(f"    {t_ok} Tid: {player.pl_t} mån (mål: ≤12)")
        print(f"    Planeringskostnad: {player.pl_kostnad:.1f} Mkr")
        print(f"    ABT kvar: {player.abt_budget:.1f} Mkr")
        print(f"    EK: {player.eget_kapital:.1f} Mkr")

        pause()

    # Summary for all players
    print("\n" + "=" * 60)
    print("  SAMMANFATTNING – Fas 2: Projektplanering")
    print("=" * 60)

    for player in game.players:
        print(f"\n  {player.name}:")
        print(f"    Q: {player.pl_q}/{player.q_krav} | "
              f"H: {player.pl_h}/{player.h_krav} | T: {player.pl_t} mån")
        print(f"    Planeringskostnad: {player.pl_kostnad:.1f} Mkr")
        print(f"    ABT kvar: {player.abt_budget:.1f} Mkr | EK: {player.eget_kapital:.1f} Mkr | Rb: {player.riskbuffertar}")
        print(f"    Erfarenhet: {player.total_erfarenhet()}")
        print(f"    Leverantörer: "
              + ", ".join(f"{n} (niv {s.niva})" for n, s in player.pl_suppliers.items()))
        print(f"    Organisation: "
              + ", ".join(f"{n} (niv {o.niva})" for n, o in player.pl_orgs.items()))

    print("\n  ─── Fas 2 avslutad! ───")
    print("  Nästa steg: Fas 3 – Projektgenomförande")

    # Snapshot Q/H/T after planning
    for player in game.players:
        player.snap_plan_q = player.pl_q
        player.snap_plan_h = player.pl_h
        player.snap_plan_t = player.pl_t


# ─────────────────────────────────────────────
# PHASE 3: PROJEKTGENOMFÖRANDE
# ─────────────────────────────────────────────

def parse_competence_req(req_text: str) -> Dict[str, int]:
    """Parse competence requirements like 'SAM 3, LED 2' into dict."""
    reqs: Dict[str, int] = {}
    if not req_text or req_text.strip() in ("—", "— (skippa)", ""):
        return reqs
    parts = [p.strip() for p in req_text.split(",")]
    for part in parts:
        tokens = part.strip().split()
        if len(tokens) == 2 and tokens[0] in ("STA", "KOM", "SAM", "NOG", "INN", "ABM"):
            try:
                reqs[tokens[0]] = int(tokens[1])
            except ValueError:
                pass
    return reqs


def get_available_competence_cards(player: Player) -> List[Dict]:
    """Get all cards the player can still play for competence.

    Returns list of dicts: {source, key, kompetenser, display}
    Leverantörer get kompetens bonus based on BYA/BTA class:
      A/B: +0, C: +1, D: +2 on all kompetens values.
    """
    CLASS_KOMP_BONUS = {"A": 0, "B": 0, "C": 1, "D": 2}

    cards = []
    # Unused suppliers
    for namn, s in player.pl_suppliers.items():
        if namn not in player.used_supplier_keys:
            # Apply class-based kompetens bonus
            klass = player.bya_klass() if s.beror_av == "BYA" else player.bta_klass()
            bonus = CLASS_KOMP_BONUS.get(klass, 0)
            komp = {k: v + bonus if v > 0 else v for k, v in s.kompetenser.items()}
            bonus_str = f" [+{bonus} klass {klass}]" if bonus > 0 else ""
            cards.append({
                "source": "supplier", "key": namn,
                "kompetenser": komp,
                "display": f"Lev: {namn} (niv {s.niva}) – "
                           + ", ".join(f"{k}:{v}" for k, v in komp.items() if v > 0)
                           + bonus_str,
            })
    # Unused organisations
    for namn, o in player.pl_orgs.items():
        if namn not in player.used_org_keys:
            cards.append({
                "source": "org", "key": namn,
                "kompetenser": dict(o.kompetenser),
                "display": f"Org: {namn} (niv {o.niva}) – "
                           + ", ".join(f"{k}:{v}" for k, v in o.kompetenser.items() if v > 0),
            })
    # External support in hand (not yet played)
    for i, ext in enumerate(player.external_hand):
        cards.append({
            "source": "external", "key": i,
            "kompetenser": dict(ext.kompetenser),
            "display": f"Ext: {ext.display()}",
        })
    # Arbetschef (can be played once as competence card)
    if player.arbetschef and "ac" not in player.used_org_keys:
        ac = player.arbetschef
        if ac.kompetenser:
            cards.append({
                "source": "ac", "key": "ac",
                "kompetenser": dict(ac.kompetenser),
                "display": f"AC: {ac.namn} ({ac.specialisering}) – "
                           + ", ".join(f"{k}:{v}" for k, v in ac.kompetenser.items() if v > 0),
            })
    return cards


def play_cards_for_requirement(player: Player, reqs: Dict[str, int]) -> bool:
    """Let player play cards to fulfil competence requirements.

    Returns True if requirements were met.
    Cards are returned if the player aborts.
    """
    fulfilled: Dict[str, int] = {k: 0 for k in reqs}

    # Track what was played this attempt (for undo on abort)
    played_supplier_keys: List[str] = []
    played_org_keys: List[str] = []
    played_external: List[ExternalSupport] = []

    while True:
        # Show remaining requirements
        remaining = {k: v - fulfilled[k] for k, v in reqs.items() if fulfilled[k] < v}
        if not remaining:
            print("    ✓ Alla krav uppfyllda!")
            return True

        print(f"\n    Kvar att uppfylla: "
              + ", ".join(f"{k} {v}" for k, v in remaining.items()))

        available = get_available_competence_cards(player)
        if not available:
            print("    ⚠ Inga kort kvar att spela!")
            # Undo all played cards
            for key in played_supplier_keys:
                player.used_supplier_keys.remove(key)
            for key in played_org_keys:
                player.used_org_keys.remove(key)
            for ext in played_external:
                player.external_hand.append(ext)
                player.used_external.remove(ext)
            return False

        print("    Tillgängliga kort:")
        for i, c in enumerate(available):
            # Show which requirements this card can contribute to
            useful = {k: min(v, remaining.get(k, 0))
                      for k, v in c["kompetenser"].items() if remaining.get(k, 0) > 0}
            useful_str = f" → uppfyller {useful}" if useful else ""
            print(f"      {i + 1}. {c['display']}{useful_str}")
        print(f"      0. Avbryt (korten returneras)")

        choice = input_int(f"    Spela kort (0-{len(available)}): ", 0, len(available))
        if choice == 0:
            # Undo all played cards this attempt
            for key in played_supplier_keys:
                player.used_supplier_keys.remove(key)
            for key in played_org_keys:
                player.used_org_keys.remove(key)
            for ext in played_external:
                player.external_hand.append(ext)
                player.used_external.remove(ext)
            print("    Kort returnerade.")
            return False

        card = available[choice - 1]

        # Mark card as used and track for undo
        if card["source"] == "supplier":
            player.used_supplier_keys.append(card["key"])
            played_supplier_keys.append(card["key"])
        elif card["source"] == "org":
            player.used_org_keys.append(card["key"])
            played_org_keys.append(card["key"])
        elif card["source"] == "ac":
            player.used_org_keys.append("ac")
            played_org_keys.append("ac")
        elif card["source"] == "external":
            idx = card["key"]
            ext = player.external_hand.pop(idx)
            player.used_external.append(ext)
            played_external.append(ext)

        # Apply competences (can't "change" – all values used even if wasted)
        for k, v in card["kompetenser"].items():
            if k in fulfilled:
                fulfilled[k] += v
                print(f"      {k}: {fulfilled[k]}/{reqs[k]}"
                      + (" ✓" if fulfilled[k] >= reqs[k] else ""))

    return False


def apply_phase_effect(effect_text: str, player: Player) -> None:
    """Apply a faskort effect (similar to planning effects but also handles T)."""
    if not effect_text or effect_text.strip() == "0":
        print("    → Ingen effekt.")
        return

    print(f"    → {effect_text}")

    # Parse Mkr
    mkr_matches = re.findall(r'([+-]?\d+)\s*Mkr', effect_text)
    for m in mkr_matches:
        val = int(m)
        player.abt_budget += val
        if player.abt_budget < 0:
            handle_abt_overflow(player)
        else:
            print(f"      ABT {val:+d} Mkr (ABT: {player.abt_budget:.1f} Mkr)")

    # Parse months
    mon_matches = re.findall(r'([+-]?\d+)\s*mån', effect_text)
    for m in mon_matches:
        val = int(m)
        player.pl_t = max(MIN_T, player.pl_t + val)
        print(f"      Tid {val:+d} mån (nu: {player.pl_t} mån)")

    # Parse Q
    q_matches = re.findall(r'([+-]?\d+)\s*Q', effect_text)
    for m in q_matches:
        val = int(m)
        player.pl_q += val
        print(f"      Q {val:+d} (nu: {player.pl_q})")

    # Parse H
    h_matches = re.findall(r'([+-]?\d+)\s*H', effect_text)
    for m in h_matches:
        val = int(m)
        player.pl_h += val
        print(f"      H {val:+d} (nu: {player.pl_h})")

    # Parse T (direct, e.g. "-1 T")
    t_matches = re.findall(r'([+-]?\d+)\s*T', effect_text)
    for m in t_matches:
        val = int(m)
        player.pl_t = max(MIN_T, player.pl_t + val)
        print(f"      Tid {val:+d} mån (nu: {player.pl_t} mån)")

    # Parse Rb
    rb_matches = re.findall(r'([+-]?\d+)\s*Rb', effect_text)
    for m in rb_matches:
        val = int(m)
        player.riskbuffertar = max(0, player.riskbuffertar + val)
        print(f"      Riskbuffert {val:+d} (nu: {player.riskbuffertar})")


def downgrade_energy_class(player: Player, count: int) -> None:
    """Downgrade energy class on 'count' projects.

    Rule: highest class first, ties broken by highest marknadsvärde first.
    """
    if count <= 0:
        return

    # Sort projects: highest energy class first, then highest marknadsvärde
    def sort_key(namn):
        klass = player.projekt_energiklass.get(namn, "C")
        proj = next((p for p in player.projects if p.namn == namn), None)
        mv = proj.marknadsvarde if proj else 0
        class_idx = ENERGY_CLASSES.index(klass) if klass in ENERGY_CLASSES else 3
        return (class_idx, -mv)  # lowest index = highest class = downgraded first

    project_names = sorted(player.projekt_energiklass.keys(), key=sort_key)

    downgraded = 0
    for namn in project_names:
        if downgraded >= count:
            break
        klass = player.projekt_energiklass[namn]
        idx = ENERGY_CLASSES.index(klass) if klass in ENERGY_CLASSES else 3
        if idx < len(ENERGY_CLASSES) - 1:
            new_klass = ENERGY_CLASSES[idx + 1]
            player.projekt_energiklass[namn] = new_klass
            print(f"      {namn}: Energiklass {klass} → {new_klass}")
            downgraded += 1

    if downgraded < count:
        print(f"      (Kunde bara sänka {downgraded} av {count} projekt)")


def apply_penalty(card: PenaltyCard, player: Player, label: str = "STRAFF") -> None:
    """Apply a penalty/garanti card using D20 + experience."""
    print(f"\n    🔴 {label}: {card.namn}")

    exp = player.total_erfarenhet()
    d20 = roll_display("D20", f"{card.namn}")
    total = d20 + exp
    print(f"    D20: {d20} + erfarenhet {exp} = {total}")

    # Offer reroll with riskbuffert on worst tier
    if player.riskbuffertar > 0 and total <= D20_THRESHOLDS[0]:
        if input_yes_no(f"    Använd riskbuffert för omslag? ({player.riskbuffertar} kvar)"):
            player.riskbuffertar -= 1
            d20 = roll_display("D20", "Omslag")
            total = d20 + exp
            print(f"    Nytt: {d20} + {exp} = {total}")

    effect_text, ek_down = card.get_effect(total)

    # Apply the effect text (parse Mkr, Q, H etc.)
    apply_phase_effect(effect_text, player)

    # Energy class downgrade (only on worst tier)
    if ek_down > 0:
        print(f"      Energiklass -1 på {ek_down} projekt:")
        downgrade_energy_class(player, ek_down)


def show_execution_status(player: Player) -> None:
    """Show player's status during execution phase."""
    used_s = len(player.used_supplier_keys)
    total_s = len(player.pl_suppliers)
    used_o = len(player.used_org_keys)
    total_o = len(player.pl_orgs)

    print(f"\n  ┌─── {player.name} – Genomförandestatus ─────────")
    print(f"  │ Q: {player.pl_q} (krav: {player.q_krav}) | "
          f"H: {player.pl_h} (krav: {player.h_krav}) | "
          f"T: {player.pl_t} mån (mål: ≤12)")
    real_remaining = player.abt_budget - player.abt_loans_net
    tb = real_remaining - player.abt_borrowing_cost
    tg_real = (tb / player.abt_start * 100) if player.abt_start > 0 else 0
    print(f"  │ ABT: {player.abt_budget:.1f} Mkr (start: {player.abt_start:.0f}) | "
          f"TG: {tg_real:.0f}% | EK: {player.eget_kapital:.1f} Mkr | "
          f"Rb: {player.riskbuffertar}")
    print(f"  │ Kort: Lev {used_s}/{total_s} använda | Org {used_o}/{total_o} använda | "
          f"Kultur på hand: {len(player.external_hand)}")
    print(f"  │ Erfarenhet: {player.total_erfarenhet()}")
    print(f"  └{'─' * 55}")


def phase_genomforande(game: GameState) -> None:
    """Execute Phase 3: Projektgenomförande."""
    print("\n" + "=" * 60)
    print("  FAS 3: PROJEKTGENOMFÖRANDE")
    print("=" * 60)

    # Load Phase 3 data
    print("\n  Laddar genomförandedata...")
    phase_cards = load_phase_cards()
    all_external = load_external_support()
    penalty_cards = load_penalty_cards()

    print(f"    Faskort: {sum(len(v) for v in phase_cards.values())} st (8 faser)")
    print(f"    Företagskultur: {len(all_external)} kort")
    print(f"    Konsekvenskort: T:{len(penalty_cards['T'])} Q:{len(penalty_cards['Q'])} "
          f"H:{len(penalty_cards['H'])}")

    # Load garantibesiktning cards
    garanti_cards = load_garanti_cards()
    print(f"    Garantikort: T:{len(garanti_cards['T'])} Q:{len(garanti_cards['Q'])} "
          f"H:{len(garanti_cards['H'])} EK:{len(garanti_cards['EK'])}")

    # Initialize energy classes from projects
    for player in game.players:
        player.projekt_energiklass = {
            p.namn: p.energiklass for p in player.projects
        }

    # Determine turn order (D6)
    print(f"\n  ── Slår om turordning för genomförande ──")
    rolls = {}
    for player in game.players:
        r = roll_display("D6", player.name)
        rolls[player.name] = r

    turn_order = sorted(game.players, key=lambda p: rolls[p.name], reverse=True)
    print(f"\n  Turordning: {', '.join(p.name for p in turn_order)}")

    # External support deck (shared)
    ext_draw_pile = list(all_external)
    ext_discard_pile: List[ExternalSupport] = []

    # Execute 8 phases
    for fas_nr in range(1, 9):
        print(f"\n{'═' * 60}")
        print(f"  FAS {fas_nr}/8 – Företagskultur kostar {PHASE_COST[fas_nr - 1]} Mkr")
        print(f"{'═' * 60}")

        # Draw one faskort for this phase (same card for all players)
        fas_cards = phase_cards.get(fas_nr, [])
        if not fas_cards:
            print(f"  Inga faskort för fas {fas_nr}.")
            continue

        drawn_card = random.choice(fas_cards)
        print(f"\n  📋 FASKORT: {drawn_card.namn}")
        print(f"     {drawn_card.beskrivning}")

        # Each player takes their turn
        for player in turn_order:
            print(f"\n  {'─' * 55}")
            print(f"  {player.name} – Fas {fas_nr}")
            show_execution_status(player)

            trigger = player.kvarter_trigger()

            # Check if this card is skippable for this trigger
            col = {"BOSTÄDER": "req_b", "STAPLAD": "req_s", "KOMPLEX": "req_k"}[trigger]
            neg_req = drawn_card.levels[0][col]
            if neg_req.strip() == "— (skippa)":
                print(f"\n  Faskortet skippas (gäller inte {trigger}).")
                # Still draw event card
                print(f"\n  Drar händelsekort...")
                handle_planning_event(player, game.pl_draw_piles.get(player.name, []),
                                      game.pl_discard_piles.get(player.name, []))
                continue

            # Step 1: Buy external support
            ext_cost = PHASE_COST[fas_nr - 1]
            while True:
                if not ext_draw_pile:
                    # Reshuffle discard into draw
                    if ext_discard_pile:
                        ext_draw_pile.extend(ext_discard_pile)
                        ext_discard_pile.clear()
                        random.shuffle(ext_draw_pile)
                        print("    Företagskultur: kasthögen blandas till ny draghög.")
                    else:
                        print("    Företagskultur: inga kort kvar.")
                        break

                if not input_yes_no(f"\n  Köp företagskultur? ({ext_cost} Mkr, "
                                    f"ABT: {player.abt_budget:.1f} Mkr, "
                                    f"{len(ext_draw_pile)} kort kvar)"):
                    break

                card_drawn = ext_draw_pile.pop(0)
                player.abt_budget -= ext_cost
                abt_warn = ""
                if player.abt_budget < 0:
                    handle_abt_overflow(player)
                    abt_warn = " ⚠ Moderbolagstillskott!"
                player.external_hand.append(card_drawn)
                print(f"    Köpte: {card_drawn.display()} "
                      f"(-{ext_cost} Mkr{abt_warn})")

            # Step 2: Draw event card
            print(f"\n  Drar händelsekort...")
            if player.name in game.pl_draw_piles and game.pl_draw_piles[player.name]:
                handle_planning_event(player, game.pl_draw_piles[player.name],
                                      game.pl_discard_piles[player.name])
            else:
                print("    Inga händelsekort kvar.")

            # Step 3: Resolve faskort
            print(f"\n  ── FASKORT: {drawn_card.namn} ──")
            print(f"  Kvartertyp: {trigger}")
            print(f"  Vad vill du uppnå?")

            # Show available levels for this trigger
            level_names = ["Negativt", "Neutralt", "Positivt", "Bonus"]
            valid_levels = []
            for i, level in enumerate(drawn_card.levels):
                req = level[col]
                effect = level["effect"]
                if req.strip() in ("— (skippa)", ""):
                    continue
                if req.strip() == "—":
                    req_display = "(ingen insats krävs)"
                    reqs_parsed = {}
                else:
                    req_display = req
                    reqs_parsed = parse_competence_req(req)

                valid_levels.append((i, level_names[i], req_display, effect, reqs_parsed))

            for idx, (i, name, req_d, effect, _) in enumerate(valid_levels):
                print(f"    {idx + 1}. [{name}] Krav: {req_d} → Effekt: {effect}")

            choice = input_int(f"  Välj nivå (1-{len(valid_levels)}): ", 1, len(valid_levels))
            chosen_idx, chosen_name, _, chosen_effect, chosen_reqs = valid_levels[choice - 1]

            if chosen_reqs:
                # Player must play cards to meet requirements
                print(f"\n  Du siktar på [{chosen_name}] – uppfyll kraven:")
                success = play_cards_for_requirement(player, chosen_reqs)

                if not success:
                    # Can't meet requirements – must buy external support or fall to Negativt
                    print(f"\n  ⚠ Kunde inte uppfylla kraven!")
                    print(f"  Du kan köpa företagskultur och försöka igen, "
                          f"eller acceptera Negativt.")

                    # Offer to buy more external support and retry
                    retry = True
                    while retry and not success:
                        if ext_draw_pile or ext_discard_pile:
                            if input_yes_no(f"  Köp mer företagskultur och försök igen?"):
                                if not ext_draw_pile and ext_discard_pile:
                                    ext_draw_pile.extend(ext_discard_pile)
                                    ext_discard_pile.clear()
                                    random.shuffle(ext_draw_pile)

                                if ext_draw_pile:
                                    card_drawn = ext_draw_pile.pop(0)
                                    player.abt_budget -= ext_cost
                                    if player.abt_budget < 0:
                                        handle_abt_overflow(player)
                                    player.external_hand.append(card_drawn)
                                    print(f"    Köpte: {card_drawn.display()} (-{ext_cost} Mkr)")
                                    success = play_cards_for_requirement(player, chosen_reqs)
                                else:
                                    print("    Inga kort kvar!")
                                    retry = False
                            else:
                                retry = False
                        else:
                            print("    Inga fler företagskultur tillgängliga.")
                            retry = False

                    if not success:
                        # Fall back to Negativt
                        chosen_effect = drawn_card.levels[0]["effect"]
                        chosen_name = "Negativt"
                        print(f"  Faller tillbaka till [{chosen_name}]")

            print(f"\n  Utfall [{chosen_name}]:")
            apply_phase_effect(chosen_effect, player)

            # Return played external support to discard
            ext_discard_pile.extend(player.used_external)
            player.used_external.clear()

            pause()

    # ── Skedesavslut ──
    print(f"\n{'═' * 60}")
    print(f"  SKEDESAVSLUT – Konsekvenskort")
    print(f"{'═' * 60}")

    for player in turn_order:
        print(f"\n  {'─' * 55}")
        print(f"  {player.name} – Slutuppgörelse")
        show_execution_status(player)

        # T penalty: per step over 12
        t_over = max(0, player.pl_t - 12)
        q_under = max(0, player.q_krav - player.pl_q)
        h_under = max(0, player.h_krav - player.pl_h)

        print(f"\n  T: {player.pl_t} mån → {t_over} steg över 12")
        print(f"  Q: {player.pl_q}/{player.q_krav} → {q_under} steg under")
        print(f"  H: {player.pl_h}/{player.h_krav} → {h_under} steg under")

        # Draw T penalties first (T slår mot kostnader, kan påverka Q/H)
        if t_over > 0:
            print(f"\n  ── T-straff ({t_over} kort) ──")
            for i in range(t_over):
                if penalty_cards["T"]:
                    card = penalty_cards["T"].pop(0)
                    apply_penalty(card, player)
                else:
                    print("    Inga fler T-konsekvenskort.")
                    break
            # Recalculate Q/H after T penalties may have changed them
            q_under = max(0, player.q_krav - player.pl_q)
            h_under = max(0, player.h_krav - player.pl_h)

        if q_under > 0:
            print(f"\n  ── Q-straff ({q_under} kort) ──")
            for i in range(q_under):
                if penalty_cards["Q"]:
                    card = penalty_cards["Q"].pop(0)
                    apply_penalty(card, player)
                else:
                    print("    Inga fler Q-konsekvenskort.")
                    break

        if h_under > 0:
            print(f"\n  ── H-straff ({h_under} kort) ──")
            for i in range(h_under):
                if penalty_cards["H"]:
                    card = penalty_cards["H"].pop(0)
                    apply_penalty(card, player)
                else:
                    print("    Inga fler H-konsekvenskort.")
                    break

        pause()

    # ── Garantibesiktning ──
    print(f"\n{'═' * 60}")
    print(f"  GARANTIBESIKTNING")
    print(f"  Avsättning för framtida garantiåtgärder")
    print(f"{'═' * 60}")

    # Combine all garanti cards into one pool
    garanti_pool: List[PenaltyCard] = []
    for typ_cards in garanti_cards.values():
        garanti_pool.extend(typ_cards)
    random.shuffle(garanti_pool)

    for player in turn_order:
        print(f"\n  {'─' * 55}")
        print(f"  {player.name} – Garantibesiktning")

        # Recalculate after konsekvenskort
        q_under = max(0, player.q_krav - player.pl_q)
        h_under = max(0, player.h_krav - player.pl_h)

        # Count suppliers and orgs with nivå 1-2
        low_suppliers = sum(1 for s in player.pl_suppliers.values() if s.niva <= 2)
        low_orgs = sum(1 for o in player.pl_orgs.values() if o.niva <= 2)

        total_garanti = q_under + h_under + low_suppliers + low_orgs

        print(f"  Garantikort att dra:")
        print(f"    Leverantörer nivå 1-2: {low_suppliers} kort")
        print(f"    Organisationer nivå 1-2: {low_orgs} kort")
        print(f"    Q-underskridande: {q_under} kort")
        print(f"    H-underskridande: {h_under} kort")
        print(f"    Totalt: {total_garanti} garantikort")

        if total_garanti == 0:
            print("  ✓ Inga garantiavsättningar behövs!")
        else:
            for _ in range(total_garanti):
                if garanti_pool:
                    card = garanti_pool.pop(0)
                    apply_penalty(card, player, label="GARANTI")
                else:
                    print("    Inga fler garantikort.")
                    break

        # Save pre-transfer ABT for correct kalkylkostnad calculation
        player.abt_remaining_before_transfer = player.abt_budget

        # Transfer remaining ABT to EK
        if player.abt_budget > 0:
            print(f"\n  Kvarvarande ABT ({player.abt_budget:.1f} Mkr) → EK")
            player.eget_kapital += player.abt_budget
            player.abt_budget = 0

        # Förskott – projektvinster vid förvaltningsstart
        # BRF: (MV − Anskaffning) + tärning, Övriga: bara tärning
        print(f"\n  ── FÖRSKOTT (projektvinster) ──")
        total_forsk = 0
        for p in player.projects:
            if p.rorlig_intakt and str(p.rorlig_intakt).strip():
                die = str(p.rorlig_intakt).strip()
                roll_val = roll_display(die, f"{p.namn}")
                if p.typ == "BRF":
                    brf_bonus = p.marknadsvarde - p.anskaffning
                    total_val = brf_bonus + roll_val
                    print(f"    {p.namn}: {brf_bonus} Mkr (MV {p.marknadsvarde} "
                          f"- Ansk {p.anskaffning}) + {roll_val} ({die}) "
                          f"= {total_val} Mkr")
                    total_forsk += total_val
                else:
                    print(f"    {p.namn} ({die}): +{roll_val} Mkr")
                    total_forsk += roll_val
        if total_forsk > 0:
            player.eget_kapital += total_forsk
            print(f"    Totalt förskott: +{total_forsk:.0f} Mkr "
                  f"(EK: {player.eget_kapital:.1f} Mkr)")

        print(f"\n  Energiklasser efter genomförande:")
        for namn, klass in player.projekt_energiklass.items():
            orig = next((p.energiklass for p in player.projects if p.namn == namn), "?")
            changed = " (sänkt)" if klass != orig else ""
            print(f"    {namn}: {klass}{changed}")

        ek_status = ""
        if player.eget_kapital < 0:
            ek_status = f" (SKULD – moderföretaget har skjutit till {abs(player.eget_kapital):.1f} Mkr)"
        print(f"\n  Slutligt EK: {player.eget_kapital:.1f} Mkr{ek_status}")
        pause()

    # Summary
    print("\n" + "=" * 60)
    print("  SAMMANFATTNING – Fas 3: Projektgenomförande")
    print("=" * 60)

    for player in game.players:
        print(f"\n  {player.name}:")
        print(f"    Q: {player.pl_q}/{player.q_krav} | "
              f"H: {player.pl_h}/{player.h_krav} | T: {player.pl_t} mån")
        print(f"    EK: {player.eget_kapital:.1f} Mkr")
        print(f"    Energiklasser:")
        for namn, klass in player.projekt_energiklass.items():
            print(f"      {namn}: {klass}")

    print("\n  ─── Fas 3 avslutad! ───")
    print("  Nästa steg: Fas 4 – Förvaltning")

    # Snapshot Q/H/T after execution
    for player in game.players:
        player.snap_exec_q = player.pl_q
        player.snap_exec_h = player.pl_h
        player.snap_exec_t = player.pl_t


# ─────────────────────────────────────────────
# PHASE 4: FÖRVALTNING
# ─────────────────────────────────────────────

def mgmt_card_applies(card: ManagementEvent, player: "Player", prop: Project) -> bool:
    """Check if a management event card's trigger matches the property/player."""
    t = card.trigger.strip()
    if not t or t == "Alla":
        return True
    if t == "KOMPLEX":
        return player.kvarter_trigger() == "KOMPLEX"
    if t == "STAPLAD":
        return player.kvarter_trigger() in ("STAPLAD", "KOMPLEX")
    if t == "BTA_C+":
        return player.bta_klass() in ("C", "D")
    if t == "EK_DEF":
        ek = get_prop_ek(prop, player)
        return ek in ("D", "E", "F")
    if t == "EK_ABC":
        ek = get_prop_ek(prop, player)
        return ek in ("A", "B", "C")
    return True  # Unknown trigger = applies


def get_property_event_type(project: Project) -> str:
    """Map project type to event card type."""
    return PROJECT_TYPE_TO_EVENT.get(project.typ, "ALLA")


def calc_driftnetto(player: Player, prop: Project) -> float:
    """Calculate quarterly driftnetto for a property."""
    base = prop.driftnetto if prop.driftnetto else 0
    bonus = player.driftnetto_bonus.get(prop.namn, 0)
    return base + bonus


# Energy class modifier for property value (C=1.0, +/-5% per step)
EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.90, "F": 0.00}


def get_prop_ek(prop: Project, player: "Player" = None) -> str:
    """Get current energy class for a property, checking player upgrades."""
    if player and prop.namn in player.projekt_energiklass:
        return player.projekt_energiklass[prop.namn]
    return prop.energiklass


def calc_fastighetsvarde(prop: Project, yield_pct: float,
                         energiklass: str = "C") -> float:
    """Calculate property value: (Driftnetto * 4 / yield) * EK-modifier."""
    if yield_pct <= 0:
        return 0
    annual_dn = (prop.driftnetto if prop.driftnetto else 0) * 4
    base_fv = annual_dn / (yield_pct / 100.0)
    modifier = EK_FV_MODIFIER.get(energiklass, 1.0)
    return base_fv * modifier


def staff_has_mitigation(player: Player, roll: str, spec: str) -> Optional[Staff]:
    """Check if player has staff that can mitigate an event."""
    if not roll or not spec:
        return None
    for s in player.staff:
        if s.roll == roll and (s.specialisering == spec or s.specialisering == "Generalist"):
            return s
    return None


def hire_staff(player: Player, all_staff: List[Staff], required_capacity: int) -> None:
    """Let player hire staff to cover their properties."""
    print(f"\n  ── Personal ──")
    current_cap = sum(s.kapacitet for s in player.staff)
    current_cost = sum(s.lon_mkr_kv for s in player.staff)
    has_fc = any(s.roll == "FC" for s in player.staff)

    print(f"  Fastigheter: {required_capacity} st | "
          f"Nuvarande kapacitet: {current_cap} | "
          f"Lönekostnad: {current_cost:.1f} Mkr/kv")
    if not has_fc:
        print(f"  ⚠ Du MÅSTE ha minst en FC!")

    # Must hire until capacity >= required AND at least 1 FC
    while current_cap < required_capacity or not has_fc:
        need = required_capacity - current_cap
        print(f"\n  Behöver täcka {max(0, need)} fler fastigheter"
              + (" + en FC" if not has_fc else ""))

        # Show available staff (not already hired)
        hired_ids = {s.id for s in player.staff}
        available = [s for s in all_staff if s.id not in hired_ids]

        if not available:
            print("  Inga fler att anställa!")
            break

        # If no FC, only show FC first
        if not has_fc:
            fc_avail = [s for s in available if s.roll == "FC"]
            if fc_avail:
                print("  Du måste anställa minst en FC:")
                available = fc_avail

        for i, s in enumerate(available):
            print(f"    {i + 1}. [{s.roll}] {s.namn} – {s.specialisering} | "
                  f"Kap: {s.kapacitet} | Lön: {s.lon_mkr_kv:.1f} Mkr/kv"
                  + (f" | Förhandl: {s.forhandling}" if s.forhandling else ""))

        choice = input_int(f"  Anställ (1-{len(available)}): ", 1, len(available))
        hired = available[choice - 1]
        player.staff.append(hired)
        current_cap += hired.kapacitet
        current_cost += hired.lon_mkr_kv
        has_fc = any(s.roll == "FC" for s in player.staff)
        print(f"  ✓ Anställde {hired.namn} ({hired.roll}, {hired.specialisering})")

    # Optional additional hiring
    while True:
        hired_ids = {s.id for s in player.staff}
        available = [s for s in all_staff if s.id not in hired_ids]
        if not available:
            break
        if not input_yes_no(f"  Anställ ytterligare personal? "
                            f"(kap: {current_cap}/{required_capacity}, "
                            f"lön: {current_cost:.1f} Mkr/kv)"):
            break
        for i, s in enumerate(available):
            print(f"    {i + 1}. [{s.roll}] {s.namn} – {s.specialisering} | "
                  f"Kap: {s.kapacitet} | Lön: {s.lon_mkr_kv:.1f} Mkr/kv"
                  + (f" | Förhandl: {s.forhandling}" if s.forhandling else ""))
        choice = input_int(f"  Anställ (1-{len(available)}, 0=klar): ", 0, len(available))
        if choice == 0:
            break
        hired = available[choice - 1]
        player.staff.append(hired)
        current_cap += hired.kapacitet
        current_cost += hired.lon_mkr_kv
        print(f"  ✓ Anställde {hired.namn}")

    print(f"\n  Personal: {len(player.staff)} st | "
          f"Kapacitet: {current_cap} | Lönekostnad: {current_cost:.1f} Mkr/kv")


def pay_salaries(player: Player) -> float:
    """Pay quarterly salaries. Returns total cost."""
    total = sum(s.lon_mkr_kv for s in player.staff)
    if total > 0:
        player.eget_kapital -= total
        print(f"  Lönekostnad: -{total:.1f} Mkr (EK: {player.eget_kapital:.1f} Mkr)")
    return total


def collect_driftnetto(player: Player) -> float:
    """Collect quarterly driftnetto from all properties."""
    total = 0
    for prop in player.fastigheter:
        dn = calc_driftnetto(player, prop)
        total += dn
    if total != 0:
        player.eget_kapital += total
        print(f"  Driftnetto: +{total:.1f} Mkr (EK: {player.eget_kapital:.1f} Mkr)")
    return total


def resolve_world_event(event: WorldEvent, game: "GameState") -> None:
    """Resolve an omvärldskort for all players."""
    print(f"\n  🌍 OMVÄRLD: {event.rubrik}")
    print(f"     {event.beskrivning}")

    for player in game.players:
        if not player.fastigheter:
            continue
        total_effect = 0

        if event.effekt_typ in ("kostnad_alla", "intäkt_alla"):
            # Per property
            total_effect = event.effekt_mkr * len(player.fastigheter)

        elif event.effekt_typ == "kostnad_kommersiellt" or event.effekt_typ == "kostnad_kon":
            # Only commercial properties
            count = sum(1 for p in player.fastigheter if p.typ in KOMMERSIELLT_TYPES)
            total_effect = event.effekt_mkr * count

        elif event.effekt_typ == "intäkt_hr":
            count = sum(1 for p in player.fastigheter if p.typ == "Hyresrätt")
            total_effect = event.effekt_mkr * count

        elif event.effekt_typ == "intäkt_fsk":
            count = sum(1 for p in player.fastigheter if p.typ == "FÖRSKOLOR")
            total_effect = event.effekt_mkr * count

        elif event.effekt_typ == "kostnad_per_ek":
            # Hits properties with poor energy class
            targets = event.paverkar  # e.g. "EK D+E+F"
            for prop in player.fastigheter:
                ek = player.projekt_energiklass.get(prop.namn, "C")
                if ek in targets:
                    total_effect += event.effekt_mkr

        elif event.effekt_typ == "intäkt_per_ek":
            targets = event.paverkar
            for prop in player.fastigheter:
                ek = player.projekt_energiklass.get(prop.namn, "C")
                if ek in targets:
                    total_effect += event.effekt_mkr

        elif event.effekt_typ == "ingen_budgivning":
            print(f"    {player.name}: Inga fastighetsköp detta kvartal!")
            game.no_trading = True
            continue

        elif event.effekt_typ == "ingen":
            continue

        if total_effect != 0:
            player.eget_kapital += total_effect
            print(f"    {player.name}: {total_effect:+.1f} Mkr "
                  f"(EK: {player.eget_kapital:.1f} Mkr)")


def resolve_mgmt_event(card: ManagementEvent, player: Player, prop: Project) -> None:
    """Resolve a management event card for a property."""
    print(f"    📋 {prop.namn}: {card.rubrik}")

    # Check for staff mitigation
    mitigator = staff_has_mitigation(player, card.mildring_roll, card.mildring_spec)
    if mitigator:
        effect = card.mildring_effekt_mkr
        print(f"       {mitigator.namn} ({mitigator.roll} {mitigator.specialisering}) mildrar!")
    else:
        effect = card.effekt_mkr

    if effect != 0:
        player.eget_kapital += effect
        print(f"       {effect:+.1f} Mkr (EK: {player.eget_kapital:.1f} Mkr)")
    elif card.effekt_mkr == 0:
        print(f"       Ingen effekt. {card.beskrivning}")
    else:
        print(f"       Mildrad till 0. {card.beskrivning}")


def do_rent_negotiation(player: Player, rent_scale: Dict[int, float]) -> None:
    """Handle annual rent negotiation (Q2 only, HR properties only)."""
    hr_props = [p for p in player.fastigheter if p.typ == "Hyresrätt"]
    if not hr_props:
        print("  Inga hyresrätter – ingen hyresförhandling.")
        return

    print(f"\n  ── Hyresförhandling ({len(hr_props)} hyresrätter) ──")

    # HGF rolls D6
    hgf = roll_display("D6", "Hyresgästföreningen")
    # FÄ (Fastighetsägarna) rolls D6
    fa = roll_display("D6", "Fastighetsägarna")

    # Player's best FC negotiation die
    best_fc = None
    best_die_val = 0
    for s in player.staff:
        if s.roll == "FC" and s.forhandling:
            die_sides = DICE_MAP.get(s.forhandling.upper(), 0)
            if die_sides > best_die_val:
                best_die_val = die_sides
                best_fc = s

    if best_fc:
        fc_roll = roll_display(best_fc.forhandling, f"FC {best_fc.namn}")
        print(f"  FC {best_fc.namn} använder {best_fc.forhandling}")
    else:
        fc_roll = 0
        print("  ⚠ Ingen FC med förhandlingstärning!")

    netto = fc_roll + fa - hgf
    print(f"\n  Netto: FC({fc_roll}) + FÄ({fa}) - HGF({hgf}) = {netto}")

    # Look up scale
    netto_clamped = max(min(netto, 17), -4)
    hojning = rent_scale.get(netto_clamped, 0)
    total = hojning * len(hr_props)

    print(f"  Höjning: {hojning:.1f} Mkr × {len(hr_props)} HR = {total:.1f} Mkr")

    if total > 0:
        player.eget_kapital += total
        print(f"  EK: {player.eget_kapital:.1f} Mkr")


def do_energy_upgrade(player: Player, max_upgrades: int) -> None:
    """Let player upgrade energy class on properties (max max_upgrades steg)."""
    if max_upgrades <= 0:
        return
    print(f"\n  ── Energiuppgradering ──")
    print(f"  Max {max_upgrades} steg detta kvartal "
          f"({ENERGY_UPGRADE_COST_PER_STEP:.0f} Mkr per steg).")

    upgrades_done = 0
    while upgrades_done < max_upgrades:
        upgradeable = [p for p in player.fastigheter
                       if player.projekt_energiklass.get(p.namn, "C") != "A"]

        if not upgradeable:
            print("  Alla fastigheter har redan energiklass A!")
            break

        remaining = max_upgrades - upgrades_done
        print(f"  Uppgraderingsbara fastigheter ({remaining} steg kvar):")
        for i, prop in enumerate(upgradeable):
            ek = player.projekt_energiklass.get(prop.namn, "C")
            ek_idx = ENERGY_CLASSES.index(ek) if ek in ENERGY_CLASSES else 2
            new_ek = ENERGY_CLASSES[ek_idx - 1] if ek_idx > 0 else "A"
            print(f"    {i + 1}. {prop.namn} ({prop.typ}) – EK: {ek} → {new_ek} | "
                  f"Kostnad: {ENERGY_UPGRADE_COST_PER_STEP:.1f} Mkr")

        choice = input_int(f"  Uppgradera (1-{len(upgradeable)}, 0=klar): ",
                           0, len(upgradeable))
        if choice == 0:
            break

        prop = upgradeable[choice - 1]
        ek = player.projekt_energiklass.get(prop.namn, "C")
        ek_idx = ENERGY_CLASSES.index(ek)
        new_ek = ENERGY_CLASSES[ek_idx - 1]

        player.eget_kapital -= ENERGY_UPGRADE_COST_PER_STEP
        player.projekt_energiklass[prop.namn] = new_ek
        upgrades_done += 1
        print(f"  ✓ {prop.namn}: EK {ek} → {new_ek} "
              f"(-{ENERGY_UPGRADE_COST_PER_STEP:.1f} Mkr, "
              f"EK: {player.eget_kapital:.1f} Mkr)")

    if upgrades_done >= max_upgrades:
        print(f"  Max antal uppgraderingar nått — gå vidare.")


def calc_player_tg(player: Player) -> float:
    """Beräkna spelarens verkliga TG% (täckningsgrad)."""
    if player.abt_start <= 0:
        return 0.0
    real_remaining = player.abt_budget - player.abt_loans_net
    tb = real_remaining - player.abt_borrowing_cost
    return tb / player.abt_start * 100


def calc_real_ek(player: Player) -> float:
    """Beräkna verkligt EK efter moderbolagslån.
    
    Bruttolån = netto + avgift. Avgiften redan dragen under spelet,
    men hela lånebeloppet (brutto) ska återbetalas.
    """
    loans_gross = player.abt_loans_net + player.abt_borrowing_cost
    return player.eget_kapital - loans_gross


def do_market_phase(player: Player, market_properties: List[Project],
                    dd_deck: List[DDCard], game: "GameState",
                    yield_b: float, yield_k: float, num_new: int) -> None:
    """Handle buying/selling properties on the open market.
    
    Ordning: Sälj först, köp sedan.
    - Negativt EK → MÅSTE sälja (minst 1 kvar)
    - Negativt TG → FÅR INTE köpa
    """
    if game.no_trading:
        print("\n  ⛔ Kreditåtstramning – inga köp/försäljningar detta kvartal!")
        return

    print(f"\n  ── Fastighetsmarknad ──")

    # Draw new properties from the pile (visa info oavsett)
    new_avail: List[Project] = []
    for _ in range(num_new):
        if market_properties:
            new_avail.append(market_properties.pop(0))

    # Show available properties
    if new_avail:
        print(f"\n  Nya fastigheter på marknaden ({len(new_avail)} st):")
        for i, prop in enumerate(new_avail):
            y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
            fv = calc_fastighetsvarde(prop, y, prop.energiklass)
            cost_30 = fv * (1 - LOAN_RATIO)
            print(f"    {i + 1}. {prop.namn} ({prop.typ}) BTA:{prop.bta} | "
                  f"DN: {prop.driftnetto:.1f}/kv | EK: {prop.energiklass} | "
                  f"FV: {fv:.1f} Mkr | Du betalar 30%: {cost_30:.1f} Mkr")

    # ═══ STEG 1: SÄLJ FÖRST ═══
    real_ek = calc_real_ek(player)
    forced_sell = real_ek < 0
    if forced_sell and len(player.fastigheter) > 1:
        loans_gross = player.abt_loans_net + player.abt_borrowing_cost
        print(f"\n  ⚠ TVÅNGSFÖRSÄLJNING – Negativt EK!")
        print(f"    EK: {player.eget_kapital:.1f} Mkr − Lån: {loans_gross:.0f} Mkr "
              f"= Verkligt EK: {real_ek:.1f} Mkr")
        print(f"    Du måste sälja tills verkligt EK ≥ 0 (minst 1 fastighet kvar).")

    while len(player.fastigheter) > 1:
        real_ek = calc_real_ek(player)
        if forced_sell and real_ek < 0:
            pass  # Måste fortsätta sälja
        else:
            if not input_yes_no("  Vill du sälja en fastighet?"):
                break

        print("  Dina fastigheter:")
        for i, prop in enumerate(player.fastigheter):
            y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
            fv = calc_fastighetsvarde(prop, y, get_prop_ek(prop, player))
            earn_30 = fv * (1 - LOAN_RATIO)
            print(f"    {i + 1}. {prop.namn} ({prop.typ}) | FV: {fv:.1f} | "
                  f"Du får 30%: {earn_30:.1f} Mkr")

        if forced_sell and calc_real_ek(player) < 0:
            choice = input_int(f"  Sälj (1-{len(player.fastigheter)}): ",
                               1, len(player.fastigheter))
        else:
            choice = input_int(f"  Sälj (1-{len(player.fastigheter)}, 0=avbryt): ",
                               0, len(player.fastigheter))
            if choice == 0:
                break

        prop = player.fastigheter.pop(choice - 1)
        y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
        fv = calc_fastighetsvarde(prop, y, get_prop_ek(prop, player))
        earn_30 = fv * (1 - LOAN_RATIO)
        player.eget_kapital += earn_30
        player.projekt_energiklass.pop(prop.namn, None)
        print(f"  ✓ Sålde {prop.namn} för {earn_30:.1f} Mkr "
              f"(EK: {player.eget_kapital:.1f} Mkr)")

        if forced_sell and calc_real_ek(player) >= 0:
            print(f"  ✓ Verkligt EK nu positivt – tvångsförsäljning avslutad.")
            forced_sell = False

    if forced_sell and calc_real_ek(player) < 0 and len(player.fastigheter) <= 1:
        print(f"  ⚠ Bara 1 fastighet kvar men verkligt EK fortfarande negativt "
              f"({calc_real_ek(player):.1f} Mkr)")

    # ═══ STEG 2: KÖP (om tillåtet) ═══
    real_ek = calc_real_ek(player)
    if new_avail and real_ek < 0:
        print(f"\n  ⛔ Negativt verkligt EK ({real_ek:.1f} Mkr) – inga köp tillåtna!")
    elif new_avail:
        while True:
            # Visa vad spelaren har råd med
            real_ek = calc_real_ek(player)
            print(f"\n  Tillgängligt EK: {real_ek:.1f} Mkr")

            # Beräkna pris och dela upp i köpbara/ej köpbara
            affordable = []
            for prop in new_avail:
                y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
                fv = calc_fastighetsvarde(prop, y, prop.energiklass)
                cost_30 = fv * (1 - LOAN_RATIO)
                affordable.append((prop, cost_30, cost_30 <= real_ek))

            # Visa alla (info) men markera de man ej har råd med
            for i, (prop, cost, can) in enumerate(affordable):
                tag = "" if can else " ⛔ EJ RÅD"
                print(f"    {i+1}. {prop.namn} ({prop.typ}) BTA:{prop.bta} – "
                      f"Pris: {cost:.1f} Mkr{tag}")

            buyable = [(i, prop, cost) for i, (prop, cost, can) in enumerate(affordable) if can]
            if not buyable:
                print(f"  ⚠ Inget köp möjligt – alla fastigheter för dyra!")
                break

            if not input_yes_no("  Vill du köpa en fastighet?"):
                break

            choice = input_int(f"  Välj (1-{len(new_avail)}, 0 = avbryt): ", 0, len(new_avail))
            if choice == 0:
                break

            idx = choice - 1
            prop, cost_30, can_afford = affordable[idx]

            if not can_afford:
                print(f"  ⛔ Du har inte råd! {prop.namn} kostar {cost_30:.1f} Mkr "
                      f"men du har bara {real_ek:.1f} Mkr.")
                break  # Bryt istället för continue → undvik loop

            # Genomför köp
            new_avail.pop(idx)
            player.eget_kapital -= cost_30
            player.fastigheter.append(prop)
            player.projekt_energiklass[prop.namn] = prop.energiklass

            print(f"\n  ✓ Köpte {prop.namn} för {cost_30:.1f} Mkr "
                  f"(EK: {player.eget_kapital:.1f} Mkr)")

            # DD card
            if dd_deck:
                dd = dd_deck.pop(0)
                print(f"  📋 DD: {dd.rubrik} – {dd.beskrivning}")
                if dd.effekt_mkr != 0:
                    player.eget_kapital += dd.effekt_mkr
                    print(f"     {dd.effekt_mkr:+.1f} Mkr (EK: {player.eget_kapital:.1f} Mkr)")
                else:
                    print(f"     Ingen ekonomisk effekt.")

            # Kolla EK igen efter köp
            real_ek = calc_real_ek(player)
            if real_ek < 0:
                print(f"  ⛔ Verkligt EK nu negativt ({real_ek:.1f} Mkr) – inga fler köp!")
                break

            if not new_avail:
                break

    # Return unsold properties to the pile
    for prop in new_avail:
        market_properties.append(prop)


def show_forvaltning_status(player: Player, yield_b: float, yield_k: float) -> None:
    """Show player's management phase status."""
    total_fv = 0
    total_bta = 0
    for prop in player.fastigheter:
        y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
        fv = calc_fastighetsvarde(prop, y, get_prop_ek(prop, player))
        total_fv += fv
        total_bta += prop.bta

    fv_30 = total_fv * (1 - LOAN_RATIO)
    staff_cost = sum(s.lon_mkr_kv for s in player.staff)

    print(f"\n  ┌─── {player.name} – Förvaltningsstatus ───────")
    print(f"  │ Fastigheter: {len(player.fastigheter)} st | BTA: {total_bta} kvm")
    loans_gross = player.abt_loans_net + player.abt_borrowing_cost
    real_ek = player.eget_kapital - loans_gross
    if loans_gross > 0:
        print(f"  │ FV (30%): {fv_30:.1f} Mkr | EK: {real_ek:.1f} Mkr (kassa {player.eget_kapital:.1f} − lån {loans_gross:.0f})")
    else:
        print(f"  │ FV (30%): {fv_30:.1f} Mkr | EK: {real_ek:.1f} Mkr")
    print(f"  │ Personal: {len(player.staff)} ({staff_cost:.1f} Mkr/kv)")
    print(f"  │ Yield B: {yield_b:.2f}% | K: {yield_k:.2f}%")
    print(f"  └{'─' * 55}")


def phase_forvaltning(game: "GameState") -> None:
    """Execute Phase 4: Fastighetsförvaltning (4 quarters)."""
    print("\n" + "=" * 60)
    print("  FAS 4: FASTIGHETSFÖRVALTNING")
    print("=" * 60)

    # Load Phase 4 data
    print("\n  Laddar förvaltningsdata...")
    all_staff = load_staff()
    yield_cards = load_yield_cards()
    dd_deck = load_dd_cards()
    world_events = load_world_events()
    mgmt_events = load_mgmt_events()
    rent_scale = load_rent_scale()

    print(f"    Personal: {len(all_staff)} st (FC+FS)")
    print(f"    Yield-kort: B:{len(yield_cards['bostäder'])} K:{len(yield_cards['kommersiellt'])}")
    print(f"    DD-kort: {len(dd_deck)}")
    print(f"    Omvärldskort: {len(world_events)}")
    print(f"    Händelsekort: {sum(len(v) for v in mgmt_events.values())} "
          f"({', '.join(f'{k}:{len(v)}' for k, v in mgmt_events.items())})")

    # Initialize management phase
    yield_b = YIELD_START_BOSTADER
    yield_k = YIELD_START_KOMMERSIELLT

    # Build market property pile (remaining project cards, exclude BRF)
    market_properties: List[Project] = []
    all_project_stacks = load_projects()
    for typ, stack in all_project_stacks.items():
        if typ == "BRF":
            continue
        for prop in stack:
            # Don't include properties already owned by players
            owned = {p.namn for pl in game.players for p in pl.projects}
            if prop.namn not in owned:
                market_properties.append(prop)
    random.shuffle(market_properties)
    print(f"    Marknadsfastigheter: {len(market_properties)} st")

    # Setup: remove BRF, assign properties
    for player in game.players:
        player.fastigheter = [p for p in player.projects if p.typ != "BRF"]
        # Ensure energiklass is tracked for all
        for prop in player.fastigheter:
            if prop.namn not in player.projekt_energiklass:
                player.projekt_energiklass[prop.namn] = prop.energiklass

        brf_count = len(player.projects) - len(player.fastigheter)
        print(f"\n  {player.name}: {len(player.fastigheter)} fastigheter "
              f"(tog bort {brf_count} BRF)")
        for prop in player.fastigheter:
            ek = player.projekt_energiklass.get(prop.namn, prop.energiklass)
            print(f"    {prop.namn} ({prop.typ}) BTA:{prop.bta} DN:{prop.driftnetto:.1f}/kv EK:{ek}")

    # Per-player event card decks (shuffled per type, reusable)
    player_event_decks: Dict[str, Dict[str, List[ManagementEvent]]] = {}
    for player in game.players:
        decks: Dict[str, List[ManagementEvent]] = {}
        for typ, cards in mgmt_events.items():
            decks[typ] = list(cards)
            random.shuffle(decks[typ])
        player_event_decks[player.name] = decks

    pause()

    # Q1-Q4
    quarter_new_props = {1: 3, 2: 2, 3: 1, 4: 0}  # New properties per quarter

    for q in range(1, 5):
        print(f"\n{'═' * 60}")
        print(f"  KVARTAL {q}/4")
        print(f"{'═' * 60}")

        game.no_trading = False

        # Q2-Q4: Draw yield cards
        if q >= 2:
            print(f"\n  ── Yield-förändring ──")
            if yield_cards["bostäder"]:
                yb_change = yield_cards["bostäder"].pop(0)
                yield_b += yb_change
                print(f"  Bostäder: {yb_change:+.2f}% → nu {yield_b:.2f}%")
            if yield_cards["kommersiellt"]:
                yk_change = yield_cards["kommersiellt"].pop(0)
                yield_k += yk_change
                print(f"  Kommersiellt: {yk_change:+.2f}% → nu {yield_k:.2f}%")

        # Omvärldskort (shared, drawn at start of quarter)
        if world_events:
            we = world_events.pop(0)
            resolve_world_event(we, game)

        for player in game.players:
            print(f"\n  {'─' * 55}")
            print(f"  {player.name} – Q{q}")
            show_forvaltning_status(player, yield_b, yield_k)

            # 1. Driftnetto
            print(f"\n  ── Driftnetto ──")
            collect_driftnetto(player)

            # 2. Omvärldskort (shared)
            # Draw once per quarter (first player triggers it)

            # 3. Q1: Hire staff | Other Qs: pay salaries
            if q == 1:
                hire_staff(player, all_staff, len(player.fastigheter))
            pay_salaries(player)

            # 4. Q2: Rent negotiation
            if q == 2:
                print(f"\n  {'▶' * 3} HYRESFÖRHANDLING {'◀' * 3}")
                do_rent_negotiation(player, rent_scale)

            # 5. Händelsekort per fastighet
            print(f"\n  ── Händelsekort ──")
            for prop in player.fastigheter:
                event_type = get_property_event_type(prop)
                deck = player_event_decks[player.name]

                # Find a card that applies (trigger matches)
                card = None
                for deck_type in [event_type, "ALLA"]:
                    if deck_type not in deck or not deck[deck_type]:
                        continue
                    # Search through deck for an applicable card
                    for attempt in range(len(deck[deck_type])):
                        candidate = deck[deck_type].pop(0)
                        if mgmt_card_applies(candidate, player, prop):
                            card = candidate
                            deck[deck_type].append(candidate)  # Put back
                            break
                        else:
                            deck[deck_type].append(candidate)  # Put back, try next
                    if card:
                        break

                if card:
                    resolve_mgmt_event(card, player, prop)
                else:
                    print(f"    {prop.namn}: Inga kort kvar.")

            # Shuffle all event decks for next quarter
            if player.name in player_event_decks:
                for typ_key in player_event_decks[player.name]:
                    random.shuffle(player_event_decks[player.name][typ_key])

            # 6. Energy upgrade (Q2-Q4 med kvartalsvis tak)
            limit = ENERGY_UPGRADE_QUARTERLY_LIMITS[q]
            if limit > 0:
                if input_yes_no(f"\n  Vill du göra energiuppgraderingar? (max {limit})"):
                    do_energy_upgrade(player, limit)

            # 7. Market phase (not Q4)
            if q <= 3:
                do_market_phase(player, market_properties, dd_deck, game,
                                yield_b, yield_k, quarter_new_props[q])
                # After buying: need to hire new staff?
                current_cap = sum(s.kapacitet for s in player.staff)
                if current_cap < len(player.fastigheter):
                    print(f"\n  ⚠ Personal täcker inte alla fastigheter!")
                    hire_staff(player, all_staff, len(player.fastigheter))
                    pay_salaries(player)  # Pay the new hires for this quarter

            pause()

    # ── Final valuation ──
    print(f"\n{'═' * 60}")
    print(f"  SLUTVÄRDERING")
    print(f"{'═' * 60}")

    results = []
    for player in game.players:
        total_fv = 0
        total_bta = 0
        print(f"\n  {player.name}:")
        for prop in player.fastigheter:
            y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
            fv = calc_fastighetsvarde(prop, y, get_prop_ek(prop, player))
            fv_30 = fv * (1 - LOAN_RATIO)
            ek = player.projekt_energiklass.get(prop.namn, "C")
            total_fv += fv_30
            total_bta += prop.bta
            print(f"    {prop.namn} ({prop.typ}) BTA:{prop.bta} EK:{ek} | "
                  f"DN:{prop.driftnetto:.1f}/kv | FV:{fv:.1f} | 30%:{fv_30:.1f} Mkr")

        # ABT-ekonomi
        abt_start = getattr(player, 'abt_start', 0)
        abt_remaining = getattr(player, 'abt_remaining_before_transfer',
                                getattr(player, 'abt_budget', 0))
        abt_loans_net = getattr(player, 'abt_loans_net', 0)
        abt_borrow_cost = getattr(player, 'abt_borrowing_cost', 0)
        real_remaining = abt_remaining - abt_loans_net
        abt_k = abt_start - real_remaining + abt_borrow_cost
        tb = abt_start - abt_k

        # Verkligt EK (efter moderbolagslån)
        loans_gross = abt_loans_net + abt_borrow_cost
        ek_verkligt = player.eget_kapital - loans_gross

        # Råpoäng = (FV×30% + EK + TB) / BTA × 1000
        score_abs = total_fv + ek_verkligt + tb
        rapoang = (score_abs / total_bta * 1000) if total_bta > 0 else 0

        # Straffaktor för Q/H/T-avvikelser vid Skede 2:s slut
        n_avvikelse = qht_penalty_n(player)
        penalty = qht_penalty_factor(n_avvikelse)
        score_per_kvm = rapoang * penalty

        print(f"\n    FV (30%): {total_fv:.1f} Mkr")
        print(f"    EK verkligt: {ek_verkligt:.1f} Mkr")
        print(f"    TB: {tb:+.1f} Mkr")
        print(f"    ─────────────────")
        print(f"    Summa: {score_abs:.1f} Mkr")
        print(f"    BTA: {total_bta} kvm")
        print(f"    Råpoäng: {rapoang:.1f}")
        print(f"    Q/H/T-avvikelse: n={n_avvikelse} (Q:{max(0, player.q_krav - player.snap_exec_q)} + "
              f"H:{max(0, player.h_krav - player.snap_exec_h)} + "
              f"T:{max(0, player.snap_exec_t - T_KRAV)}) → straffaktor {int(penalty*100)} %")
        print(f"    Slutpoäng: {score_per_kvm:.1f}")

        results.append((player.name, score_per_kvm, total_fv, ek_verkligt, tb, total_bta, score_abs))

    # Winner
    results.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {'═' * 78}")
    print(f"  ┌{'─' * 76}┐")
    print(f"  │{'SLUTRESULTAT':^76}│")
    print(f"  │{'Poäng = (FV×30% + EK + TB) / BTA × 1000 (kr/kvm)':^76}│")
    print(f"  ├{'─' * 76}┤")
    print(f"  │ {'Plats':<6}{'Spelare':<16}{'FV×30%':>10}{'EK':>10}"
          f"{'TB':>10}{'Summa':>10}{'BTA':>8}{'Poäng':>10} │")
    print(f"  │ {'':6}{'':16}{'Mkr':>10}{'Mkr':>10}"
          f"{'Mkr':>10}{'Mkr':>10}{'kvm':>8}{'kr/kvm':>10} │")
    print(f"  ├{'─' * 76}┤")
    for i, (name, score, fv_30, ek, tb, bta, score_abs) in enumerate(results):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f" {i+1}"
        print(f"  │ {medal:<6}{name:<16}{fv_30:>10.1f}{ek:>+10.1f}"
              f"{tb:>+10.1f}{score_abs:>10.1f}{bta:>8}{score:>10.1f} │")
    print(f"  └{'─' * 76}┘")

    print(f"\n  🏆 {results[0][0]} VINNER!")

    # Show detailed property portfolio for winner
    winner_name = results[0][0]
    winner = next(p for p in game.players if p.name == winner_name)
    print(f"\n  {winner_name}s fastighetsportfölj:")
    for prop in winner.fastigheter:
        y = yield_b if prop.typ in BOSTADER_TYPES else yield_k
        ek = get_prop_ek(prop, winner)
        fv = calc_fastighetsvarde(prop, y, ek)
        print(f"    {prop.namn} ({prop.typ}) BTA:{prop.bta} EK:{ek} "
              f"FV:{fv:.1f} Mkr")

    print(f"\n  {'═' * 64}")
    input("\n  Tryck ENTER för att avsluta...")
    if input_yes_no("\n  Vill du spela igen?"):
        main()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    global DATA_DIR

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + "HUSBYGGSPELET".center(58) + "║")
    print("║" + "Ett utbildningsspel om fastighetsutveckling".center(58) + "║")
    print("║" + "och projektledning inom byggsektorn".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # Configure data path
    default_path = SCRIPT_DIR  # Assume data folders are siblings to script by default
    print(f"\n  Datafilerna söks i undermappar (1. Projektutveckling/ etc.)")
    path_input = input(f"  Sökväg till Husbyggspelet-mappen [Enter = {default_path}]: ").strip()
    DATA_DIR = path_input if path_input else default_path

    # Verify a key file exists
    test_file = data_path("projekt")
    if not os.path.exists(test_file):
        print(f"\n  ⚠ Hittade inte: {test_file}")
        print(f"  Kontrollera att mappstrukturen ser ut så här:")
        print(f"    {DATA_DIR}/")
        print(f"      1. Projektutveckling/PU_projekt.csv")
        print(f"      2. Planering/PL_Leverantörer.csv")
        print(f"      ...")
        sys.exit(1)

    print(f"  ✓ Datafiler hittade i: {DATA_DIR}")

    num_players = input_int("\n  Antal spelare (1-4): ", 1, 4)

    game = GameState(num_players)
    game.setup()

    # Phase 1a: Mark och tomt
    phase_mark_och_tomt(game)

    # Phase 1b: Board game
    phase_board_game(game)

    # Extra markanvisning – varje spelare får en expansion
    print("\n" + "=" * 60)
    print("  EXTRA MARKANVISNING")
    print("  Varje spelare får en markexpansion (3-5 extra rutor).")
    print("=" * 60)
    for player in game.players:
        d4 = roll_display("D4", f"{player.name} expansion")
        expansion = min(5, d4 + 2)  # D4(1-4) + 2 = 3-5 (4→5 capped)
        player.mark_expansions += expansion
        player.expansion_events += 1
        print(f"  {player.name}: +{expansion} rutor (total expansion: "
              f"{player.mark_expansions} rutor)")
    pause()

    # Phase 1c: Nämnd decisions
    phase_namndbeslut(game)

    # Phase 1d: Placement
    phase_placement(game)

    # Phase 1e: Economics
    phase_ekonomi(game)

    # Summary
    phase_summary(game)

    # Phase 2: Projektplanering
    phase_planering(game)

    # Prognosis before Fas 3
    print("\n" + "=" * 60)
    print("  PROGNOS INFÖR GENOMFÖRANDE")
    print("=" * 60)
    for player in game.players:
        print(f"\n  {player.name}:")
        print(f"    ABT-budget kvar: {player.abt_budget:.1f} Mkr")
        print(f"    EK (orörd): {player.eget_kapital:.1f} Mkr")
        tb = player.abt_budget + player.eget_kapital
        print(f"    Totalt tillgängligt: {tb:.1f} Mkr")
        if player.abt_budget <= 0:
            print(f"    ⚠ ABT-budgeten är slut – EK används vid ytterligare kostnader!")
    pause()

    # Phase 3: Projektgenomförande
    phase_genomforande(game)

    # Phase 4: Förvaltning
    phase_forvaltning(game)

    return game


if __name__ == "__main__":
    try:
        game = main()
    except Exception as e:
        import traceback
        print(f"\n\n  ⚠ FEL: {e}")
        traceback.print_exc()
        input("\n  Tryck Enter för att stänga...")
        sys.exit(1)

