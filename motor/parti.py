"""Ett parti: hela spelet (Skede 1 → Skede 2 → Förvaltning) för 1–4 kvarter, styrt utifrån.

Motorn körs i en egen tråd. När den behöver ett beslut av en människa stannar tråden och partiet
lämnar ut en Fråga; när svaret kommer fortsätter motorn. Bottar svarar direkt. Allt loggas, och ett
parti kan återskapas ur sin logg (t.ex. efter omstart av servern) och sedan spelas vidare.

    p = Parti([{"namn": "Norr", "styrning": "människa"}, {"namn": "Söder"}], fro=7)
    while (fraga := p.steg()) is not None:
        p.svara(fraga.forslag)            # här svarar en människa via gränssnittet
    p.resultat
"""
import queue
import threading
from collections import deque

from .data import Kortdata
from .motor import Motor, Parametrar
from .pu_strategi import PU_STRATEGIER
from .skede2_strategi import S2_STRATEGIER
from .slump import DigitalSlump, InmatadSlump
from .strategi import STRATEGIER
from .styrning import Fraga, LoggFel, Styrd, StyrdSlump, avkoda, koda

REGELVERSION = "2026-09-26"      # höjs när reglerna i motorn ändras; loggen bär versionen
BOTTAR = {"PU": PU_STRATEGIER, "S2": S2_STRATEGIER, "F": STRATEGIER}
STANDARDBOTT = {"PU": "balanserad", "S2": "balanserad", "F": "balanserad"}


class Avbrutet(Exception):
    pass


_AVBRYT = object()


class Parti:
    def __init__(self, kvarter, fro=None, logg=None, parametrar=None, data=None, regelversion=REGELVERSION,
                 slump="digital"):
        """kvarter: [{"namn": str, "styrning": "bott" | "människa", "bottar": {"PU": .., "S2": .., "F": ..}}]
        logg: en tidigare logg att spela upp innan partiet fortsätter.
        slump: "digital" (motorn slår och drar) eller "inmatad" (fysiskt spel: spelarna anger tärningar
        och dragna kort; frågorna kommer som Fråga med kanal "slump")."""
        if slump not in ("digital", "inmatad"):
            raise ValueError("slump är 'digital' eller 'inmatad'")
        self.slumpsatt = slump
        if not 1 <= len(kvarter) <= 4:
            raise ValueError("ett parti har 1–4 kvarter")
        self.kvarter = [{"styrning": "bott", **k, "bottar": {**STANDARDBOTT, **k.get("bottar", {})}} for k in kvarter]
        self.fro = fro
        self.regelversion = regelversion
        self.parametrar = parametrar or Parametrar()
        self.data = data or Kortdata()
        self.logg = []
        self._uppspelning = deque(logg or [])
        self._fragor, self._svar = queue.Queue(), queue.Queue()
        self._nr = 0
        self.motor = None
        self.resultat = None
        self.aktuell = None           # frågan som väntar på svar
        self._trad = None

    # ------------------------------------------------------------------ inställningar som kan sparas
    def uppstart(self):
        return {"regelversion": self.regelversion, "fro": self.fro, "kvarter": self.kvarter, "slump": self.slumpsatt}

    @classmethod
    def fran_sparat(cls, uppstart, logg, **kw):
        return cls(uppstart["kvarter"], fro=uppstart["fro"], logg=logg, regelversion=uppstart["regelversion"],
                   slump=uppstart.get("slump", "digital"), **kw)

    # ------------------------------------------------------------------ gränssnitt utåt
    def steg(self):
        """Kör tills en människa behöver svara (returnerar Frågan) eller partiet är slut (None)."""
        if self._trad is None:
            self._trad = threading.Thread(target=self._kor, daemon=True)
            self._trad.start()
        typ, varde = self._fragor.get()
        if typ == "fel":
            raise varde
        self.aktuell = varde if typ == "fraga" else None
        return self.aktuell

    def svara(self, kod):
        """Svara på den aktuella frågan med ett kodat värde (se styrning.koda)."""
        if self.aktuell is None:
            raise RuntimeError("ingen fråga väntar på svar")
        self.aktuell = None
        self._svar.put(kod)

    def avbryt(self):
        if self.aktuell is not None:
            self.aktuell = None
            self._svar.put(_AVBRYT)

    def spela_klart(self, svara=None):
        """Kör partiet till slut. `svara(fraga)` svarar för människorna (standard: bottens förslag)."""
        while (f := self.steg()) is not None:
            self.svara(svara(f) if svara else f.forslag)
        return self.resultat

    # ------------------------------------------------------------------ motorn (egen tråd)
    def _kor(self):
        try:
            def styrd(k, skede):
                bott = BOTTAR[skede][k["bottar"][skede]]()
                return Styrd(self, k["namn"], skede, bott=bott, manniska=k["styrning"] == "människa")
            bas = (DigitalSlump(self.fro) if self.slumpsatt == "digital"
                   else InmatadSlump(self._fraga_slump, self.fro))
            self.motor = Motor([styrd(k, "F") for k in self.kvarter], self.parametrar,
                               StyrdSlump(self, bas), self.data,
                               pu_strategier=[styrd(k, "PU") for k in self.kvarter],
                               s2_strategier=[styrd(k, "S2") for k in self.kvarter],
                               namn=[k["namn"] for k in self.kvarter])
            self.resultat = self.motor.spela()
            if self._uppspelning:
                raise LoggFel(f"partiet tog slut med {len(self._uppspelning)} loggposter kvar")
            self._fragor.put(("klar", None))
        except Avbrutet:
            self._fragor.put(("klar", None))
        except BaseException as e:           # noqa: BLE001 — skickas vidare till den som väntar
            self._fragor.put(("fel", e))

    def _fraga(self, **kw):
        self._nr += 1
        f = Fraga(nr=self._nr, **kw)
        self._fragor.put(("fraga", f))
        svar = self._svar.get()
        if svar is _AVBRYT:
            raise Avbrutet()
        return svar

    def _fraga_slump(self, metod, argument):
        """Fysiskt spel: fråga spelarna om en tärning eller ett draget kort (svaret: tal eller index)."""
        return self._fraga(kanal="slump", kvarter=None, skede=None, metod=metod, argument=argument)

    def _nasta_post(self, kanal, metod, kvarter=None):
        post = self._uppspelning.popleft()
        if post["kanal"] != kanal or post["metod"] != metod or post.get("kvarter") != kvarter:
            raise LoggFel(f"loggen säger {post['kanal']}/{post['metod']}/{post.get('kvarter')}, "
                          f"motorn vill ha {kanal}/{metod}/{kvarter} (post {len(self.logg)})")
        return post

    def beslut(self, styrd, metod, motor, subjekt, args, kw):
        rotter = [*args, *kw.values(), subjekt, motor]
        kvarter, skede = styrd._kvarter, styrd._skede
        if self._uppspelning:
            # botten räknar som i originalet (före beslutet): dess egen slump och det den tittar på
            # (t.ex. översta kortet i en hög) kommer i samma ordning som i loggen
            if styrd._bott is not None:
                getattr(styrd._bott, metod)(motor, subjekt, *args, **kw)
            post = self._nasta_post("beslut", metod, kvarter)
            self.logg.append(post)
            return avkoda(post["svar"], rotter)
        forslag = None
        if styrd._bott is not None:
            svar = getattr(styrd._bott, metod)(motor, subjekt, *args, **kw)
            forslag = koda(svar, rotter)
        if styrd._manniska:
            kod = self._fraga(kanal="beslut", kvarter=kvarter, skede=skede, metod=metod, forslag=forslag)
            svar = avkoda(kod, rotter)
            av = "människa"
        else:
            kod, av = forslag, "bott"
        self.logg.append({"kanal": "beslut", "kvarter": kvarter, "skede": skede, "metod": metod, "svar": kod, "av": av})
        return svar

    def slump(self, ss, metod, args):
        if self._uppspelning:
            post = self._nasta_post("slump", metod)
            varde = ss.avkoda(metod, args, post["varde"])
            if getattr(ss.bas, "digital", False):       # håll den digitala slumpen i takt och kontrollera
                egen = ss.koda(metod, args, getattr(ss.bas, metod)(*args))
                if egen != post["varde"]:
                    raise LoggFel(f"slumpen avviker från loggen i {metod}: {egen} ≠ {post['varde']}")
            elif hasattr(ss.bas, "notera_" + metod):      # inmatad: håll högarna i takt utan att fråga
                getattr(ss.bas, "notera_" + metod)(*args, varde)
        else:
            varde = getattr(ss.bas, metod)(*args)
            post = {"kanal": "slump", "metod": metod, "varde": ss.koda(metod, args, varde)}
            if metod == "dra":
                post["lek"] = args[0]
        self.logg.append(post)
        return varde
