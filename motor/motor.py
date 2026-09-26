"""Skede 3 — Förvaltning 2.1. Reglerna enligt FORVALTNING_DESIGN_2-1.md och FORVALTNING_KORTSPEC.md.

Motorn fattar inga beslut själv: varje val går till spelarens strategi (bot eller människa).
Antaganden där designen inte är låst står som `# ANTAGANDE:` och samlas i Parametrar.
"""
import math
import re
from dataclasses import dataclass, field

from .data import Kortdata, tal
from .modell import (EK_MOD, FC_TYPER, KLASSER, SPAR, START_YIELD, TYPER, YIELD_SPANN, Fastighet, Spel, Spelare,
                     avrunda)
from .slump import DigitalSlump

NEGATIVA = {"dolt_minus_dn", "energi_minus", "direkt_dn_minus", "underhallsvarning", "engangskassa_minus",
            "villkorskort"}


@dataclass
class Parametrar:
    startkassa: float = None                       # None = TB + sålda BRF (beslut); tal = fast kassa (test)
    start_projekt: tuple = (4, 6)                  # ANTAGANDE: antal projekt från genomförandet (inkl. BRF)
    tg: tuple = (0.0, 0.20, 0.08)                  # ANTAGANDE: täckningsgrad (min, max, typvärde) — 20 % = tokbra
    kassa_vikt: float = 0.5                        # F-poäng: kassa räknas till denna andel, fastigheter fullt
    start_riskbuffert: tuple = (0, 2)              # riskbuffertar som följer med från Skede 2
    plus_visning: str = "direkt"                   # "direkt" (tvingande) eller "val" — testas
    fokustyp: tuple = ("HYRESRÄTT", "FÖRSKOLA", "LOKAL", "KONTOR")   # ANTAGANDE: fast rotation Q1–Q4
    pafyllning: tuple = (3, 2, 1, 0)               # nya projekt i projektbanken per kvartal
    max_uppgraderingar: tuple = (3, 2, 1, 0)
    uppgradering_kostnad: int = 10                 # kalibrerat (varv 2)
    uppgradering_troskel: int = 10                 # slaget måste vara över detta
    extra_handelse: dict = field(default_factory=lambda: {t: {"direkt_dn_minus": 2} for t in ("LOKAL", "KONTOR")})
                                                   # kalibrering: {typ: {effekt: antal}} läggs till i typleken
    tvang: float = 0.7                             # bankens nedskrivning vid fynd
    fientlig: float = 1.2                          # tvångsbud
    losen_andel: float = 0.1                       # lösen: ägaren behåller fastigheten mot 10 % av MV till budgivaren
    handgrans: int = 6
    lan_andel: float = 0.7                         # fast i grundspelet (beslut)
    ranta_sats: float = 0.03                       # ANTAGANDE: fast ränta i grundspelet; räntemarknad = expansion
    dn_faktor: float = 2.0                         # kalibrering: DN före ränta/år = faktor × gamla kortets DN/kvartal + tillägg
    dn_tillagg: float = 1.0


class Motor:
    def __init__(self, strategier, parametrar=None, slump=None, data=None):
        self.p = parametrar or Parametrar()
        self.s = slump or DigitalSlump()
        self.d = data or Kortdata()
        self.spel = Spel(spelare=[Spelare(namn=f"Spelare {i + 1}", strategi=st) for i, st in enumerate(strategier)])
        self.stat = {k: 0 for k in ("bank_tar", "sanering_tagen", "sanering_raddad", "sanering_forlorad", "fynd_salt",
                                    "kop", "tvangsbud", "tvangsbud_stoppat", "salj", "konkurs", "uppgradering",
                                    "uppgradering_forsok", "eliminerat", "senior", "tvangskop", "budstrid",
                                    "overtagande", "affarskort", "stopp_motbud", "stopp_kort", "stopp_rb",
                                    "stopp_losen", "motbud_kop")}
        self.stat["dn_drift"] = {t: 0 for t in TYPER}
        self.spel.statistik = self.stat

    # ------------------------------------------------------------------ hjälpare
    def d_fc_typer(self, fc):
        return FC_TYPER.get(fc["Typ"], set())

    def logg(self, text):
        self.spel.logg.append(f"Q{self.spel.kvartal}: {text}")

    def agare(self, f):
        return next((sp for sp in self.spel.spelare if f in sp.fastigheter), None)

    def villkorsavdrag(self, f, sp):
        avdrag = 0
        for text in f.villkor:
            t = text.lower()
            if "energiklass d eller sämre" in t or "d eller sämre" in t:
                avdrag -= 1 if f.ek in ("D", "E") else 0
            elif "3 eller fler" in t:
                avdrag -= 1 if sp and sum(1 for x in sp.fastigheter if x.typ == f.typ) >= 3 else 0
        return avdrag

    def eff_dn(self, f, sp=None):
        sp = sp or self.agare(f)
        return f.eff_dn(self.villkorsavdrag(f, sp))

    def eff_noi(self, f, sp=None):
        sp = sp or self.agare(f)
        return f.eff_noi(self.villkorsavdrag(f, sp))

    def mv(self, f, faktor=1.0):
        """Marknadsvärde = driftnetto före ränta ÷ yield."""
        y = self.spel.yieldniva[SPAR[f.typ]]
        return avrunda(self.eff_noi(f) / (y / 100) * faktor, 5)

    def satt_lan(self, f, lan):
        f.lan = lan
        f.ranta = int(round(self.p.ranta_sats * lan))

    def ny_fastighet(self, projekt):
        f = Fastighet(namn=projekt["Namn"], typ=projekt["Typ"], bas_dn=int(round(self.p.dn_faktor * tal(projekt["Driftnetto (Mkr/kvartal)"]) + self.p.dn_tillagg)),
                      ek=projekt["Energiklass"] or "C", lan=0)
        mv = f.eff_noi() / (START_YIELD[SPAR[f.typ]] / 100)
        self.satt_lan(f, min(avrunda(self.p.lan_andel * mv, 10), avrunda(mv, 5)))
        return f

    # ------------------------------------------------------------------ brickor, trösklar, utveckling
    def dn_bricka(self, f, n):
        f.dn_brickor += n
        self.trosklar(f)

    def ek_bricka(self, f, n):
        f.ek_brickor += n
        self.trosklar(f)

    def andra_ek(self, f, steg):
        i = min(max(KLASSER.index(f.ek) - steg, 0), len(KLASSER) - 1)
        f.ek = KLASSER[i]

    def andra_bas(self, f, n):
        f.bas_dn += n
        self.stat["dn_drift"][f.typ] += n

    def trosklar(self, f, slut=False):
        while f.dn_brickor <= -3:                 # minus visas tvingande
            f.dn_brickor += 3
            self.andra_bas(f, -1)
        while f.dn_brickor >= 3 and (self.p.plus_visning == "direkt" or slut):
            f.dn_brickor -= 3
            self.andra_bas(f, 1)
        while f.ek_brickor <= -3:
            f.ek_brickor += 3
            self.andra_ek(f, -1)
        while f.ek_brickor >= 3 and (self.p.plus_visning == "direkt" or slut):
            f.ek_brickor -= 3
            self.andra_ek(f, 1)

    def visa_plus(self, f):
        while f.dn_brickor >= 3:
            f.dn_brickor -= 3
            self.andra_bas(f, 1)
        while f.ek_brickor >= 3:
            f.ek_brickor -= 3
            self.andra_ek(f, 1)

    def varning(self, f, sp, kostnad):
        f.varningar.append(kostnad - (1 if self.ar_fc(sp, "Bostadsveteranen") and f.typ == "HYRESRÄTT" else 0))
        grans = 4 if self.ar_fc(sp, "Bostadsveteranen") and f.typ == "HYRESRÄTT" else 3
        if len(f.varningar) >= grans and not f.varningsstraff_tagit:
            self.andra_bas(f, -1)
            f.varningsstraff_tagit = True
            f.uppgraderingsstopp = True

    def utveckling(self, sp, typ=None):
        till_fc = typ is None and sp.fc_utveckling <= sp.fs_utveckling or (typ in sp.fc_typer())
        if till_fc and not sp.fc_senior:
            sp.fc_utveckling += 1
            if sp.fc_utveckling >= 2:
                sp.fc_senior = True
                self.stat["senior"] += 1
        elif not sp.fs_senior:
            sp.fs_utveckling += 1
            if sp.fs_utveckling >= 2:
                sp.fs_senior = True
                self.stat["senior"] += 1

    def ar_fc(self, sp, namn):
        return sp.fc and sp.fc["Namn"] == namn

    def ar_fs(self, sp, namn):
        return sp.fs and namn in sp.fs["Namn"]

    # ------------------------------------------------------------------ effekter
    def fastighetseffekt(self, kort, f, sp):
        """Händelse- och DD-effekter på en fastighet."""
        e, v = kort["Effekt"], tal(kort.get("Värde"))
        if e == "dolt_plus_dn":
            self.dn_bricka(f, 1)
        elif e == "dolt_minus_dn":
            self.dn_bricka(f, -1)
        elif e == "energi_plus":
            self.ek_bricka(f, 1)
        elif e == "energi_minus":
            grans_4 = self.ar_fs(sp, "Energicoachen")
            f.ek_brickor -= 1
            if not (grans_4 and f.ek_brickor == -3):
                self.trosklar(f)
        elif e == "direkt_dn_plus":
            self.andra_bas(f, 1)
        elif e == "direkt_dn_minus":
            self.andra_bas(f, -1)
        elif e == "direkt_ek_plus":
            self.andra_ek(f, 1)
        elif e == "direkt_ek_minus":
            self.andra_ek(f, -1)
        elif e == "underhallsvarning":
            self.varning(f, sp, int(v or 3))
        elif e == "villkorskort":
            f.villkor.append(kort.get("Beskrivning") or "")
        elif e == "engangskassa_plus":
            sp.vantande_kassa += v
        elif e == "engangskassa_minus":
            sp.vantande_kassa -= v
        elif e == "forkop":
            self.ta_emot(sp, dict(kort, Typ=f.typ))
        elif e == "utveckling":
            self.utveckling(sp, f.typ)
        elif e == "riskbuffert":
            sp.riskbuffert += 1

    def dra_handelse(self, f, sp):
        kort = self.s.dra("handelse_" + f.typ)
        if kort["Effekt"] in NEGATIVA:
            skold = (self.ar_fc(sp, "Skölden") and not sp.skold_anvand
                     and (f.typ == "LOKAL" or sp.fc_senior))
            if skold and sp.strategi.eliminera(self, sp, f, kort, gratis=True):
                sp.skold_anvand = True
                self.stat["eliminerat"] += 1
                if sp.fc_senior:
                    sp.riskbuffert += 1
                return
            if sp.riskbuffert >= 1 and sp.strategi.eliminera(self, sp, f, kort, gratis=False):
                sp.riskbuffert -= 1
                self.stat["eliminerat"] += 1
                return
        self.fastighetseffekt(kort, f, sp)

    def dra_dd(self, f, sp):
        val = self.ar_fs(sp, "Besiktningsgeniet")
        if not val:
            kort = next((k for k in sp.hand if k["Effekt"] == "dd_val"), None)
            if kort:
                sp.hand.remove(kort)
                val = True
        if val:
            a, b = self.s.dra("dd"), self.s.dra("dd")
            kort = sp.strategi.valj_dd(self, sp, f, [a, b])
        else:
            kort = self.s.dra("dd")
        self.fastighetseffekt(kort, f, sp)

    def ta_emot(self, sp, kort):
        """All väg in till handen går hit, så att handgränsen alltid gäller."""
        sp.hand.append(kort)
        while len(sp.hand) > self.p.handgrans:
            sp.hand.remove(sp.strategi.slang(self, sp))

    def dra_personkort(self, sp, n=1):
        for _ in range(n):
            self.ta_emot(sp, self.s.dra("person"))

    # ------------------------------------------------------------------ uppställning (Kvartal 0)
    def starta(self):
        d, s = self.d, self.s
        for typ in TYPER:
            extra = [{"ID": f"X-{typ}-{e}-{i}", "Typ": typ, "Effekt": e, "Värde": None}
                     for e, n in self.p.extra_handelse.get(typ, {}).items() for i in range(n)]
            s.blanda("handelse_" + typ, [k for k in d.handelse if k["Typ"] == typ] + extra)
            s.blanda("kvartal_" + typ, [k for k in d.kvartal if k["Typ"] == typ])
        s.blanda("person", d.person)
        s.blanda("omvarld", d.omvarld)
        s.blanda("dd", d.dd)
        for spar in ("bostäder", "kommersiellt"):
            s.blanda("yield_" + spar, [k for k in d.yieldkort if k["Spår"] == spar])
            self.spel.yieldbana[spar] = [tal(s.dra("yield_" + spar)["Ändring"]) for _ in range(4)]
        pool = s.blanda_lista(d.projekt)
        self.projektpool = pool
        brf = s.blanda_lista(d.brf)
        fc_kvar, fs_kvar = list(d.fc), list(d.fs)
        for sp in s.blanda_lista(self.spel.spelare):
            sp.riskbuffert = s.rng.randint(*self.p.start_riskbuffert)
            # Genomförandet: projekten dras ur hela leken (BRF med), BRF säljs direkt
            antal = s.rng.randint(*self.p.start_projekt)
            abt = brf_intakt = 0.0
            for _ in range(antal):
                ar_brf = brf and s.rng.random() < len(brf) / (len(brf) + len(pool))
                projekt = brf.pop() if ar_brf else pool.pop()
                # ANTAGANDE: ABT-budget ≈ anskaffning − utvecklingskostnad (tomt och expansion ej modellerade)
                abt += tal(projekt["Anskaffning (Mkr)"]) - tal(projekt["Utvecklingskostnad (Mkr)"])
                if ar_brf:
                    brf_intakt += tal(projekt["Marknadsvärde (Mkr)"])   # ANTAGANDE: BRF säljs till kortets MV
                else:
                    sp.fastigheter.append(self.ny_fastighet(projekt))
            sp.tb = max(0.0, s.rng.triangular(self.p.tg[0], self.p.tg[1], self.p.tg[2]) * abt)
            sp.brf_intakt = brf_intakt
            sp.kassa = self.p.startkassa if self.p.startkassa is not None else round(sp.tb + brf_intakt)
            sp.fc = sp.strategi.valj_fc(self, sp, fc_kvar)
            fc_kvar.remove(sp.fc)
            sp.fs = sp.strategi.valj_fs(self, sp, fs_kvar)
            fs_kvar.remove(sp.fs)
        for sp in self.spel.spelare:
            for f in sp.fastigheter:
                self.dra_handelse(f, sp)
            self.dra_personkort(sp, 3)
            sp.start_ek = sum(self.mv(f) - f.lan for f in sp.fastigheter)
            sp.start_kassa = sp.kassa
            sp.startvarde = self.varde(sp, sp.kassa)

    # ------------------------------------------------------------------ 1. marknad
    def marknad(self):
        q = self.spel.kvartal
        if q >= 2:
            for spar, bana in self.spel.yieldbana.items():
                lo, hi = YIELD_SPANN[spar]
                self.spel.yieldniva[spar] = min(max(self.spel.yieldniva[spar] + bana[q - 2], lo), hi)
        for _ in range(self.p.pafyllning[q - 1]):
            if self.projektpool:
                self.spel.projektbank.append(self.ny_fastighet(self.projektpool.pop()))

        for sp in self.spel.spelare:
            sp.kassa += sp.vantande_kassa
            sp.vantande_kassa = 0
            if self.p.plus_visning == "val":
                for f in sp.fastigheter:
                    if sp.strategi.visa_plus(self, sp, f):
                        self.visa_plus(f)
            for f, i in sp.strategi.roj(self, sp):
                if i < len(f.varningar) and sp.kassa >= f.varningar[i]:
                    sp.kassa -= f.varningar.pop(i)
                    f.uppgraderingsstopp = False

        # saneringsuppdrag från förra marknaden avräknas
        tagna = []
        for sp in self.spel.spelare:
            for f, _ in sp.sanering:
                if f not in sp.fastigheter:
                    continue
                if self.mv(f) >= f.lan:
                    self.stat["sanering_raddad"] += 1
                else:
                    sp.kassa -= f.lan - self.mv(f)
                    sp.fastigheter.remove(f)
                    tagna.append(f)
                    self.stat["sanering_forlorad"] += 1
            sp.sanering = []

        # balanskrav: MV < lån -> banken tar
        for sp in self.spel.spelare:
            for f in list(sp.fastigheter):
                if self.mv(f) < f.lan:
                    sp.fastigheter.remove(f)
                    tagna.append(f)
                    self.stat["bank_tar"] += 1
                    self.logg(f"banken tar {f.namn} från {sp.namn}")

        # bankens disposition: sanering först, annars fynd
        for f in tagna:
            skuld = f.lan - self.mv(f)
            for sp in self.s.blanda_lista(self.spel.spelare):
                if sp.strategi.vill_sanera(self, sp, f, skuld):
                    sp.kassa += skuld
                    sp.fastigheter.append(f)
                    sp.sanering.append((f, skuld))
                    self.stat["sanering_tagen"] += 1
                    break
            else:
                mv = self.mv(f)
                self.satt_lan(f, min(avrunda(self.p.lan_andel * mv, 10), mv))   # banken lånar om
                self.spel.bankfynd.append(f)

        self.kopsrundor()
        self.tvangsbud()
        for sp in self.spel.spelare:
            for f in sp.strategi.salj(self, sp):
                self.salj_till_bank(sp, f)
        self.kopsrundor()
        self.likviditet()

    def salj_till_bank(self, sp, f):
        faktor = 1.1 if self.ar_fs(sp, "Mäklaren") else 1.0
        sp.kassa += self.mv(f, faktor) - f.lan
        sp.fastigheter.remove(f)
        self.visa_plus(f)
        self.spel.bankfynd.append(f)
        self.stat["salj"] += 1

    def forhandlingsslag(self, sp, f):
        slag = self.s.d20()
        if sp.fc:
            namn = sp.fc["Namn"]
            if namn == "Förhandlaren":
                slag += 3 if f.typ == "KONTOR" else 1
            elif namn == "Tekniska experten" and not sp.fc_senior:
                slag -= 1
            elif namn == "Nätverkaren" and not sp.fc_senior and SPAR[f.typ] == "bostäder":
                slag -= 1
        for kort in sp.strategi.forhandlingskort(self, sp, f):
            sp.hand.remove(kort)
            if kort["Effekt"] == "forhandling_auto":
                return 100
            slag += tal(kort["Värde"])
        return slag

    def kopsrundor(self):
        while True:
            utbud = [(f, "projekt") for f in self.spel.projektbank] + [(f, "fynd") for f in self.spel.bankfynd]
            kopt = False
            for f, kalla in utbud:
                pris = self.mv(f) - f.lan
                intresse = [sp for sp in self.spel.spelare
                            if sp.kassa >= pris and sp.strategi.vill_kopa(self, sp, f, pris)]
                if not intresse:
                    continue
                forkop = [sp for sp in intresse if any(k["Effekt"] == "forkop" and k.get("Typ") == f.typ for k in sp.hand)]
                if forkop:
                    vinnare = forkop[0]
                    kort = next(k for k in vinnare.hand if k["Effekt"] == "forkop" and k.get("Typ") == f.typ)
                    vinnare.hand.remove(kort)
                elif len(intresse) == 1:
                    vinnare = intresse[0]
                else:
                    slag = {sp.namn: (self.forhandlingsslag(sp, f), -len(sp.fastigheter)) for sp in intresse}
                    vinnare = max(intresse, key=lambda sp: slag[sp.namn])
                vinnare.kassa -= pris
                (self.spel.projektbank if kalla == "projekt" else self.spel.bankfynd).remove(f)
                vinnare.fastigheter.append(f)
                f.kopt_kvartal = self.spel.kvartal
                self.dra_dd(f, vinnare)
                self.stat["kop"] += 1
                if kalla == "fynd":
                    self.stat["fynd_salt"] += 1
                kopt = True
                break
            if not kopt:
                return

    def stoppsatt(self, sp, f):
        """Sätt som ägaren har att stoppa ett tvångsbud, i den ordning de brukar väljas."""
        satt = []
        if self.har_kort(sp, "motbud"):
            satt.append("motbud")
        if self.har_kort(sp, "stopp"):
            satt.append("kort")
        if sp.riskbuffert >= (1 if (self.ar_fc(sp, "Den lugna") and sp.fc_senior) else 2):
            satt.append("rb")
        if sp.kassa >= self.losen(f):
            satt.append("losen")
        return satt

    def losen(self, f):
        """Lösen: ägaren behåller fastigheten mot att budgivaren får andel × MV."""
        return avrunda(self.mv(f) * self.p.losen_andel, 5) or 5

    def kan_tvangsbudas(self, f):
        return f.kopt_kvartal != self.spel.kvartal          # nyköpt är skyddad i samma marknad

    def har_kort(self, sp, effekt):
        return next((k for k in sp.hand if k["Effekt"] == effekt), None)

    def tvangsfaktor(self, sp):
        """Priset på ett tvångsbud i × MV: 1,2, lägre vid köparnas marknad eller med budstrid på hand."""
        faktor = self.spel.tvang_faktor or self.p.fientlig
        kort = self.har_kort(sp, "budstrid")
        return min(faktor, tal(kort["Värde"])) if kort else faktor

    def tvangsbud(self):
        for budgivare in self.spel.spelare:
            val = budgivare.strategi.tvangsbud(self, budgivare)
            if not val:
                continue
            offer, f = val
            faktor = self.tvangsfaktor(budgivare)
            pris = self.mv(f, faktor)
            if budgivare.kassa < pris - f.lan:
                continue
            self.stat["tvangsbud"] += 1
            if faktor < (self.spel.tvang_faktor or self.p.fientlig):
                budgivare.hand.remove(self.har_kort(budgivare, "budstrid"))
                self.stat["budstrid"] += 1
            overtag = self.har_kort(budgivare, "overtagande")
            satt = self.stoppsatt(offer, f)
            if satt and overtag:
                budgivare.hand.remove(overtag)          # budet kan inte stoppas
                self.stat["overtagande"] += 1
                satt = []
            val_ = offer.strategi.stoppa(self, offer, f, satt) if satt else None
            if val_:
                self.stat["tvangsbud_stoppat"] += 1
                self.stat["stopp_" + val_] += 1
                if val_ == "kort":
                    offer.hand.remove(self.har_kort(offer, "stopp"))
                elif val_ == "rb":
                    offer.riskbuffert -= 1 if (self.ar_fc(offer, "Den lugna") and offer.fc_senior) else 2
                elif val_ == "losen":
                    belopp = self.losen(f)
                    offer.kassa -= belopp
                    budgivare.kassa += belopp
                elif val_ == "motbud":
                    offer.hand.remove(self.har_kort(offer, "motbud"))
                    mal = offer.strategi.motbudsmal(self, offer, budgivare)
                    if mal:                              # köp en av budgivarens fastigheter till MV
                        offer.kassa -= self.mv(mal) - mal.lan
                        budgivare.kassa += self.mv(mal) - mal.lan
                        budgivare.fastigheter.remove(mal)
                        self.visa_plus(mal)
                        offer.fastigheter.append(mal)
                        mal.kopt_kvartal = self.spel.kvartal
                        self.dra_dd(mal, offer)
                        self.stat["motbud_kop"] += 1
                continue
            ersattning = self.mv(f, max(faktor, 1.3) if (self.ar_fs(offer, "Mäklaren") and offer.fs_senior) else faktor)
            offer.kassa += ersattning - f.lan
            budgivare.kassa -= pris - f.lan
            offer.fastigheter.remove(f)
            self.visa_plus(f)
            budgivare.fastigheter.append(f)
            f.kopt_kvartal = self.spel.kvartal
            self.stat["tvangskop"] += 1
            self.dra_dd(f, budgivare)
            gratis = self.har_kort(budgivare, "gratis_uppgradering")
            if gratis and f.ek != "A":                  # köpet var planerat kring kortet
                budgivare.hand.remove(gratis)
                self.andra_ek(f, 1)
        self.spel.tvang_faktor = None

    def likviditet(self):
        for sp in self.spel.spelare:
            while sp.kassa < 0 and sp.fastigheter:
                self.salj_till_bank(sp, sp.strategi.salj_for_likviditet(self, sp))
            if sp.kassa < 0:
                self.stat["konkurs"] += 1

    # ------------------------------------------------------------------ 2. omvärld
    def omvarld(self):
        kort = self.s.dra("omvarld")
        e, v, pav = kort["Effekt"], tal(kort.get("Värde")), kort.get("Påverkar") or ""
        q = self.spel.kvartal                       # påverkar plats q+1 = index q-1 (Q2..Slut)
        spar = ["bostäder", "kommersiellt"] if pav in ("båda", "alla") else [pav]
        if e == "yield_ersatt":
            for sp_ in spar:
                self.spel.yieldbana[sp_][q - 1] = v
        elif e == "yield_byt":
            for sp_ in spar:
                self.spel.yieldbana[sp_][q - 1] = tal(self.s.dra("yield_" + sp_)["Ändring"])
        elif e == "yield_byt_alla":
            for sp_ in spar:
                for i in range(q - 1, 4):
                    self.spel.yieldbana[sp_][i] = tal(self.s.dra("yield_" + sp_)["Ändring"])
        elif e == "bords_dn":
            n = 1 if "+1" in (kort.get("Beskrivning") or "") else -1
            valjare = self.s.valj(self.spel.spelare)
            typ = valjare.strategi.valj_typ(self, valjare, n)
            for sp in self.spel.spelare:
                for f in sp.fastigheter:
                    if f.typ == typ:
                        self.andra_bas(f, n)
        elif e == "resurs":
            for sp in self.spel.spelare:
                if "riskbuffert" in (kort.get("Beskrivning") or "").lower():
                    sp.riskbuffert += 1
                else:
                    self.dra_personkort(sp)
        elif e == "personalrotation":
            spl = self.spel.spelare
            tagna = [self.s.valj(spl[(i + 1) % len(spl)].hand) if spl[(i + 1) % len(spl)].hand else None
                     for i in range(len(spl))]
            for i, k in enumerate(tagna):
                if k:
                    spl[(i + 1) % len(spl)].hand.remove(k)
            for i, k in enumerate(tagna):
                if k:
                    self.ta_emot(spl[i], k)
        elif e == "energistod":
            for sp in self.spel.spelare:
                f = sp.strategi.valj_energifastighet(self, sp)
                if f:
                    self.andra_ek(f, 1)
        elif e == "slang_personkort":
            for sp in self.spel.spelare:
                if sp.hand:
                    sp.hand.remove(sp.strategi.slang(self, sp))
        elif e == "personkort_per_typ":
            for sp in self.spel.spelare:
                self.dra_personkort(sp, sum(1 for f in sp.fastigheter if f.typ == pav))
        elif e == "personkort_minst":
            ek = {sp.namn: sum(self.mv(f) - f.lan for f in sp.fastigheter) for sp in self.spel.spelare}
            for sp in self.spel.spelare:
                if ek[sp.namn] == min(ek.values()):
                    self.dra_personkort(sp, int(v))
        elif e in ("kopares_marknad", "saljares_marknad"):
            self.spel.tvang_faktor = v

    # ------------------------------------------------------------------ 3. driftnetto
    def driftnetto(self):
        for sp in self.spel.spelare:
            # dolda brickor ger inget förrän nettot når ±3 och bas-DN ändras (beslut)
            ar = sum(self.eff_dn(f, sp) for f in sp.fastigheter)
            kvartal = max(0.0, ar / 4)
            hela = math.floor(kvartal)
            sp.kassa += hela
            sp.restkort += round((kvartal - hela) * 4)
            while sp.restkort >= 4:
                sp.restkort -= 4
                sp.kassa += 1

    # ------------------------------------------------------------------ 4. personal
    def personal(self):
        q = self.spel.kvartal
        for sp in self.spel.spelare:
            sp.skold_anvand = False
            if self.ar_fc(sp, "Den lugna"):
                sp.riskbuffert += 1
            self.dra_personkort(sp, 3 if self.ar_fc(sp, "Nätverkaren") else 2)
            aktiv = sp.fs_senior or q in ((1, 3) if "Rivaren" in sp.fs["Namn"] else (2, 4))
            if self.ar_fs(sp, "Rivaren") and aktiv:
                f = min(sp.fastigheter, key=lambda x: x.dn_brickor, default=None)
                if f and f.dn_brickor < 0:
                    f.dn_brickor += 1
                elif f and f.varningar:
                    f.varningar.pop()
            if self.ar_fs(sp, "Kvalitetsoptimeraren") and aktiv and sp.fastigheter:
                self.dn_bricka(sp.strategi.valj_plusfastighet(self, sp), 1)
            self.spela_hand(sp)

    def spela_hand(self, sp):
        for kort in sp.strategi.spela_nu(self, sp):
            if kort not in sp.hand:
                continue
            sp.hand.remove(kort)
            e = kort["Effekt"]
            if e == "lagg_dn_plus_egen" and sp.fastigheter:
                self.dn_bricka(sp.strategi.valj_plusfastighet(self, sp), 1)
            elif e == "lagg_energi_plus_egen" and sp.fastigheter:
                self.ek_bricka(sp.strategi.valj_energifastighet(self, sp) or sp.fastigheter[0], 1)
            elif e == "direkt_dn_plus_egen" and sp.fastigheter:
                self.andra_bas(sp.strategi.valj_plusfastighet(self, sp), 1)
            elif e == "stada" and sp.fastigheter:
                f = min(sp.fastigheter, key=lambda x: (x.dn_brickor, -len(x.varningar)))
                if f.dn_brickor < 0:
                    f.dn_brickor += 1
                elif f.varningar:
                    f.varningar.pop()
            elif e == "dra_personkort":
                self.dra_personkort(sp)
            elif e == "riskbuffert":
                sp.riskbuffert += 1
            elif e == "utveckling":
                self.utveckling(sp)
            elif e == "hyresgastvarvning":
                mal = sp.strategi.varvningsmal(self, sp)
                if mal:
                    egen, motspelarens = mal
                    self.dn_bricka(egen, 1)
                    self.dn_bricka(motspelarens, -1)
            elif e == "gratis_uppgradering":
                f = sp.strategi.valj_energifastighet(self, sp)
                if f:
                    self.andra_ek(f, 1)
                    self.stat["affarskort"] += 1
            elif e == "omforhandlat_lan" and sp.fastigheter:
                f = max(sp.fastigheter, key=lambda x: x.ranta)
                f.ranta = max(0, f.ranta - int(tal(kort["Värde"], 1)))
                self.stat["affarskort"] += 1
            elif e == "konvertering":
                f = sp.strategi.konverteringsmal(self, sp)
                if f and sp.kassa >= tal(kort["Värde"]):
                    sp.kassa -= tal(kort["Värde"])
                    f.typ = "HYRESRÄTT"
                    self.stat["affarskort"] += 1
                else:
                    self.ta_emot(sp, kort)              # ingen nytta nu — behåll kortet
            elif e == "headhunting":
                offer = max((o for o in self.spel.spelare if o is not sp), key=lambda o: len(o.hand))
                if offer.hand:
                    k = self.s.valj(offer.hand)
                    offer.hand.remove(k)
                    self.ta_emot(sp, k)

    # ------------------------------------------------------------------ 5–6. händelser, kvartalskort
    def handelser(self):
        for sp in self.spel.spelare:
            for f in list(sp.fastigheter):
                self.dra_handelse(f, sp)

    def kvartalskort(self):
        typ = self.p.fokustyp[self.spel.kvartal - 1]
        kort = self.s.dra("kvartal_" + typ)
        e, v = kort["Effekt"], tal(kort.get("Värde"))
        for sp in self.spel.spelare:
            egna = [f for f in sp.fastigheter if f.typ == typ]
            if not egna:
                continue
            if e in ("typbred_dn_plus", "typbred_dn_minus"):
                for f in egna:
                    self.andra_bas(f, 1 if e.endswith("plus") else -1)
            elif e in ("typbred_ek_plus", "typbred_ek_minus"):
                for f in egna:
                    self.andra_ek(f, 1 if e.endswith("plus") else -1)
            elif e == "spotlight":
                for f in egna:
                    self.dra_handelse(f, sp)
            elif e == "resurs":
                self.dra_personkort(sp)
            elif e == "personkort_fokus":
                self.dra_personkort(sp, len(egna))
            elif e == "villkorat":
                for f in egna:
                    if f.ek in ("D", "E"):
                        self.andra_bas(f, -1)
            elif e == "kvartal_dd":
                self.dra_dd(egna[0], sp)
            elif e == "kvartal_kassa_minus":
                sp.vantande_kassa -= v
            elif e == "inget":
                pass

    # ------------------------------------------------------------------ 7. energiuppgradering
    def energiuppgraderingar(self):
        q = self.spel.kvartal
        for sp in self.spel.spelare:
            gratis_forsta = self.ar_fc(sp, "Tekniska experten") and sp.fc_senior
            for f in sp.strategi.uppgradera(self, sp, self.p.max_uppgraderingar[q - 1]):
                if f.uppgraderingsstopp or f.ek == "A" or f not in sp.fastigheter:
                    continue
                tarningar = 1
                while True:
                    kostnad = 0 if gratis_forsta else self.p.uppgradering_kostnad
                    gratis_forsta = False
                    if sp.kassa < kostnad:
                        break
                    self.stat["uppgradering_forsok"] += 1
                    slag = [self.s.d20() for _ in range(tarningar)]
                    if 20 in slag:
                        kostnad = 0
                    sp.kassa -= kostnad
                    mod = 0
                    if self.ar_fc(sp, "Tekniska experten"):
                        mod += 3 if f.typ == "FÖRSKOLA" else 1
                    elif self.ar_fc(sp, "Förhandlaren") and not sp.fc_senior:
                        mod -= 1
                    if self.ar_fs(sp, "Energicoachen") and sp.fs_senior:
                        mod += 1
                    bast = max(slag) + mod
                    grans = self.p.uppgradering_troskel
                    if bast <= grans:
                        for kort in sp.strategi.energikort(self, sp, grans + 1 - bast):
                            sp.hand.remove(kort)
                            bast += tal(kort["Värde"])
                    if bast <= grans and sp.riskbuffert and sp.strategi.sla_om(self, sp):
                        sp.riskbuffert -= 1
                        bast = max(self.s.d20() for _ in range(tarningar)) + mod
                    if bast > grans:
                        self.andra_ek(f, 1)
                        self.stat["uppgradering"] += 1
                        break
                    if not sp.strategi.fortsatt_uppgradera(self, sp, f, tarningar + 1):
                        break
                    tarningar += 1

    # ------------------------------------------------------------------ hela spelet
    def kvartalet(self):
        self.marknad()
        self.omvarld()
        self.driftnetto()
        self.personal()
        self.handelser()
        self.kvartalskort()
        self.energiuppgraderingar()

    def spela(self):
        self.starta()
        for q in range(1, 5):
            self.spel.kvartal = q
            self.kvartalet()
        return self.slutrakning()

    def varde(self, sp, kassa):
        """Värdet: eget kapital (MV − lån) + halva kassan. Pengar som ligger still räknas till hälften."""
        return sum(self.mv(f) - f.lan for f in sp.fastigheter) + self.p.kassa_vikt * kassa

    def f_poang(self, sp):
        """F-poäng = (värde vid slut − värde vid start) ÷ 10. ~20 = tokbra."""
        kassa = sp.kassa + sp.vantande_kassa + sp.restkort * 0.25
        return (self.varde(sp, kassa) - sp.startvarde) / 10

    def slutrakning(self):
        for spar, bana in self.spel.yieldbana.items():
            lo, hi = YIELD_SPANN[spar]
            self.spel.yieldniva[spar] = min(max(self.spel.yieldniva[spar] + bana[3], lo), hi)
        resultat = []
        for sp in self.spel.spelare:
            sp.kassa += sp.vantande_kassa
            for f in sp.fastigheter:
                self.trosklar(f, slut=True)
            eget_kapital = sum(self.mv(f) - f.lan for f in sp.fastigheter)
            resultat.append({
                "spelare": sp.namn, "strategi": sp.strategi.namn, "fc": sp.fc["Namn"], "fs": sp.fs["Namn"],
                "fc_senior": sp.fc_senior, "fs_senior": sp.fs_senior,
                "fastigheter": len(sp.fastigheter), "eget_kapital": eget_kapital,
                "kassa": sp.kassa + sp.restkort * 0.25, "S3": eget_kapital + sp.kassa + sp.restkort * 0.25,
                "start_ek": sp.start_ek, "startkassa": sp.start_kassa, "tb": sp.tb, "brf": sp.brf_intakt,
                # F-poäng: avkastning i % på viktat värde (jämför TG i Genomförandet: ~20 = tokbra)
                "F": self.f_poang(sp),
                "dn_ar": sum(self.eff_dn(f, sp) for f in sp.fastigheter),
            })
        return resultat
