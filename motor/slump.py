"""Slumpen är utbytbar: samma regler oavsett om tärningar och kort är digitala eller fysiska.

DigitalSlump  — motorn slår och drar själv (onlinespel, bottar).
En spellogg-variant (fysiskt spel) implementerar samma metoder men frågar spelaren
vad hen slog och drog — så att motorn kan följa ett fysiskt parti.
"""
import random


class DigitalSlump:
    def __init__(self, fro=None):
        self.rng = random.Random(fro)
        self.lekar = {}

    def d20(self):
        return self.rng.randint(1, 20)

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
