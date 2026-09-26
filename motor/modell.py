"""Tillståndet i Skede 3 (Förvaltning 2.1). Bara data — reglerna finns i motor.py."""
from dataclasses import dataclass, field

TYPER = ["HYRESRÄTT", "FÖRSKOLA", "LOKAL", "KONTOR"]
KLASSER = ["A", "B", "C", "D", "E"]
EK_MOD = {"A": 2, "B": 1, "C": 0, "D": -1, "E": -2}

# Yieldspår: bostadsspåret gäller hyresrätt, det kommersiella övriga typer
SPAR = {"HYRESRÄTT": "bostäder", "FÖRSKOLA": "kommersiellt", "LOKAL": "kommersiellt", "KONTOR": "kommersiellt"}
START_YIELD = {"bostäder": 4.0, "kommersiellt": 5.0}
YIELD_SPANN = {"bostäder": (2.0, 6.0), "kommersiellt": (3.0, 7.0)}

# FC-typer: specialister + två breda
FC_TYPER = {
    "HYRESRÄTT": {"HYRESRÄTT"}, "FÖRSKOLA": {"FÖRSKOLA"}, "LOKAL": {"LOKAL"}, "KONTOR": {"KONTOR"},
    "BOSTÄDER": {"HYRESRÄTT", "FÖRSKOLA"}, "KOMMERSIELLT": {"LOKAL", "KONTOR"},
}


def avrunda(v, steg):
    return int(round(v / steg) * steg)


@dataclass
class Fastighet:
    namn: str
    typ: str
    bas_dn: int              # årligt driftnetto FÖRE ränta (Mkr) i energiklass C — styr marknadsvärdet
    ek: str                  # energiklass A–E
    lan: int                 # tryckt lån (eller nedskrivet efter banken)
    ranta: int = 0           # årlig räntekostnad på lånet (fast i grundspelet)
    dn_brickor: int = 0      # dolt netto: + plus / − minus
    ek_brickor: int = 0      # dolt netto energi
    plus_att_visa: int = 0   # antal +1 DN som nått netto +3 men inte visats (regeln "plus valfritt")
    varningar: list = field(default_factory=list)   # underhållsvarningar: röjkostnader (Mkr)
    villkor: list = field(default_factory=list)     # villkorskort på fastigheten (text)
    uppgraderingsstopp: bool = False
    varningsstraff_tagit: bool = False

    def eff_noi(self, extra=0):
        """Driftnetto före ränta — det marknaden värderar."""
        return max(0, self.bas_dn + EK_MOD[self.ek] + extra)

    def eff_dn(self, extra=0):
        """Driftnetto efter ränta (det som står på kortet) — det som går till kassan. Kan vara 0."""
        return max(0, self.eff_noi(extra) - self.ranta)


@dataclass
class Spelare:
    namn: str
    strategi: object
    kassa: float = 0.0
    restkort: int = 0
    riskbuffert: int = 0
    hand: list = field(default_factory=list)       # personkort + förköpskort (dict)
    fastigheter: list = field(default_factory=list)
    fc: dict = None
    fs: dict = None
    fc_senior: bool = False
    fs_senior: bool = False
    fc_utveckling: int = 0
    fs_utveckling: int = 0
    vantande_kassa: float = 0.0                     # engångsbelopp som realiseras vid nästa marknad
    sanering: list = field(default_factory=list)    # [(fastighet, skuld)] åtaganden sedan förra marknaden
    skold_anvand: bool = False                      # FC Skölden, en gång per kvartal
    tb: float = 0.0                                 # täckningsbidrag från Genomförandet
    brf_intakt: float = 0.0                         # sålda BRF
    start_ek: float = 0.0                           # fastigheternas nettovärde vid start
    start_kassa: float = 0.0
    start_tillgangar: float = 0.0                   # MV + kassa vid start (nämnare i F-poäng)

    def fc_typer(self):
        return FC_TYPER.get(self.fc["Typ"], set()) if self.fc else set()


@dataclass
class Spel:
    spelare: list
    kvartal: int = 0
    yieldniva: dict = field(default_factory=lambda: dict(START_YIELD))
    yieldbana: dict = field(default_factory=dict)   # spår -> [ändring för Q2, Q3, Q4, Slut]
    projektbank: list = field(default_factory=list)
    bankfynd: list = field(default_factory=list)
    logg: list = field(default_factory=list)
    statistik: dict = field(default_factory=dict)
