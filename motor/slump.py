"""Slumpen är utbytbar: samma regler oavsett om tärningar och kort är digitala eller fysiska.

DigitalSlump  — motorn slår och drar själv (onlinespel, bottar).
En spellogg-variant (fysiskt spel) implementerar samma metoder men frågar spelaren
vad hen slog och drog — så att motorn kan följa ett fysiskt parti.
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

    def blanda_lista(self, lista):
        lista = list(lista)
        self.rng.shuffle(lista)
        return lista
