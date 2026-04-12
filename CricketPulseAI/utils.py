"""
utils.py
────────
All Telegram message formatters. HTML parse mode throughout.
"""

from win_probability import calculate_win_probability, build_win_bar


# ──────────────────────────── internal helpers ────────────────────

def _overs_to_float(overs_str) -> float:
    """'15.3' → 15.5 (cricket notation)."""
    parts = str(overs_str).split(".")
    full  = int(parts[0]) if parts[0].isdigit() else 0
    extra = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return full + extra / 6.0


def _projected_score(runs: int, overs_str, total: int = 20) -> int:
    ov = _overs_to_float(overs_str)
    return int((runs / ov) * total) if ov > 0 and runs else 0


def _mini_win_bar(t_bat: str, pct_bat: float,
                  t_bwl: str, pct_bwl: float) -> str:
    filled = round(pct_bat / 10)
    empty  = 10 - filled
    bar    = "█" * filled + "░" * empty
    b1     = t_bat[:4].ljust(4)
    b2     = t_bwl[:4].ljust(4)
    p1     = f"{pct_bat:.0f}%".ljust(5)
    p2     = f"{pct_bwl:.0f}%"
    return f"{b1} [{bar}] {b2}\n     {p1}          {p2}"


BALL_ICONS = {"W": "W", "6": "6", "4": "4", "0": "·"}


def _get_last12_display(last5_overs: list) -> str | None:
    """
    Returns last 12 balls as display string, or None if data is absent/boring.
    """
    if not last5_overs:
        return None

    all_balls: list[str] = []

    for over in last5_overs:
        raw = over.get("balls", [])
        if raw:
            all_balls.extend(BALL_ICONS.get(str(b), str(b)) for b in raw)
        else:
            # Reconstruct from over summary
            runs  = over.get("runs", 0)
            wkts  = over.get("wickets", 0)
            wkt_placed = False
            rem   = runs
            for i in range(6):
                if wkts and not wkt_placed and i == 3:
                    all_balls.append("W"); wkt_placed = True
                elif rem >= 6:
                    all_balls.append("6"); rem -= 6
                elif rem >= 4:
                    all_balls.append("4"); rem -= 4
                elif rem > 0:
                    all_balls.append(str(rem)); rem = 0
                else:
                    all_balls.append("·")

    balls12 = all_balls[-12:] if len(all_balls) >= 12 else all_balls
    # Skip if all dots — not informative
    if not balls12 or all(b == "·" for b in balls12):
        return None
    return "  ".join(balls12)


def _recent_event(i2: dict, last5: list) -> str:
    """Extract the most recent exciting event — wicket or boundary."""
    if last5:
        for over in reversed(last5):
            for ball in reversed(over.get("balls", [])):
                if ball == "W":
                    return f"💀 Wicket! (Over {over.get('over','?')})"
                elif ball == "6":
                    return f"🔥 SIX! (Over {over.get('over','?')})"
                elif ball == "4":
                    return f"4️⃣ FOUR! (Over {over.get('over','?')})"
    fow = (i2 or {}).get("fall_of_wickets", [])
    if fow:
        return f"💀 Last wkt: {fow[-1]}"
    return ""


def generate_tactical_nudge(i2: dict, i1: dict) -> str:
    """Rule-based Hinglish tactical nudge. Zero API calls."""
    if not i2 or i2.get("runs_needed") is None:
        if i1 and i1.get("runs") is not None:
            t1 = i1.get("team_short", "BAT")
            return f"{t1} ki innings done — ab bowling team ka asli imtihaan shuru!"
        return "Match warm-up phase — dono teams ready ho rahe hain!"

    rrr     = float(i2.get("required_run_rate") or 0)
    wickets = int(i2.get("wickets") or 0)
    balls   = int(i2.get("balls_remaining") or 120)
    rn      = int(i2.get("runs_needed") or 0)
    bat     = i2.get("team_short", "BAT")
    bwl     = (i1 or {}).get("team_short", "BWL")
    overs_done = (120 - balls) // 6

    if rn <= 0:
        return f"{bat} jeet gaya! Kya finish tha — unbelievable chase! 🏆"
    if rrr > 15:
        return f"Ab toh miracle chahiye {bat} ko — all-out attack, kuch bhi ho sakta! 🙏🔥"
    if rrr > 12:
        return f"Har ball pe boundary chahiye {bat} ko — dot ball matlab match gone! 💀"
    if rrr > 10 and wickets >= 7:
        return f"{bat} tailenders pe depend — ek last stand chahiye abhi! 🎯"
    if rrr > 10:
        return f"Smart aggression time — rotate karo, fir loose ball pe attack karo, {bat}! ⚡"
    if rrr > 9 and overs_done >= 16:
        return f"Death overs mein {bwl} yorkers dalega — {bat} ka courage test hoga! 🎳"
    if rrr > 8 and wickets <= 3:
        return f"{bat} comfortable hai — wickets bachao, boundaries apne aap aayenge! 📊"
    if rrr <= 6 and balls > 30:
        return f"{bat} driver's seat mein hai — {bwl} ko abhi quick wickets chahiye! 🚨"
    if rrr <= 7:
        return f"{bat} match control mein hai — {bwl} ko dot balls se pressure banana hoga! 🔴"
    return f"Tight contest — next boundary ya wicket sab badal dega! ⚖️"


# ──────────────────────────── MATCH DASHBOARD ─────────────────────

def format_match_dashboard(sc: dict, last5_overs: list = None) -> str:
    """
    Rich 16-line Match Dashboard with:
    • Both teams' live scores (monospace table)
    • Current batters + SR
    • Active bowler figures
    • Top performer from completed innings
    • Recent event (wicket / boundary)
    • Win probability bar (only during 2nd innings chase)
    • Last 12 balls (skipped if all-dots)
    • Rule-based Hinglish tactical nudge
    """
    if not sc:
        return "❌ Match data unavailable. Try /live again."

    i1    = sc.get("innings1") or {}
    i2    = sc.get("innings2") or {}
    last5 = last5_overs or sc.get("last_5_overs", [])

    i1_ok = bool(i1 and i1.get("runs") is not None)
    i2_ok = bool(i2 and i2.get("runs") is not None)

    # ── Header ──────────────────────────────────────────────────────
    short  = sc.get("short_name", sc.get("match_name", "Match"))
    league = sc.get("match_type", "IPL")
    venue  = sc.get("venue", "")
    # Show city only (last comma-segment)
    venue_city = venue.split(",")[-1].strip()[:30] if venue else ""

    started = sc.get("match_started", False)
    ended   = sc.get("match_ended", False)
    live_label = "✅ RESULT" if ended else ("🔴 LIVE" if started else "🔵 UPCOMING")

    lines = [
        f"🏟️ <b>{short}</b>  |  {league}",
        f"{live_label}  •  <i>{venue_city}</i>" if venue_city else live_label,
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # ── Scores block — both teams in monospace table ─────────────
    t2_short = sc.get("team2_short", i2.get("team_short", "T2"))

    if i1_ok:
        done_tag = "✅" if (i1.get("wickets", 0) == 10
                            or _overs_to_float(i1.get("overs", 0)) >= 20) else "🏏"
        lines.append(
            f"<code>{done_tag} {i1.get('team_short','T1'):<5}"
            f"{str(i1.get('runs','–'))+'/'+str(i1.get('wickets','–')):>7}  "
            f"({str(i1.get('overs','–')):>5} ov)  "
            f"RR:{i1.get('run_rate','–')}</code>"
        )

    if i2_ok:
        rn   = i2.get("runs_needed")
        bl   = i2.get("balls_remaining")
        rrr  = i2.get("required_run_rate")
        tail = f"  ← {rn} in {bl}b | RRR:{rrr}" if rn is not None else ""
        lines.append(
            f"<code>🏏 {i2.get('team_short', t2_short):<5}"
            f"{str(i2.get('runs','–'))+'/'+str(i2.get('wickets','–')):>7}  "
            f"({str(i2.get('overs','–')):>5} ov){tail}</code>"
        )
    elif i1_ok and not i2_ok:
        # 1st innings done, 2nd not started
        lines.append(f"<code>⏳ {t2_short:<5}  Innings break — chase incoming</code>")

    lines.append("")

    # ── Live batters (2nd innings active) ───────────────────────
    if i2_ok:
        batters = [b for b in i2.get("batsmen", []) if "batting*" in b.get("status", "")]
        if batters:
            bat_rows = []
            for b in batters[:2]:
                sr = round(b.get("sr") or (b.get("runs",0)/max(b.get("balls",1),1)*100), 1)
                bat_rows.append(
                    f"🟢 {b['name']:<18} {b.get('runs',0):>3}*({b.get('balls',0)}b)  SR:{sr}"
                )
            lines.append("<code>" + "\n".join(bat_rows) + "</code>")

        # Active bowler — highest wickets among those who bowled
        bowlers = sorted(i2.get("bowlers", []),
                         key=lambda x: (x.get("wickets", 0), -x.get("economy", 99)),
                         reverse=True)
        if bowlers:
            bw = bowlers[0]
            lines.append(
                f"<code>🎳 {bw['name']:<18}  "
                f"{bw.get('wickets',0)}/{bw.get('runs',0)} "
                f"({bw.get('overs',0)} ov)  Eco:{bw.get('economy',0)}</code>"
            )

    # ── Top performer from completed innings ─────────────────────
    # Show even when 2nd innings is active — adds context about the target
    perf_parts = []
    if i1_ok:
        bats1 = i1.get("batsmen", [])
        if bats1:
            top_bat = max(bats1, key=lambda x: x.get("runs", 0))
            if top_bat.get("runs", 0) >= 10:
                perf_parts.append(
                    f"⭐ {top_bat['name']} {top_bat.get('runs',0)}({top_bat.get('balls',0)}b)"
                )
        bwls1 = i2.get("bowlers", []) if i2_ok else i1.get("bowlers", [])
        if bwls1:
            top_bowl = max(bwls1, key=lambda x: x.get("wickets", 0))
            if top_bowl.get("wickets", 0) >= 1:
                perf_parts.append(
                    f"🎳 {top_bowl['name']} {top_bowl.get('wickets',0)}/{top_bowl.get('runs',0)}"
                )
    if perf_parts:
        lines.append(f"<code>{'  |  '.join(perf_parts)}</code>")

    lines.append("")

    # ── Win bar — ONLY when 2nd innings is genuinely in progress ──
    chase_live = (
        i2_ok
        and int(i2.get("target") or 0) > 0
        and int(i2.get("runs_needed") or 0) > 0
    )
    if chase_live:
        try:
            l5_runs = sum(o.get("runs", 0) for o in last5)
            wp = calculate_win_probability(
                target          = i2.get("target", 180),
                current_score   = i2.get("runs") or 0,
                wickets_lost    = i2.get("wickets") or 0,
                overs_completed = i2.get("overs", "0.0"),
                last_5_over_runs= l5_runs,
            )
            bar = _mini_win_bar(
                i2.get("team_short", "BAT"), wp["batting_team_pct"],
                i1.get("team_short", "BWL"), wp["bowling_team_pct"],
            )
            lines.append(f"<code>{bar}</code>")
            lines.append("")
        except Exception:
            pass

    # ── Last 12 balls ────────────────────────────────────────────
    balls_str = _get_last12_display(last5)
    if balls_str:
        lines.append(f"<code>Last 12:  {balls_str}</code>")
    else:
        # Fallback: recent event instead of dummy dots
        event = _recent_event(i2 if i2_ok else {}, last5)
        if event:
            lines.append(event)

    lines.append("")

    # ── Tactical nudge ───────────────────────────────────────────
    nudge = generate_tactical_nudge(i2 if i2_ok else {}, i1 if i1_ok else {})
    lines.append(f"💡 <i>{nudge}</i>")

    return "\n".join(lines)


# ──────────────────────────── FULL SCORECARD ──────────────────────

def format_scorecard(sc: dict) -> str:
    if not sc:
        return "❌ Scorecard unavailable. Try /live → select match."

    i1 = sc.get("innings1") or {}
    i2 = sc.get("innings2") or {}

    lines = [f"🏟️ <b>{sc.get('match_name', 'Match')}</b>"]
    if sc.get("venue"):
        lines.append(f"📍 {sc['venue']}")
    if sc.get("toss"):
        lines.append(f"🪙 {sc['toss']}")
    lines.append("")

    def block(inn: dict, label: str):
        if not inn or inn.get("runs") is None:
            return []
        out = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"<b>{label} — {inn.get('team_short','?')}</b>",
            f"🏏 <b>{inn.get('runs')}/{inn.get('wickets')}</b>"
            f"  ({inn.get('overs')} ov)  RR: {inn.get('run_rate')}",
            "",
        ]
        for b in inn.get("batsmen", [])[:7]:
            icon = "🟢" if "batting*" in b.get("status","") else "🔴"
            out.append(
                f"<code>{icon} {b['name']:<19} "
                f"{b.get('runs',0):>3}({b.get('balls',0)}b)"
                f"  4s·{b.get('fours',0)} 6s·{b.get('sixes',0)}</code>"
            )
        out.append("")
        bwls = inn.get("bowlers", [])
        if bwls:
            out.append("<b>Bowling:</b>")
            for bw in sorted(bwls, key=lambda x: x.get("wickets",0), reverse=True)[:5]:
                out.append(
                    f"<code>  {bw['name']:<18} {bw.get('overs',0)}ov "
                    f"{bw.get('wickets',0)}/{bw.get('runs',0)}  "
                    f"eco:{bw.get('economy',0)}</code>"
                )
            out.append("")
        return out

    lines.extend(block(i1, "1st Innings"))

    if i2 and i2.get("runs") is not None:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"<b>2nd Innings — {i2.get('team_short','?')} (chasing {i2.get('target','–')})</b>",
            f"🏏 <b>{i2.get('runs')}/{i2.get('wickets')}</b>  ({i2.get('overs')} ov)",
        ]
        if i2.get("runs_needed") is not None:
            lines.append(
                f"🎯 Need <b>{i2.get('runs_needed')}</b> in "
                f"<b>{i2.get('balls_remaining')}</b> balls  "
                f"RRR: <b>{i2.get('required_run_rate')}</b>"
            )
        lines.append("")
        lines.extend(block(i2, "")[4:])   # skip duplicate header

    # Win bar
    if i2 and i2.get("target", 0) and i2.get("runs_needed", 1) > 0:
        try:
            wp = calculate_win_probability(
                target=i2.get("target", 180),
                current_score=i2.get("runs") or 0,
                wickets_lost=i2.get("wickets") or 0,
                overs_completed=i2.get("overs", "0.0"),
            )
            lines += ["", build_win_bar(
                i2.get("team_short","BAT"), wp["batting_team_pct"],
                i1.get("team_short","BWL"), wp["bowling_team_pct"],
            )]
        except Exception:
            pass

    lines += ["", "💬 Ask me anything about this match!"]
    return "\n".join(lines)


# ──────────────────────────── LIVE LIST CARD ──────────────────────

def format_live_match_card(m: dict) -> str:
    i1 = m.get("innings1") or {}
    i2 = m.get("innings2") or {}
    lines = [f"🏏 <b>{m.get('short_name', m.get('match_name','Match'))}</b>"]
    if m.get("venue"):
        lines.append(f"📍 <i>{m['venue'][:55]}</i>")
    if i1 and i1.get("runs") is not None:
        lines.append(f"  {i1.get('team_short','T1')}: <b>{i1.get('runs')}/{i1.get('wickets')}</b> ({i1.get('overs')} ov)")
    if i2 and i2.get("runs") is not None:
        rn  = i2.get("runs_needed")
        bl  = i2.get("balls_remaining")
        tag = f" ← needs {rn} in {bl}b" if rn is not None else ""
        lines.append(f"  {i2.get('team_short','T2')}: <b>{i2.get('runs')}/{i2.get('wickets')}</b> ({i2.get('overs')} ov){tag}")
    lines.append(f"⏱ {m.get('status','')}")
    return "\n".join(lines)


# ──────────────────────────── GEMINI CONTEXT ──────────────────────

def build_match_context(sc: dict) -> str:
    if not sc:
        return "No live match data."
    i1    = sc.get("innings1") or {}
    i2    = sc.get("innings2") or {}
    last5 = sc.get("last_5_overs", [])

    lines = [
        f"Match: {sc.get('match_name','IPL')}",
        f"Status: {sc.get('status','')}",
    ]
    if sc.get("toss"):
        lines.append(f"Toss: {sc['toss']}")
    if i1 and i1.get("runs") is not None:
        lines.append(
            f"Inn1 ({i1.get('team_short','T1')}): {i1.get('runs')}/{i1.get('wickets')} "
            f"in {i1.get('overs')} ov  RR:{i1.get('run_rate')}"
        )
        tops = [b["name"] for b in i1.get("batsmen",[]) if b.get("runs",0) >= 20]
        if tops:
            lines.append(f"  Key batsmen: {', '.join(tops)}")
    if i2 and i2.get("runs") is not None:
        lines.append(
            f"Inn2 ({i2.get('team_short','T2')}): {i2.get('runs')}/{i2.get('wickets')} "
            f"in {i2.get('overs')} ov  RR:{i2.get('run_rate')}"
        )
        if i2.get("runs_needed") is not None:
            lines.append(
                f"  Chase: {i2.get('runs_needed')} in {i2.get('balls_remaining')} balls  "
                f"RRR:{i2.get('required_run_rate')}"
            )
        at = [f"{b['name']} {b.get('runs','?')}*({b.get('balls','?')}b)"
              for b in i2.get("batsmen",[]) if "batting*" in b.get("status","")]
        if at:
            lines.append(f"  Batsmen: {', '.join(at)}")
        bwls = sorted(i2.get("bowlers",[]), key=lambda x: x.get("wickets",0), reverse=True)[:3]
        if bwls:
            lines.append("  Bowling: " + ", ".join(
                f"{b['name']} {b.get('wickets',0)}/{b.get('runs',0)} eco:{b.get('economy',0)}"
                for b in bwls
            ))
        from win_probability import calculate_win_probability
        try:
            wp = calculate_win_probability(
                target=i2.get("target",180), current_score=i2.get("runs") or 0,
                wickets_lost=i2.get("wickets") or 0, overs_completed=i2.get("overs","0.0"),
                last_5_over_runs=sum(o.get("runs",0) for o in last5),
            )
            lines.append(
                f"  Win prob: {i2.get('team_short','BAT')} {wp['batting_team_pct']}%  "
                f"vs {i1.get('team_short','BWL')} {wp['bowling_team_pct']}%"
            )
        except Exception:
            pass
    if last5:
        rpo = [str(o.get("runs","?")) for o in last5]
        lines.append(f"Last 5 overs: {', '.join(rpo)}")
    return "\n".join(lines)


def format_war_room_report(sc: dict, last5: list) -> str:
    """Deterministic high-detail strategy dashboard (bypasses LLM overhead)"""
    from win_probability import calculate_win_probability_swing

    if not sc: return "❌ No match data."
    
    i1 = sc.get("innings1") or {}
    i2 = sc.get("innings2") or {}
    
    lines = [
        f"🛰️ <b>TACTICAL WAR ROOM</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    
    active_inn = i2 if (i2 and i2.get("runs") is not None) else i1
    if not active_inn or active_inn.get("runs") is None:
        return "🛰️ War Room disabled: Match hasn't started."

    bat = active_inn.get("team_short", "BAT")
    bwl = i1.get("team_short", "BWL") if active_inn == i2 else "BWL"
    
    # ── Prediction for next 12 balls ──
    try:
        crr = float(active_inn.get("run_rate", 8.0))
        proj_runs = int(round((crr / 6.0) * 12)) 
        proj_wkts = 1 if last5 and sum(o.get("wickets",0) for o in last5) >= 1 else 0
        
        lines.append(f"🔮 <b>Next 12 Balls Forecast:</b>")
        lines.append(f"<code>• Est. Runs:    {proj_runs} to {proj_runs+5}</code>")
        lines.append(f"<code>• Est. Wickets: {proj_wkts}</code>")
        lines.append("")
    except Exception:
        pass
        
    # ── Win Probability Swing ──
    if active_inn == i2 and i2.get("target"):
        target = i2.get("target", 180)
        curr = i2.get("runs", 0)
        wkts = i2.get("wickets", 0)
        ov = i2.get("overs", "0.0")
        
        try:
            swing_data = calculate_win_probability_swing(target, curr, wkts, ov, last5)
            swing = swing_data.get("swing", 0)
            sign = "+" if swing > 0 else ""
            lines.append(f"⚖️ <b>Momentum Shift (Last {swing_data.get('balls_since', 12)} balls):</b>")
            lines.append(f"<code>• Runs Scored: {swing_data.get('runs_since',0)}</code>")
            lines.append(f"<code>• Wickets:     {swing_data.get('wkts_since',0)}</code>")
            if swing > 0:
                lines.append(f"<code>• Win Prob:    {bat} {sign}{swing}% 📈</code>")
            elif swing < 0:
                lines.append(f"<code>• Win Prob:    {bat} {swing}% 📉</code>")
            else:
                lines.append(f"<code>• Win Prob:    No Change ➖</code>")
            lines.append("")
        except Exception:
            pass
        
    # ── Tactical Nudge ──
    nudge = generate_tactical_nudge(i2 if i2 and i2.get("runs") is not None else {}, i1 if i1 and i1.get("runs") is not None else {})
    lines.append(f"💡 <b>Digital Coach Nudge:</b>\n<i>{nudge}</i>")
    
    return "\n".join(lines)


def truncate(text: str, limit: int = 4050) -> str:
    if len(text) <= limit:
        return text
    truncated = text[:limit] + "..."
    # If we cut inside a code block, close it
    if truncated.count("<code>") > truncated.count("</code>"):
        truncated += "</code>"
    if truncated.count("<b>") > truncated.count("</b>"):
        truncated += "</b>"
    if truncated.count("<i>") > truncated.count("</i>"):
        truncated += "</i>"
    return truncated
