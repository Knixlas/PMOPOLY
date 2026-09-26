"""Bottar — strategier som fattar alla beslut åt en spelare.

`Strategi` är grundboten: rimliga, enkla beslut. Varianterna ändrar bara några rattar,
så att balansen kan mätas mot olika spelstilar (F3 i OMSTART.md).
"""
from .data import tal
from .modell import SPAR

POSITIVA_HANDKORT = {"lagg_dn_plus_egen", "lagg_energi_plus_egen", "direkt_dn_plus_egen", "stada",
                     "dra_personkort", "riskbuffert", "utveckling", "headhunting", "hyresgastvarvning"}


class Strategi:
    namn = "balanserad"
    kopbuffert = 5          # Mkr kvar i kassan efter köp
    min_avkastning = 0.0    # kräv att köp ger (eff DN/4) / pris över detta
    sanera = 0.5            # benägenhet att ta saneringsuppdrag (0–1)
    tvangsbud_ar = False
    uppgradera_kassa = 8    # uppgradera bara om kassan är minst så här
    rb_eliminera = True
    fc_preferens = None

    # --- uppställning
    def valj_fc(self, m, sp, lista):
        if self.fc_preferens:
            for fc in lista:
                if fc["Namn"] == self.fc_preferens:
                    return fc
        typer = [f.typ for f in sp.fastigheter]
        return max(lista, key=lambda fc: sum(t in m.d_fc_typer(fc) for t in typer) + m.s.rng.random())

    def valj_fs(self, m, sp, lista):
        return m.s.valj(lista)

    # --- marknad
    def vill_kopa(self, m, sp, f, pris):
        if sp.kassa - pris < self.kopbuffert:
            return False
        kvartalsintakt = m.eff_dn(f, sp) / 4
        return pris <= 0 or kvartalsintakt / max(pris, 1) >= self.min_avkastning

    def forhandlingskort(self, m, sp, f):
        auto = [k for k in sp.hand if k["Effekt"] == "forhandling_auto"]
        if auto and m.eff_dn(f) >= 3:
            return auto[:1]
        mod = sorted((k for k in sp.hand if k["Effekt"] == "forhandling_mod"), key=lambda k: -tal(k["Värde"]))
        return mod[:1]

    def vill_sanera(self, m, sp, f, skuld):
        return skuld > 0 and m.s.rng.random() < self.sanera and sp.kassa >= 0

    def tvangsbud(self, m, sp):
        if not self.tvangsbud_ar:
            return None
        kandidater = [(o, f) for o in m.spel.spelare if o is not sp for f in o.fastigheter
                      if sp.kassa - (m.mv(f, m.p.fientlig) - f.lan) >= self.kopbuffert and f.ek in ("A", "B")]
        return max(kandidater, key=lambda of: m.eff_dn(of[1]), default=None)

    def stoppa(self, m, sp, f):
        return True

    def salj(self, m, sp):
        return []

    def salj_for_likviditet(self, m, sp):
        return max(sp.fastigheter, key=lambda f: m.mv(f) - f.lan)

    def roj(self, m, sp):
        ut = []
        kassa = sp.kassa
        for f in sp.fastigheter:
            if len(f.varningar) >= 2 and kassa - min(f.varningar) >= self.kopbuffert:
                i = f.varningar.index(min(f.varningar))
                ut.append((f, i))
                kassa -= f.varningar[i]
        return ut

    def visa_plus(self, m, sp, f):
        return True

    # --- kort och händelser
    def eliminera(self, m, sp, f, kort, gratis):
        if gratis:
            return True
        return self.rb_eliminera and kort["Effekt"] in ("direkt_dn_minus", "underhallsvarning", "engangskassa_minus") \
            and sp.riskbuffert >= 2

    def valj_dd(self, m, sp, f, kort):
        ordning = ["direkt_dn_plus", "direkt_ek_plus", "engangskassa_plus", "dolt_plus_dn", "energi_plus"]
        return min(kort, key=lambda k: ordning.index(k["Effekt"]) if k["Effekt"] in ordning else 99)

    def slang(self, m, sp):
        varde = {"stopp": 9, "forhandling_auto": 8, "direkt_dn_plus_egen": 8, "forkop": 6}
        return min(sp.hand, key=lambda k: varde.get(k["Effekt"], 3) + tal(k.get("Värde")))

    def spela_nu(self, m, sp):
        return [k for k in list(sp.hand) if k["Effekt"] in POSITIVA_HANDKORT]

    def valj_plusfastighet(self, m, sp):
        # närmast undervatten först, annars högst eff DN
        return min(sp.fastigheter, key=lambda f: (m.mv(f) - f.lan, -m.eff_dn(f)))

    def valj_energifastighet(self, m, sp):
        kand = [f for f in sp.fastigheter if f.ek != "A"]
        return max(kand, key=lambda f: "ABCDE".index(f.ek), default=None)

    def varvningsmal(self, m, sp):
        for o in m.spel.spelare:
            if o is sp:
                continue
            for f in o.fastigheter:
                egen = next((x for x in sp.fastigheter if x.typ == f.typ), None)
                if egen:
                    return egen, f
        return None

    def valj_typ(self, m, sp, n):
        from collections import Counter
        egna = Counter(f.typ for f in sp.fastigheter)
        alla = Counter(f.typ for o in m.spel.spelare for f in o.fastigheter)
        typer = list(alla) or ["KONTOR"]
        if n > 0:
            return max(typer, key=lambda t: egna[t] - (alla[t] - egna[t]) * 0.5)
        return max(typer, key=lambda t: (alla[t] - egna[t]) - egna[t])

    # --- uppgradering
    def uppgradera(self, m, sp, antal):
        if sp.kassa < self.uppgradera_kassa:
            return []
        kand = sorted((f for f in sp.fastigheter if f.ek != "A" and not f.uppgraderingsstopp),
                      key=lambda f: (m.mv(f) - f.lan, -"ABCDE".index(f.ek)))
        return kand[:antal]

    def energikort(self, m, sp, behov):
        kort = sorted((k for k in sp.hand if k["Effekt"] == "energi_mod"), key=lambda k: tal(k["Värde"]))
        for k in kort:
            if tal(k["Värde"]) >= behov:
                return [k]
        return []

    def sla_om(self, m, sp):
        return True

    def fortsatt_uppgradera(self, m, sp, f, tarningar):
        return sp.kassa >= self.uppgradera_kassa and tarningar <= 3


class Forsiktig(Strategi):
    namn = "försiktig"
    kopbuffert = 20
    min_avkastning = 0.06
    sanera = 0.1


class Havstang(Strategi):
    namn = "hävstång"
    kopbuffert = 0
    sanera = 0.9
    uppgradera_kassa = 3


class Aggressiv(Strategi):
    namn = "aggressiv"
    kopbuffert = 2
    tvangsbud_ar = True
    sanera = 0.6


class Energi(Strategi):
    namn = "energi"
    uppgradera_kassa = 3
    fc_preferens = "Tekniska experten"

    def fortsatt_uppgradera(self, m, sp, f, tarningar):
        return sp.kassa >= 3


STRATEGIER = {k.namn: k for k in (Strategi, Forsiktig, Havstang, Aggressiv, Energi)}
