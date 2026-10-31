#!/usr/bin/env python3
"""
Husbyggspelet – Simuleringsmotor.

5 AI-strategier, upp till 1000 iterationer.
Kompakt sammanfattning → expanderad på begäran.
"""

import sys
import os
import time
import statistics
import gc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spelare_optimal import AIBrain, run_game, find_data_dir
from spelare_forsiktig import AIForsiktig
from spelare_aggressiv import AIAggressiv
from spelare_kvalitet import AIKvalitet
from spelare_kassabyggare import AIKassabyggare


# ═══════════════════════════════════════════════════════
#  AI-STRATEGIER
# ═══════════════════════════════════════════════════════

STRATEGIES = {
    "Optimal": {
        "desc": "Balanserad: nivå 3, Neutralt, köper vid >50 EK",
        "brain_class": AIBrain,
    },
    "Försiktig": {
        "desc": "Konservativ: nivå 2, aldrig köp/uppgradering",
        "brain_class": AIForsiktig,
    },
    "Aggressiv": {
        "desc": "Maxar allt: nivå 4, köper alltid, Positivt",
        "brain_class": AIAggressiv,
    },
    "Kvalitet": {
        "desc": "Få projekt, nivå 4, energiuppgraderingar",
        "brain_class": AIKvalitet,
    },
    "Kassabyggare": {
        "desc": "EK-fokus: nivå 1, Negativt, aldrig köp",
        "brain_class": AIKassabyggare,
    },
}


# ═══════════════════════════════════════════════════════
#  SIMULERING
# ═══════════════════════════════════════════════════════

def run_simulation(data_dir, strategy_name, n_iterations):
    all_results = []
    errors = 0
    brain_class = STRATEGIES[strategy_name]["brain_class"]
    brain = brain_class(data_dir=data_dir)
    t0 = time.time()

    for i in range(n_iterations):
        elapsed = time.time() - t0
        rate = (i / elapsed) if elapsed > 0 and i > 0 else 0
        eta = ((n_iterations - i) / rate) if rate > 0 else 0
        sys.stdout.write(
            f"\r  {strategy_name}: {i+1}/{n_iterations} "
            f"({(i+1)/n_iterations*100:.0f}%) "
            f"[{errors} fel, {rate:.1f} spel/s, ETA {eta:.0f}s]   "
        )
        sys.stdout.flush()

        try:
            game_t0 = time.time()
            results = run_game(data_dir, brain=brain, verbose=False)
            game_time = time.time() - game_t0
            if game_time > 10:
                # Game was very slow - log but still use results
                pass
            for r in results:
                if "error" in r:
                    errors += 1
                else:
                    all_results.append(r)
        except Exception:
            errors += 1

        # Safety: recreate brain if game took too long (might be corrupted state)
        if time.time() - game_t0 > 10:
            brain = brain_class(data_dir=data_dir)

        if (i + 1) % 50 == 0:
            gc.collect()

    elapsed = time.time() - t0
    sys.stdout.write(
        f"\r  {strategy_name}: {n_iterations} klara "
        f"({len(all_results)} ok, {errors} fel) "
        f"på {elapsed:.1f}s ({n_iterations/max(elapsed,0.01):.1f} spel/s)   \n"
    )
    sys.stdout.flush()
    return all_results


def summarize(results):
    if not results:
        return {}, {}
    keys = ["fv", "fv_30", "ek", "score", "bta", "n_fast", "fv_bta_tkr",
            "abt_t", "abt_k", "tb", "tg",
            "plan_q", "plan_h", "plan_t", "plan_qk", "plan_hk",
            "exec_q", "exec_h", "exec_t"]
    summary = {}
    for k in keys:
        vals = [r[k] for r in results if k in r]
        if vals:
            sv = sorted(vals)
            summary[k] = {
                "min": min(vals),
                "medel": statistics.mean(vals),
                "max": max(vals),
                "stddev": statistics.stdev(vals) if len(vals) > 1 else 0,
                "p10": sv[max(0, len(sv)//10 - 1)],
                "p90": sv[min(len(sv)-1, len(sv)*9//10)],
            }
    by_score = sorted(results, key=lambda r: r.get("score", 0))
    score_games = {
        "Sämsta": by_score[0],
        "Median": by_score[len(by_score) // 2],
        "Bästa": by_score[-1],
    }
    return summary, score_games


# ═══════════════════════════════════════════════════════
#  TABELLER
# ═══════════════════════════════════════════════════════

def print_compact_table(all_data):
    """Kompakt jämförelsetabell: FV, EK, Score, Q/H/T per strategi."""
    w = 84
    print(f"\n  ┌{'─' * w}┐")
    print(f"  │ {'SAMMANFATTNING – Medelvärden':<{w}} │")
    print(f"  ├{'─' * w}┤")
    print(f"  │ {'Strategi':<16}{'FV tot':>9}{'EK':>9}{'TG':>8}{'Score':>9}"
          f"{'FV/BTA':>9}{'Fast':>6}{'BTA':>9}{'N':>9} │")
    print(f"  │ {'':16}{'Mkr':>9}{'Mkr':>9}{'%':>8}{'tkr/kvm':>9}"
          f"{'tkr/kvm':>9}{'st':>6}{'kvm':>9}{'':>9} │")
    print(f"  ├{'─' * w}┤")

    # Sortera på medel-score
    ranked = sorted(all_data.items(),
                    key=lambda x: x[1][0].get("score", {}).get("medel", 0),
                    reverse=True)

    for i, (name, (summary, sg, n)) in enumerate(ranked):
        medal = ["🥇", "🥈", "🥉", "  ", "  "][i] if i < 5 else "  "
        fv = summary.get("fv", {}).get("medel", 0)
        ek = summary.get("ek", {}).get("medel", 0)
        tg = summary.get("tg", {}).get("medel", 0)
        sc = summary.get("score", {}).get("medel", 0)
        fb = summary.get("fv_bta_tkr", {}).get("medel", 0)
        nf = summary.get("n_fast", {}).get("medel", 0)
        bt = summary.get("bta", {}).get("medel", 0)
        print(f"  │{medal}{name:<14}{fv:>9.1f}{ek:>9.1f}{tg:>7.1f}%{sc:>9.1f}"
              f"{fb:>9.1f}{nf:>6.1f}{bt:>9.0f}{n:>9} │")

    print(f"  └{'─' * w}┘")

    # Q/H/T table
    print(f"\n  ┌{'─' * w}┐")
    print(f"  │ {'PROJEKTMÅL – Q/H/T (medelvärden)':<{w}} │")
    print(f"  ├{'─' * w}┤")
    print(f"  │ {'Strategi':<16}{'── Efter Planering ──':^30}{'── Efter Genomförande ──':^30} │")
    print(f"  │ {'':16}{'Q':>6}{'Qkr':>6}{'H':>6}{'Hkr':>6}{'T':>6}"
          f"{'Q':>6}{'H':>6}{'T':>6}{'':>14} │")
    print(f"  ├{'─' * w}┤")

    for i, (name, (summary, sg, n)) in enumerate(ranked):
        medal = ["🥇", "🥈", "🥉", "  ", "  "][i] if i < 5 else "  "
        pq = summary.get("plan_q", {}).get("medel", 0)
        ph = summary.get("plan_h", {}).get("medel", 0)
        pt = summary.get("plan_t", {}).get("medel", 0)
        qk = summary.get("plan_qk", {}).get("medel", 0)
        hk = summary.get("plan_hk", {}).get("medel", 0)
        eq = summary.get("exec_q", {}).get("medel", 0)
        eh = summary.get("exec_h", {}).get("medel", 0)
        et = summary.get("exec_t", {}).get("medel", 0)
        print(f"  │{medal}{name:<14}{pq:>6.1f}{qk:>6.1f}{ph:>6.1f}{hk:>6.1f}{pt:>6.1f}"
              f"{eq:>6.1f}{eh:>6.1f}{et:>6.1f}{'':>14} │")

    print(f"  └{'─' * w}┘")


def print_expanded_table(name, summary, n, score_games):
    """Full tabell med min/P10/medel/P90/max + sammanhängande omgångar."""
    w = 80
    print(f"\n  ┌{'─' * w}┐")
    print(f"  │ {'AI: ' + name + f'  ({n} omgångar)':<{w}} │")
    print(f"  ├{'─' * w}┤")
    print(f"  │ {'Nyckeltal':<16}{'Min':>9}{'P10':>9}{'Medel':>9}"
          f"{'P90':>9}{'Max':>9}{'Stddev':>9}{'Enhet':>10} │")
    print(f"  ├{'─' * w}┤")

    rows = [
        ("FV(30%)", "fv_30", "Mkr"),
        ("EK", "ek", "Mkr"),
        ("FV/BTA", "fv_bta_tkr", "tkr/kvm"),
        ("Slutpoäng", "score", ""),
        ("BTA", "bta", "kvm"),
        ("Fastigheter", "n_fast", "st"),
        None,  # separator
        ("ABT-T", "abt_t", "Mkr"),
        ("ABT-K", "abt_k", "Mkr"),
        ("TB", "tb", "Mkr"),
        ("TG", "tg", "%"),
    ]

    for item in rows:
        if item is None:
            print(f"  ├{'─' * w}┤")
            continue
        label, key, unit = item
        if key in summary:
            s = summary[key]
            print(f"  │ {label:<16}{s['min']:>9.1f}{s['p10']:>9.1f}"
                  f"{s['medel']:>9.1f}{s['p90']:>9.1f}{s['max']:>9.1f}"
                  f"{s['stddev']:>9.1f}{unit:>10} │")

    print(f"  └{'─' * w}┘")

    if score_games:
        print(f"  ┌{'─' * w}┐")
        print(f"  │ {'Sammanhängande omgångar (sorterat på Score)':<{w}} │")
        print(f"  ├{'─' * w}┤")
        print(f"  │ {'Omgång':<16}{'Score':>9}{'FV(30%)':>9}{'EK':>9}"
              f"{'TB':>9}{'TG':>8}{'BTA':>9}{'Fast':>6}{'':>5} │")
        print(f"  ├{'─' * w}┤")
        for label, g in score_games.items():
            tg_val = g.get('tg', 0)
            print(f"  │ {label:<16}{g.get('score',0):>9.1f}"
                  f"{g.get('fv_30',0):>9.1f}{g.get('ek',0):>9.1f}"
                  f"{g.get('tb',0):>9.1f}{tg_val:>7.1f}%{g.get('bta',0):>9.0f}"
                  f"{g.get('n_fast',0):>6}{'':>5} │")
        print(f"  └{'─' * w}┘")


# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║          HUSBYGGSPELET – SIMULERINGSMOTOR           ║")
    print("╚══════════════════════════════════════════════════════╝")

    data_dir = find_data_dir()
    print(f"\n  📂 Data: {data_dir}")

    print(f"\n  Tillgängliga AI-strategier:")
    strat_names = list(STRATEGIES.keys())
    for i, (name, info) in enumerate(STRATEGIES.items()):
        print(f"    {i+1}. {name}: {info['desc']}")

    print(f"\n  Vilka strategier? (nummer kommasep., eller 'alla')")
    choice = input(f"  Val [alla]: ").strip()
    if not choice or choice.lower() == "alla":
        chosen = strat_names
    else:
        indices = [int(x.strip()) - 1 for x in choice.split(",")
                   if x.strip().isdigit()]
        chosen = [strat_names[i] for i in indices if 0 <= i < len(strat_names)]
        if not chosen:
            chosen = strat_names
    print(f"  → {', '.join(chosen)}")

    n_input = input(f"\n  Antal iterationer (max 1000) [10]: ").strip()
    n_iter = min(1000, int(n_input)) if n_input.isdigit() else 10
    print(f"  → {n_iter} omgångar\n")

    while True:
        # Kör simuleringar
        all_data = {}  # {name: (summary, score_games, n)}
        for strat in chosen:
            results = run_simulation(data_dir, strat, n_iter)
            summary, sg = summarize(results)
            all_data[strat] = (summary, sg, len(results))

        # Visa kompakt tabell
        print_compact_table(all_data)

        # Meny
        while True:
            print(f"\n  Vad vill du göra?")
            print(f"    1. Visa expanderad tabell (per strategi)")
            print(f"    2. Simulera igen")
            print(f"    3. Avsluta")
            val = input("  Val [3]: ").strip()

            if val == "1":
                print(f"\n  Vilken strategi? (nummer eller 'alla')")
                for i, name in enumerate(chosen):
                    print(f"    {i+1}. {name}")
                exp_choice = input(f"  Val [alla]: ").strip()

                if not exp_choice or exp_choice.lower() == "alla":
                    show = chosen
                else:
                    exp_indices = [int(x.strip()) - 1
                                   for x in exp_choice.split(",")
                                   if x.strip().isdigit()]
                    show = [chosen[i] for i in exp_indices
                            if 0 <= i < len(chosen)]
                    if not show:
                        show = chosen

                for name in show:
                    s, sg, n = all_data[name]
                    print_expanded_table(name, s, n, sg)
                continue

            elif val == "2":
                n_input = input(
                    f"  Antal iterationer [{n_iter}]: ").strip()
                n_iter = min(1000, int(n_input)) \
                    if n_input.isdigit() else n_iter
                print()
                break  # Kör om

            else:
                print(f"\n  Tack för simuleringen!")
                return

    # Ska aldrig nås, men för säkerhets skull
    return


if __name__ == "__main__":
    main()

