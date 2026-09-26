"""Bottar för Skede 1 — samma idé som för Förvaltningen: några rattar, rimliga beslut."""
from .pu import BOSTAD, TYPER, tal


class PUStrategi:
    namn = "balanserad"
    max_namnd = 9           # sikta på nämndsumma högst så här (≈ 55 % på första slaget)
    max_kravsumma = 26      # tar inte projekt som driver kraven över detta
    spara_rb = 2            # riskbuffertar som sparas till Skede 2–3

    # --- värdering
    def projektvarde(self, m, kv, p):
        """Vad projektet ger till ABT-budgeten."""
        return tal(p["Anskaffning (Mkr)"]) - tal(p["Utvecklingskostnad (Mkr)"])

    def godtar(self, m, kv, p):
        if not kv.ryms(p):
            return False
        if kv.namndsumma() + tal(p["Passera nämnden (>)"]) > self.max_namnd:
            return False
        return kv.kravsumma + tal(p["Kvalitetskrav Q"]) + tal(p["Hållbarhetskrav H"]) <= self.max_kravsumma

    # --- uppställning
    def valj_pc(self, m, kv, lista):
        return max(lista, key=lambda pc: 2 * tal(pc["Nämndslag"]) + tal(pc["Riskbuffert"]) + 2 * tal(pc["Erfarenhet"])
                   + tal(pc["Minskar krav: kvalitet (Q)"]) + tal(pc["Minskar krav: hållbarhet (H)"]) + m.s.bott.random())

    def starttyp(self, m, kv):
        return max((t for t in TYPER if m.hogar[t]), key=lambda t: self.projektvarde(m, kv, m.hogar[t][-1]))

    # --- brädet
    def valj_projekt(self, m, kv, kandidater):
        ok = [p for p in kandidater if self.godtar(m, kv, p)]
        return max(ok, key=lambda p: self.projektvarde(m, kv, p), default=None)

    def dra_anda(self, m, kv, typ):
        return True          # dra kortet och lägg det i banken om det inte passar

    def vill_expandera(self, m, kv):
        mark, bostad = kv.upptaget()
        return max(mark, bostad) >= kv.markceller - 4

    def stadshuset(self, m, kv):
        """Inget projekt togs: vilket projekt lämnas tillbaka (None = inget)? Det sämsta om kraven är för höga."""
        if kv.projekt and (kv.kravsumma > self.max_kravsumma or kv.namndsumma() > self.max_namnd):
            return self.samsta_projekt(m, kv)
        return None

    def fordela_krav(self, m, kv, n):
        """Fördela n steg (minus = sänk) mellan Q och H: sänk det högsta, höj det lägsta."""
        q = h = 0
        qk, hk = kv.q_krav, kv.h_krav
        for _ in range(abs(n)):
            if n < 0:
                if qk >= hk and qk > 0:
                    q -= 1; qk -= 1
                elif hk > 0:
                    h -= 1; hk -= 1
            else:
                if qk <= hk:
                    q += 1; qk += 1
                else:
                    h += 1; hk += 1
        return q, h

    # --- händelser
    def sla_om_handelse(self, m, kv, kort, utfall):
        t = (utfall or "").lower()
        return t.startswith(("lämna tillbaka", "förlora", "+2 hållbarhet", "+2 kvalitet"))

    def byt_samma_typ(self, m, kv):
        """Vilket eget projekt byts mot översta kortet i samma typs hög (None = inget)?"""
        for p in sorted(kv.projekt, key=lambda p: self.projektvarde(m, kv, p)):
            hog = m.hogar[p["Typ"]]
            if hog and self.projektvarde(m, kv, hog[-1]) > self.projektvarde(m, kv, p):
                return p
        return None

    def placeringsordning(self, m, kv, godkanda):
        """I vilken ordning läggs projekten i pusslet (det som inte ryms blir oplacerat)?"""
        return sorted(godkanda, key=lambda p: -self.projektvarde(m, kv, p))

    def samsta_projekt(self, m, kv, projekt=None):
        projekt = kv.projekt if projekt is None else projekt
        return min(projekt, key=lambda p: self.projektvarde(m, kv, p) / max(1, tal(p["Passera nämnden (>)"])))

    def ta_tva_projekt(self, m, kv):
        return kv.kravsumma <= self.max_kravsumma - 4

    def hellre_lamna_an_krav(self, m, kv, okning):
        return kv.kravsumma + okning > self.max_kravsumma

    # --- nämnd och avslut
    def sla_om_namnd(self, m, kv, summa, forsok):
        return kv.riskbuffert > self.spara_rb or summa >= 12

    def namnd_miss_hoj_krav(self, m, kv, summa, forsok):
        return kv.kravsumma < self.max_kravsumma

    def komplettera(self, m, kv):
        if kv.kompletterade or len(kv.godkanda) != len(kv.projekt):
            return None                                      # högst ett projekt, och bara om nämnden gått rent
        kandidater = list(m.bank) + [m.hogar[t][-1] for t in TYPER if m.hogar[t]]
        ok = [p for p in kandidater if self.godtar(m, kv, p)
              and self.projektvarde(m, kv, p) - 2 * tal(p["Utvecklingskostnad (Mkr)"]) > 30]
        return max(ok, key=lambda p: self.projektvarde(m, kv, p), default=None)

    def rb_sank_krav(self, m, kv):
        return max(0, kv.riskbuffert - self.spara_rb) if kv.kravsumma > 20 else 0


class PUForsiktig(PUStrategi):
    namn = "försiktig"
    max_namnd = 6
    max_kravsumma = 22


class PUExpansiv(PUStrategi):
    namn = "expansiv"
    max_namnd = 12
    max_kravsumma = 32
    spara_rb = 1

    def vill_expandera(self, m, kv):
        return True


class PUBostad(PUStrategi):
    namn = "bostad"

    def projektvarde(self, m, kv, p):
        return super().projektvarde(m, kv, p) * (1.3 if p["Typ"] in BOSTAD else 1.0)


PU_STRATEGIER = {k.namn: k for k in (PUStrategi, PUForsiktig, PUExpansiv, PUBostad)}
