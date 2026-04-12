"""
win_probability.py
──────────────
Lightweight, rule-based T20 win probability engine.
No ML required — inspired by DLS resource model.
Optimised for IPL match scenarios.
"""

from config import MAX_OVERS_T20, TOTAL_WICKETS


# DLS-style wicket resource table (% of innings remaining when wicket falls)
WICKET_RESOURCES = {
    10: 1.00, 9: 0.91, 8: 0.81, 7: 0.70,
    6: 0.58,  5: 0.46, 4: 0.34, 3: 0.23,
    2: 0.13,  1: 0.05, 0: 0.00,
}


def _overs_to_balls(overs_str) -> int:
    """Convert '15.2' → 92 balls completed."""
    if isinstance(overs_str, (int, float)):
        overs_str = str(overs_str)
    parts = str(overs_str).split(".")
    full = int(parts[0])
    extra = int(parts[1]) if len(parts) > 1 else 0
    return full * 6 + extra


def calculate_win_probability(
    target: int,
    current_score: int,
    wickets_lost: int,
    overs_completed,
    last_5_over_runs: int = 0,
    total_overs: int = MAX_OVERS_T20,
) -> dict:
    """
    Returns win probability dict for both teams in a T20 chase.
    """
    balls_done     = _overs_to_balls(overs_completed)
    balls_total    = total_overs * 6
    balls_remaining = balls_total - balls_done
    wickets_remaining = TOTAL_WICKETS - wickets_lost
    runs_needed    = target - current_score

    # Edge cases
    if runs_needed <= 0:
        batting_pct = 100.0
    elif wickets_remaining == 0 or balls_remaining <= 0:
        batting_pct = 0.0
    else:
        # Factor 1: Required Run Rate pressure (40 %)
        required_rr = (runs_needed / balls_remaining) * 6
        par_rr      = 9.0   # IPL average
        rr_pressure = max(0.0, min(1.0, 1.0 - (required_rr - par_rr) / 14.0))

        # Factor 2: Wickets remaining / DLS resource (35 %)
        wicket_factor = WICKET_RESOURCES.get(wickets_remaining, 0.0)

        # Factor 3: Match phase (15 %)
        phase = balls_done / balls_total
        if phase < 0.30:
            phase_mod = 0.50    # Powerplay volatility
        elif phase < 0.70:
            phase_mod = 0.70    # Middle overs
        else:
            phase_mod = 1.00    # Death overs

        # Factor 4: Recent momentum (10 %)
        if last_5_over_runs > 0:
            recent_rr  = last_5_over_runs / 5.0
            momentum   = max(0.0, min(1.0, recent_rr / 12.0))
        else:
            momentum = 0.50

        raw = (rr_pressure  * 0.40
             + wicket_factor * 0.35
             + phase_mod     * 0.15
             + momentum      * 0.10)

        batting_pct = round(max(3.0, min(97.0, raw * 100)), 1)

    bowling_pct = round(100.0 - batting_pct, 1)

    return {
        "batting_team_pct": batting_pct,
        "bowling_team_pct": bowling_pct,
        "runs_needed":      max(0, runs_needed),
        "balls_remaining":  max(0, balls_remaining),
        "required_rr":      round((runs_needed / max(1, balls_remaining)) * 6, 2),
    }


def build_win_bar(team_batting: str, pct_batting: float,
                  team_bowling: str, pct_bowling: float) -> str:
    """
    Builds a visual text win-probability bar for Telegram.
    """
    TOTAL_BLOCKS = 10
    filled = round(pct_batting / 100 * TOTAL_BLOCKS)
    empty  = TOTAL_BLOCKS - filled

    bar = "█" * filled + "░" * empty
    short1 = team_batting[:3].upper()
    short2 = team_bowling[:3].upper()

    return (
        f"🏆 Win Probability\n"
        f"`{short1} [{bar}] {short2}`\n"
        f"  `{pct_batting:>5.1f}%` {'':>12} `{pct_bowling:.1f}%`"
    )

def calculate_win_probability_swing(target: int, current_score: int, wickets_lost: int, overs_completed, last5: list) -> dict:
    """
    Computes Win Probability manually then rewinds 12 balls to calculate shift.
    Returns: wp_now, wp_past, swing (positive means batting team improved).
    """
    wp_now = calculate_win_probability(target, current_score, wickets_lost, overs_completed)
    
    if not last5:
        return {"swing": 0.0, "wp_now": wp_now["batting_team_pct"], "wp_past": wp_now["batting_team_pct"], "runs_since": 0, "wkts_since": 0, "balls_since": 0}
        
    past_overs = sorted(last5, key=lambda x: str(x.get("over", "")), reverse=True)[:2]
    runs_since = sum(o.get("runs", 0) for o in past_overs)
    wkts_since = sum(o.get("wickets", 0) for o in past_overs)
    
    balls_since = sum(len(o.get("balls", [])) for o in past_overs) if any(o.get("balls") for o in past_overs) else len(past_overs) * 6
    if balls_since == 0: balls_since = 12
    
    past_balls = _overs_to_balls(overs_completed) - balls_since
    past_overs_str = f"{past_balls // 6}.{past_balls % 6}"
    
    wp_past = calculate_win_probability(
        target,
        max(0, current_score - runs_since),
        max(0, wickets_lost - wkts_since),
        past_overs_str
    )
    
    swing = wp_now["batting_team_pct"] - wp_past["batting_team_pct"]
    return {
        "swing": round(swing, 1),
        "wp_now": wp_now["batting_team_pct"],
        "wp_past": wp_past["batting_team_pct"],
        "runs_since": runs_since,
        "wkts_since": wkts_since,
        "balls_since": balls_since
    }
