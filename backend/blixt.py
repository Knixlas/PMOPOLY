"""Åkepol Blixt – mässversionen. Ett kvarter, fyra beslut och två tärningsslag på tre minuter.

Spelet körs helt i webbläsaren (frontend/js/blixt.js), så att det tål ett mässnät.
Här plockas bara de kort Blixt använder ur GameData, så att namn, priser och effekter
alltid är brädspelets egna (data/*.csv – källan vinner). Försvinner ett kort ur datan
stoppar bygget i stället för att Blixt visar något gammalt.

Reglerna runt korten (startbudget, bonus på slagen, slagens gränser och straffet per
saknat kravsteg) är Blixts egna förenklingar och står i REGLER.
"""
from config import MARK_TOMT_KOSTNAD, PHASE_COST, data_path
from data_loader import read_csv
from kvarteret import parse_effekt
import models

PROJEKT = "BRF Gläntan"
HANDELSE = "Grannprotester mot buller"
FASKORT = "Arbetsmiljöverket inspekterar"
KULTURKORT = "Skyddsfika"
GARANTIKORT = "Ventilation ej injusterad korrekt"
ANBUD = {"billig": 1, "erfaren": 3}        # leverantörsnivå för mark och stomme
ANBUD_SLOTS = ("MARK", "STOMME")

REGLER = {
    "q_start": 1, "h_start": 0,            # övriga upphandlingar, lika för alla
    "q_krav": 2, "h_krav": 2,
    "ovrigt": 4,                           # Mkr: övriga upphandlingar, schablon
    "dialog_kostnad": 1, "dialog_bonus": 5,
    "avsteg_kostnad": 4, "standard_h": 1,
    "fas_granser": [8, 15, 21],            # D20 + erfarenhet: negativt / neutralt / positivt / bonus
    "saknat_steg": 5,                      # Mkr per saknat kravsteg (konsekvenskort)
}


def _en(lista, villkor, vad: str):
    hit = next((x for x in lista if villkor(x)), None)
    if hit is None:
        raise LookupError(f"Blixt: hittar inte {vad} i speldatan. Har kortet bytt namn i källan?")
    return hit


def blixt_kort(gd) -> dict:
    """Korten som Blixt spelar med, hämtade ur GameData."""
    proj = _en([p for ps in gd.projects.values() for p in ps], lambda p: p.namn == PROJEKT, PROJEKT)
    bta_klass = models.classify(proj.bta, models.BTA_CLASSES)
    bya_klass = models.classify(proj.bta, models.BYA_CLASSES)

    handelse = _en(gd.politik + gd.dialog, lambda c: c.rubrik == HANDELSE, HANDELSE)

    slogan = {((r.get("Namn") or "").strip(), (r.get("Nivå") or "").strip()): (r.get("Ny beskrivning") or "").strip()
              for r in read_csv(data_path("leverantorer"))}
    anbud = {}
    for nyckel, niva in ANBUD.items():
        lev = [_en(gd.suppliers.get(slot, []), lambda s: s.niva == niva, f"{slot} nivå {niva}")
               for slot in ANBUD_SLOTS]
        anbud[nyckel] = {
            "namn": [s.beskrivning for s in lev],
            "niva": niva,
            "kostnad": sum(s.kostnad(bya_klass if s.beror_av == "BYA" else bta_klass) for s in lev),
            "q": sum(s.q for s in lev), "h": sum(s.h for s in lev),
            "erf": sum(s.erfarenhet for s in lev),
            "citat": slogan.get(("STOMME", str(niva)), ""),
        }

    fas = _en([c for cs in gd.phase_cards.values() for c in cs], lambda c: c.namn == FASKORT, FASKORT)
    kultur = _en(gd.external_support, lambda k: k.namn == KULTURKORT, KULTURKORT)
    garanti = _en([c for cs in gd.garanti_cards.values() for c in cs],
                  lambda c: c.namn == GARANTIKORT, GARANTIKORT)

    def eff(text):
        return {"text": text or "Ingen effekt", **parse_effekt(text or "")}

    budget = proj.anskaffning - MARK_TOMT_KOSTNAD - proj.kostnad - REGLER["ovrigt"]
    return {
        "regler": {**REGLER, "budget": budget},
        "projekt": {"namn": proj.namn, "typ": proj.typ, "bta": proj.bta, "rutor": max(1, proj.bta // 250),
                    "anskaffning": proj.anskaffning, "utveckling": proj.kostnad, "mark": MARK_TOMT_KOSTNAD},
        "handelse": {"nr": handelse.nr, "rubrik": handelse.rubrik, "text": handelse.text,
                     "effekter": {k: eff(v) for k, v in handelse.effects.items()}},
        "anbud": anbud,
        "fas": {"id": fas.id, "namn": fas.namn, "beskrivning": fas.beskrivning,
                "nivaer": [{"namn": l["name"], **eff(l["effect"])} for l in fas.levels]},
        "kultur": {"namn": kultur.namn, "bonus": kultur.kompetenser.get("ABM", 0),
                   "kostnad": PHASE_COST[fas.steg - 1]},
        "garanti": {"namn": garanti.namn, **eff(garanti.effects[0])},
    }
