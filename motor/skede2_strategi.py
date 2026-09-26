"""Bottar för Skede 2 (Planering och Genomförande)."""
from .pu import tal
from .skede2 import kompetenser


class S2Strategi:
    namn = "balanserad"
    niva = 2                 # grundnivå på leverantörer och organisation
    kultur = 1               # kulturkort per fas om kassan tillåter
    spara_rb = 1

    def valj_ac(self, m, b, lista):
        return max(lista, key=lambda k: 2 * tal(k["Erfarenhet"]) + tal(k["Riskbuffert"])
                   + tal(k["Förbättrar krav: kvalitet (Q)"]) + tal(k["Förbättrar krav: hållbarhet (H)"])
                   + tal(k["Förbättrar krav: tid (T)"]) + sum(kompetenser(k).values()) / 4 + m.s.rng.random())

    def valj_niva(self, m, b, alternativ):
        mal = self.niva
        if b.q < b.q_krav - 6 or b.h < b.h_krav - 6:  # långt efter kraven: en nivå upp
            mal += 1
        mal = min(mal, int(tal(alternativ[-1]["Nivå"])))
        return next((k for k in alternativ if tal(k["Nivå"]) >= mal), alternativ[-1])

    def sla_om(self, m, b, utfall):
        return b.riskbuffert > self.spara_rb

    def kulturkort(self, m, b, fas, pris):
        return self.kultur if b.kvar - self.kultur * pris > 20 else 0

    def spela_niva(self, m, b, niva, kort):
        return True


class S2Billig(S2Strategi):
    namn = "billig"
    niva = 1
    kultur = 0


class S2Kvalitet(S2Strategi):
    namn = "kvalitet"
    niva = 3
    kultur = 2


S2_STRATEGIER = {k.namn: k for k in (S2Strategi, S2Billig, S2Kvalitet)}
