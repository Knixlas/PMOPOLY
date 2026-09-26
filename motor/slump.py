"""Slumpen är utbytbar: samma regler oavsett om tärningar och kort är digitala eller fysiska.

DigitalSlump  — motorn slår och drar själv (onlinespel, bottar).
InmatadSlump  — fysiskt spel (läge 2): spelarna anger vad tärningen visade och vilket kort de drog,
                så att motorn kan följa ett parti på brädet. Högar i okänd ordning är InmatadHog.
"""
import random


class DigitalSlump:
    digital = True        # slår själv; vid uppspelning slås samma slag igen och jämförs med loggen

    def __init__(self, fro=None):
        self.rng = random.Random(fro)
        # Bottarnas egen slump (tiebreak i deras val): hålls isär från spelets tärningar och kort,
        # så att ett parti blir detsamma oavsett om en bott eller en människa fattar besluten.
        self.bott = random.Random(None if fro is None else f"bott-{fro}")
        self.lekar = {}

    def d20(self):
        return self.rng.randint(1, 20)

    def tarning(self, sidor):
        """Ett slag med en tärning med `sidor` sidor (D6, kortens D-tärningar)."""
        return self.rng.randint(1, sidor)

    def heltal(self, lagst, hogst):
        """Slumpat heltal i ett spann (bara i förenklade startlägen, inte i det fysiska spelet)."""
        return self.rng.randint(lagst, hogst)

    def slumptal(self):
        return self.rng.random()

    def triangel(self, lagst, hogst, typvarde):
        return self.rng.triangular(lagst, hogst, typvarde)

    def index(self, n):
        """Slumpad position i en hög med n kort (dra ett kort ur högen utan att titta)."""
        return self.rng.randrange(n)

    def blanda(self, namn, kort):
        """Lägg upp en lek som dras utan återläggning (blandas om när den tar slut)."""
        lek = list(kort)
        self.rng.shuffle(lek)
        self.lekar[namn] = {"alla": list(kort), "hog": lek}

    def dra(self, namn):
        lek = self.lekar[namn]
        if not lek["hog"]:
            lek["hog"] = list(lek["alla"])
            self.rng.shuffle(lek["hog"])
        return lek["hog"].pop()

    def valj(self, lista):
        return self.rng.choice(lista)

    def blanda_lista(self, lista, namn=None):
        """En blandad hög (lista) att dra ur med pop(); namn anger högen i fysiskt spel."""
        lista = list(lista)
        self.rng.shuffle(lista)
        return lista

    def dra_kort(self, namn, kandidater):
        """Ett kort ur kandidaterna (dras blint ur en hög utan ordning)."""
        return self.rng.choice(kandidater)

    def dra_fran(self, lista, namn):
        """Dra ett kort blint ur en lista (tas bort ur listan)."""
        kort = self.dra_kort(namn, list(lista))
        ta_bort(lista, kort)
        return kort


def ta_bort(lista, kort):
    """Ta bort just det här kortet (identitet — två exemplar av samma kort är olika kort)."""
    for i, k in enumerate(lista):
        if k is kort:
            del lista[i]
            return
    raise ValueError("kortet finns inte i högen")


def kortnamn(kort):
    """Kortets id som spelarna ser det (tryckt på kortet)."""
    if isinstance(kort, dict):
        for nyckel in ("ID", "Kort-id", "Namn"):
            if kort.get(nyckel) not in (None, ""):
                return str(kort[nyckel])
    return str(getattr(kort, "namn", kort))


class VisadHog(list):
    """En blandad hög i digitalt spel: när ett kort dras (pop) får gränssnittet veta det."""

    def __init__(self, kort, namn, visa):
        super().__init__(kort)
        self.namn, self._visa = namn, visa

    def pop(self, i=-1):
        kort = super().pop(i)
        self._visa(self.namn, kort)
        return kort


class InmatadHog(list):
    """En blandad hög i fysiskt spel: motorn vet vilka kort som finns kvar men inte ordningen.
    Det översta kortet (hog[-1]) och pop() frågar vilket kort det är; svaret gäller tills kortet dras."""

    def __init__(self, slump, namn, kort):
        super().__init__(kort)
        self._slump, self.namn, self._topp = slump, namn, None

    def _vilket(self):
        if self._topp is None or not any(k is self._topp for k in self):
            self._topp = self._slump.dra_kort(self.namn, list(self))
        return self._topp

    def __getitem__(self, i):
        if i == -1 and len(self):
            return self._vilket()
        return super().__getitem__(i)

    def pop(self, i=-1):
        if not len(self):
            raise IndexError("högen är tom")
        kort = self._vilket()
        self._topp = None
        ta_bort(self, kort)
        return kort

    def insert(self, i, kort):                     # t.ex. "längst ned i högen": ordningen är okänd ändå
        super().insert(i, kort)


class InmatadSlump:
    """Fysiskt spel: allt slumpmässigt frågas. `fraga(metod, argument)` ställer frågan till spelarna och
    returnerar svaret: ett tal för tärningar, ett index i kandidaterna för kort."""
    digital = False
    inmatad = True

    def __init__(self, fraga, fro=None):
        self.fraga = fraga
        self.bott = random.Random(None if fro is None else f"bott-{fro}")
        self.lekar = {}                            # namn -> kort kvar i högen

    def d20(self):
        return int(self.fraga("d20", [1, 20]))

    def tarning(self, sidor):
        return int(self.fraga("tarning", [1, sidor]))

    def blanda(self, namn, kort):
        self.lekar[namn] = {"alla": list(kort), "kvar": list(kort)}

    def dra(self, namn):
        lek = self.lekar[namn]
        if not lek["kvar"]:
            lek["kvar"] = list(lek["alla"])        # blandas om
        kort = lek["kvar"][int(self.fraga("dra", [namn, [kortnamn(k) for k in lek["kvar"]]]))]
        ta_bort(lek["kvar"], kort)
        return kort

    def notera_dra(self, namn, kort):
        """Uppspelning: kortet drogs (utan fråga) — håll högen i takt."""
        lek = self.lekar[namn]
        if not lek["kvar"]:
            lek["kvar"] = list(lek["alla"])
        ta_bort(lek["kvar"], kort)

    def dra_kort(self, namn, kandidater):
        return kandidater[int(self.fraga("dra", [namn, [kortnamn(k) for k in kandidater]]))]

    def valj(self, lista):
        return lista[int(self.fraga("valj", [kortnamn(k) for k in lista]))]

    def blanda_lista(self, lista, namn=None):
        return InmatadHog(self, namn or "hög", lista)

    def dra_fran(self, lista, namn):
        kort = self.dra_kort(namn, list(lista))
        ta_bort(lista, kort)
        return kort

    def index(self, n):
        return int(self.fraga("index", [0, n - 1]))

    def heltal(self, lagst, hogst):
        return int(self.fraga("heltal", [lagst, hogst]))

    def slumptal(self):
        raise RuntimeError("slumptal används bara i simuleringens förenklade start")

    def triangel(self, lagst, hogst, typvarde):
        raise RuntimeError("triangel används bara i simuleringens förenklade start")
