"""Skede 2 — Planering (2.1) och Genomförande (2.2). Regelboken kapitel 6–8 och de tryckta korten.

Tar emot Skede 1:s resultat (motor/pu.py) och lämnar TB, TG, avvikelser (Mu), riskbuffert och
moderbolagslån till Förvaltningen. Motorn fattar inga beslut själv: valen går till strategin.
"""
import re
from dataclasses import dataclass, field

from .data import las_lek
from .pu import tal
from .slump import DigitalSlump

KOMPETENSER = ["STA", "KOM", "SAM", "NOG", "INN", "ABM"]
# Planeringens 13 steg (brädet och korten): (kategori, lev/org, nivåkrav-kolumn på projektkortet)
STEG = [
    ("STÖDFUNKTIONER", "org", None), ("MARK", "lev", "Nivåkrav Mark"),
    ("HUSUNDERBYGGNAD", "lev", "Nivåkrav Husunderbyggnad"), ("DIGITALISERING", "org", None),
    ("STOMME", "lev", "Nivåkrav Stomme"), ("INSTALLATIONER", "lev", "Nivåkrav Installationer"),
    ("OPERATIVT TEAM", "org", None), ("GEMENSAMMA ARBETEN", "lev", "Nivåkrav Gemensamma arbeten"),
    ("YTTERTAK", "lev", "Nivåkrav Yttertak"), ("FASADER", "lev", "Nivåkrav Fasader"),
    ("MARKNADSTEAM", "org", None), ("STOMKOMPLETTERING", "lev", "Nivåkrav Stomkomplettering"),
    ("INV YTSKIKT", "lev", "Nivåkrav Ytskikt"),
]
# PL-händelsekortens kategori -> planeringssteg
HANDELSE_STEG = {"INSTALLATÖRER": "INSTALLATIONER", "STOMKOMP": "STOMKOMPLETTERING",
                 "GEM ARBETEN": "GEMENSAMMA ARBETEN"}
KLASS_BTA = [(5000, "A"), (7000, "B"), (9000, "C")]
KLASS_BYA = [(4000, "A"), (4750, "B"), (5000, "C")]
KOLUMN = {"BOSTÄDER": "B", "BOSTAD+1": "S", "ÖVRIGA": "K"}
NIVAER = ["Negativt", "Neutralt", "Positivt", "Bonus"]
MU = [100, 90, 82, 75, 70, 65, 61, 58, 55, 52, 50]


def klass(varde, grans):
    return next((k for g, k in grans if varde <= g), "D")


def mu(n):
    return (MU[n] if n <= 10 else max(0, 50 - (n - 10))) / 100


def kompetenser(kort):
    """Kortets kompetenser; kolumnerna heter 'STA Stabilitet' … (organisation: 'ARB Arbetsmiljö')."""
    ut = {}
    for k, v in kort.items():
        if k and k[:3] in KOMPETENSER + ["ARB"] and k[3:4] == " ":
            n = int(tal(v))
            if n:
                ut["ABM" if k[:3] == "ARB" else k[:3]] = n
    return ut


def nada_niva(nivaer, kort):
    """Högsta nivån vars krav korten tillsammans når ('Negativt' om ingen)."""
    summa = {}
    for k in kort:
        for c, n in kompetenser(k).items():
            summa[c] = summa.get(c, 0) + n
    bast = "Negativt"
    for n, kr in nivaer:
        if all(summa.get(c, 0) >= v for c, v in kr.items()):  # tomt krav ('—') nås utan kort
            bast = n
    return bast


def krav(text):
    """'KOM 2, SAM 5' -> {'KOM': 2, 'SAM': 5}; '—' -> {}; tomt -> None (nivån finns inte för typen)."""
    if text in (None, ""):
        return None
    if str(text).strip() in ("—", "-"):
        return {}
    return {k: int(n) for k, n in re.findall(r"([A-Z]{3}) (\d+)", str(text))}


@dataclass
class S2Parametrar:
    lan_nominellt: float = 100
    lan_utbetalt: float = 95
    erfarenhet_tak: int = 12
    t_start: int = 12
    t_projekt_tak: int = 14
    t_golv: int = 8


@dataclass
class Bolag:
    """Ett kvarter genom Skede 2."""
    namn: str
    strategi: object
    pu: dict
    q_krav: int = 0
    h_krav: int = 0
    q: int = 0                    # beslut: utfallen (färgade kuber) startar på 0
    h: int = 0
    t: int = 12
    erfarenhet: int = 0
    riskbuffert: int = 0
    abt: float = 0.0              # ABT-budgeten (från Skede 1)
    kostnad: float = 0.0          # ABT-kostnad (minus intäkter som B-ÄTA)
    lan: int = 0
    kvartertyp: str = "ÖVRIGA"
    bta_klass: str = "A"
    bya_klass: str = "A"
    ac: dict = None
    ledning: list = field(default_factory=list)       # CEO, CFO, COO
    hand: list = field(default_factory=list)          # kompetenskort som kan spelas en gång i Genomförandet
    handelsehog: list = field(default_factory=list)
    lev_niva_1_2: int = 0
    konsekvenskort: int = 0
    garantikort: int = 0
    fas_utfall: list = field(default_factory=list)

    @property
    def kvar(self):
        return self.abt - self.kostnad + self.lan * 95


class S2Data:
    def __init__(self):
        self.leverantorer = las_lek("PL_leverantörer.xlsx")
        self.organisation = las_lek("PL_organisation.xlsx")
        self.arbetschef = las_lek("PL_personal.xlsx")
        self.ledning = las_lek("L_personal.xlsx")
        self.handelse = [k for k in las_lek("PL_Händelsekort.xlsx") if k.get("Namn")]
        self.fas = las_lek("GF_faskort.xlsx")
        self.kultur = las_lek("GF_kultur.xlsx")
        self.konsekvens = las_lek("GF_Konsekvenskort.xlsx")
        self.garanti = las_lek("GF_garantibesiktning.xlsx")


class Skede2:
    def __init__(self, pu_resultat, strategier, parametrar=None, slump=None, data=None):
        self.p = parametrar or S2Parametrar()
        self.s = slump or DigitalSlump()
        self.d = data or S2Data()
        self.bolag = [Bolag(namn=r["kvarter"], strategi=st, pu=r) for r, st in zip(pu_resultat, strategier)]
        self.fas, self.steg_nr, self.steg_namn, self.fas_kort = "uppstallning", 0, None, None   # för spelledaren
        self.aktiv = None                                                                        # vems tur
        self.stat = {k: 0 for k in ("lan", "kultur_kopt", "fas_nivå_Negativt", "fas_nivå_Neutralt",
                                    "fas_nivå_Positivt", "fas_nivå_Bonus", "fas_opaverkad", "omslag")}

    # ------------------------------------------------------------------ effekter
    def betala(self, b, mkr):
        b.kostnad += mkr
        while b.kvar < 0:                                    # beslut: moderbolagslån tas automatiskt (7.2)
            b.lan += 1
            self.stat["lan"] += 1

    def andra(self, b, q=0, h=0, t=0, erf=0):
        b.q = max(0, b.q + q)
        b.h = max(0, b.h + h)
        b.t = max(self.p.t_golv, b.t + t)
        b.erfarenhet = max(0, min(self.p.erfarenhet_tak, b.erfarenhet + erf))

    def effekt(self, b, text):
        """Kortens effekttext: '-4 Mkr, -1 Q', 'Fördröjning: 2 månader', '(B)ÄTA +6/+8/+10' …"""
        text = str(text or "").strip()
        if ":" in text and not text.startswith("("):
            text = text.split(":", 1)[1].strip()
        for del_ in [d.strip() for d in text.split(", ") if d.strip()]:
            if del_.lower().startswith("ingen"):
                continue
            if m := re.fullmatch(r"\(B\)ÄTA \+(\d+)/\+(\d+)/\+(\d+)", del_):
                self.betala(b, -int(m.group("BSK".index(KOLUMN[b.kvartertyp]) + 1)))   # beslut: B-ÄTA till ABT
            elif m := re.fullmatch(r"([+-]?\d+(?:,\d+)?) Mkr", del_):
                self.betala(b, -tal(m.group(1)))
            elif m := re.fullmatch(r"([+-]\d+) ([QHT])", del_):
                n = int(m.group(1))
                self.andra(b, **{m.group(2).lower(): n})
            elif m := re.fullmatch(r"\+?(\d+) (mån|månad|månader)", del_):
                self.andra(b, t=int(m.group(1)))
            elif m := re.fullmatch(r"(\d+) (månad|månader) förkortad tidplan", del_):
                self.andra(b, t=-int(m.group(1)))
            else:
                raise ValueError(f"Okänd effekt: {del_!r}")

    def slag(self, b, kort, kolumner, grans, farlig):
        """D20 + erfarenhet mot kortets skala; omslag med riskbuffert om strategin vill (max 1)."""
        def las(v):
            for g, kol in zip(grans, kolumner):
                if v <= g:
                    return kort[kol]
            return kort[kolumner[-1]]
        utfall = las(self.s.d20() + b.erfarenhet)
        # 3.6: omslag med en riskbuffert på vilket utfall som helst, högst en gång per slag
        samst = utfall == kort[kolumner[0]] and farlig
        if b.riskbuffert and b.strategi.sla_om_kort(self, b, kort, utfall, samst):
            b.riskbuffert -= 1
            self.stat["omslag"] += 1
            utfall = las(self.s.d20() + b.erfarenhet)
        self.effekt(b, utfall)

    def pl_handelse(self, b):
        if b.handelsehog:
            kort = self.s.dra_fran(b.handelsehog, "PL-händelser")
            self.slag(b, kort, ["Konsekvens 1–5", "Konsekvens 6–17", "Konsekvens 18–20", "Konsekvens 21+"],
                      [5, 17, 20], True)

    # ------------------------------------------------------------------ Planering
    def planering(self):
        ledning = {r: self.s.blanda_lista([k for k in self.d.ledning if k["Roll"] == r], r) for r in ("CEO", "CFO", "COO")}
        for b in self.bolag:
            r = b.pu
            b.q_krav, b.h_krav = r["q_krav"], r["h_krav"]
            b.abt = r["abt"]
            b.riskbuffert = r["riskbuffert"]
            b.erfarenhet = min(self.p.erfarenhet_tak, r["erfarenhet"])
            b.kvartertyp = r["kvartertyp"]
            b.bta_klass, b.bya_klass = klass(r["bta"], KLASS_BTA), klass(r["bya"], KLASS_BYA)
            max_t = max((int(tal(p["Tidspåverkan T"])) for p in r["placerade"]), default=0)
            # beslut: T = 12 + projektens högsta T (högst 14) + tidsjusteringen från Skede 1, golv 8
            b.t = max(self.p.t_golv, min(self.p.t_projekt_tak, self.p.t_start + max_t) + r["tid"])
            b.ledning = [ledning[roll].pop() for roll in ("CEO", "CFO", "COO")]   # 2.3 (här: slumpat)
            b.hand = [r["pc_kort"]] + b.ledning
        ac_kvar = list(self.d.arbetschef)
        for b in sorted(self.bolag, key=lambda b: b.pu["bta"]):     # 6.1: lägst BTA väljer först
            self.aktiv = b
            b.ac = b.strategi.valj_ac(self, b, ac_kvar)
            ac_kvar.remove(b.ac)
            b.riskbuffert += int(tal(b.ac["Riskbuffert"]))
            self.andra(b, q=int(tal(b.ac["Förbättrar krav: kvalitet (Q)"])),
                       h=int(tal(b.ac["Förbättrar krav: hållbarhet (H)"])),
                       t=-int(tal(b.ac["Förbättrar krav: tid (T)"])), erf=int(tal(b.ac["Erfarenhet"])))
            b.hand.append(b.ac)
        self.fas = "planering"
        for nr, (kategori, sort, kravkol) in enumerate(STEG, 1):
            self.steg_nr, self.steg_namn = nr, kategori
            for b in self.bolag:
                self.aktiv = b
                b.handelsehog += [k for k in self.d.handelse
                                  if HANDELSE_STEG.get(k["Kategori"], k["Kategori"]) == kategori]
                lek = self.d.leverantorer if sort == "lev" else self.d.organisation
                alternativ = sorted((k for k in lek if k["Kategori"] == kategori), key=lambda k: tal(k["Nivå"]))
                lagst = 1
                if kravkol:                                  # leverantören måste klara projektens nivåkrav
                    lagst = max([1] + [int(m.group(1)) for p in b.pu["placerade"]
                                       if (m := re.search(r"(\d)", str(p.get(kravkol) or "")))])
                kort = b.strategi.valj_niva(self, b, [k for k in alternativ if tal(k["Nivå"]) >= lagst])
                if sort == "lev":
                    self.betala(b, tal(kort[f"Kostnad klass {b.bya_klass if kort['Kostnaden beror av'] == 'BYA' else b.bta_klass} (Mkr)"]))
                    if tal(kort["Nivå"]) <= 2:
                        b.lev_niva_1_2 += 1
                else:
                    self.betala(b, tal(kort["Fast kostnad (Mkr)"]))
                    b.riskbuffert += int(tal(kort["Riskbuffert"]))
                self.andra(b, q=int(tal(kort["Q"])), h=int(tal(kort["H"])), t=int(tal(kort["T (mån)"])),
                           erf=int(tal(kort["Erfarenhet"])))
                b.hand.append(kort)
                self.pl_handelse(b)

    # ------------------------------------------------------------------ Genomförande
    def losning(self, krav_, hand):
        """Minsta uppsättning kompetenskort som når kravet (per kompetens), eller None. Ta-tillbaka-regeln:
        når man inte nivån förbrukas inga kort."""
        brist = dict(krav_)
        valda = []
        tillgangliga = list(hand)
        while any(v > 0 for v in brist.values()):
            bast = max(tillgangliga, default=None,
                       key=lambda k: (sum(min(n, brist.get(c, 0)) for c, n in kompetenser(k).items()),
                                      -sum(kompetenser(k).values())))
            if bast is None or not sum(min(n, brist.get(c, 0)) for c, n in kompetenser(bast).items()):
                return None
            tillgangliga.remove(bast)
            valda.append(bast)
            for c, n in kompetenser(bast).items():
                if c in brist:
                    brist[c] -= n
        return valda

    def genomforande(self):
        hogar = {s: self.s.blanda_lista([k for k in self.d.fas if int(tal(k["Steg"])) == s], f"FAS {s}") for s in range(1, 9)}
        kulturhog = self.s.blanda_lista(self.d.kultur, "kultur")
        ordning = sorted(self.bolag, key=lambda b: b.pu["bta"])     # beslut: lägst BTA först
        self.fas = "genomforande"
        for steg in range(1, 9):
            self.steg_nr, self.fas_kort = steg, None
            fas = hogar[steg].pop()
            self.fas_kort = fas
            pris = tal(fas["Kostnad kulturaktiviteter (Mkr)"])
            for b in ordning:
                self.aktiv = b
                for _ in range(b.strategi.kulturkort(self, b, fas, pris)):
                    if kulturhog:
                        b.hand.append(kulturhog.pop())
                        self.betala(b, pris)
                        self.stat["kultur_kopt"] += 1
                kol = KOLUMN[b.kvartertyp]
                if all(krav(fas[f"{n} {kol}"]) is None for n in NIVAER[1:]):
                    self.stat["fas_opaverkad"] += 1               # beslut: tom kolumn = påverkas inte alls
                else:
                    # 7.5: kvarteret lägger kompetenskort på bordet; summan avgör nivån. Når korten ingen nivå
                    # över Negativt tas de tillbaka till handen (inget förbrukas).
                    nivaer = [(n, krav(fas[f"{n} {kol}"])) for n in NIVAER if krav(fas[f"{n} {kol}"]) is not None]
                    valda = b.strategi.spela_fas(self, b, fas, nivaer)
                    kort = []
                    for k in valda or []:
                        if any(k is h for h in b.hand) and not any(k is x for x in kort):
                            kort.append(k)
                    niva = nada_niva(nivaer, kort)
                    if niva != "Negativt":
                        for k in kort:
                            b.hand.remove(k)
                    self.stat["fas_nivå_" + niva] += 1
                    b.fas_utfall.append(niva)
                    self.effekt(b, fas[f"Effekt {niva.lower()}"])
                self.pl_handelse(b)

    # ------------------------------------------------------------------ Skedesavslut
    def konsekvens(self, b, typ, kvar):
        hog = self.s.blanda_lista([k for k in self.d.konsekvens if k["Typ"] == typ], f"konsekvens {typ}")
        while kvar > 0:
            if not hog:
                hog = self.s.blanda_lista([k for k in self.d.konsekvens if k["Typ"] == typ], f"konsekvens {typ}")
            fore = (b.q, b.h)
            self.slag(b, hog.pop(), ["Utfall D20+ER 1-9", "Utfall D20+ER 10-17", "Utfall D20+ER 18-24",
                                     "Utfall D20+ER 25+"], [9, 17, 24], True)
            b.konsekvenskort += 1
            kvar -= 1
            if typ == "KVALITET":                             # sänker kortet Q ytterligare: dra fler (8.2)
                kvar += fore[0] - b.q
                if b.q == 0:
                    break
            elif typ == "HÅLLBARHET":
                kvar += fore[1] - b.h
                if b.h == 0:
                    break

    def skedesavslut(self):
        self.fas, self.fas_kort = "avslut", None
        for b in self.bolag:                                  # 8.1–8.3: T, sedan Q, sedan H
            self.aktiv = b
            self.konsekvens(b, "TID", max(0, b.t - 12))
            if b.q > 0:
                self.konsekvens(b, "KVALITET", max(0, b.q_krav - b.q))
            if b.h > 0:
                self.konsekvens(b, "HÅLLBARHET", max(0, b.h_krav - b.h))
            # 8.4: garanti = dragna konsekvenskort + valda leverantörer på nivå 1–2
            antal = b.konsekvenskort + b.lev_niva_1_2
            hog = []
            for _ in range(antal):
                if not hog:
                    hog = self.s.blanda_lista(self.d.garanti, "garanti")
                self.slag(b, hog.pop(), ["Utfall D20+erfarenhet 1-9", "Utfall D20+erfarenhet 10-17",
                                         "Utfall D20+erfarenhet 18-24", "Utfall D20+erfarenhet 25+"],
                          [9, 17, 24], True)
                b.garantikort += 1

    # ------------------------------------------------------------------ hela skedet
    def spela(self):
        self.planering()
        self.genomforande()
        self.skedesavslut()
        return [self.resultat(b) for b in self.bolag]

    def resultat(self, b):
        tb = b.abt - b.kostnad
        tg = 100 * tb / b.abt if b.abt > 0 else 0.0
        n = max(0, b.q_krav - b.q) + max(0, b.h_krav - b.h) + max(0, b.t - 12)
        return {"kvarter": b.namn, "strategi": b.strategi.namn, "tb": tb, "TG": tg, "lan": b.lan,
                "kassa": tb + b.lan * self.p.lan_utbetalt, "n": n, "Mu": mu(n), "q": b.q, "q_krav": b.q_krav,
                "h": b.h, "h_krav": b.h_krav, "t": b.t, "riskbuffert": b.riskbuffert, "erfarenhet": b.erfarenhet,
                "konsekvenskort": b.konsekvenskort, "garantikort": b.garantikort, "ac": b.ac["Namn"],
                "fas": b.fas_utfall}
