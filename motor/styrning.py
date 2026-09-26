"""Styrningen: allt motorn behöver utifrån går genom två kanaler.

Beslut — varje anrop till ett kvarters strategi blir ett beslut. En bott kan svara, en människa
         kan tillfrågas, eller så läses svaret ur loggen (uppspelning).
Slump  — tärningar och kort. Motorn slår själv (online), spelarna anger vad de slog och drog
         (fysiskt spel), eller så läses utfallet ur loggen.

Allt som passerar skrivs i partiets logg i en form som kan sparas som JSON. Loggen räcker för att
spela upp partiet igen: samma regler + samma logg = samma parti. Reglerna i motorn rörs inte.

Värden kodas som referenser in i motorns eget tillstånd ("det tredje projektet i listan", "kvarter
2:s första fastighet"), så att en logg inte beror på Python-objekt och kan läsas av webbklienten.
"""
from collections import deque
from dataclasses import dataclass, field, is_dataclass

PRIMITIVA = (type(None), bool, int, float, str)
HOPPA_OVER = {"d", "p", "s", "stat", "statistik"}   # data, parametrar, slump: letas bara i sista hand


class LoggFel(Exception):
    """Loggen stämmer inte med partiet (annan regelversion eller skadad logg)."""


# ---------------------------------------------------------------------------- kodning
def _barn(obj):
    """Ett objekts delar som (steg, värde). Steg: ("a", namn), ("i", index) eller ("k", nyckel)."""
    if isinstance(obj, (list, tuple)):
        return [(("i", i), v) for i, v in enumerate(obj)]
    if isinstance(obj, dict):
        return [(("k", k), v) for k, v in obj.items() if isinstance(k, str)]
    if is_dataclass(obj) or hasattr(obj, "__dict__"):
        return [(("a", k), v) for k, v in vars(obj).items() if not k.startswith("_")]
    return []


def hitta(varde, rotter, djup=7):
    """Sök en väg från någon rot till exakt detta objekt (identitet), bredden först."""
    sedda = set()
    ko = deque(((("r", i),), r) for i, r in enumerate(rotter))
    reserv = []
    while ko:
        vag, obj = ko.popleft()
        if obj is varde:
            return list(vag)
        if isinstance(obj, PRIMITIVA) or id(obj) in sedda or len(vag) > djup:
            continue
        sedda.add(id(obj))
        for steg, v in _barn(obj):
            if isinstance(v, PRIMITIVA):
                continue
            if steg[0] == "a" and steg[1] in HOPPA_OVER:
                reserv.append((vag + (steg,), v))
            else:
                ko.append((vag + (steg,), v))
        if not ko and reserv:
            ko.extend(reserv)
            reserv = []
    return None


def folj(vag, rotter):
    obj = None
    for typ, nyckel in vag:
        if typ == "r":
            obj = rotter[nyckel]
        elif typ == "a":
            obj = getattr(obj, nyckel)
        else:
            obj = obj[nyckel]
    return obj


def koda(varde, rotter):
    """Kodar ett värde som JSON: primitiva som de är, objekt som en väg in i rötterna."""
    if isinstance(varde, PRIMITIVA):
        return varde
    vag = hitta(varde, rotter)
    if vag is not None:
        return {"ref": [list(s) for s in vag]}
    if isinstance(varde, (list, tuple)):
        return {"tupel" if isinstance(varde, tuple) else "lista": [koda(v, rotter) for v in varde]}
    raise LoggFel(f"kan inte koda {type(varde).__name__}: {varde!r}"[:200])


def avkoda(kod, rotter):
    if isinstance(kod, PRIMITIVA):
        return kod
    if "ref" in kod:
        return folj([tuple(s) for s in kod["ref"]], rotter)
    if "tupel" in kod:
        return tuple(avkoda(v, rotter) for v in kod["tupel"])
    return [avkoda(v, rotter) for v in kod["lista"]]


# ---------------------------------------------------------------------------- frågor
@dataclass
class Fraga:
    """Ett beslut som väntar på en människa (eller ett slumputfall i fysiskt spel)."""
    nr: int
    kanal: str                    # "beslut" eller "slump"
    kvarter: str | None
    skede: str | None             # "PU", "S2", "F"
    metod: str                    # strategimetodens eller slumpmetodens namn
    argument: list = field(default_factory=list)   # kodade argument (vägar in i rötterna)
    forslag: object = None        # bottens svar, kodat (ledtråd och standardval)


# ---------------------------------------------------------------------------- beslut
class Styrd:
    """Står i motorn där en strategi förväntas. Varje metodanrop blir ett beslut i partiet."""

    def __init__(self, parti, kvarter, skede, bott=None, manniska=False):
        self._parti, self._kvarter, self._skede = parti, kvarter, skede
        self._bott, self._manniska = bott, manniska

    @property
    def namn(self):
        return "människa" if self._manniska else getattr(self._bott, "namn", "logg")

    def __getattr__(self, metod):
        attr = getattr(self._bott, metod) if self._bott is not None else None
        if attr is not None and not callable(attr):
            return attr

        def beslut(motor, subjekt, *args, **kw):
            return self._parti.beslut(self, metod, motor, subjekt, args, kw)
        return beslut


# ---------------------------------------------------------------------------- slump
SLUMPMETODER = ("d20", "tarning", "heltal", "slumptal", "triangel", "index", "valj", "blanda_lista", "dra")


class StyrdSlump:
    """Slump som loggas och kan spelas upp. `bas` slår på riktigt (DigitalSlump) när loggen tar slut."""

    def __init__(self, parti, bas):
        self._parti, self.bas = parti, bas
        self.bott = bas.bott
        self.lekar = {}               # namn -> alla kort i leken (för att koda dragna kort)

    def blanda(self, namn, kort):
        self.lekar[namn] = list(kort)
        self.bas.blanda(namn, kort)

    def __getattr__(self, metod):
        if metod not in SLUMPMETODER:
            return getattr(self.bas, metod)

        def slump(*args):
            return self._parti.slump(self, metod, args)
        return slump

    # kodning av slumpens svar, relativt argumenten
    def koda(self, metod, args, varde):
        if metod == "valj":
            return next(i for i, v in enumerate(args[0]) if v is varde)
        if metod == "blanda_lista":
            kvar = list(enumerate(args[0]))
            ordning = []
            for v in varde:
                j = next(n for n, (_, x) in enumerate(kvar) if x is v)
                ordning.append(kvar.pop(j)[0])
            return ordning
        if metod == "dra":
            return next(i for i, v in enumerate(self.lekar[args[0]]) if v is varde)
        return varde

    def avkoda(self, metod, args, kod):
        if metod == "valj":
            return args[0][kod]
        if metod == "blanda_lista":
            return [args[0][i] for i in kod]
        if metod == "dra":
            return self.lekar[args[0]][kod]
        return kod
