"""Spelläget som en bild för gränssnittet: vilket skede, och siffrorna för varje kvarter.

Läses medan motorn väntar på ett svar (då står den still). Allt är JSON: tal, text och listor.
"""
from .fragor import TYPNAMN, _tal


def _pu(m):
    from .pu import BRADE
    return {"skede": "PU", "namn": "Skede 1 · Projektutveckling", "handelser": list(getattr(m, "logg", []))[-40:],
            "kvarter": [{
                "namn": kv.namn,
                "ruta": BRADE[kv.position], "position": kv.position, "varv": kv.varv,
                "q_krav": kv.q_krav, "h_krav": kv.h_krav, "tid": kv.tid,
                "riskbuffert": kv.riskbuffert, "erfarenhet": kv.erfarenhet,
                "pc": (kv.pc or {}).get("Namn"),
                "projekt": [{"namn": p["Namn"], "typ": p["Typ"]} for p in kv.projekt],
                "markexpansioner": len(kv.expansioner), "mark": len(kv.mark),
            } for kv in m.kvarter],
            "projektbank": [p["Namn"] for p in getattr(m, "bank", [])]}


def _s2(m):
    ut = []
    for b in m.bolag:
        rad = {"namn": b.namn, "q": b.q, "q_krav": b.q_krav, "h": b.h, "h_krav": b.h_krav, "t": b.t,
               "riskbuffert": b.riskbuffert, "erfarenhet": b.erfarenhet, "abt": b.abt, "kostnad": round(b.kostnad, 1),
               "hand": len(b.hand), "ac": (b.ac or {}).get("Namn")}
        try:
            rad["kvar"] = round(b.kvar, 1)
        except Exception:                                  # noqa: BLE001
            pass
        ut.append(rad)
    return {"skede": "S2", "namn": "Skede 2 · Planering och genomförande", "handelser": [], "kvarter": ut}


def _f(m):
    spel = m.spel

    def fastighet(f):
        try:
            mv = m.mv(f)
        except Exception:                                  # noqa: BLE001
            mv = None
        return {"namn": f.namn, "typ": TYPNAMN.get(f.typ, f.typ), "dn": m.eff_dn(f), "mv": mv, "lan": f.lan,
                "ek": f.ek, "varningar": len(f.varningar)}
    return {"skede": "F", "namn": "Förvaltning", "kvartal": spel.kvartal,
            "yield": {k: _tal(v) for k, v in spel.yieldniva.items()},
            "handelser": list(spel.logg)[-40:],
            "kvarter": [{
                "namn": sp.namn, "kassa": round(sp.kassa, 1), "riskbuffert": sp.riskbuffert,
                "hand": len(sp.hand), "fc": (sp.fc or {}).get("Namn") if isinstance(sp.fc, dict) else None,
                "fs": (sp.fs or {}).get("Namn") if isinstance(sp.fs, dict) else None,
                "fastigheter": [fastighet(f) for f in sp.fastigheter],
            } for sp in spel.spelare],
            "projektbank": [f.namn for f in spel.projektbank]}


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
        if hasattr(m, "spel") and m.spel.kvartal:
            return _f(m)
        return {"skede": "start", "namn": "Förbereder", "handelser": [], "kvarter": []}
    except Exception as e:                                 # noqa: BLE001 — en bild får aldrig stoppa spelet
        return {"skede": "okänt", "namn": f"Läget kunde inte läsas ({e})", "handelser": [], "kvarter": []}
