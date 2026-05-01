"""Economic calculations for PMOPOLY."""
import math


def handle_abt_overflow(player, verbose_events: list = None) -> float:
    """Handle ABT deficit by taking parent company loans.
    Returns the deficit amount that was covered."""
    if player.abt_budget >= 0:
        return 0

    deficit = abs(player.abt_budget)
    n_loans = math.ceil(deficit / 95)  # 95 Mkr net per 100 Mkr loan
    gross = n_loans * 100
    fee = n_loans * 5
    net = n_loans * 95

    player.abt_overflow += deficit
    player.abt_borrowing_cost += fee
    player.abt_loans_net += net
    player.abt_budget = net - deficit
    player.eget_kapital -= fee

    if verbose_events is not None:
        verbose_events.append({
            "type": "loan",
            "text": f"Moderbolagslån: {n_loans}x100 Mkr (avgift {fee} Mkr). ABT fyllt till {player.abt_budget:.1f} Mkr",
            "deficit": deficit,
            "loans": n_loans,
            "fee": fee,
        })

    return deficit


def calc_phase1_economics(player, events: list):
    """Calculate Phase 1 economics: revenue, costs, ABT/EK split."""
    # Revenue = sum of anskaffning for all projects
    revenue = sum(p.anskaffning for p in player.projects)

    # Costs
    mark_cost = 15 if player.has_mark_tomt else 0
    expansion_cost = player.mark_expansions * 5
    dev_cost = sum(p.kostnad for p in player.projects)
    pc_cost = player.projektchef.get("lon", 0) if player.projektchef else 0
    total_cost = mark_cost + expansion_cost + dev_cost + pc_cost

    # Net
    net = revenue - total_cost

    # All net goes to ABT (EK starts at 0)
    player.eget_kapital = 0
    player.abt_budget = net
    player.abt_start = net

    events.append({
        "type": "economics",
        "revenue": revenue,
        "mark_cost": mark_cost,
        "expansion_cost": expansion_cost,
        "dev_cost": dev_cost,
        "total_cost": total_cost,
        "net": net,
        "abt": net,
    })


def calc_tg(player) -> float:
    """Calculate TG% (Täckningsgrad)."""
    if player.abt_start <= 0:
        return 0
    real_remaining = player.abt_budget - player.abt_loans_net
    tb = real_remaining - player.abt_borrowing_cost
    return (tb / player.abt_start) * 100


def calc_real_ek(player) -> float:
    """Calculate real equity after loans."""
    loans_gross = player.abt_loans_net + player.abt_borrowing_cost
    return player.eget_kapital - loans_gross


# ── Måluppfyllelse-faktor f(n) per regelboken §9.2 ──
# n = Q-avvikelse + H-avvikelse + T-avvikelse (sätts vid Skede 2-avslut, §7.7).
# Tabellen 0-10, sedan linjär nedgång (1 procentenhet per steg) tills 0% vid n=60.
_DEVIATION_FACTOR_TABLE = {
    0: 1.00, 1: 0.90, 2: 0.82, 3: 0.75, 4: 0.70,
    5: 0.65, 6: 0.61, 7: 0.58, 8: 0.55, 9: 0.52, 10: 0.50,
}


def deviation_factor(n: int) -> float:
    """Måluppfyllelse-faktor f(n) som multipliceras på råpoängen.

    n=0 → 100% (alla mål uppfyllda), n=10 → 50%, n≥60 → 0%.
    Mellan 11 och 60 sjunker faktorn 1 procentenhet per ytterligare avvikelse.
    """
    if n <= 0:
        return 1.00
    if n in _DEVIATION_FACTOR_TABLE:
        return _DEVIATION_FACTOR_TABLE[n]
    return max(0.0, (50 - (n - 10)) / 100.0)


def calc_deviation_n(player) -> dict:
    """Beräkna n = summan av Q/H/T-avvikelser per §7.7.

    Q-avvikelse = max(0, Q-krav − Q-utfall)
    H-avvikelse = max(0, H-krav − H-utfall)
    T-avvikelse = max(0, T-utfall − 12)

    Q/H/T-utfall hämtas från snap_exec_* (slutet av Skede 2.2 Genomförandet).
    Returnerar dict med n_q, n_h, n_t, n_total för transparens.
    """
    q_krav = getattr(player, 'q_krav', 0)
    h_krav = getattr(player, 'h_krav', 0)
    q_utfall = getattr(player, 'snap_exec_q', q_krav)
    h_utfall = getattr(player, 'snap_exec_h', h_krav)
    t_utfall = getattr(player, 'snap_exec_t', 12)

    n_q = max(0, q_krav - q_utfall)
    n_h = max(0, h_krav - h_utfall)
    n_t = max(0, t_utfall - 12)
    return {"n_q": n_q, "n_h": n_h, "n_t": n_t, "n_total": n_q + n_h + n_t}


def calc_final_score(player, total_fv_30: float) -> dict:
    """Beräkna slutpoäng per regelboken §9.1 + §9.2.

    Råpoäng = (FV × 30% × Energibonus + EK + TB) ÷ (BTA / 1000)
    Slutpoäng = Råpoäng × f(n)

    FV med energibonus per fastighet appliceras innan summan skickas hit
    (via _calc_fastighetsvarde i engine.py som multiplicerar med EK_FV_MODIFIER).
    EK-faktor (0.10 / 2.00) bibehållen som straff för negativ EK.
    TB sätts till 0 om ABT-budget var 0 eller negativ.
    """
    real_ek = calc_real_ek(player)
    tg = calc_tg(player)  # behållen för rapport / tooltip

    # FV = total fastighetsvärde (energibonus redan applicerad per fastighet)
    fv = total_fv_30 / 0.3 if total_fv_30 > 0 else 0  # total_fv_30 är 30 %-andelen; konvertera tillbaka
    ek = real_ek
    owned_bta = player.total_bta

    # TB i Mkr per §9.1
    if player.abt_start <= 0:
        tb = 0.0
    else:
        abt_remaining = getattr(player, 'abt_remaining_before_transfer', player.abt_budget)
        tb = abt_remaining - player.abt_loans_net - player.abt_borrowing_cost

    ek_factor = 0.10 if ek >= 0 else 2.00

    if owned_bta > 0:
        rapong = (0.30 * fv + ek_factor * ek + tb) / owned_bta * 1000
    else:
        rapong = tb

    # f(n) — måluppfyllelse-faktor
    dev = calc_deviation_n(player)
    f_n = deviation_factor(dev["n_total"])
    score = rapong * f_n

    return {
        "fv": round(fv, 1),
        "fv_30": round(fv * 0.3, 1),
        "real_ek": round(real_ek, 1),
        "tb": round(tb, 1),
        "tg_pct": round(tg, 1),
        "rapong": round(rapong, 1),
        "n_q": dev["n_q"],
        "n_h": dev["n_h"],
        "n_t": dev["n_t"],
        "n_total": dev["n_total"],
        "f_n": round(f_n, 2),
        "score": round(score, 1),
        "total_bta": owned_bta,
        "n_projects": len(player.projects),
    }
