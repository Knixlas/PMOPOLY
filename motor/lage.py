"""Spelläget som en bild för gränssnittet: vilket skede, och siffrorna för varje kvarter.

Läses medan motorn väntar på ett svar (då står den still). Allt är JSON: tal, text och listor.
"""
from .fragor import TYPNAMN, _tal


def _pu(m):
    from .parti import kortvy
    from .pu import BRADE
    return {"skede": "PU", "namn": "Skede 1 · Projektutveckling", "handelser": list(getattr(m, "logg", []))[-40:],
            "kvarter": [{
                "namn": kv.namn,
                "ruta": BRADE[kv.position], "position": kv.position, "varv": kv.varv,
                "q_krav": kv.q_krav, "h_krav": kv.h_krav, "tid": kv.tid,
                "riskbuffert": kv.riskbuffert, "erfarenhet": kv.erfarenhet,
                "pc": (kv.pc or {}).get("Namn"),
                "projekt": [{"namn": p["Namn"], "typ": p["Typ"], "kort": kortvy(p)} for p in kv.projekt],
                "markexpansioner": len(kv.expansioner), "mark": len(kv.mark),
                **_pu_siffror(m, kv),
            } for kv in m.kvarter],
            "projektbank": [p["Namn"] for p in getattr(m, "bank", [])]}


def _pu_siffror(m, kv):
    """Nuläget för ett kvarter i Skede 1: projekten, BTA, anskaffning, marknadsvärde och ABT just nu (5.1)."""
    from .pu import tal
    p = kv.projekt
    anskaffning = sum(tal(x["Anskaffning (Mkr)"]) for x in p)
    utveckling = sum(tal(x["Utvecklingskostnad (Mkr)"]) for x in p)
    kostnad = m.p.tomtkostnad + m.p.markexpansion_kostnad * len(kv.expansioner) + utveckling
    return {"antal": len(p), "bta": sum(tal(x["BTA (kvm)"]) for x in p), "anskaffning": anskaffning,
            "marknadsvarde": sum(tal(x["Marknadsvärde (Mkr)"]) for x in p), "utveckling": utveckling,
            "abt_kostnad": kostnad, "abt": anskaffning - kostnad, "namndsumma": kv.namndsumma()}


def _s2(m):
    from .parti import kortvy
    from .skede2 import KOLUMN, NIVAER
    ut = []
    for b in m.bolag:
        rad = {"namn": b.namn, "q": b.q, "q_krav": b.q_krav, "h": b.h, "h_krav": b.h_krav, "t": b.t,
               "riskbuffert": b.riskbuffert, "erfarenhet": b.erfarenhet, "abt": b.abt, "kostnad": round(b.kostnad, 1),
               "hand": len(b.hand), "ac": (b.ac or {}).get("Namn"),
               "handkort": [kortvy(k) for k in b.hand], "kompetens": _kompetens(b.hand),
               "fas_utfall": list(b.fas_utfall)}
        if m.fas_kort:                                      # Genomförandet: fasens nivåer för kvarterets typ
            kol = KOLUMN[b.kvartertyp]
            rad["fas_krav"] = [[n, str(m.fas_kort.get(f"{n} {kol}")), str(m.fas_kort.get(f"Effekt {n.lower()}") or "")]
                               for n in NIVAER if m.fas_kort.get(f"{n} {kol}") not in (None, "")]
        try:
            rad["kvar"] = round(b.kvar, 1)
        except Exception:                                  # noqa: BLE001
            pass
        ut.append(rad)
    namn = "Skede 2.1 · Planering" if m.fas in ("uppstallning", "planering") else "Skede 2.2 · Genomförande"
    ut_ = {"skede": "S2", "namn": namn, "fas": m.fas, "steg_nr": m.steg_nr, "handelser": [], "kvarter": ut}
    if m.fas_kort:
        ut_["fas_kort"] = {**kortvy(m.fas_kort), "lek": f"FAS {m.steg_nr}"}
    return ut_


def _kompetens(hand):
    from .skede2 import kompetenser
    summa = {}
    for k in hand:
        for c, n in kompetenser(k).items():
            summa[c] = summa.get(c, 0) + n
    return summa


def _f(m):
    from .parti import kortvy
    spel = m.spel

    def fastighet(f, sp=None):
        try:
            mv = m.mv(f)
        except Exception:                                  # noqa: BLE001
            mv = None
        try:
            dn = m.eff_dn(f, sp) if sp is not None else m.eff_dn(f)
        except TypeError:
            dn = m.eff_dn(f)
        return {"namn": f.namn, "typ": TYPNAMN.get(f.typ, f.typ), "typkod": f.typ, "dn": dn, "mv": mv, "lan": f.lan,
                "ek": f.ek, "varningar": len(f.varningar), "varningskostnad": list(f.varningar),
                "villkor": [v for v in f.villkor if v],
                # dolda brickor: bara ägaren ser nettot (klienten visar dem för det egna kvarteret)
                "dn_brickor": f.dn_brickor, "ek_brickor": f.ek_brickor, "plus_att_visa": f.plus_att_visa}
    return {"skede": "F", "namn": "Förvaltning", "kvartal": spel.kvartal, "fas": getattr(spel, "fas", None),
            "yield": {k: _tal(v) for k, v in spel.yieldniva.items()},
            "handelser": list(spel.logg)[-40:],
            "kvarter": [{
                "namn": sp.namn, "kassa": round(sp.kassa, 1), "riskbuffert": sp.riskbuffert,
                "restkort": sp.restkort, "vantande_kassa": round(sp.vantande_kassa, 1),
                "hand": len(sp.hand), "handkort": [kortvy(k) for k in sp.hand if isinstance(k, dict)],
                "fc": (sp.fc or {}).get("Namn") if isinstance(sp.fc, dict) else None, "fc_senior": sp.fc_senior,
                "fs": (sp.fs or {}).get("Namn") if isinstance(sp.fs, dict) else None, "fs_senior": sp.fs_senior,
                "fastigheter": [fastighet(f, sp) for f in sp.fastigheter],
            } for sp in spel.spelare],
            "projektbank": [f.namn for f in spel.projektbank],
            "marknad": [fastighet(f) for f in spel.projektbank]}


def bild(parti):
    """Spelläget just nu (None innan motorn har startat)."""
    m = getattr(parti, "aktuell_motor", None) or parti.motor
    if m is None:
        return None
    try:
        namn = type(m).__name__
        if namn == "PUMotor":
            return _pu(m)
        if namn == "Skede2":
            return _s2(m)
        if hasattr(m, "spel") and (m.spel.kvartal or m.spel.spelare and any(sp.fastigheter for sp in m.spel.spelare)):
            b = _f(m)
            if not m.spel.kvartal:
                b["namn"] = "Förvaltning · uppstart"
            return b
        return {"skede": "start", "namn": "Förbereder", "handelser": [], "kvarter": []}
    except Exception as e:                                 # noqa: BLE001 — en bild får aldrig stoppa spelet
        return {"skede": "okänt", "namn": f"Läget kunde inte läsas ({e})", "handelser": [], "kvarter": []}
