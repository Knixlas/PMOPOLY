#!/usr/bin/env python3
"""ABT Kostnadsanalys – Husbyggspelet. Spelar ETT spel, visar varje ABT-rad."""

import sys, io, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for mod in list(sys.modules):
    if 'husbygg' in mod or 'simuler' in mod or 'spelare' in mod:
        del sys.modules[mod]
import builtins; _real_input = builtins.input; builtins.input = lambda p='': ''
from simulering import find_data_dir
from spelare_optimal import run_game

def parse(output, result):
    lines = output.split('\n')
    W = 110

    # Fas 1 info
    f1end = next((i for i,l in enumerate(lines) if 'PROJEKTPLANERING' in l), len(lines))
    f1 = '\n'.join(lines[:f1end])
    projs = re.findall(r'✓ Tog (.+?)!', f1)
    m_mk = re.search(r'Mark & tomt:\s*(\d+)', f1)
    m_dv = re.search(r'Utvecklingskostnader:\s*(\d+)', f1)
    m_ek = re.search(r'Eget kapital \(EK\):\s*([\d.]+)', f1)
    m_ab = re.search(r'ABT-budget:\s*([\d.]+)', f1)

    print("\n" + "═"*W)
    print("  ABT KOSTNADSANALYS")
    print("═"*W)
    print(f"\n  ── FAS 1: PROJEKTUTVECKLING ──")
    for i,p in enumerate(projs,1): print(f"    Projekt {i}: {p}")
    if m_mk: print(f"    Mark & tomt:           {m_mk.group(1):>6} Mkr")
    if m_dv: print(f"    Utvecklingskostnader:   {m_dv.group(1):>6} Mkr")
    if m_ek: print(f"    EK vid start:          {float(m_ek.group(1)):>6.1f} Mkr")
    if m_ab: print(f"    ABT-budget:            {float(m_ab.group(1)):>6.1f} Mkr")

    abt_start = result.get('abt_t', 0)
    events = []
    phase = "FAS1"; step = ""; last_ev = ""; last_faskort = ""; abt_context = "HÄND"
    plk_seen = False  # Avoid double-counting planeringskostnad

    for i, line in enumerate(lines):
        s = line.strip()

        # Phase detection - exact headers from game
        if 'PROJEKTPLANERING' in s and 'FAS 2' not in s:
            phase = "PLAN"; continue
        if 'FAS 3: PROJEKTGENOMFÖRANDE' in s:
            phase = "EXEC"; continue
        if 'FASTIGHETSFÖRVALTNING' in s:
            phase = "FÖRV"; continue
        # Also catch prognos as marker that planning is done
        if 'PROGNOS INFÖR GENOMFÖRANDE' in s:
            phase = "PROGNOS"; continue

        # Step detection (planning: "STEG X/13: Name")
        ms = re.match(r'STEG\s+(\d+)/\d+:\s*(.+)', s)
        if ms: step = f"Steg {ms.group(1)}: {ms.group(2).strip()}"

        # Execution fas detection: "FAS X/8 – Företagskultur kostar Y Mkr"
        mf = re.match(r'FAS\s+(\d+)/8\s*[–-]\s*(.*)', s)
        if mf:
            step = f"Fas {mf.group(1)}/8"
            if phase != "EXEC": phase = "EXEC"  # Safety

        # Only collect events in PLAN or EXEC
        if phase not in ("PLAN", "EXEC"):
            continue

        # ── Leverantör/org vald ──
        mv = re.match(r'✓ Valde\s+(.+?)(?:\s+\(nivå\s+(\d+)\)|\s+nivå\s+(\d+))', s)
        if mv:
            name = mv.group(1).strip(); niva = mv.group(2) or mv.group(3)
            cl = lines[i+1].strip() if i+1<len(lines) else ""
            mk = re.search(r'Kostnad:\s*(\d+)', cl)
            qht_parts = re.findall(r'([QHT]):\s*([+-]\d+)', cl)
            cost = int(mk.group(1)) if mk else 0
            qht = ' '.join(f"{k}:{v}" for k,v in qht_parts)
            abt_k = None
            for j in range(i+1, min(i+4, len(lines))):
                ma = re.search(r'ABT kvar:\s*([-\d.]+)', lines[j])
                if ma: abt_k = float(ma.group(1)); break
            typ = "ORG" if "(Organisation)" in step or "(Organisa" in step else "LEV"
            events.append((phase, step, typ, f"{name} (niv {niva})", -cost, abt_k, qht))
            continue

        # ── Händelsekort namn ──
        mh = re.match(r'📋 HÄNDELSE(?:KORT)?:\s*(.+)', s)
        if mh: last_ev = mh.group(1).strip(); abt_context = "HÄND"; continue

        # ── Faskort draget ──
        mfc = re.match(r'📋 FASKORT:\s*(.+)', s)
        if mfc: last_faskort = mfc.group(1).strip(); continue

        # ── Faskort utfall med nivå ──
        mu = re.match(r'Utfall\s*\[(\w+)\]', s)
        if mu:
            chosen_level = mu.group(1)
            # Emit a FASK event with faskort name + level
            fask_label = f"{last_faskort} [{chosen_level}]" if last_faskort else f"[{chosen_level}]"
            last_ev = fask_label
            abt_context = "UTFALL"
            continue

        # ── Q/H/T-ändringar (kommer EFTER ABT-raden → bifoga till senaste event) ──
        mq = re.match(r'Q\s*([+-]\d+)\s*\(nu:\s*(\d+)\)', s)
        if mq:
            if events and events[-1][6]:
                events[-1] = (*events[-1][:6], events[-1][6] + f" Q:{mq.group(1)}")
            elif events:
                events[-1] = (*events[-1][:6], f"Q:{mq.group(1)}")
            continue
        mhh = re.match(r'H\s*([+-]\d+)\s*\(nu:\s*(\d+)\)', s)
        if mhh:
            if events and events[-1][6]:
                events[-1] = (*events[-1][:6], events[-1][6] + f" H:{mhh.group(1)}")
            elif events:
                events[-1] = (*events[-1][:6], f"H:{mhh.group(1)}")
            continue
        mt = re.match(r'Tid\s*([+-]\d+)\s*mån\s*\(nu:\s*(\d+)', s)
        if mt:
            if events and events[-1][6]:
                events[-1] = (*events[-1][:6], events[-1][6] + f" T:{mt.group(1)}")
            elif events:
                events[-1] = (*events[-1][:6], f"T:{mt.group(1)}")
            continue

        # ── Konsekvenskort / straff ──
        mk = re.match(r'🔴\s*(?:STRAFF|GARANTI):\s*(.+)', s)
        if mk:
            last_ev = mk.group(1).strip()
            abt_context = "KONS"; continue
        if 'STRAFF' in s.upper() and '🔴' not in s:
            abt_context = "KONS"; continue

        # ── Skedesavslut → allt är konsekvenskort ──
        if 'SKEDESAVSLUT' in s:
            abt_context = "KONS"; continue

        # ── ABT-effekt ──
        mae = re.match(r'ABT\s*([+-]\d+)\s*Mkr\s*\(ABT:\s*([-\d.]+)\s*Mkr\)', s)
        if mae:
            typ = abt_context if phase == "EXEC" else "HÄND"
            events.append((phase, step, typ, last_ev or "ABT-ändring", int(mae.group(1)), float(mae.group(2)), ""))
            continue

        # ── Företagskultur prisannonsering (EJ en kostnad – bara pris/kort) ──
        mfk = re.search(r'Företagskultur kostar\s*(\d+)\s*Mkr', s)
        if mfk:
            abt_context = "HÄND"  # Reset context for next phase
            continue

        # ── Externt stöd ──
        mex = re.match(r'Köpte:\s*(.+?)\s*\(-(\d+)\s*Mkr\)', s)
        if mex:
            events.append((phase, step, "STÖD", mex.group(1).strip()[:36], -int(mex.group(2)), None, ""))
            continue

        # ── Moderbolagstillskott ──
        ml = re.search(r'Moderbolagstillskott:\s*(\d+)×(\d+)', s)
        if ml:
            n = int(ml.group(1))
            events.append((phase, step, "LÅN⚠", f"{n} lån à {ml.group(2)} Mkr (avg {n*5} Mkr)", -(n*5), None, ""))
            continue

        # ── Planeringskostnad (only count once) ──
        mp = re.search(r'Planeringskostnad:\s*([\d.]+)\s*Mkr', s)
        if mp and not plk_seen:
            plk_seen = True
            abt_k = None
            for j in range(i, min(i+3, len(lines))):
                ma = re.search(r'ABT kvar:\s*([-\d.]+)', lines[j])
                if ma: abt_k = float(ma.group(1)); break
            events.append((phase, "Summering", "PLK", "Planeringskostnad (lev+org totalt)", -float(mp.group(1)), abt_k, "ingår ej separat"))

    # ── PRINT ──
    def show(title, pk):
        evts = [e for e in events if e[0]==pk]
        if not evts: return
        print(f"\n  ── {title} ──")
        print(f"  {'#':>3}  {'Typ':<5}  {'Steg/Fas':<22}  {'Namn':<38}  {'Mkr':>7}  {'ABT':>8}  {'QHT/Not'}")
        print(f"  {'─'*3}  {'─'*5}  {'─'*22}  {'─'*38}  {'─'*7}  {'─'*8}  {'─'*20}")
        t_lo = t_ev = t_fk = t_st = t_ln = t_ut = t_kn = 0
        for nr, (_,steg,typ,namn,mkr,abt,qht) in enumerate(evts,1):
            a = f"{abt:.0f}" if abt is not None else ""
            m = f"{mkr:+.0f}" if mkr!=0 else "0"
            if typ == "PLK": continue  # Don't show separately - it's a subtotal
            print(f"  {nr:>3}  {typ:<5}  {steg[:22]:<22}  {namn[:38]:<38}  {m:>7}  {a:>8}  {qht}")
            if typ in ("LEV","ORG"): t_lo += mkr
            elif typ == "HÄND": t_ev += mkr
            elif typ == "UTFALL": t_ut += mkr
            elif typ == "KONS": t_kn += mkr
            elif typ == "STÖD": t_st += mkr
            elif typ == "LÅN⚠": t_ln += mkr
        tot = t_lo + t_ev + t_ut + t_kn + t_st + t_ln
        print(f"  {'─'*3}  {'─'*5}  {'─'*22}  {'─'*38}  {'─'*7}")
        print(f"       {'':5}  {'Leverantörer + Org':<22}  {'':38}  {t_lo:>+7.0f}")
        print(f"       {'':5}  {'Händelsekort':<22}  {'':38}  {t_ev:>+7.0f}")
        if t_ut: print(f"       {'':5}  {'Faskort-utfall':<22}  {'':38}  {t_ut:>+7.0f}")
        if t_kn: print(f"       {'':5}  {'Konsekvenskort':<22}  {'':38}  {t_kn:>+7.0f}")
        if t_st: print(f"       {'':5}  {'Externt stöd':<22}  {'':38}  {t_st:>+7.0f}")
        if t_ln: print(f"       {'':5}  {'Moderbolagslån (avg)':<22}  {'':38}  {t_ln:>+7.0f}")
        print(f"       {'':5}  {'═ TOTALT':<22}  {'':38}  {tot:>+7.0f}")

    show("FAS 2: PLANERING", "PLAN")
    show("FAS 3: GENOMFÖRANDE", "EXEC")

    # Slutresultat
    abt_t=result.get('abt_t',0); abt_k=result.get('abt_k',0)
    tb=result.get('tb',0); tg=result.get('tg',0)
    ek=result.get('ek',0); ek_raw=result.get('ek_raw',0)
    loans=result.get('loans_gross',0)

    print(f"\n  ── SLUTRESULTAT ──")
    print(f"  {'ABT-T (budget)':<30}  {abt_t:>8.1f} Mkr")
    print(f"  {'ABT-K (faktisk)':<30}  {abt_k:>8.1f} Mkr")
    print(f"  {'TB':<30}  {tb:>+8.1f} Mkr")
    print(f"  {'TG':<30}  {tg:>+8.1f} %")
    print(f"  {'EK kassa':<30}  {ek_raw:>+8.1f} Mkr")
    if loans > 0:
        print(f"  {'Lån brutto':<30}  {loans:>8.1f} Mkr")
    print(f"  {'EK verkligt':<30}  {ek:>+8.1f} Mkr")
    print(f"  {'Score (FV30+EK+TB)':<30}  {result.get('score',0):>8.1f} Mkr")
    print(f"  {'Fastigheter':<30}  {result.get('n_fast',0):>8}  ({result.get('bta',0)} kvm)")

    # ── QHT-sammanställning ──
    pq = result.get('plan_q', 0); ph = result.get('plan_h', 0); pt = result.get('plan_t', 0)
    qk = result.get('plan_qk', 0); hk = result.get('plan_hk', 0)
    eq = result.get('exec_q', 0); eh = result.get('exec_h', 0)
    et = result.get('exec_t', pt)  # fallback to plan_t if no exec snapshot

    print(f"\n  ── Q / H / T ──")
    print(f"  {'':30}  {'Krav':>8}  {'Plan':>8}  {'Slut':>8}  {'Diff':>8}")
    q_diff = eq - qk
    h_diff = eh - hk
    t_over = max(0, et - 12)
    print(f"  {'Kvalitet (Q)':<30}  {qk:>8}  {pq:>8}  {eq:>8}  {q_diff:>+8}")
    print(f"  {'Hållbarhet (H)':<30}  {hk:>8}  {ph:>8}  {eh:>8}  {h_diff:>+8}")
    print(f"  {'Tid (T) mån':<30}  {'≤12':>8}  {pt:>8}  {et:>8}  {'OK' if t_over == 0 else f'+{t_over} över':>8}")
    if q_diff < 0 or h_diff < 0 or t_over > 0:
        penalties = []
        if q_diff < 0: penalties.append(f"Q: {abs(q_diff)} konsekvenskort")
        if h_diff < 0: penalties.append(f"H: {abs(h_diff)} konsekvenskort")
        if t_over > 0: penalties.append(f"T: {t_over} konsekvenskort")
        print(f"  → Straff: {', '.join(penalties)}")
    else:
        print(f"  → Inga konsekvenskort!")

    print("═"*W)

def main():
    strat = sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('-') else "Optimal"
    data_dir = find_data_dir()
    while True:
        old = sys.stdout; sys.stdout = buf = io.StringIO()
        result = run_game(data_dir, verbose=True)
        if isinstance(result, list): result = result[0] if result else {}
        sys.stdout = old; output = buf.getvalue()
        parse(output, result)
        if '--raw' in sys.argv: print("\n\nRAW:\n" + output)
        print()
        svar = _real_input("  Kör igen? (j/n): ").strip().lower()
        if svar not in ('j', 'ja', 'y', 'yes', ''):
            break

if __name__ == '__main__':
    main()

