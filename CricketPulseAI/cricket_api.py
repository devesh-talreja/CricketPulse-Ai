"""
cricket_api.py
──────────────
Async CricketData.org (cricapi.com/v1) integration.
Properly normalises raw API → our internal match dict format.
"""

import httpx
import logging
from config import CRICKET_API_KEY, CRICKET_API_BASE

log = logging.getLogger(__name__)
TIMEOUT = 12.0


# ── Helpers ────────────────────────────────────────────────────────

def _overs_to_balls(overs) -> int:
    """'15.3' → 93 balls. Cricket overs notation, not decimal."""
    parts = str(overs).split(".")
    full = int(parts[0]) if parts[0].isdigit() else 0
    extra = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return full * 6 + extra


def _run_rate(runs, overs) -> float:
    balls = _overs_to_balls(overs)
    if balls == 0:
        return 0.0
    return round((runs / balls) * 6, 2)


def _short_name(full_name: str, team_info: list) -> str:
    """Get team short name from teamInfo list."""
    for ti in team_info:
        if ti.get("name", "").lower() == full_name.lower():
            sn = ti.get("shortname", "")
            if sn:
                return sn
    # Fallback: first 3 chars uppercase
    return full_name[:3].upper() if full_name else "UNK"


def _parse_batting(batting_list: list) -> list:
    """Normalize batting scorecard entries."""
    out = []
    for b in batting_list:
        player = b.get("batsman", {})
        name = player.get("name", b.get("name", "Unknown"))
        dismissal = b.get("dismissal-wicket", {})
        dis_text = dismissal.get("dismissal", "") if dismissal else ""
        out.append({
            "name":   name,
            "runs":   b.get("r", 0),
            "balls":  b.get("b", 0),
            "fours":  b.get("4s", 0),
            "sixes":  b.get("6s", 0),
            "sr":     b.get("sr", 0.0),
            "status": dis_text if dis_text else "batting*",
        })
    return out


def _parse_bowling(bowling_list: list) -> list:
    """Normalize bowling figures entries."""
    out = []
    for b in bowling_list:
        player = b.get("bowler", {})
        name = player.get("name", b.get("name", "Unknown"))
        overs = b.get("o", "0")
        out.append({
            "name":     name,
            "overs":    float(overs) if str(overs).replace(".", "").isdigit() else 0,
            "runs":     b.get("r", 0),
            "wickets":  b.get("w", 0),
            "economy":  b.get("eco", 0.0),
            "maidens":  b.get("m", 0),
        })
    return out


def normalize_match(m: dict) -> dict:
    """
    Convert raw CricketData.org currentMatches OR match_scorecard dict
    into our unified internal format with innings1 + innings2.
    """
    teams_raw = m.get("teams", []) or []
    team_info = m.get("teamInfo", []) or []
    scores    = m.get("score", []) or []
    scorecard = m.get("scorecard", []) or []     # detailed — premium only

    t1 = teams_raw[0] if len(teams_raw) > 0 else "Team 1"
    t2 = teams_raw[1] if len(teams_raw) > 1 else "Team 2"
    t1_short = _short_name(t1, team_info)
    t2_short = _short_name(t2, team_info)

    # ── Innings from score array (always present) ──────────────────
    def build_innings(idx: int, team: str, team_short: str,
                      target: int = 0) -> dict:
        if idx >= len(scores):
            return {}
        s    = scores[idx]
        runs = s.get("r") or 0
        wkts = s.get("w") or 0
        ovrs = s.get("o") or "0"

        inn: dict = {
            "team":       team,
            "team_short": team_short,
            "runs":       runs,
            "wickets":    wkts,
            "overs":      str(ovrs),
            "run_rate":   _run_rate(runs, ovrs),
            "batsmen":    [],
            "bowlers":    [],
            "fall_of_wickets": [],
        }

        if target:
            runs_needed    = max(0, target - runs)
            balls_remaining = max(0, 120 - _overs_to_balls(ovrs))
            rrr = round((runs_needed / balls_remaining) * 6, 2) \
                  if balls_remaining > 0 else 0.0
            inn.update({
                "target":           target,
                "runs_needed":      runs_needed,
                "balls_remaining":  balls_remaining,
                "required_run_rate": rrr,
            })

        # Enrich from detailed scorecard if available
        if scorecard and idx < len(scorecard):
            sc_entry = scorecard[idx]
            inn["batsmen"] = _parse_batting(sc_entry.get("batting", []))
            inn["bowlers"] = _parse_bowling(sc_entry.get("bowling", []))
            fow = sc_entry.get("fow", []) or []
            inn["fall_of_wickets"] = [
                f"{f.get('r','?')}/{f.get('wkt','?')} "
                f"({f.get('o','?')} ov) - "
                f"{(f.get('batsman') or {}).get('name', '?')}"
                for f in fow
            ]

        return inn

    innings1 = build_innings(0, t1, t1_short)
    t1_total  = (scores[0].get("r") or 0) if scores else 0
    target    = t1_total + 1 if t1_total else 0
    innings2  = build_innings(1, t2, t2_short, target=target)

    # ── Toss ──────────────────────────────────────────────────────
    toss     = m.get("tossResults") or {}
    toss_str = ""
    if isinstance(toss, dict) and toss.get("winner"):
        toss_str = f"{toss['winner']} won the toss & elected to {toss.get('decision','bat')}"

    return {
        "match_id":    m.get("id", ""),
        "match_name":  m.get("name", "Live Match"),
        "short_name":  f"{t1_short} vs {t2_short}",
        "team1":       t1,
        "team2":       t2,
        "team1_short": t1_short,
        "team2_short": t2_short,
        "venue":       m.get("venue", ""),
        "status":      m.get("status", ""),
        "toss":        toss_str,
        "match_type":  (m.get("matchType") or "T20").upper(),
        "innings1":    innings1,
        "innings2":    innings2,
        "last_5_overs": [],
        "match_started": bool(m.get("matchStarted")),
        "match_ended":   bool(m.get("matchEnded")),
    }


# ── API layer ──────────────────────────────────────────────────────

async def _get(endpoint: str, params: dict = None):
    url = f"{CRICKET_API_BASE}/{endpoint}"
    p = {"apikey": CRICKET_API_KEY}
    if params:
        p.update(params)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=p)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data")
            log.warning("API non-success [%s]: %s", endpoint, data.get("status"))
            return None
    except Exception as exc:
        log.error("Cricket API [%s] failed: %s", endpoint, exc)
        return None


async def fetch_live_matches() -> list[dict]:
    """Return normalized list of current matches."""
    raw = await _get("currentMatches")
    if not raw or not isinstance(raw, list):
        return []
    return [normalize_match(m) for m in raw]


async def fetch_scorecard(match_id: str) -> dict | None:
    """
    Attempt detailed scorecard (premium). Returns normalized dict or None.
    """
    raw = await _get("match_scorecard", {"id": match_id})
    if raw and isinstance(raw, dict):
        return normalize_match(raw)
    return None
