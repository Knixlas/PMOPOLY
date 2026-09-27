"""Placeringspusslet (regelboken 4.3): kvarteret byggs av formbitar på tomten.

Facit för reglerna. Webbklienten (spel/webb/src/pussel/) har samma regler för direkt återkoppling;
båda provas mot samma testfall (tester/pussel_fall.json).

Tomten är 16 × 16 rutor. Rutorna skrivs [rad, kolumn].
  Lager 0 — mark: grundmarken 4 × 4 mitt på tomten plus markexpansioner, kant i kant med befintlig mark.
  Lager 1 — projekt direkt på marken. Alla typer. Inom marken, utan överlapp.
  Lager 2 — bostäder (BRF, hyresrätt) ovanpå andra projekt. Hela biten ska vila på lager 1.
Bitarna får roteras och speglas (8 lägen).
"""
from dataclasses import dataclass, field

TOMT = 16
GRUNDMARK = frozenset((r, k) for r in range(6, 10) for k in range(6, 10))
BOSTAD = {"BRF", "HYRESRÄTT"}
GRANNAR = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ---------------------------------------------------------------------------- former
def normalisera(celler):
    r0 = min(r for r, _ in celler)
    k0 = min(k for _, k in celler)
    return tuple(sorted((r - r0, k - k0) for r, k in celler))


def lagen(form):
    """Formens olika lägen (rotation × spegling), utan dubbletter, i fast ordning.
    Läge i: i % 4 kvartsvarv medurs, i ≥ 4 speglad först (vänster–höger)."""
    ut = []
    for i in range(8):
        c = vrid(form, i)
        if c not in ut:
            ut.append(c)
    return ut


def vrid(form, lage):
    """Formen i läge 0–7 (se lagen), normaliserad."""
    c = [(r, k) for r, k in form]
    if lage >= 4:
        c = [(r, -k) for r, k in c]
    for _ in range(lage % 4):
        c = [(k, -r) for r, k in c]           # kvartsvarv medurs
    return normalisera(c)


def placera(form, lage, rad, kol):
    """Rutorna på tomten när formens övre vänstra hörn (i läget) hamnar på [rad, kol]."""
    return frozenset((rad + r, kol + k) for r, k in vrid(form, lage))


# ---------------------------------------------------------------------------- kvarteret
@dataclass
class Bit:
    id: str
    typ: str                  # "MARK" eller projekttyp
    celler: frozenset
    lager: int                # 0 mark, 1 på marken, 2 ovanpå

    @classmethod
    def fran(cls, d):
        return cls(d["id"], d["typ"], frozenset(tuple(c) for c in d["celler"]), int(d["lager"]))

    def till(self):
        return {"id": self.id, "typ": self.typ, "celler": sorted(list(c) for c in self.celler), "lager": self.lager}


@dataclass
class Granskning:
    fel: dict = field(default_factory=dict)          # bitens id -> skäl
    mark: frozenset = frozenset()
    lager1: frozenset = frozenset()

    @property
    def giltigt(self):
        return not self.fel


def pa_tomten(celler):
    return all(0 <= r < TOMT and 0 <= k < TOMT for r, k in celler)


def sammanhangande(celler, start):
    """De rutor i `celler` som hänger ihop (kant i kant) med `start`."""
    sedda, ko = set(), [c for c in start if c in celler]
    while ko:
        c = ko.pop()
        if c in sedda:
            continue
        sedda.add(c)
        ko.extend((c[0] + dr, c[1] + dk) for dr, dk in GRANNAR if (c[0] + dr, c[1] + dk) in celler)
    return sedda


def granska(bitar, grundmark=GRUNDMARK):
    """Kontrollera ett kvarter. Returnerar vilka bitar som bryter mot reglerna och varför."""
    g = Granskning()
    mark = set(grundmark)
    expansioner = [b for b in bitar if b.lager == 0]
    for b in expansioner:
        if not pa_tomten(b.celler):
            g.fel[b.id] = "utanför tomten"
        elif b.celler & mark:
            g.fel[b.id] = "överlappar marken"
        else:
            mark |= b.celler
    nara = sammanhangande(mark, grundmark)
    for b in expansioner:
        if b.id not in g.fel and not b.celler <= nara:
            g.fel[b.id] = "inte kant i kant med marken"
    g.mark = frozenset(nara)
    upptaget = set()
    for b in (b for b in bitar if b.lager == 1):
        if not b.celler <= g.mark:
            g.fel[b.id] = "utanför marken"
        elif b.celler & upptaget:
            g.fel[b.id] = "överlappar ett annat projekt"
        else:
            upptaget |= b.celler
    g.lager1 = frozenset(upptaget)
    ovanpa = set()
    for b in (b for b in bitar if b.lager == 2):
        if b.typ not in BOSTAD:
            g.fel[b.id] = "bara bostäder får ligga ovanpå andra projekt"
        elif not b.celler <= g.lager1:
            g.fel[b.id] = "vilar inte helt på andra projekt"
        elif b.celler & ovanpa:
            g.fel[b.id] = "överlappar en annan bostad"
        else:
            ovanpa |= b.celler
    for b in bitar:
        if b.lager not in (0, 1, 2):
            g.fel[b.id] = "okänt lager"
    return g


def lager_for(typ, celler, mark, lager1):
    """Vilket lager en bit hamnar i om den släpps här: 1 på fri mark, 2 ovanpå projekt (bara bostäder).
    None om den inte får ligga här alls."""
    if celler <= mark and not celler & lager1:
        return 1
    if typ in BOSTAD and celler <= lager1:
        return 2
    return None


def form_av(kort):
    """Formen ur kortdatans kolumn "Form (rutor)" (JSON [[rad, kol], ...])."""
    import json
    return [tuple(c) for c in json.loads(kort["Form (rutor)"])]


def platser_markexpansion(mark, form):
    """Alla sätt att lägga en markexpansion kant i kant med marken, på tomten, utan överlapp.
    Ordnade stabilt (läge, rad, kolumn) och utan dubbletter."""
    mark = frozenset(mark)
    kant = {(r + dr, k + dk) for r, k in mark for dr, dk in GRANNAR} - mark
    ut, sedda = [], set()
    for c in lagen(form):
        for rad in range(TOMT):
            for kol in range(TOMT):
                celler = frozenset((rad + r, kol + k) for r, k in c)
                if celler in sedda or not pa_tomten(celler) or celler & mark or not celler & kant:
                    continue
                sedda.add(celler)
                ut.append(celler)
    return ut


def las_marklayout(svar, former):
    """En hel marklayout från en spelare: [[id, [[rad, kol], ...]], ...] med varje markexpansion
    (former: id -> kortets form). Returnerar {id: rutor} om layouten följer reglerna, annars ett
    felmeddelande (str). Alla markexpansioner ska vara med, var och en med sitt korts form."""
    try:
        bitar = {str(i): frozenset((int(r), int(k)) for r, k in celler) for i, celler in svar}
    except (TypeError, ValueError):
        return "marken ska vara [[id, [[rad, kol], ...]], ...]"
    if set(bitar) != set(former):
        return "alla markexpansioner ska vara med, och inga andra"
    for i, celler in bitar.items():
        if len(celler) != len(former[i]) or normalisera(celler) not in lagen(former[i]):
            return f"{i} har inte sitt korts form"
    fel = granska([Bit(i, "MARK", c, 0) for i, c in bitar.items()]).fel
    if fel:
        i, varfor = next(iter(fel.items()))
        return f"{i}: {varfor}"
    return bitar


# ---------------------------------------------------------------------------- lösaren
def _platser(form, index):
    """Alla sätt att lägga formen inom rutorna i `index` ({ruta: bit}), som bitmasker."""
    rader = [r for r, _ in index]
    kolumner = [k for _, k in index]
    ut = set()
    for c in lagen(form):
        for r in range(min(rader), max(rader) + 1):
            for k in range(min(kolumner), max(kolumner) + 1):
                mask = 0
                for dr, dk in c:
                    b = index.get((r + dr, k + dk))
                    if b is None:
                        break
                    mask |= b
                else:
                    ut.add(mask)
    return sorted(ut)


def _antal_som_ryms(storlekar, yta):
    n = 0
    for s in sorted(storlekar):
        if s > yta:
            break
        yta -= s
        n += 1
    return n


def losa(mark, projekt, alla=False, grans=300_000):
    """Lägg så många projekt som möjligt (flest, sedan störst yta) på marken.

    projekt: [(id, typ, form)]. alla=True: bara lösningar där alla får plats (svarar på "går det?").
    Returnerar (placeringar {id: (celler, lager)}, fullständig) — fullständig=False om sökningen
    avbröts vid `grans` steg (då är svaret det bästa som hittats)."""
    rutor = sorted(mark)
    index = {c: 1 << i for i, c in enumerate(rutor)}
    hela = (1 << len(rutor)) - 1
    ordning = sorted(projekt, key=lambda p: -len(p[2]))
    storlek = {p[0]: len(p[2]) for p in ordning}
    platser = {p[0]: _platser(p[2], index) for p in ordning}
    bast = {"n": -1, "yta": -1, "plac": {}}
    steg = [0]
    stopp = [False]

    def spara(plac):
        n, yta = len(plac), sum(storlek[i] for i in plac)
        if (n, yta) > (bast["n"], bast["yta"]):
            bast.update(n=n, yta=yta, plac=dict(plac))

    def rakna():
        steg[0] += 1
        if steg[0] > grans:
            stopp[0] = True
        return stopp[0]

    def fas2(uppe, plac, underlag, i):
        """Bostäderna som ska ligga ovanpå, på lager 1."""
        if rakna():
            return
        if i == len(uppe):
            spara(plac)
            return
        kvar = [storlek[p[0]] for p in uppe[i:]]
        if len(plac) + _antal_som_ryms(kvar, bin(underlag).count("1")) < bast["n"]:
            return
        id_ = uppe[i][0]
        for m in platser[id_]:
            if m & underlag == m:
                plac[id_] = (m, 2)
                fas2(uppe, plac, underlag & ~m, i + 1)
                del plac[id_]
        if not alla:
            fas2(uppe, plac, underlag, i + 1)

    def fas1(i, fritt, plac, uppe):
        if rakna():
            return
        if alla and bast["n"] == len(ordning):
            return
        kvar = ordning[i:]
        fri_yta = bin(fritt).count("1")
        ovriga = [len(p[2]) for p in kvar if p[1] not in BOSTAD]
        bostader = [len(p[2]) for p in kvar if p[1] in BOSTAD] + [storlek[p[0]] for p in uppe]
        tak = len(plac) + _antal_som_ryms(ovriga, fri_yta) + _antal_som_ryms(bostader, fri_yta + len(rutor))
        if tak < bast["n"] or (alla and tak < len(ordning)):
            return
        if i == len(ordning):
            underlag = hela & ~fritt
            fas2(uppe, dict(plac), underlag, 0)
            return
        id_, typ, _ = ordning[i]
        for m in platser[id_]:
            if m & fritt == m:
                plac[id_] = (m, 1)
                fas1(i + 1, fritt & ~m, plac, uppe)
                del plac[id_]
        if typ in BOSTAD:                          # skjut upp: läggs ovanpå i fas 2
            fas1(i + 1, fritt, plac, uppe + [ordning[i]])
        if not alla:                               # lämna oplacerad
            fas1(i + 1, fritt, plac, uppe)

    fas1(0, hela, {}, [])
    if alla and bast["n"] < len(ordning):
        return {}, not stopp[0]

    def celler(m):
        return frozenset(c for c, b in index.items() if m & b)
    return {i: (celler(m), l) for i, (m, l) in bast["plac"].items()}, not stopp[0]
