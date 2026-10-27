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

PROJECT_TYPES = ["BRF", "FÖRSKOLA", "LOKAL", "KONTOR", "HYRESRÄTT"]
TYPE_CODES = {"BRF": "B", "FÖRSKOLA": "F", "LOKAL": "L", "KONTOR": "K", "HYRESRÄTT": "H"}
CODE_TO_TYPES = {"B": ["BRF"], "F": ["FÖRSKOLA"], "L": ["LOKAL"], "K": ["KONTOR"], "H": ["HYRESRÄTT"]}

# Phase 3: external support cost per phase (1-8)
PHASE_COST = [2, 2, 3, 3, 4, 5, 6, 7]
ENERGY_CLASSES = ["A", "B", "C", "D", "E"]  # Per regelboken §9.1 — F borttaget i paket 1

# Phase 4: Förvaltning constants
YIELD_START_BOSTADER = 4.0   # %
YIELD_START_KOMMERSIELLT = 5.0  # %
LOAN_RATIO = 0.70  # 70% debt financing
BOSTADER_TYPES = ["HYRESRÄTT"]
KOMMERSIELLT_TYPES = ["FÖRSKOLA", "LOKAL", "KONTOR"]
PROJECT_TYPE_TO_EVENT = {
    "HYRESRÄTT": "HR", "FÖRSKOLA": "FSK", "LOKAL": "LOK", "KONTOR": "KON",
}
EK_FV_MODIFIER = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95, "E": 0.0}
QUARTER_NEW_PROPS = {1: 3, 2: 2, 3: 1, 4: 0}

# Förvaltning 2.0: energiklass → DN-modifier (hela mkr, designdoc 2026-05-09).
# Effektiv DN = bas-DN + EK_DN_MODIFIER[energiklass]. Inga halvsteg.
EK_DN_MODIFIER = {"A": 2, "B": 1, "C": 0, "D": -1, "E": -2}

# MV-tabell: marknadsvärdesfaktorer beroende på säljläge.
# Avrundning till närmaste 5 Mkr för läsbarhet (designdoc §MV-tabellen).
MV_MULTIPLIERS = {"tvang": 0.7, "normal": 1.0, "fientlig": 1.2}

# Effektiv DN cap = bas_dn × 2, absolut max 15 (designdoc §Fastigheter, DN och DN-kort).
EFFECTIVE_DN_ABS_MAX = 15

# Yield-kön: hur många omvärldskort/yield-rörelser ligger uppvända framför kartan.
YIELD_QUEUE_SIZE = 3

# Rent negotiation scale: netto value -> höjning per HR property (Mkr)
RENT_SCALE = {
    -4: -0.5, -3: -0.4, -2: -0.3, -1: -0.2, 0: -0.1,
    1: 0.0, 2: 0.1, 3: 0.2, 4: 0.3, 5: 0.4,
    6: 0.5, 7: 0.6, 8: 0.7, 9: 0.8, 10: 0.9,
    11: 1.0, 12: 1.1, 13: 1.2, 14: 1.3, 15: 1.4,
    16: 1.5, 17: 1.6,
}

# Energiuppgradering — Förvaltning 2.0 (Regelhäfte §8): 5 mkr/steg, D20 ≥ 10 för success.
# Vid fail spenderas kostnaden ändå. FC/FS-modifier appliceras på slaget.
ENERGY_UPGRADE_COST_PER_STEP = 5.0  # Mkr per steg, fast pris
ENERGY_UPGRADE_D20_THRESHOLD = 10   # D20-tröskel för success

# Pusselspel inaktiverat under provspel — alla projekt anses placerade automatiskt.
# Sätt till False för att återaktivera pusselplaceringen mellan Skede 1 och 2.
SKIP_PUZZLE_PLACEMENT = True

# Förvaltning 2.0 – Personal: F2-arketyperna (6 FC + 4 FS) ersätter gamla F_personal.csv-staff.
# F2-designdoket säger 'Inga separata kostnader eller kapacitetstak' – varje FC/FS har
# egenskaper på fastighetsnivå istället. Sätt till False för att gå tillbaka till
# gamla löne-/kapacitets-modellen.
USE_F2_STAFF = True

# Slutformel – tre delpoäng som var och en landar runt 20–25 vid "riktigt bra" spel,
# 25 vid "superbra". Kalibrera dessa baserat på provspel.
#
#   Skede 1 (Utveckling)  = total anskaffning / 100   → 25 vid 2500 Mkr förvärv
#   Skede 2 (Byggande)    = TG (procent)              → 25 vid TG 25 %
#   Skede 3 (Förvaltning) = (FV_obelånat + kassa × faktor) / divisor
#                           där FV_obelånat = säljvärde (normal MV) − utestående lån,
#                           kassa = EK efter moderbolagslån,
#                           faktor justerar kassans vikt mot fastighetsvärdet,
#                           divisor kalibrerar så superbra ger 25.
#
# Justera dessa när du har testspels-data.
SKEDE3_KASSA_FAKTOR = 1.0
SKEDE3_DIVISOR = 30

# Förvaltning 2.0 – händelsekort per fastighet är inaktiverade tills nya
# F2_händelsekort-systemet aktiveras (Steg G). Gamla mgmt_events ger
# konstigt utfall i nuvarande Skede 3, så vi hoppar över dem helt.
SKIP_MGMT_EVENTS = True

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

# D20 + experience thresholds for planning event cards
# High thresholds to balance total_erfarenhet bonus on all rolls
D20_THRESHOLDS = [8, 20, 26, 9999]

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

# Board squares — Skede 1-brädet enligt PU_spelbräde2.pdf (2026-05-12).
# 24 rutor totalt: 4 hörn (Stadsbyggnadskontoret-start, Skönhetsrådet,
# Stadshuset, Länsstyrelsen), 15 enskilda projektrutor (3 per typ),
# 3 händelsekortrutor och 2 riskbuffert-rutor. Kombinationsrutor som
# "BRF + Kontor" är borttagna; tidigare "Politik"/"Dialog" är sammanslagna
# till en enhetlig "Händelsekort"-ruta (kort_typ="händelsekort").
BOARD_SQUARES = [
    {"nr": 1,  "typ": "start",         "namn": "Stadsbyggnadskontoret"},
    {"nr": 2,  "typ": "projekt",       "namn": "Hyresrätt",    "projekt_typer": ["HYRESRÄTT"]},
    {"nr": 3,  "typ": "kort",          "namn": "Händelsekort", "kort_typ": "händelsekort"},
    {"nr": 4,  "typ": "projekt",       "namn": "Kontor",       "projekt_typer": ["KONTOR"]},
    {"nr": 5,  "typ": "projekt",       "namn": "BRF",          "projekt_typer": ["BRF"]},
    {"nr": 6,  "typ": "projekt",       "namn": "Lokal",        "projekt_typer": ["LOKAL"]},
    {"nr": 7,  "typ": "skonhetsradet", "namn": "Skönhetsrådet"},
    {"nr": 8,  "typ": "projekt",       "namn": "Förskola",     "projekt_typer": ["FÖRSKOLA"]},
    {"nr": 9,  "typ": "riskbuffert",   "namn": "Ta en riskbuffert"},
    {"nr": 10, "typ": "projekt",       "namn": "Hyresrätt",    "projekt_typer": ["HYRESRÄTT"]},
    {"nr": 11, "typ": "kort",          "namn": "Händelsekort", "kort_typ": "händelsekort"},
    {"nr": 12, "typ": "projekt",       "namn": "Kontor",       "projekt_typer": ["KONTOR"]},
    {"nr": 13, "typ": "stadshuset",    "namn": "Stadshuset"},
    {"nr": 14, "typ": "projekt",       "namn": "Förskola",     "projekt_typer": ["FÖRSKOLA"]},
    {"nr": 15, "typ": "projekt",       "namn": "Hyresrätt",    "projekt_typer": ["HYRESRÄTT"]},
    {"nr": 16, "typ": "kort",          "namn": "Händelsekort", "kort_typ": "händelsekort"},
    {"nr": 17, "typ": "projekt",       "namn": "Lokal",        "projekt_typer": ["LOKAL"]},
    {"nr": 18, "typ": "projekt",       "namn": "BRF",          "projekt_typer": ["BRF"]},
    {"nr": 19, "typ": "lansstyrelsen", "namn": "Länsstyrelsen"},
    {"nr": 20, "typ": "projekt",       "namn": "Lokal",        "projekt_typer": ["LOKAL"]},
    {"nr": 21, "typ": "projekt",       "namn": "BRF",          "projekt_typer": ["BRF"]},
    {"nr": 22, "typ": "projekt",       "namn": "Kontor",       "projekt_typer": ["KONTOR"]},
    {"nr": 23, "typ": "projekt",       "namn": "Förskola",     "projekt_typer": ["FÖRSKOLA"]},
    {"nr": 24, "typ": "riskbuffert",   "namn": "Ta en riskbuffert"},
]
