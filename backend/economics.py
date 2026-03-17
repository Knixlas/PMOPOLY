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
    total_cost = mark_cost + expansion_cost + dev_cost

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


def calc_final_score(player, total_fv_30: float) -> dict:
    """Calculate final game score."""
    real_ek = calc_real_ek(player)
    tg = calc_tg(player)
    tb = (tg / 100) * player.abt_start if player.abt_start > 0 else 0
    score = total_fv_30 + real_ek + tb

    return {
        "fv_30": round(total_fv_30, 1),
        "real_ek": round(real_ek, 1),
        "tb": round(tb, 1),
        "tg_pct": round(tg, 1),
        "score": round(score, 1),
        "total_bta": player.total_bta,
        "n_projects": len(player.projects),
    }
