"""Provspela Kvarteret, Kampanj och Staden med enbart datorbolag.

Det finns ingen testsvit, så det här är röktestet för kvarteret.py och staden.py: varje
parti spelas från start till slutresultat, och ett undantag eller ett parti som fastnar
stoppar körningen. Skriver också ut poängspridningen, som stöd när lägena balanseras.

Kör:  python tools/provspela.py [antal partier per läge]
"""
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

import kvarteret  # noqa: E402
from data_loader import GameData  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def kod(prefix, i):
    """Fyra bokstäver, som riktiga rumskoder."""
    return prefix + "".join(chr(65 + (i // 26 ** k) % 26) for k in (2, 1, 0))


def spela_rum(room, max_steg=400):
    """Driv ett rum till slutresultatet. Alla obesvarade beslut tas av datorbolagens logik."""
    room.start()
    for _ in range(max_steg):
        if room.kind == "final":
            return
        room.force()
    raise RuntimeError(f"Partiet fastnade i steget {room.step} (runda {room.round}).")


def provspela_lage(gd, lage):
    poang, steg = [], []
    for i in range(N):
        room = kvarteret.KRoom(kod("T", i), gd, lage)
        room.add_player("Människa")
        for n in (1, 2):
            room.add_player(f"Datorbolag {n}", is_bot=True)
        spela_rum(room)
        steg.append(len(room.flow))
        for p in room.players.values():
            poang.append(p.result["score"])
        if lage == "kampanj" and i == 0:    # sparningen ska gå att läsa tillbaka
            mgr = kvarteret.KvarteretManager()
            mgr.gd = gd
            laddat = mgr.hamta(room.code, gd)
            assert laddat and laddat.step == "final" and len(laddat.players) == 3, "sparat rum gick inte att läsa"
    print(f"{lage:8s} {N} partier · {steg[0]} steg · poäng min {min(poang):.1f} / median "
          f"{statistics.median(poang):.1f} / max {max(poang):.1f}")


def provspela_staden(gd):
    try:
        import staden
    except ImportError:
        print("staden   (finns inte än)")
        return
    for i in range(max(3, N // 10)):
        stad = staden.Stad.ny(kod("S", i), gd, "Människa", antal_datorbolag=3, langd="kort")
        omgangar = 0
        while not stad.klar:
            room = stad.starta_omgang(gd)
            spela_rum(room)
            omgangar += 1
            assert omgangar <= 30, "staden tar aldrig slut"
        st = stad.vy(None)["stallning"]
        if i == 0:
            print(f"staden   {omgangar} omgångar · ställning: "
                  + ", ".join(f"{b['namn']} {b['poang']:.0f}" for b in st))
            laddad = staden.Stad.las(stad.kod)
            assert laddad and laddad.klar and len(laddad.bolag) == len(stad.bolag), "sparad stad gick inte att läsa"
    print(f"staden   {max(3, N // 10)} städer spelade till slut")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:      # provspel ska inte lämna loggar eller sparfiler efter sig
        kvarteret.LOG_DIR = os.path.join(tmp, "loggar")
        kvarteret.SPAR_DIR = os.path.join(tmp, "sparade")
        gd = GameData()
        for lage in kvarteret.LAGEN:
            provspela_lage(gd, lage)
        try:
            import staden
            staden.STAD_DIR = os.path.join(tmp, "staden")
        except ImportError:
            pass
        provspela_staden(gd)
        print("Klart: inga krascher.")
