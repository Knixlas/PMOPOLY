"""Spelledaren: var partiet är, vad som görs nu och vilka regler som gäller.

Används framför allt vid brädet (analogt spel), där appen leder spelet: skedets steg, var ni är i dem,
vad ni gör vid bordet just nu och vilka avsnitt i regelboken (regler/regelbok.html) som gäller.
Stegen följer regelboken och brädena; motorn märker ut var den är (`fas` på skedets motor).
"""

# (id, namn, vad man gör, regelbokens avsnitt)
PU_STEG = [
    ("uppstallning", "Uppställning",
     "Välj projektchef (PC). Sätt Q-kravet och H-kravet på {start_krav} ({svarighet}). Blanda projekthögarna, "
     "händelsekorten och markexpansionerna.", ["k3-1", "k3-8"]),
    ("bradet", "Brädet",
     "Slå D6 och flytta pjäsen medsols. Projektruta: ta projektet eller lägg det i projektbanken. "
     "Händelseruta: dra ett händelsekort och slå D20. Hörnen är institutioner. Passerar ni start får ni "
     "ta en markexpansion (5 Mkr). Brädet slutar efter två varv; rundan spelas klart.",
     ["k3-2", "k3-3", "k3-4", "k3-5", "k3-6", "k3-7"]),
    ("namnd", "Nämnden",
     "Summera nämndsiffrorna på era projekt och dra av PC:ns nämndslag. Slå D20: över summan är mixen "
     "godkänd. Vid miss höjer ni Q- eller H-kravet med 1, eller lämnar tillbaka ett projekt, och slår igen "
     "med en tärning mer.", ["k4-1"]),
    ("komplettering", "Komplettering",
     "Ni får komplettera med ett projekt för 3 × utvecklingskostnaden. Det ska också igenom nämnden.",
     ["k4-2"]),
    ("placering", "Placering",
     "Lägg kvarteret på tomten. Allt ska ligga på marken; bostäder får ligga ovanpå andra projekt. Det som "
     "inte får plats går till projektbanken. Räkna sedan ut ABT-budgeten.", ["k4-3", "k4-4", "k5-1", "k5-2"]),
]

S2_STEG = [
    ("uppstallning", "Uppställning",
     "Välj arbetschef (AC); kvarteret med lägst BTA väljer först. PC och ledningens kort (CEO, CFO, COO) "
     "blir era första kompetenskort.", ["k6-1", "k6-2"]),
    ("planering", "Planering",
     "Välj nivå för steget (leverantör eller organisation), betala kostnaden, flytta Q-, H- och T-kuberna "
     "och dra ett PL-händelsekort.", ["k6-3", "k6-4", "k6-5"]),
    ("genomforande", "Genomförande",
     "Vänd FAS-kortet. Köp kulturkort om ni vill. Spela kompetenskort från handen för att nå en nivå – "
     "når ni ingen blir det Negativt. Dra sedan ett händelsekort.",
     ["k7-2", "k7-3", "k7-4", "k7-5", "k7-6", "k7-7"]),
    ("avslut", "Skedesavslut",
     "Dra konsekvenskort för tid, kvalitet och hållbarhet som inte nåtts. Behåll korten – de blir "
     "underhållsvarningar (1/3) i Förvaltningen. Sedan garantibesiktning, "
     "ekonomisk uppgörelse och BRF-försäljning.", ["k8-1", "k8-2", "k8-3", "k8-4", "k8-5", "k8-6"]),
]

F_STEG = [
    ("uppstart", "Uppstart",
     "Kvarteren blir fastigheter och BRF:erna säljs (marknadsvärde − anskaffning + kortets tärning) till "
     "startkassan. Lägg konsekvenskorten från Genomförandet på fastigheterna – varje kort är en underhållsvarning "
     "(1/3): störst driftnetto först, en per fastighet, sedan varvet runt. Välj fastighetschef (FC) och förvaltningsstöd (FS); den med minst kassa väljer "
     "först. Varje kvarter drar tre nätverkskort och sedan ett händelsekort per fastighet.",
     ["k9-1", "k9-2", "k9-3"]),
    ("marknad", "Marknad",
     "Uppdatera yielden. Nya fastigheter kommer ut på marknaden (3, 2 och 1 i kvartal 1–3). Köp, sälj, "
     "lägg tvångsbud eller ta saneringsuppdrag.", ["k9-4", "k9-5", "k9-6"]),
    ("omvarld", "Omvärld", "Dra ett omvärldskort. Det gäller alla.", ["k9-10"]),
    ("ekonomi", "Ekonomi",
     "Ta kvartalets driftnetto till kassan (en fjärdedel av årets, resten som restkort). Dra två "
     "nätverkskort.", ["k9-7", "k9-9"]),
    ("fastigheter", "Fastigheter",
     "Dra ett händelsekort per fastighet. Ett negativt kort kan stoppas med en riskbuffert.", ["k9-8", "k9-12"]),
    ("omgivning", "Omgivning", "Dra kvartalets omgivningskort. Det påverkar fastighetstypen på kortet.",
     ["k9-10"]),
    ("energi", "Energi",
     "Energiuppgradera om ni vill: högst 3 fastigheter i kvartal 1, 2 i kvartal 2 och 1 i kvartal 3. 3 Mkr per "
     "slag; slå D20 över tröskeln för energiklassen (E 6, D 8, C 10, B 13). Miss: betala igen och slå en tärning "
     "till – det räcker att en klarar. Lyckat steg: ta gärna nästa, tärningarna börjar om på en.",
     ["k9-11"]),
]


def _lista(steg):
    return [{"id": i, "namn": n} for i, n, _, _ in steg]


def ledare(parti, fraga=None):
    """Spelledarens bild: {skede, steg, nu, plats, gor, regler}. None innan motorn startat."""
    m = getattr(parti, "aktuell_motor", None) or parti.motor
    if m is None:
        return None
    namn = type(m).__name__
    try:
        if namn == "PUMotor":
            steg, nu = PU_STEG, getattr(m, "fas", "uppstallning")
            skede = "Skede 1 · Projektutveckling"
            if nu == "bradet":
                varv = max((kv.varv for kv in m.kvarter), default=0)
                plats = f"Varv {min(varv + 1, m.p.varv)} av {m.p.varv}"
            elif getattr(m, "i_tur", None) is not None:
                plats = f"{m.i_tur.namn} avslutar"
            else:
                plats = ""
        elif namn == "Skede2":
            steg, nu = S2_STEG, getattr(m, "fas", "uppstallning")
            skede = "Skede 2.1 · Planering" if nu in ("uppstallning", "planering") else "Skede 2.2 · Genomförande"
            if nu == "planering":
                plats = f"Steg {m.steg_nr} av 13 · {str(m.steg_namn).capitalize()}"
            elif nu == "genomforande":
                fas = m.fas_kort or {}
                plats = f"Fas {m.steg_nr} av 8 · {fas.get('Namn som tryckt') or fas.get('Namn') or ''}".rstrip(" ·")
            else:
                plats = ""
        elif hasattr(m, "spel"):
            steg, nu = F_STEG, getattr(m.spel, "fas", None) or "uppstart"
            skede = "Skede 3 · Förvaltning"
            plats = f"Kvartal {m.spel.kvartal} av 4" if m.spel.kvartal else "Innan första kvartalet"
        else:
            return None
    except Exception:                                  # noqa: BLE001 — spelledaren får aldrig stoppa spelet
        return None
    rad = next((s for s in steg if s[0] == nu), steg[0])
    gor = rad[2].format(start_krav=parti.parametrar.start_krav, svarighet=f"svårighet {parti.svarighet}") \
        if hasattr(parti, "svarighet") else rad[2]
    ut = {"skede": skede, "steg": _lista(steg), "nu": rad[0], "plats": plats, "gor": gor, "regler": rad[3]}
    if fraga is not None and fraga.kvarter:
        ut["tur"] = fraga.kvarter
    return ut
