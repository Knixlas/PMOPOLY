"""Kortversionen (~20 minuter): samma regler, kortare parti.

Motorn är oförändrad i allt som spelas. Kortversionen bestämmer bara *hur mycket* som spelas och
*vem* som svarar på de beslut som inte spelas själva:

- Skede 1: fyra startprojekt per kvarter, lika stora för alla (intäkt, utvecklingskostnad, BTA,
  krav och nämndsumma), därefter några drag på brädet, nämnden som vanligt (4.1). Kompletteringen
  i 4.2 hoppas över och pusslet i 4.3 läggs av lösaren.
- Skede 2: man upphandlar själv ett par av de 13 posterna; övriga får en slumpad nivå som är
  densamma för alla kvarter och ger varken händelse- eller garantikort. Man spelar två byggfaser;
  övriga godkänns utan effekt.
- Förvaltningen: ett kvartal.

Det som slumpas av kortversionen själv (startportföljen, de automatiska nivåerna och vilka faser som
spelas) tas ur blandningar som redan är loggade, så partiet kan spelas upp och återupptas som vanligt.
"""
import hashlib
import random

KORT = {
    "start_portfolj": 4,        # startprojekt per kvarter, ett per typ
    "start_mark": 12,           # rutor mark som startportföljen högst får ta (av 16; bostäder staplas)
    "drag": 3,                  # drag på PU-brädet per kvarter
    "egna_upphandlingar": 3,    # poster i Skede 2 som man upphandlar själv
    "spelade_faser": 2,         # byggfaser som spelas (en ur 1–4, en ur 5–8)
    "kvartal": 1,               # kvartal i Förvaltningen
}

# beslut som automaten tar även för människor i kortversionen
AUTOMAT = {"placering", "placera_markexpansion", "komplettera", "rb_sank_krav"}


def fro_av(*listor):
    """Ett frö ur redan blandade (och loggade) högar: samma parti ger samma frö vid uppspelning."""
    from .slump import kortnamn
    text = "|".join(kortnamn(k) if isinstance(k, dict) else str(k) for lista in listor for k in lista)
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:12], 16)


def rattvis_startportfolj(motor, antal, mark, ryms):
    """Välj en startportfölj per kvarter så att de blir så lika som möjligt.

    motor: PUMotor (högarna är blandade). ryms(projekt) -> bool: får portföljen plats i pusslet.
    Returnerar en lista med portföljer, en per kvarter i spelordning."""
    from .pu import BOSTAD, tal
    r = random.Random(fro_av(*(motor.hogar[t] for t in sorted(motor.hogar))))
    typer = [t for t in sorted(motor.hogar) if motor.hogar[t]]
    nycklar = ("Anskaffning (Mkr)", "Utvecklingskostnad (Mkr)", "BTA (kvm)", "Kvalitetskrav Q",
               "Hållbarhetskrav H", "Passera nämnden (>)")

    def celler(p):
        return int(tal(p["Antal rutor"]))

    def markbehov(projekt):
        bostad = sum(celler(p) for p in projekt if p["Typ"] in BOSTAD)
        ovrigt = sum(celler(p) for p in projekt if p["Typ"] not in BOSTAD)
        return max(bostad, ovrigt)

    kandidater = []
    for _ in range(3000):
        valda = r.sample(typer, min(antal, len(typer)))
        kand = [r.choice(motor.hogar[t]) for t in valda]
        if markbehov(kand) <= mark:
            kandidater.append(kand)
    if not kandidater:
        return [[] for _ in motor.ordning]
    vek = [[sum(tal(p[k]) for p in kand) for k in nycklar] for kand in kandidater]
    median = [sorted(v[i] for v in vek)[len(vek) // 2] for i in range(len(nycklar))]
    skala = [max(1.0, max(v[i] for v in vek) - min(v[i] for v in vek)) for i in range(len(nycklar))]
    ordning = sorted(range(len(kandidater)),
                     key=lambda i: sum(((a - b) / c) ** 2 for a, b, c in zip(vek[i], median, skala)))
    anvanda, ut = set(), []
    for _ in motor.ordning:
        val = []
        for i in ordning:
            if any(id(p) in anvanda for p in kandidater[i]):
                continue
            if ryms(kandidater[i]):
                val = kandidater[i]
                break
        for p in val:
            anvanda.add(id(p))
        ut.append(val)
    return ut


def automatiska_nivaer(kategorier, fro):
    """Samma slumpade nivå (2 eller 3) per post för alla kvarter."""
    r = random.Random(fro)
    return {k: r.choice((2, 3)) for k in kategorier}


def spelade_faser(antal, fro):
    """Vilka byggfaser som spelas: jämnt fördelade över 1–8 (två: en ur 1–4 och en ur 5–8)."""
    r = random.Random(fro)
    delar = [list(range(1 + i * 8 // antal, 1 + (i + 1) * 8 // antal)) for i in range(antal)]
    return sorted(r.choice(d) for d in delar)
