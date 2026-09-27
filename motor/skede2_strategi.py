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
                   + tal(k["Förbättrar krav: tid (T)"]) + sum(kompetenser(k).values()) / 4 + m.s.bott.random())

    def valj_niva(self, m, b, alternativ):
        mal = self.niva
        if b.q < b.q_krav - 6 or b.h < b.h_krav - 6:  # långt efter kraven: en nivå upp
            mal += 1
        mal = min(mal, int(tal(alternativ[-1]["Nivå"])))
        return next((k for k in alternativ if tal(k["Nivå"]) >= mal), alternativ[-1])

    def sla_om(self, m, b, utfall):
        return b.riskbuffert > self.spara_rb

    def sla_om_kort(self, m, b, kort, utfall, samst):
        """Slå om händelse-, konsekvens- eller garantikortet? Botten gör det bara på sämsta utfallet."""
        return samst and self.sla_om(m, b, utfall)

    def kulturkort(self, m, b, fas, pris):
        return self.kultur if b.kvar - self.kultur * pris > 20 else 0

    def spela_niva(self, m, b, niva, kort):
        return True

    def spela_fas(self, m, b, fas, nivaer):
        """Vilka kompetenskort läggs på bordet? Högsta nivån som handen når, med så få kort som möjligt."""
        for n, kr in reversed(nivaer):
            kort = m.losning(kr, b.hand) if kr else []
            if kort is not None and self.spela_niva(m, b, n, kort):
                return kort
        return []


class S2Billig(S2Strategi):
    namn = "billig"
    niva = 1
    kultur = 0


class S2Kvalitet(S2Strategi):
    namn = "kvalitet"
    niva = 3
    kultur = 2


S2_STRATEGIER = {k.namn: k for k in (S2Strategi, S2Billig, S2Kvalitet)}
