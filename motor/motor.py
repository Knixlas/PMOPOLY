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
    projektutveckling: bool = True                 # spela Skede 1 först (annars slumpad portfölj)
    handkort_nar_som_helst: bool = False           # människors handkort spelas vid varje station (Parti sätter)
    start_krav: int = 4                            # 3.1: Q- och H-kravet från Detaljplanen = svårighetsgraden
    roj_med_pengar: bool = False                   # regeländring (Niklas): varningar röjs bara med kort, inte köps bort
    startkassa: float = None                       # None = TB + sålda BRF (beslut); tal = fast kassa (test)
    start_projekt: tuple = (4, 6)                  # ANTAGANDE: antal projekt från genomförandet (inkl. BRF)
    tg: tuple = (0.0, 0.20, 0.08)                  # ANTAGANDE: täckningsgrad (min, max, typvärde) — 20 % = tokbra
    kassa_vikt: float = 0.5                        # F-poäng: kassa räknas till denna andel, fastigheter fullt
    f_delare: float = 30                           # F-poäng = (eget kapital + vikt × kassa) ÷ delare (30 sedan MV-höjningen)
    start_riskbuffert: tuple = (0, 2)              # riskbuffertar som följer med från Skede 2
    plus_visning: str = "direkt"                   # "direkt" (tvingande) eller "val" — testas
    fokustyp: tuple = ("HYRESRÄTT", "LOKAL", "KONTOR", "FÖRSKOLA")   # som tryckt på F-brädet (Kvartal 1–4)
    pafyllning: tuple = (3, 2, 1, 0)               # nya projekt i projektbanken per kvartal
    max_uppgraderingar: tuple = (3, 2, 1, 0)
    uppgradering_kostnad: int = 3                  # 9.11 (beslut 2026-09-27): per slag(omgång)
    # 9.11: slaget måste vara över tröskeln för fastighetens nuvarande energiklass – svårare ju bättre klassen är
    uppgradering_troskel: dict = field(default_factory=lambda: {"E": 6, "D": 8, "C": 10, "B": 13})
    ta_bort_handelse: dict = field(default_factory=dict)  # kalibrering: {typ: {effekt: antal}} tas ur typleken
    ta_bort_kvartal: dict = field(default_factory=dict)
    yield_spann: dict = None                               # kalibrering: ersätter YIELD_SPANN
    bostadsveteran_duell: bool = False                     # beslut: Bostadsveteranen har ingen duellbonus
    skold_typer: tuple = ("LOKAL", "KONTOR", "FÖRSKOLA")   # FC Skölden (junior) skyddar dessa typer (beslut 2026-09-27)
    skold_per_kvartal: int = 1                             # så många gånger per kvartal
    extra_handelse: dict = field(default_factory=lambda: {t: {"direkt_dn_minus": 2} for t in ("LOKAL", "KONTOR")})
                                                   # kalibrering: {typ: {effekt: antal}} läggs till i typleken
    tvang: float = 0.7                             # bankens nedskrivning vid fynd
    fientlig: float = 1.2                          # tvångsbud
    tvang_avgift: float = 2                        # budavgift för tvångsbud (Mkr till banken, oavsett utfall)
    handgrans: int = 6
    stor_hand: dict = field(default_factory=lambda: {"Nätverkaren": 8})   # FC med större handgräns (beslut 2026-09-27)
    lan_andel: float = 0.7                         # fast i grundspelet (beslut)
    ranta_sats: float = 0.02                       # fast ränta i grundspelet (beslut 2026-09-27: 2 %, "A-läge")


class Motor:
    def __init__(self, strategier, parametrar=None, slump=None, data=None, pu_strategier=None, s2_strategier=None,
                 namn=None):
        """strategier: en per kvarter i Förvaltningen. pu_/s2_strategier: samma kvarter i Skede 1 och 2
        (utelämnas de väljs bottar på måfå, som i simuleringen). namn: kvarterens namn."""
        self.pu_strategier, self.s2_strategier = pu_strategier, s2_strategier
        self.p = parametrar or Parametrar()
        self.s = slump or DigitalSlump()
        self.d = data or Kortdata()
        self.spel = Spel(spelare=[Spelare(namn=namn[i] if namn else f"Spelare {i + 1}", strategi=st)
                                  for i, st in enumerate(strategier)])
        self.stat = {k: 0 for k in ("bv_varning", "bank_tar", "sanering_tagen", "sanering_raddad", "sanering_forlorad", "fynd_salt",
                                    "kop", "tvangsbud", "tvangsbud_stoppat", "salj", "konkurs", "uppgradering",
                                    "uppgradering_forsok", "eliminerat", "senior", "tvangskop", "budstrid",
                                    "overtagande", "affarskort", "stopp_motbud", "stopp_kort", "stopp_rb",
                                    "duell_forlorad", "motbud_kop")}
        self.stat["dn_drift"] = {t: 0 for t in TYPER}
        self.spel.statistik = self.stat

    # ------------------------------------------------------------------ hjälpare
    def d_fc_typer(self, fc):
        return FC_TYPER.get(fc["Typ"], set())

    def logg(self, text):
        self.spel.logg.append(f"Q{self.spel.kvartal}: {text}" if self.spel.kvartal else f"Uppstart: {text}")

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
        f.ranta = max(1, int(self.p.ranta_sats * lan + 0.5)) if lan else 0

    def kopelan(self, f):
        """9.5 (beslut 2026-09-27): köparen tar ett nytt lån på 70 % av marknadsvärdet; resten, och vid
        tvångsbud hela övervärdet, betalas ur kassan."""
        mv = self.mv(f)
        return min(avrunda(self.p.lan_andel * mv, 5), mv)

    def kontant(self, f, pris=None):
        """Det köparen betalar ur kassan för f till priset pris (standard: marknadsvärdet)."""
        return (self.mv(f) if pris is None else pris) - self.kopelan(f)

    def overta(self, sp, f):
        """Köparen tar över f med ett nytt lån (säljaren har redan löst sitt)."""
        self.satt_lan(f, self.kopelan(f))
        sp.fastigheter.append(f)
        f.kopt_kvartal = self.spel.kvartal

    @staticmethod
    def utan(lek, bort):
        """Kalibrering: ta bort ett antal kort av givna effekter ur en lek."""
        bort = dict(bort)
        ut = []
        for k in lek:
            if bort.get(k["Effekt"], 0) > 0:
                bort[k["Effekt"]] -= 1
            else:
                ut.append(k)
        return ut

    def projektutveckling(self):
        """Spela Skede 1 med samma slump; ett resultat per spelare (i spelarordning)."""
        from .pu import PUData, PUMotor, PUParametrar
        from .pu_strategi import PU_STRATEGIER
        from .skede2 import S2Data, Skede2
        from .skede2_strategi import S2_STRATEGIER
        if not hasattr(self.d, "pu"):
            self.d.pu, self.d.s2 = PUData(), S2Data()     # läses en gång per Kortdata
        strategier = self.pu_strategier or [self.s.bott.choice(list(PU_STRATEGIER.values()))() for _ in self.spel.spelare]
        pu = PUMotor(strategier, PUParametrar(start_q=self.p.start_krav, start_h=self.p.start_krav), self.s, self.d.pu, [sp.namn for sp in self.spel.spelare]).spela()
        strategier = self.s2_strategier or [self.s.bott.choice(list(S2_STRATEGIER.values()))() for _ in self.spel.spelare]
        s2 = Skede2(pu, strategier, slump=self.s, data=self.d.s2).spela()
        for r, r2 in zip(pu, s2):
            r.update({"s2_strategi": r2["strategi"], "tb": r2["tb"], "TG": r2["TG"], "lan": r2["lan"],
                      "n": r2["n"], "Mu": r2["Mu"], "riskbuffert": r2["riskbuffert"]})
        return pu

    def ny_fastighet(self, projekt):
        """Fastigheten som den står på projektkortet: driftnetto efter ränta, ränta, lån, energiklass."""
        ek = projekt["Energiklass"] or "C"
        noi = int(tal(projekt["Driftnetto (Mkr/år)"]) + tal(projekt["Räntekostnad (Mkr/år)"]))
        return Fastighet(namn=projekt["Namn"], typ=projekt["Typ"], bas_dn=noi - EK_MOD[ek], ek=ek,
                         lan=int(tal(projekt["Lån (Mkr)"])), ranta=int(tal(projekt["Räntekostnad (Mkr/år)"])))

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
        f.varningar.append(kostnad)
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
            # beslut 2026-09-27: villkoret prövas när kortet dras och ger en direkt, permanent ändring (inget att
            # komma ihåg): energiklass D/E, "3 eller fler" av typen, eller en underhållsvarning på fastigheten
            t = (kort.get("Beskrivning") or "").lower()
            if "3 eller fler" in t:
                egna = [x for x in sp.fastigheter if x.typ == f.typ]
                if len(egna) >= 3:
                    for x in egna:
                        self.andra_bas(x, -1)
            elif "underhållsvarning" in t:
                if f.varningar:
                    self.andra_bas(f, -1)
            elif "d eller sämre" in t:
                if f.ek in ("D", "E"):
                    self.andra_bas(f, -1)
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
            skold = (self.ar_fc(sp, "Skölden") and sp.skold_anvand < self.p.skold_per_kvartal
                     and (f.typ in self.p.skold_typer or sp.fc_senior))
            if skold and sp.strategi.eliminera(self, sp, f, kort, gratis=True):
                sp.skold_anvand += 1
                self.stat["eliminerat"] += 1
                if sp.fc_senior:
                    sp.riskbuffert += 1
                return
            # FC Bostadsveteranen (beslut 2026-09-27): en gång per kvartal (vrid kortet) blir en negativ händelse
            # på en hyresrätt en underhållsvarning i stället; som senior tar kvarteret dessutom en riskbuffert
            if (self.ar_fc(sp, "Bostadsveteranen") and f.typ == "HYRESRÄTT" and kort["Effekt"] != "underhallsvarning"
                    and sp.bv_anvand < 1 and sp.strategi.till_varning(self, sp, f, kort)):
                sp.bv_anvand += 1
                if sp.fc_senior:
                    sp.riskbuffert += 1
                self.stat["bv_varning"] += 1
                self.logg(f"{sp.namn}: Bostadsveteranen gör händelsen på {f.namn} till en underhållsvarning")
                self.varning(f, sp, 0)
                return
            if sp.riskbuffert >= 1 and sp.strategi.eliminera(self, sp, f, kort, gratis=False):
                sp.riskbuffert -= 1
                self.stat["eliminerat"] += 1
                return
        self.fastighetseffekt(kort, f, sp)

    def dra_dd(self, f, sp):
        # 9.9: ett DD-kort dras och gäller. Undantag: FS Besiktningsgeniet och nätverkskorten "dd_val"
        # låter kvarteret dra två och välja.
        val = self.ar_fs(sp, "Besiktningsgeniet")
        self.orsak_dd = "Ert förvaltningsstöd Besiktningsgeniet" if val else None
        if not val:
            kort = next((k for k in sp.hand if k["Effekt"] == "dd_val"), None)
            if kort:
                sp.hand.remove(kort)
                val = True
                self.orsak_dd = f"Nätverkskortet ”{kort.get('Rubrik', '')}”"
        if val:
            antal = 3 if self.ar_fs(sp, "Besiktningsgeniet") and sp.fs_senior else 2   # senior: tre kort
            kort = sp.strategi.valj_dd(self, sp, f, [self.s.dra("dd") for _ in range(antal)])
        else:
            kort = self.s.dra("dd")
        self.fastighetseffekt(kort, f, sp)

    def handgrans(self, sp):
        return self.p.stor_hand.get((sp.fc or {}).get("Namn"), self.p.handgrans)

    def ta_emot(self, sp, kort):
        """All väg in till handen går hit, så att handgränsen alltid gäller."""
        sp.hand.append(kort)
        while len(sp.hand) > self.handgrans(sp):
            sp.hand.remove(sp.strategi.slang(self, sp))

    def dra_natverkskort(self, sp, n=1):
        for _ in range(n):
            self.ta_emot(sp, self.s.dra("natverk"))

    # ------------------------------------------------------------------ uppställning (Kvartal 0)
    def starta(self):
        self.spel.fas = "uppstart"
        d, s = self.d, self.s
        for typ in TYPER:
            extra = [{"ID": f"X-{typ}-{e}-{i}", "Typ": typ, "Effekt": e, "Värde": None}
                     for e, n in self.p.extra_handelse.get(typ, {}).items() for i in range(n)]
            s.blanda("handelse_" + typ, self.utan([k for k in d.handelse if k["Typ"] == typ],
                                                  self.p.ta_bort_handelse.get(typ, {})) + extra)
            s.blanda("kvartal_" + typ, self.utan([k for k in d.kvartal if k["Typ"] == typ],
                                                 self.p.ta_bort_kvartal.get(typ, {})))
        s.blanda("natverk", d.natverk)
        s.blanda("omvarld", d.omvarld)
        s.blanda("dd", d.dd)
        for spar in ("bostäder", "kommersiellt"):
            s.blanda("yield_" + spar, [k for k in d.yieldkort if k["Spår"] == spar])
        pool = s.blanda_lista(d.projekt, "projektpool")
        self.projektpool = pool
        brf = s.blanda_lista(d.brf, "BRF")
        fc_kvar, fs_kvar = list(d.fc), list(d.fs)
        pu = self.projektutveckling() if self.p.projektutveckling else None
        parti = getattr(self.s, "_parti", None)
        if parti is not None:                        # Förvaltningen är nu motorn som slår (bordet, "Slå")
            parti.aktuell_motor = self
        for spar in ("bostäder", "kommersiellt"):    # 9.2: yieldbanan läggs när Förvaltningen ställs upp
            # F-brädet: tre platser per spår (Q2–Q4); yielden flyttas vid varje kvartals start
            self.spel.yieldbana[spar] = [tal(s.dra("yield_" + spar)["Ändring"]) for _ in range(3)]
        if pu:                                       # kvarterens egna projekt finns inte på marknaden
            byggda = {p["Namn"] for r in pu for p in r["placerade"]}
            pool[:] = [p for p in pool if p["Namn"] not in byggda]
        for sp in s.blanda_lista(self.spel.spelare, "spelordning"):
            sp.riskbuffert = s.heltal(*self.p.start_riskbuffert)
            if pu:                                   # Skede 1 och 2 i motorn
                r = pu[self.spel.spelare.index(sp)]
                sp.pu = r
                sp.riskbuffert = r["riskbuffert"]
                sp.lan = r["lan"]
                valda = r["placerade"]
                abt = r["abt"]
            else:                                    # utan Skede 1: slumpa en portfölj
                antal = s.heltal(*self.p.start_projekt)
                valda = []
                for _ in range(antal):
                    ar_brf = brf and s.slumptal() < len(brf) / (len(brf) + len(pool))
                    valda.append(brf.pop() if ar_brf else pool.pop())
                # ANTAGANDE: ABT-budget ≈ anskaffning − utvecklingskostnad
                abt = sum(tal(p["Anskaffning (Mkr)"]) - tal(p["Utvecklingskostnad (Mkr)"]) for p in valda)
            brf_intakt = 0.0
            self.aktiv = sp                          # BRF-tärningen hör till kvarteret (bordet på skärmen)
            for projekt in valda:
                ar_brf = projekt["Typ"] == "BRF"
                if ar_brf:   # 8.6: intäkt = marknadsvärde − anskaffning + rörlig intäkt (kortets tärning)
                    tarning = int(re.search(r"D(\d+)", projekt["Rörligt marknadsvärde"] or "D0").group(1))
                    mv, ansk = tal(projekt["Marknadsvärde (Mkr)"]), tal(projekt["Anskaffning (Mkr)"])
                    self.kastsyfte = f"{projekt['Namn']} säljs – rörligt marknadsvärde"
                    slag = s.tarning(tarning) if tarning else 0
                    brf_intakt += mv - ansk + slag
                    sp.brf_salda.append({"namn": projekt["Namn"], "mv": mv, "anskaffning": ansk,
                                         "tarning": tarning, "slag": slag, "intakt": mv - ansk + slag})
                    self.logg(f"{sp.namn} säljer {projekt['Namn']}: marknadsvärde {mv:g} − anskaffning {ansk:g}"
                              + (f" + D{tarning} {slag}" if tarning else "") + f" = {mv - ansk + slag:g} Mkr")
                else:
                    sp.fastigheter.append(self.ny_fastighet(projekt))
            if pu:                                   # 8.5: TB (och moderbolagslånens 95 Mkr) följer med
                sp.tb = r["tb"]
                start = sp.tb + sp.lan * 95 + brf_intakt
            else:
                sp.tb = max(0.0, s.triangel(self.p.tg[0], self.p.tg[1], self.p.tg[2]) * abt)
                start = sp.tb + brf_intakt
            sp.brf_intakt = brf_intakt
            sp.kassa = self.p.startkassa if self.p.startkassa is not None else round(start)
        for sp in sorted(self.spel.spelare, key=lambda x: x.kassa):     # 9.2: minst kassa väljer först
            sp.fc = sp.strategi.valj_fc(self, sp, fc_kvar)
            fc_kvar.remove(sp.fc)
            sp.fs = sp.strategi.valj_fs(self, sp, fs_kvar)
            fs_kvar.remove(sp.fs)
        for sp in self.spel.spelare:
            while sp.lan and len(sp.fastigheter) > 1:        # 7.2: moderbolagslån → sälj ned till en fastighet
                self.salj_till_bank(sp, min(sp.fastigheter, key=lambda f: self.mv(f) - f.lan))
            self.dra_natverkskort(sp, 3)                 # 9.2: först tre nätverkskort, sedan händelsekorten
            for f in sp.fastigheter:
                self.dra_handelse(f, sp)
            sp.start_ek = sum(self.mv(f) - f.lan for f in sp.fastigheter)
            sp.start_kassa = sp.kassa

    # ------------------------------------------------------------------ 1. marknad
    def marknad(self):
        q = self.spel.kvartal
        if q >= 2:
            for spar, bana in self.spel.yieldbana.items():
                lo, hi = (self.p.yield_spann or YIELD_SPANN)[spar]
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
            for f, i in (sp.strategi.roj(self, sp) if self.p.roj_med_pengar else []):
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
            for sp in self.s.blanda_lista(self.spel.spelare, "spelordning"):
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

    def kast(self, sp, syfte, grupp=None):
        """Nästa tärningsslag är sp:s (helt digitalt trycker spelaren själv på Slå, se Parti._kasta_sjalv)."""
        self.aktiv, self.kastsyfte, self.slaggrupp = sp, syfte, grupp

    def forhandlingsslag(self, sp, f):
        self.kast(sp, f"förhandling om {f.namn}")
        slag = self.s.d20()
        if sp.fc:
            namn = sp.fc["Namn"]
            if namn == "Förhandlaren":
                slag += (5 if sp.fc_senior else 3) if f.typ == "KONTOR" else 1
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
                pris = self.kontant(f)
                intresse = [sp for sp in self.spel.spelare          # 7.2: köpstopp med moderbolagslån
                            if not sp.lan and sp.kassa >= pris and sp.strategi.vill_kopa(self, sp, f, pris)]
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
                self.overta(vinnare, f)
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
        return satt

    def duell_fc(self, sp, f, anfall):
        """FC:s justering i tvångsbudsduellen. Senior ger +1 extra på en justering som finns."""
        if not sp.fc:
            return 0
        namn, mod = sp.fc["Namn"], 0
        if namn == "Förhandlaren" and anfall:
            mod = 3 if f.typ == "KONTOR" else 2
        elif namn in ("Den lugna", "Skölden") and not anfall:
            mod = 2
        elif namn == "Bostadsveteranen" and not anfall and f.typ == "HYRESRÄTT" and self.p.bostadsveteran_duell:
            mod = 2
        elif namn == "Nätverkaren":
            mod = 1
        return mod + (1 if mod and sp.fc_senior else 0)

    def duell_chans(self, budgivare, offer, f):
        """Sannolikheten att budgivaren vinner duellen (d20 mot d20, lika = ägaren), med FC och
        ungefär +2 per förhandlingskort på hand."""
        kort = lambda sp: 2 * sum(1 for k in sp.hand if k["Effekt"] == "forhandling_mod")
        diff = (self.duell_fc(budgivare, f, True) + kort(budgivare)) - (self.duell_fc(offer, f, False) + kort(offer))
        return sum(1 for a in range(1, 21) for b in range(1, 21) if a + diff > b) / 400

    def duell(self, budgivare, offer, f):
        """Tvångsbudsduell. Returnerar True om budgivaren vinner."""
        self.kast(budgivare, f"tvångsbud på {f.namn} – budgivarens slag")
        a = self.s.d20() + self.duell_fc(budgivare, f, True)
        self.kast(offer, f"tvångsbud på {f.namn} – ert försvar (budgivaren fick {a})")
        b = self.s.d20() + self.duell_fc(offer, f, False)
        # den som ligger under får slå om med en riskbuffert (en gång)
        self.omslag_info = (f"Tvångsbudet på {f.namn}: ni fick {a}, försvaret {b}. Ni behöver slå högre än försvaret."
                            if a <= b else f"Tvångsbudet på {f.namn}: budgivaren fick {a}, ni {b}. Får ni minst {a} "
                            f"(lika vinner ägaren) behåller ni fastigheten.")
        if a <= b and budgivare.riskbuffert and budgivare.strategi.sla_om(self, budgivare):
            budgivare.riskbuffert -= 1
            self.kast(budgivare, f"tvångsbud på {f.namn} – omslag (−1 riskbuffert)")
            a = self.s.d20() + self.duell_fc(budgivare, f, True)
        elif a > b and offer.riskbuffert and offer.strategi.sla_om(self, offer):
            offer.riskbuffert -= 1
            self.kast(offer, f"tvångsbud på {f.namn} – omslag av försvaret (−1 riskbuffert)")
            b = self.s.d20() + self.duell_fc(offer, f, False)
        # förhandlingskort: först budgivaren om den ligger under, sedan ägaren
        for sp, eget, mot, maste_over in ((budgivare, "a", "b", True), (offer, "b", "a", False)):
            varden = {"a": a, "b": b}
            behov = varden[mot] - varden[eget] + (1 if maste_over else 0)
            if behov > 0:
                for kort in sp.strategi.duellkort(self, sp, behov):
                    sp.hand.remove(kort)
                    varden[eget] += tal(kort["Värde"])
            a, b = varden["a"], varden["b"]
        return a > b

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
            if budgivare.lan:                                  # 7.2: köpstopp gäller även tvångsbud
                continue
            val = budgivare.strategi.tvangsbud(self, budgivare)
            if not val:
                continue
            offer, f = val
            faktor = self.tvangsfaktor(budgivare)
            pris = self.mv(f, faktor)
            if budgivare.kassa < self.kontant(f, pris) + self.p.tvang_avgift:
                continue
            self.stat["tvangsbud"] += 1
            budgivare.kassa -= self.p.tvang_avgift          # budavgift till banken, oavsett utfall
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
                elif val_ == "motbud":
                    offer.hand.remove(self.har_kort(offer, "motbud"))
                    mal = offer.strategi.motbudsmal(self, offer, budgivare)
                    if mal:                              # köp en av budgivarens fastigheter till MV
                        offer.kassa -= self.kontant(mal)
                        budgivare.kassa += self.mv(mal) - mal.lan
                        budgivare.fastigheter.remove(mal)
                        self.visa_plus(mal)
                        self.overta(offer, mal)
                        self.dra_dd(mal, offer)
                        self.stat["motbud_kop"] += 1
                continue
            if not overtag and not self.duell(budgivare, offer, f):
                self.stat["duell_forlorad"] += 1
                continue
            ersattning = self.mv(f, max(faktor, 1.3) if (self.ar_fs(offer, "Mäklaren") and offer.fs_senior) else faktor)
            offer.kassa += ersattning - f.lan
            budgivare.kassa -= self.kontant(f, pris)            # övervärdet betalas helt ur kassan
            offer.fastigheter.remove(f)
            self.visa_plus(f)
            self.overta(budgivare, f)
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
        q = self.spel.kvartal                       # påverkar plats q+1 = index q-1 (Q2..Q4)
        spar = ["bostäder", "kommersiellt"] if pav in ("båda", "alla") else [pav]
        if e.startswith("yield") and q >= 4:        # ingen plats efter Q4: slutvärderingen sker på Q4-yielden
            return
        if e == "yield_ersatt":
            for sp_ in spar:
                self.spel.yieldbana[sp_][q - 1] = v
        elif e == "yield_byt":
            for sp_ in spar:
                self.spel.yieldbana[sp_][q - 1] = tal(self.s.dra("yield_" + sp_)["Ändring"])
        elif e == "yield_byt_alla":
            for sp_ in spar:
                for i in range(q - 1, 3):
                    self.spel.yieldbana[sp_][i] = tal(self.s.dra("yield_" + sp_)["Ändring"])
        elif e == "bords_dn":
            n = 1 if "+1" in (kort.get("Beskrivning") or "") else -1
            valjare = self.s.valj(self.spel.spelare)
            self.orsak_kort = kort                    # frågan visar omvärldskortet
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
                    self.dra_natverkskort(sp)
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
        elif e == "slang_natverkskort":
            for sp in self.spel.spelare:
                if sp.hand:
                    sp.hand.remove(sp.strategi.slang(self, sp))
        elif e == "natverkskort_per_typ":
            for sp in self.spel.spelare:
                self.dra_natverkskort(sp, sum(1 for f in sp.fastigheter if f.typ == pav))
        elif e == "natverkskort_minst":
            ek = {sp.namn: sum(self.mv(f) - f.lan for f in sp.fastigheter) for sp in self.spel.spelare}
            for sp in self.spel.spelare:
                if ek[sp.namn] == min(ek.values()):
                    self.dra_natverkskort(sp, int(v))
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
            if sp.fastigheter:
                self.logg(f"{sp.namn} får {hela} Mkr i driftnetto ({ar:g} Mkr/år från {len(sp.fastigheter)} fastigheter)")
            sp.restkort += round((kvartal - hela) * 4)
            while sp.restkort >= 4:
                sp.restkort -= 4
                sp.kassa += 1

    # ------------------------------------------------------------------ 4. personal
    def personal(self):
        q = self.spel.kvartal
        for sp in self.spel.spelare:
            self.aktiv = sp
            sp.skold_anvand = sp.bv_anvand = 0
            if self.ar_fc(sp, "Den lugna"):
                sp.riskbuffert += 1
            self.dra_natverkskort(sp, 3 if self.ar_fc(sp, "Nätverkaren") else 2)
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

    def handkort_nu(self):
        """Kort som en spelare tryckt på i handen spelas när nästa station börjar (loggas som ett beslut)."""
        if not self.p.handkort_nar_som_helst:
            return
        for sp in self.spel.spelare:
            if sp.hand and getattr(sp.strategi, "_manniska", False):
                kort = sp.strategi.handkort(self, sp)
                if kort:
                    self.spela_hand(sp, kort)

    def spela_hand(self, sp, valda=None):
        for kort in (sp.strategi.spela_nu(self, sp) if valda is None else valda):
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
                    if len(f.varningar) < 3:
                        f.uppgraderingsstopp = False
            elif e == "dra_natverkskort":
                self.dra_natverkskort(sp)
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
            elif e == "headhunting":                      # ensam i partiet: ingen att värva från
                offer = max((o for o in self.spel.spelare if o is not sp), key=lambda o: len(o.hand), default=None)
                if offer and offer.hand:
                    k = self.s.valj(offer.hand)
                    offer.hand.remove(k)
                    self.ta_emot(sp, k)

    # ------------------------------------------------------------------ 5–6. händelser, kvartalskort
    def handelser(self):
        for sp in self.spel.spelare:
            self.aktiv = sp
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
                self.dra_natverkskort(sp)
            elif e == "natverkskort_fokus":
                self.dra_natverkskort(sp, len(egna))
            elif e == "villkorat":
                for f in egna:
                    if f.ek in ("D", "E"):
                        self.andra_bas(f, -1)
            elif e == "kvartal_dd":
                self.dra_dd(egna[0], sp)
            elif e == "kvartal_kassa_minus":                 # äldre kort (kort ger inte längre kostnader)
                sp.vantande_kassa -= v
            elif e == "typbred_dolt_minus":                  # en dold minusbricka på varje fastighet av typen
                for f in egna:
                    self.dn_bricka(f, -1)
            elif e == "inget":
                pass

    # ------------------------------------------------------------------ 7. energiuppgradering
    def energiuppgraderingar(self):
        q = self.spel.kvartal
        if not self.p.max_uppgraderingar[q - 1]:              # Q4: inga uppgraderingar (fråga inte)
            return
        for sp in self.spel.spelare:
            # FC Tekniska experten som senior: försöken kostar 2 Mkr i stället för 3
            forsokskostnad = self.p.uppgradering_kostnad - (1 if self.ar_fc(sp, "Tekniska experten") and sp.fc_senior else 0)
            if sp.lan:                                        # 7.2: uppgraderingsstopp med moderbolagslån
                continue
            for f in sp.strategi.uppgradera(self, sp, self.p.max_uppgraderingar[q - 1]):
                if f.uppgraderingsstopp or f.ek == "A" or f not in sp.fastigheter:
                    continue
                tarningar = 1
                while True:
                    kostnad = forsokskostnad
                    if sp.kassa < kostnad:
                        break
                    self.stat["uppgradering_forsok"] += 1
                    self.kast(sp, f"energiuppgradering av {f.namn} med {tarningar} D20, över "
                                  f"{self.p.uppgradering_troskel[f.ek]} ({kostnad} Mkr)", ("energi", sp.namn, f.namn, tarningar, q))
                    slag = [self.s.d20() for _ in range(tarningar)]
                    self.slaggrupp = None
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
                    grans = self.p.uppgradering_troskel[f.ek]
                    if bast <= grans and any(k["Effekt"] == "energi_mod" for k in sp.hand):
                        for kort in sp.strategi.energikort(self, sp, grans + 1 - bast):
                            sp.hand.remove(kort)
                            bast += tal(kort["Värde"])
                    self.omslag_info = (f"Energiuppgradering av {f.namn}: bästa slaget blev {bast} med plus, det "
                                        f"behövde bli över {grans}.")
                    if bast <= grans and sp.riskbuffert and sp.strategi.sla_om(self, sp):
                        sp.riskbuffert -= 1
                        self.kast(sp, f"omslag för {f.namn} (−1 riskbuffert)", ("energi omslag", sp.namn, f.namn, tarningar, q))
                        bast = max(self.s.d20() for _ in range(tarningar)) + mod
                        self.slaggrupp = None
                    if bast > grans:
                        self.andra_ek(f, 1)
                        self.stat["uppgradering"] += 1
                        break
                    if not sp.strategi.fortsatt_uppgradera(self, sp, f, tarningar + 1):
                        break
                    tarningar += 1

    # ------------------------------------------------------------------ hela spelet
    def kvartalet(self):
        # stationerna på Förvaltningsbrädets spiral (Ekonomi = driftnetto + nätverkskort)
        for fas, steg in (("marknad", self.marknad), ("omvarld", self.omvarld), ("ekonomi", self.driftnetto),
                          ("ekonomi", self.personal), ("fastigheter", self.handelser),
                          ("omgivning", self.kvartalskort), ("energi", self.energiuppgraderingar)):
            self.spel.fas = fas                        # för gränssnittet (motor/lage.py)
            self.aktiv = None
            self.handkort_nu()
            steg()

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
        """F-poäng = (eget kapital + halva kassan) ÷ 20, räknat vid slut. ~20 = tokbra.
        Beslut: prova den enklaste varianten först (inget startvärde att komma ihåg)."""
        kassa = sp.kassa + sp.vantande_kassa + sp.restkort * 0.25
        return (self.varde(sp, kassa) - 100 * sp.lan) / self.p.f_delare   # 10.1: −100 Mkr per moderbolagslån

    def slutrakning(self):
        resultat = []                               # värdering på Q4-yielden
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
                **({"PU": sp.pu["PU"], "TG": sp.pu["TG"], "Mu": sp.pu["Mu"], "lan": sp.lan,
                    "total": (sp.pu["PU"] + sp.pu["TG"] + self.f_poang(sp)) * sp.pu["Mu"],
                    "pu_strategi": sp.pu["strategi"], "s2_strategi": sp.pu["s2_strategi"]} if sp.pu else {}),
            })
        return resultat
