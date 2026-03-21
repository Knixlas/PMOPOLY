"""PMOPOLY configuration and constants."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Game constants (from husbyggspelet.py)
MARK_TOMT_KOSTNAD = 15      # Mkr
EXPANSION_KOSTNAD = 5        # Mkr per expansion
TOMT_CELLS = 16              # 4x4 grid
EXPANSION_MIN = 3
EXPANSION_MAX = 5
MAX_PROJECTS = 9
MAX_BTA = 12500              # kvm
START_Q_KRAV = 4
START_H_KRAV = 4
MIN_T = 8                    # months minimum

DICE_MAP = {"D4": 4, "D6": 6, "D8": 8, "D10": 10, "D12": 12, "D20": 20}

PROJECT_TYPES = ["BRF", "FÖRSKOLOR", "LOKAL", "KONTOR", "Hyresrätt"]
TYPE_CODES = {"BRF": "B", "FÖRSKOLOR": "F", "LOKAL": "L", "KONTOR": "K", "Hyresrätt": "H"}
CODE_TO_TYPES = {"B": ["BRF"], "F": ["FÖRSKOLOR"], "L": ["LOKAL"], "K": ["KONTOR"], "H": ["Hyresrätt"]}

# Phase 3: external support cost per phase (1-8)
PHASE_COST = [2, 2, 3, 3, 4, 5, 6, 7]
ENERGY_CLASSES = ["A", "B", "C", "D", "E", "F"]

# Phase 4: Förvaltning constants
YIELD_START_BOSTADER = 4.0   # %
YIELD_START_KOMMERSIELLT = 5.0  # %
LOAN_RATIO = 0.70  # 70% debt financing
BOSTADER_TYPES = ["Hyresrätt"]
KOMMERSIELLT_TYPES = ["FÖRSKOLOR", "LOKAL", "KONTOR"]
PROJECT_TYPE_TO_EVENT = {
    "Hyresrätt": "HR", "FÖRSKOLOR": "FSK", "LOKAL": "LOK", "KONTOR": "KON",
}
EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.90, "F": 0.85}
QUARTER_NEW_PROPS = {1: 3, 2: 2, 3: 1, 4: 0}

# Rent negotiation scale: netto value -> höjning per HR property (Mkr)
RENT_SCALE = {
    -4: -0.5, -3: -0.4, -2: -0.3, -1: -0.2, 0: -0.1,
    1: 0.0, 2: 0.1, 3: 0.2, 4: 0.3, 5: 0.4,
    6: 0.5, 7: 0.6, 8: 0.7, 9: 0.8, 10: 0.9,
    11: 1.0, 12: 1.1, 13: 1.2, 14: 1.3, 15: 1.4,
    16: 1.5, 17: 1.6,
}

# Energy upgrade costs: step -> {BTA_class: cost_Mkr}
ENERGY_UPGRADE_COSTS = {
    "F-E": {"A": 1.0, "B": 1.5, "C": 2.0, "D": 2.5},
    "E-D": {"A": 1.5, "B": 2.0, "C": 2.5, "D": 3.0},
    "D-C": {"A": 2.0, "B": 2.5, "C": 3.0, "D": 3.5},
    "C-B": {"A": 3.0, "B": 3.5, "C": 4.0, "D": 4.5},
    "B-A": {"A": 4.0, "B": 4.5, "C": 5.0, "D": 5.5},
}

# Planning step order: (slot_name, slot_type)
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

# Maps planning slot names to event card Kort_ID values in CSV
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

# D20 + experience thresholds for planning event cards [5, 17, 20, 9999]
D20_THRESHOLDS = [5, 17, 20, 9999]

# Data file paths (relative to DATA_DIR)
DATA_FILES = {
    "projekt": os.path.join("1_projektutveckling", "PU_projekt.csv"),
    "markexpansion": os.path.join("1_projektutveckling", "PU_markepansion.csv"),
    "btabya": os.path.join("1_projektutveckling", "PU_BTABYA.csv"),
    "poldia": os.path.join("1_projektutveckling", "PU_poldia.csv"),
    "poldia_spec": os.path.join("1_projektutveckling", "PU_poldia_spec.csv"),
    "bradet": os.path.join("1_projektutveckling", "PU_Projektutvecklingsbrädet.xlsx"),
    "leverantorer": os.path.join("2_planering", "PL_Leverantörer.csv"),
    "organisation": os.path.join("2_planering", "PL_Organisation.csv"),
    "handelsekort_pl": os.path.join("2_planering", "PL_Händelsekort.csv"),
    "faskort": os.path.join("3_genomforande", "GF_Faskort_utforande.csv"),
    "kultur": os.path.join("3_genomforande", "GF_kultur.csv"),
    "konsekvenskort": os.path.join("3_genomforande", "GF_konsekvenskort.csv"),
    "garantibesiktning": os.path.join("3_genomforande", "GF_garantibesiktning.csv"),
    "personal": os.path.join("4_forvaltning", "F_personal.csv"),
    "yield": os.path.join("4_forvaltning", "F_yield.csv"),
    "dd": os.path.join("4_forvaltning", "F_DD.csv"),
    "omvarldskort": os.path.join("4_forvaltning", "F_omvärldskort.csv"),
    "handelsekort_forv": os.path.join("4_forvaltning", "F_händelsekort.csv"),
    "moderbolagslan": os.path.join("4_forvaltning", "F_moderbolagslån.csv"),
    "pu_pl_personal": "PU_PL_personal.csv",
}

def data_path(key: str) -> str:
    return os.path.join(DATA_DIR, DATA_FILES[key])

# Board squares (hardcoded from original, 24 squares)
BOARD_SQUARES = [
    {"nr": 1, "typ": "start", "namn": "Stadsbyggnadskontoret"},
    {"nr": 2, "typ": "projekt", "namn": "Förskola", "projekt_typer": ["FÖRSKOLOR"]},
    {"nr": 3, "typ": "projekt", "namn": "Hyresrätt", "projekt_typer": ["Hyresrätt"]},
    {"nr": 4, "typ": "kort", "namn": "Dialog", "kort_typ": "dialog"},
    {"nr": 5, "typ": "projekt", "namn": "BRF", "projekt_typer": ["BRF"]},
    {"nr": 6, "typ": "stjarna", "namn": "Stjärna"},
    {"nr": 7, "typ": "stadshuset", "namn": "Stadshuset"},
    {"nr": 8, "typ": "projekt", "namn": "Lokal", "projekt_typer": ["LOKAL"]},
    {"nr": 9, "typ": "kort", "namn": "Politik", "kort_typ": "politik"},
    {"nr": 10, "typ": "projekt", "namn": "BRF + Kontor", "projekt_typer": ["BRF", "KONTOR"]},
    {"nr": 11, "typ": "projekt", "namn": "Kontor", "projekt_typer": ["KONTOR"]},
    {"nr": 12, "typ": "stjarna", "namn": "Stjärna"},
    {"nr": 13, "typ": "kort", "namn": "Dialog", "kort_typ": "dialog"},
    {"nr": 14, "typ": "projekt", "namn": "Lokal + Hyresrätt", "projekt_typer": ["LOKAL", "Hyresrätt"]},
    {"nr": 15, "typ": "lansstyrelsen", "namn": "Länsstyrelsen"},
    {"nr": 16, "typ": "projekt", "namn": "Förskola", "projekt_typer": ["FÖRSKOLOR"]},
    {"nr": 17, "typ": "kort", "namn": "Politik", "kort_typ": "politik"},
    {"nr": 18, "typ": "projekt", "namn": "Lokal + Förskola", "projekt_typer": ["LOKAL", "FÖRSKOLOR"]},
    {"nr": 19, "typ": "skonhetsradet", "namn": "Skönhetsrådet"},
    {"nr": 20, "typ": "stjarna", "namn": "Stjärna"},
    {"nr": 21, "typ": "kort", "namn": "Dialog", "kort_typ": "dialog"},
    {"nr": 22, "typ": "projekt", "namn": "Hyresrätt", "projekt_typer": ["Hyresrätt"]},
    {"nr": 23, "typ": "kort", "namn": "Politik", "kort_typ": "politik"},
    {"nr": 24, "typ": "projekt", "namn": "BRF", "projekt_typer": ["BRF"]},
]
