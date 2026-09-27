"""Skede 1 — Projektutveckling. Reglerna enligt regelboken kapitel 3–5 och det tryckta PU-brädet.

Motorn fattar inga beslut själv: varje val går till kvarterets strategi (bot eller människa).
Antaganden där varken kort, bräde eller regelbok säger något står som `# ANTAGANDE:` och samlas
i PUParametrar.
"""
import re
from dataclasses import dataclass, field

from .data import las_lek
from .pussel import GRUNDMARK, Bit, form_av, granska, lagen, las_marklayout, normalisera, platser_markexpansion
from .slump import DigitalSlump

BOSTAD = {"BRF", "HYRESRÄTT"}
TYPER = ["BRF", "HYRESRÄTT", "FÖRSKOLA", "LOKAL", "KONTOR"]

# Det tryckta PU-brädet, medsols från start (Stadsbyggnadskontoret, hörnet nere till höger).
BRADE = [
    "STADSBYGGNADSKONTORET", "FÖRSKOLA", "HYRESRÄTT", "HÄNDELSE", "LOKAL", "BRF",
    "STADSHUSET", "FÖRSKOLA", "KONTOR", "BRF", "RISKBUFFERT", "LOKAL",
    "LÄNSSTYRELSEN", "HYRESRÄTT", "HÄNDELSE", "KONTOR", "BRF", "LOKAL",
    "SKÖNHETSRÅDET", "FÖRSKOLA", "RISKBUFFERT", "HYRESRÄTT", "HÄNDELSE", "KONTOR",
]
HORN = {"STADSBYGGNADSKONTORET", "STADSHUSET", "LÄNSSTYRELSEN", "SKÖNHETSRÅDET"}
def markid(kort):
    return f"Markexpansion {kort['Kort-id']}"


TYPER_NAMN = {"BRF": "BRF-", "HYRESRÄTT": "Hyresrätts", "FÖRSKOLA": "Förskole", "LOKAL": "Lokal", "KONTOR": "Kontors"}
CELL_KVM = 250          # en ruta = 250 kvm (markexpansionskortens BYA / 250)
MARK_CELLER = 16        # 4 × 4


def tal(v):
    """Kortvärde som tal: '-', tomt och None är 0."""
    if v in (None, "", "-"):
        return 0
    return float(str(v).replace(",", ".").replace("−", "-"))


@dataclass
class PUParametrar:
    varv: int = 2                        # beslut: brädfasen slutar efter två varv; rundan spelas klart
    tomtkostnad: float = 10              # kalibrerat: vinnarens PU-poäng ≈ 20 (regelboken anger inget belopp)
    markexpansion_kostnad: float = 5     # regelboken 3.7
    komplettering_faktor: float = 3      # regelboken 4.2: 3 × utvecklingskostnaden
    horn_vid_passering: bool = True      # ANTAGANDE: hörnen verkar när man passerar eller stannar (regelboken 3.7)
    start_q: int = 6
    start_h: int = 6
    start_t: int = 12
    namnd_hoj_max: int = 99              # hur många gånger kraven får höjas för ett nytt nämndförsök (99 = obegränsat)
    namnd_stor_mix: int = 99             # varje projekt utöver så här många höjer nämndsumman med 1 (99 = av)
    handelse_vid_nej: bool = True        # regeländring: tar man inte ett draget projekt, eller lämnar tillbaka
                                         # ett vid Stadshuset, drar man ett händelsekort


@dataclass
class Kvarter:
    namn: str
    strategi: object
    pc: dict = None
    q_krav: int = 6
    h_krav: int = 6
    tid: int = 0                         # justering av T-utfallet (T-kravet är fast 12)
    erfarenhet: int = 0
    riskbuffert: int = 0
    namndslag: int = 0
    projekt: list = field(default_factory=list)       # tagna projekt (dict), ej nämndprövade
    vantande_rb: int = 0
    expansioner: list = field(default_factory=list)   # markexpansionskort
    mark: frozenset = GRUNDMARK                         # markens rutor på tomten (4.3)
    markbitar: dict = field(default_factory=dict)       # markexpansionens id -> rutor (flyttbara till 4.3)
    layout: dict = field(default_factory=dict)          # projektets namn -> (rutor, lager)
    position: int = 0
    varv: int = 0
    godkanda: list = field(default_factory=list)
    kompletterade: list = field(default_factory=list)  # tagna i 4.2 (3 × utvecklingskostnad)
    placerade: list = field(default_factory=list)
    oplacerade: list = field(default_factory=list)
    namndforsok: int = 0
    abt: float = 0.0
    kvartertyp: str = ""

    @property
    def kravsumma(self):
        return self.q_krav + self.h_krav

    def celler(self, p):
        return int(tal(p["Antal rutor"]))

    @property
    def markceller(self):
        return len(self.mark)

    def upptaget(self, projekt=None):
        """(celler ej bostad, celler bostad) — bostäder får ligga på mark eller ovanpå andra projekt."""
        projekt = self.projekt if projekt is None else projekt
        mark = sum(self.celler(p) for p in projekt if p["Typ"] not in BOSTAD)
        bostad = sum(self.celler(p) for p in projekt if p["Typ"] in BOSTAD)
        return mark, bostad

    def ryms(self, p, projekt=None):
        mark, bostad = self.upptaget(projekt)
        if p["Typ"] in BOSTAD:
            return bostad + self.celler(p) <= self.markceller
        return mark + self.celler(p) <= self.markceller

    def namndsumma(self, projekt=None):
        projekt = self.projekt if projekt is None else projekt
        return sum(tal(p["Passera nämnden (>)"]) for p in projekt) - self.namndslag


class PUData:
    def __init__(self):
        self.projekt = las_lek("PU_projekt.xlsx")
        self.handelse = las_lek("PU_poldia.xlsx")
        self.special = las_lek("PU_poldia_spec.xlsx")
        self.personal = las_lek("PU_personal.xlsx")
        self.markexpansion = las_lek("PU_markexpansion.xlsx")


class PUMotor:
    def __init__(self, strategier, parametrar=None, slump=None, data=None, namn=None):
        self.p = parametrar or PUParametrar()
        self.s = slump or DigitalSlump()
        self.d = data or PUData()
        self.kvarter = [Kvarter(namn=namn[i] if namn else f"Kvarter {i + 1}", strategi=st)
                        for i, st in enumerate(strategier)]
        self.bank = []                   # projektbanken (öppen, gemensam)
        self.hogar = {}                  # typ -> dragbunt
        self.logg = []
        self.stat = {k: 0 for k in ("handelse", "omslag", "markexpansion", "lamnat", "tagit_bank", "banken_in",
                                    "namnd_forsok", "namnd_hojt_krav", "namnd_lamnat", "kompletterat", "oplacerat")}

    # ------------------------------------------------------------------ hjälpare
    def logga(self, text):
        self.logg.append(text)

    def andra_krav(self, kv, q=0, h=0):
        kv.q_krav = max(0, kv.q_krav + q)
        kv.h_krav = max(0, kv.h_krav + h)

    def ta_projekt(self, kv, p):
        kv.projekt.append(p)
        self.andra_krav(kv, int(tal(p["Kvalitetskrav Q"])), int(tal(p["Hållbarhetskrav H"])))

    def lamna_projekt(self, kv, p, till_bank=True):
        # beslut: ett återlämnat projekt läggs i projektbanken
        kv.projekt.remove(p)
        self.andra_krav(kv, -int(tal(p["Kvalitetskrav Q"])), -int(tal(p["Hållbarhetskrav H"])))
        if till_bank:
            self.bank.append(p)
        self.stat["lamnat"] += 1

    def dra_hog(self, typ):
        hog = self.hogar[typ]
        return hog.pop() if hog else None

    def projektval(self, kv, typer, bara_banken=False, orsak=None):
        """Ta ett projekt av någon av typerna: översta i högen eller ur banken. Avböjt översta kort → banken.
        `orsak` visas i frågan (projektruta, Stadshuset, händelsekort …)."""
        self.orsak = orsak or (f"{TYPER_NAMN.get(typer[0], typer[0])}rutan" if len(typer) == 1 else None)
        self.projektval_typer = list(typer)
        kandidater = [p for p in self.bank if p["Typ"] in typer]
        toppar = {} if bara_banken else {t: self.hogar[t][-1] for t in typer if self.hogar[t]}
        val = kv.strategi.valj_projekt(self, kv, list(toppar.values()) + kandidater)
        if val is None:
            # 3.3: ett draget projektkort som inte tas läggs i projektbanken — inget val. Kort dras bara på en
            # projektruta (en typ); vid t.ex. Stadshuset väljer man ur högarnas toppar utan att dra.
            if len(typer) == 1 and toppar:
                self.bank.append(self.dra_hog(typer[0]))
                self.stat["banken_in"] += 1
                if self.p.handelse_vid_nej:                   # regeländring 2026-09: nej = ett händelsekort
                    self.handelse(kv)
            return None
        if val in kandidater:
            self.bank.remove(val)
            self.stat["tagit_bank"] += 1
        else:
            self.hogar[val["Typ"]].pop()
        self.ta_projekt(kv, val)
        return val

    def markexpansion(self, kv):
        if not self.markhog:
            return
        if kv.strategi.vill_expandera(self, kv):
            kort = self.markhog.pop()
            kv.expansioner.append(kort)
            self.stat["markexpansion"] += 1
            # "Placera på tomt, kasta kortet": kant i kant med marken (4.3). Svaret är en av platserna
            # för den nya biten, eller en hel ny marklayout där de lagda också får flyttas.
            alternativ = platser_markexpansion(kv.mark, form_av(kort))
            if alternativ:
                val = kv.strategi.placera_markexpansion(self, kv, kort, alternativ)
                ny = markid(kort)
                if val in alternativ:
                    self.lagg_mark(kv, {**kv.markbitar, ny: val})
                elif not self.flytta_mark(kv, val, extra=kort):
                    self.lagg_mark(kv, {**kv.markbitar, ny: alternativ[0]})

    def markformer(self, kv, extra=None):
        former = {markid(k): form_av(k) for k in kv.expansioner if markid(k) in kv.markbitar}
        if extra is not None:
            former[markid(extra)] = form_av(extra)
        return former

    def flytta_mark(self, kv, svar, extra=None):
        """Spelarens nya marklayout ([[id, rutor], ...]); följer den reglerna läggs den, annars inte."""
        if not isinstance(svar, (list, tuple)):
            return False
        bitar = las_marklayout(svar, self.markformer(kv, extra))
        if isinstance(bitar, str):
            return False
        self.lagg_mark(kv, bitar)
        return True

    @staticmethod
    def lagg_mark(kv, bitar):
        kv.markbitar = dict(bitar)
        kv.mark = GRUNDMARK.union(*bitar.values()) if bitar else GRUNDMARK

    # ------------------------------------------------------------------ uppställning
    def starta(self):
        self.fas, self.i_tur = "uppstallning", None           # för spelledaren (motor/spelledare.py)
        self.orsak = None                                      # varför kraven ändras (visas i frågan)
        self.aktiv = None
        s = self.s
        for typ in TYPER:
            self.hogar[typ] = s.blanda_lista([p for p in self.d.projekt if p["Typ"] == typ], f"projekt {typ}")
        self.handelsehog = s.blanda_lista(self.d.handelse + self.d.special, "PU-händelser")
        self.markhog = s.blanda_lista(self.d.markexpansion, "markexpansion")
        self.ordning = s.blanda_lista(self.kvarter, "spelordning")          # ANTAGANDE: slumpad (regelboken: slå D6)
        pc_kvar = list(self.d.personal)
        for kv in self.ordning:                              # beslut: PC väljs öppet i spelordning
            self.aktiv = kv                                  # vems tur (för bordet på skärmen)
            kv.q_krav, kv.h_krav = self.p.start_q, self.p.start_h
            pc = kv.strategi.valj_pc(self, kv, pc_kvar)
            pc_kvar.remove(pc)
            kv.pc = pc
            kv.erfarenhet = int(tal(pc["Erfarenhet"]))
            kv.riskbuffert = int(tal(pc["Riskbuffert"]))
            kv.namndslag = int(tal(pc["Nämndslag"]))
            # beslut: PC:s kravminskning gäller direkt
            self.andra_krav(kv, -int(tal(pc["Minskar krav: kvalitet (Q)"])), -int(tal(pc["Minskar krav: hållbarhet (H)"])))
            kv.tid -= int(tal(pc["Minskar krav: tid (T)"]))
        for kv in self.ordning:                              # brädet: "Vid start: ta markruta och valfritt projekt"
            self.aktiv = kv
            typ = kv.strategi.starttyp(self, kv)
            p = self.dra_hog(typ)
            if p:
                self.ta_projekt(kv, p)

    # ------------------------------------------------------------------ brädet
    def flytta(self, kv):
        steg = self.s.tarning(6)
        start = kv.position
        for i in range(1, steg + 1):
            pos = (start + i) % len(BRADE)
            ruta = BRADE[pos]
            kv.position = pos                                 # pjäsen står på rutan när dess effekt sker
            if pos == 0:
                kv.varv += 1
                if kv.varv >= self.p.varv:
                    kv.position = 0
                    return True                               # klar; stannar på start
            if ruta in HORN and (i == steg or self.p.horn_vid_passering):
                self.horn(kv, ruta, passerar=i != steg)
        kv.position = (start + steg) % len(BRADE)
        ruta = BRADE[kv.position]
        if ruta in TYPER:
            self.projektval(kv, [ruta])                      # orsak: projektrutan
        elif ruta == "HÄNDELSE":
            self.handelse(kv)
        elif ruta == "RISKBUFFERT":
            kv.riskbuffert += 1
        return False

    def horn(self, kv, ruta, passerar):
        if ruta == "STADSBYGGNADSKONTORET":
            self.markexpansion(kv)
        elif ruta == "STADSHUSET":                           # ta ett projekt, annars ev. lämna tillbaka ett
            if not self.projektval(kv, TYPER, orsak="Stadshuset (hörnruta)"):
                p = kv.strategi.stadshuset(self, kv)
                if p:
                    self.lamna_projekt(kv, p)
                    if self.p.handelse_vid_nej:               # regeländring 2026-09: lämna tillbaka = händelsekort
                        self.handelse(kv)
        elif ruta == "LÄNSSTYRELSEN":
            self.orsak = f"Länsstyrelsen ({'ni passerar' if passerar else 'ni stannar på'} hörnrutan)"
            q, h = kv.strategi.fordela_krav(self, kv, -2)
            self.andra_krav(kv, q, h)
        elif ruta == "SKÖNHETSRÅDET":                        # tryckt bräde: ÖKA kraven med 2
            self.orsak = f"Skönhetsrådet ({'ni passerar' if passerar else 'ni stannar på'} hörnrutan)"
            q, h = kv.strategi.fordela_krav(self, kv, +2)
            self.andra_krav(kv, q, h)

    # ------------------------------------------------------------------ händelsekort
    def handelse(self, kv):
        if not self.handelsehog:
            self.handelsehog = self.s.blanda_lista(self.d.handelse + self.d.special, "PU-händelser")   # ANTAGANDE: blandas om
        kort = self.handelsehog.pop()
        self.stat["handelse"] += 1
        if str(kort.get("Nr", "")).startswith(("PS", "DS")):
            self.orsak = f"Händelsekortet ”{kort.get('Rubrik') or kort.get('Nr')}”"
            self.specialkort(kv, kort)
            return
        slag = self.s.d20() + kv.erfarenhet
        utfall = self.utfall(kort, slag)
        if kv.riskbuffert and kv.strategi.sla_om_handelse(self, kv, kort, utfall):
            kv.riskbuffert -= 1
            self.stat["omslag"] += 1
            utfall = self.utfall(kort, self.s.d20() + kv.erfarenhet)
        self.effekt(kv, utfall)

    @staticmethod
    def utfall(kort, slag):
        for grans, kol in ((4, "Utfall D20 1-4"), (10, "Utfall D20 5-10"), (15, "Utfall D20 11-15"),
                           (19, "Utfall D20 16-19")):
            if slag <= grans:
                return kort[kol]
        return kort["Utfall D20 20+"]

    def effekt(self, kv, text):
        t = (text or "").lower()
        if not t or t.startswith("ingen"):
            return
        if m := re.fullmatch(r"([+-]\d) kvalitetskrav och ([+-]\d) hållbarhetskrav", t):
            self.andra_krav(kv, int(m.group(1)), int(m.group(2)))
        elif m := re.fullmatch(r"([+-]\d) kvalitetskrav", t):
            self.andra_krav(kv, q=int(m.group(1)))
        elif m := re.fullmatch(r"([+-]\d) hållbarhetskrav", t):
            self.andra_krav(kv, h=int(m.group(1)))
        elif m := re.fullmatch(r"([+-]\d) tid", t):
            kv.tid += int(m.group(1))                        # beslut: "tid" flyttar T-utfallet (start 12)
        elif m := re.fullmatch(r"\+(\d) riskbuffert(ar)?", t):
            kv.riskbuffert += int(m.group(1))
        elif m := re.fullmatch(r"förlora (\d) riskbuffertar", t):
            kv.riskbuffert = max(0, kv.riskbuffert - int(m.group(1)))
        elif t.startswith("lämna tillbaka projekt med"):
            if kv.projekt:
                # beslut: "intäkt" = anskaffning; vid lika väljer kvarteret (här: först i listan)
                nyckel = {"högst intäkt": lambda p: -tal(p["Anskaffning (Mkr)"]),
                          "högst bta": lambda p: -tal(p["BTA (kvm)"]),
                          "lägst anskaffning": lambda p: tal(p["Anskaffning (Mkr)"])}
                for k, f in nyckel.items():
                    if k in t:
                        self.lamna_projekt(kv, min(kv.projekt, key=f))
        elif t.startswith("byt projekt"):                  # mot översta kortet i samma typs hög
            p = kv.strategi.byt_samma_typ(self, kv)
            if p:
                hog = self.hogar[p["Typ"]]
                self.lamna_projekt(kv, p, till_bank=False)
                hog.insert(0, p)                             # längst ned i högen
                self.ta_projekt(kv, hog.pop())
        elif t.startswith("ta projekt från valfri hög"):
            self.projektval(kv, TYPER, orsak="Händelsekortet")
        elif t.startswith("dra markanvisning"):
            self.markexpansion(kv)                           # beslut: markanvisning = markexpansion (5 Mkr)
        else:
            raise ValueError(f"Okänd effekt: {text}")

    def specialkort(self, kv, kort):
        nr = kort["Nr"]
        alla = self.kvarter
        hogst = lambda f: [k for k in alla if f(k) == max(f(x) for x in alla)]
        lagst = lambda f: [k for k in alla if f(k) == min(f(x) for x in alla)]
        ks = lambda k: k.kravsumma          # ANTAGANDE: "K+Q-krav" = kravsumma Q + H
        if nr == "PS1":
            for k in alla:
                if k.projekt:
                    self.lamna_projekt(k, max(k.projekt, key=lambda p: tal(p["Anskaffning (Mkr)"])))
        elif nr == "PS2":
            self.andra_krav(kv, q=2)
            for k in hogst(lambda k: k.riskbuffert):
                self.andra_krav(k, q=1)
        elif nr == "PS3":
            for k in alla:
                self.andra_krav(k, h=2)
        elif nr == "PS4":
            for k in lagst(ks):
                if k.strategi.ta_tva_projekt(self, k):
                    self.projektval(k, TYPER, orsak=self.orsak)
                    self.projektval(k, TYPER, orsak=self.orsak)
                else:
                    q, h = k.strategi.fordela_krav(self, k, +3)
                    self.andra_krav(k, q, h)
        elif nr == "PS5":
            for k in alla:
                if ks(k) > 13 and k.projekt:
                    self.lamna_projekt(k, k.strategi.samsta_projekt(self, k))
                else:
                    k.riskbuffert = max(0, k.riskbuffert - 1)
        elif nr == "PS6":
            for k in hogst(lambda k: sum(tal(p["Anskaffning (Mkr)"]) for p in k.projekt)):
                k.riskbuffert = max(0, k.riskbuffert - 2)
                if k.projekt and k.strategi.hellre_lamna_an_krav(self, k, 4):
                    self.lamna_projekt(k, max(k.projekt, key=lambda p: tal(p["Anskaffning (Mkr)"])))
                else:
                    self.andra_krav(k, 2, 2)
        elif nr == "DS1":
            q, h = kv.strategi.fordela_krav(self, kv, -2)
            self.andra_krav(kv, q, h)
            for k in hogst(ks):
                q, h = k.strategi.fordela_krav(self, k, -1)
                self.andra_krav(k, q, h)
        elif nr == "DS2":
            for k in alla:
                k.riskbuffert += 2
        elif nr == "DS3":
            for k in [kv] + [x for x in lagst(ks) if x is not kv]:
                if k.strategi.vill_expandera(self, k):
                    self.markexpansion(k)
                else:
                    self.projektval(k, TYPER, orsak=self.orsak)
        elif nr == "DS4":
            for k in alla:
                q, h = k.strategi.fordela_krav(self, k, -1)
                self.andra_krav(k, q, h)
        elif nr == "DS5":
            for k in hogst(ks):
                q, h = k.strategi.fordela_krav(self, k, -2)  # boten väljer alltid kravsänkning
                self.andra_krav(k, q, h)
        elif nr == "DS6":
            for k in alla:
                k.riskbuffert += 1
            k = max(alla, key=lambda k: (k.h_krav, k.q_krav))
            self.andra_krav(k, h=-1)
        else:
            raise ValueError(f"Okänt specialkort {nr}")

    # ------------------------------------------------------------------ nämnd, komplettering, placering
    def namnd(self, kv, projekt):
        """4.1: summan av 'Passera nämnden' minus nämndslag ska slås över; en tärning mer per försök."""
        forsok = 0
        while projekt:
            summa = (sum(tal(p["Passera nämnden (>)"]) for p in projekt) - kv.namndslag
                     + max(0, len(projekt) - self.p.namnd_stor_mix))
            while summa > 19 and projekt:                    # måste kunna klara nämnden
                p = kv.strategi.samsta_projekt(self, kv, projekt)
                projekt.remove(p)
                self.lamna_projekt(kv, p)
                summa = (sum(tal(x["Passera nämnden (>)"]) for x in projekt) - kv.namndslag
                         + max(0, len(projekt) - self.p.namnd_stor_mix))
            forsok += 1
            self.stat["namnd_forsok"] += 1
            kv.strategi.sla_namnd(self, kv, summa, forsok)   # frågan "slå för nämnden" (ett synligt steg)
            self.slaggrupp = f"nämnd {kv.namn} {forsok}"          # tärningarna slås tillsammans (bordet)
            slag = [self.s.d20() for _ in range(forsok)]
            self.slaggrupp = None
            self.logga(f"{kv.namn}: nämnden, summa {summa:g}, slog {', '.join(map(str, slag))} – "
                       f"{'godkänt' if max(slag) > summa else 'inte godkänt'}")
            if max(slag) <= summa and kv.riskbuffert and kv.strategi.sla_om_namnd(self, kv, summa, forsok):
                kv.riskbuffert -= 1                          # beslut: omslag med riskbuffert tillåtet
                self.stat["omslag"] += 1
                slag = [self.s.d20() for _ in range(forsok)]
            if max(slag) > summa:
                return projekt, forsok
            if forsok <= self.p.namnd_hoj_max and kv.strategi.namnd_miss_hoj_krav(self, kv, summa, forsok):
                self.orsak = "Nämnden sa nej (4.1)"
                q, h = kv.strategi.fordela_krav(self, kv, +1)
                self.andra_krav(kv, q, h)
                self.stat["namnd_hojt_krav"] += 1
            else:
                p = kv.strategi.samsta_projekt(self, kv, projekt)
                projekt.remove(p)
                self.lamna_projekt(kv, p)
                self.stat["namnd_lamnat"] += 1
        return projekt, forsok

    def avsluta(self, kv):
        self.fas, self.i_tur = "namnd", kv
        self.aktiv = kv
        godkanda, kv.namndforsok = self.namnd(kv, list(kv.projekt))
        self.fas = "komplettering"
        kv.godkanda = list(godkanda)
        # 4.2 komplettering (3 × utvecklingskostnad, egen nämnd)
        nya = []
        while True:
            p = kv.strategi.komplettera(self, kv)
            if not p:
                break
            (self.bank.remove(p) if p in self.bank else self.hogar[p["Typ"]].pop())
            self.ta_projekt(kv, p)
            nya.append(p)
        if nya:
            nya, _ = self.namnd(kv, nya)
            kv.kompletterade = list(nya)
            kv.godkanda += nya
            self.stat["kompletterat"] += len(nya)
        # 4.3 placering: kvarteret lägger pusslet; det som inte ligger enligt reglerna placeras inte
        self.fas = "placering"
        svar = kv.strategi.placering(self, kv, list(kv.godkanda))
        namn = {p["Namn"]: p for p in kv.godkanda}
        if all(isinstance(x, str) for x in svar):            # vid brädet: bara vilka som fick plats
            svar = [[n, [], 1] for n in svar if n in namn]
            kv.layout = {n: (frozenset(), 1) for n, _, _ in svar}
            self.avsluta_placering(kv)
            return

        # markexpansionerna får flyttas i samma drag (lager 0 med markexpansionens id)
        mark = [[n, celler] for n, celler, lager in svar if n in kv.markbitar and int(lager) == 0]
        if mark:
            self.flytta_mark(kv, mark)
        bitar = [Bit(n, namn[n]["Typ"], frozenset(tuple(c) for c in celler), int(lager))
                 for n, celler, lager in svar if n in namn]
        for b in bitar:                                      # biten måste ha projektets egen form (i något läge)
            if normalisera(b.celler) not in lagen(form_av(namn[b.id])):
                b.lager = -1                                 # granskningen underkänner den
        fel = granska([Bit("mark", "MARK", kv.mark - GRUNDMARK, 0)] + bitar).fel
        kv.layout = {b.id: (b.celler, b.lager) for b in bitar if b.id not in fel}
        self.avsluta_placering(kv)

    def avsluta_placering(self, kv):
        kv.placerade = [p for p in kv.godkanda if p["Namn"] in kv.layout]
        kv.oplacerade = [p for p in kv.godkanda if p["Namn"] not in kv.layout]
        for p in kv.oplacerade:                              # beslut: oplacerade tar med sig kraven, går till banken
            self.andra_krav(kv, -int(tal(p["Kvalitetskrav Q"])), -int(tal(p["Hållbarhetskrav H"])))
            self.bank.append(p)
            self.stat["oplacerat"] += 1
        # riskbuffertar på godkända projekt aktiveras (3.6)
        kv.riskbuffert += sum(int(tal(p["Riskbuffert"])) for p in kv.placerade)
        # 4.4 kvartertyp
        ovriga = {p["Typ"] for p in kv.placerade} - BOSTAD
        kv.kvartertyp = "BOSTÄDER" if not ovriga else "BOSTAD+1" if len(ovriga) == 1 else "ÖVRIGA"
        # 5.1 ABT-budget
        utv = sum(tal(p["Utvecklingskostnad (Mkr)"]) for p in kv.godkanda)
        utv += (self.p.komplettering_faktor - 1) * sum(tal(p["Utvecklingskostnad (Mkr)"]) for p in kv.kompletterade)
        kv.abt = (sum(tal(p["Anskaffning (Mkr)"]) for p in kv.placerade) - self.p.tomtkostnad
                  - self.p.markexpansion_kostnad * len(kv.expansioner) - utv)
        # 5.2 riskbuffert får sänka krav
        for _ in range(kv.strategi.rb_sank_krav(self, kv)):
            kv.riskbuffert -= 1
            self.orsak = "En riskbuffert sänker kraven (5.2)"
            q, h = kv.strategi.fordela_krav(self, kv, -1)
            self.andra_krav(kv, q, h)

    # ------------------------------------------------------------------ hela skedet
    def spela(self):
        self.starta()
        klara = set()
        self.fas = "bradet"
        while not klara:                                     # beslut: när någon gått klart spelas rundan klart
            for kv in self.ordning:
                self.aktiv = kv
                if kv.namn not in klara and self.flytta(kv):
                    klara.add(kv.namn)
        for kv in self.ordning:                              # 4.2 sker i spelordning
            self.avsluta(kv)
        return [self.resultat(kv) for kv in self.kvarter]

    def resultat(self, kv):
        bta = sum(tal(p["BTA (kvm)"]) for p in kv.placerade)
        bya = sum(len(c) for c, lager in kv.layout.values() if lager == 1) * CELL_KVM   # BYA = fotavtrycket
        if kv.placerade and not any(c for c, _ in kv.layout.values()):
            # vid brädet är lagren okända: allt som ryms på marken räknas som fotavtryck
            bya = min(sum(kv.celler(p) for p in kv.placerade), kv.markceller) * CELL_KVM
        return {
            "kvarter": kv.namn, "strategi": kv.strategi.namn, "pc": kv.pc["Namn"],
            "projekt": len(kv.placerade), "oplacerade": len(kv.oplacerade),
            "anskaffning": sum(tal(p["Anskaffning (Mkr)"]) for p in kv.placerade),
            "bta": bta, "bya": bya, "abt": kv.abt, "PU": kv.abt / 20,
            "q_krav": kv.q_krav, "h_krav": kv.h_krav, "tid": kv.tid, "riskbuffert": kv.riskbuffert,
            "erfarenhet": kv.erfarenhet, "kvartertyp": kv.kvartertyp, "namndforsok": kv.namndforsok,
            "expansioner": len(kv.expansioner), "placerade": kv.placerade, "pc_kort": kv.pc,
            "mark": sorted(kv.mark), "markbitar": {i: sorted(c) for i, c in kv.markbitar.items()}, "layout": {n: (sorted(c), l) for n, (c, l) in kv.layout.items()},
        }
