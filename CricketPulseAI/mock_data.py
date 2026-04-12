# ─────────────────────────────────────────────
#  MOCK DATA  –  MI vs RCB, April 12 2026
#  Match 20 | Wankhede Stadium, Mumbai
#  Simulated: 15.2 overs into MI's chase
# ─────────────────────────────────────────────

MI_VS_RCB_MOCK = {
    "match_id": "mock_mi_rcb_20260412",
    "match_name": "Mumbai Indians vs Royal Challengers Bengaluru",
    "short_name": "MI vs RCB",
    "team1": "Mumbai Indians",
    "team2": "Royal Challengers Bengaluru",
    "team1_short": "MI",
    "team2_short": "RCB",
    "venue": "Wankhede Stadium, Mumbai",
    "date": "2026-04-12",
    "match_type": "T20",
    "status": "MI need 46 runs in 28 balls",
    "toss": "RCB won the toss and elected to bat",

    # ── 1st Innings : RCB batting ──────────────────────
    "innings1": {
        "team": "Royal Challengers Bengaluru",
        "team_short": "RCB",
        "runs": 187,
        "wickets": 5,
        "overs": "20.0",
        "run_rate": 9.35,
        "batsmen": [
            {"name": "Faf du Plessis", "runs": 45, "balls": 31, "fours": 4, "sixes": 2, "status": "c Rohit b Bumrah"},
            {"name": "Virat Kohli",     "runs": 72, "balls": 49, "fours": 6, "sixes": 3, "status": "c Surya b Hardik"},
            {"name": "Rajat Patidar",   "runs": 28, "balls": 18, "fours": 3, "sixes": 1, "status": "b Boult"},
            {"name": "Glenn Maxwell",   "runs": 31, "balls": 17, "fours": 2, "sixes": 2, "status": "not out"},
            {"name": "Dinesh Karthik",  "runs": 8,  "balls": 5,  "fours": 1, "sixes": 0, "status": "not out"},
        ],
        "bowlers": [
            {"name": "Jasprit Bumrah",  "overs": 4, "runs": 28, "wickets": 2, "economy": 7.0},
            {"name": "Hardik Pandya",   "overs": 4, "runs": 42, "wickets": 1, "economy": 10.5},
            {"name": "Trent Boult",     "overs": 4, "runs": 35, "wickets": 1, "economy": 8.75},
            {"name": "Suryakumar Yadav","overs": 2, "runs": 24, "wickets": 0, "economy": 12.0},
            {"name": "Tilak Varma",     "overs": 4, "runs": 38, "wickets": 1, "economy": 9.5},
            {"name": "Krunal Pandya",   "overs": 2, "runs": 20, "wickets": 0, "economy": 10.0},
        ],
        "fall_of_wickets": [
            "51/1 (7.3 ov) - du Plessis",
            "112/2 (13.1 ov) - Kohli",
            "148/3 (16.4 ov) - Patidar",
            "175/4 (19.0 ov) - Siraj",
            "181/5 (19.3 ov) - Hazlewood",
        ],
    },

    # ── 2nd Innings : MI batting (ongoing) ─────────────
    "innings2": {
        "team": "Mumbai Indians",
        "team_short": "MI",
        "runs": 142,
        "wickets": 4,
        "overs": "15.2",
        "run_rate": 9.26,
        "target": 188,
        "required_run_rate": 9.86,
        "balls_remaining": 28,
        "runs_needed": 46,
        "batsmen": [
            {"name": "Rohit Sharma",     "runs": 58, "balls": 38, "fours": 6, "sixes": 3, "status": "c Maxwell b Siraj"},
            {"name": "Ishan Kishan",     "runs": 22, "balls": 15, "fours": 2, "sixes": 1, "status": "b Hazlewood"},
            {"name": "Suryakumar Yadav", "runs": 34, "balls": 22, "fours": 3, "sixes": 2, "status": "c Karthik b Chahal"},
            {"name": "Tilak Varma",      "runs": 12, "balls": 10, "fours": 1, "sixes": 0, "status": "run out (Maxwell)"},
            {"name": "Hardik Pandya",    "runs": 12, "balls": 8,  "fours": 1, "sixes": 1, "status": "batting*"},
            {"name": "Tim David",        "runs": 4,  "balls": 2,  "fours": 0, "sixes": 1, "status": "batting*"},
        ],
        "bowlers": [
            {"name": "Mohammad Siraj",   "overs": 3,   "runs": 28, "wickets": 1, "economy": 9.33},
            {"name": "Josh Hazlewood",   "overs": 3,   "runs": 22, "wickets": 1, "economy": 7.33},
            {"name": "Yuzvendra Chahal", "overs": 3,   "runs": 31, "wickets": 1, "economy": 10.33},
            {"name": "Glenn Maxwell",    "overs": 3,   "runs": 33, "wickets": 0, "economy": 11.0},
            {"name": "Alzarri Joseph",   "overs": 2,   "runs": 21, "wickets": 1, "economy": 10.5},
            {"name": "Virat Kohli",      "overs": 1.2, "runs": 7,  "wickets": 0, "economy": 5.25},
        ],
        "fall_of_wickets": [
            "47/1 (5.2 ov) - Kishan",
            "98/2 (10.4 ov) - Rohit",
            "118/3 (13.1 ov) - Surya",
            "130/4 (14.3 ov) - Tilak",
        ],
        "partnerships": {
            "current": {"bat1": "Hardik Pandya", "bat2": "Tim David", "runs": 16, "balls": 12},
        },
    },

    # ── Last 5 overs (over 11–15) ──────────────────────
    "last_5_overs": [
        {"over": 11, "runs": 9,  "wickets": 0, "balls": ["1","1","2","1","4","0"], "bowler": "Maxwell"},
        {"over": 12, "runs": 14, "wickets": 0, "balls": ["2","4","2","0","6","0"], "bowler": "Chahal"},
        {"over": 13, "runs": 7,  "wickets": 1, "balls": ["1","W","2","1","2","1"], "bowler": "Chahal"},
        {"over": 14, "runs": 5,  "wickets": 1, "balls": ["1","1","W","1","1","1"], "bowler": "Joseph"},
        {"over": 15, "runs": 10, "wickets": 0, "balls": ["1","4","1","2","2","0"], "bowler": "Hazlewood"},
    ],
}

# Mini list for /live command
MOCK_LIVE_MATCHES = [
    {
        "match_id": "mock_mi_rcb_20260412",
        "match_name": "MI vs RCB",
        "status": "Live • 15.2 Ov • MI 142/4 needs 46 in 28 balls",
        "score": "RCB 187/5 (20) | MI 142/4 (15.2)",
    },
    {
        "match_id": "mock_csk_kkr_20260412",
        "match_name": "CSK vs KKR",
        "status": "Today 3:30 PM IST • MA Chidambaram Stadium",
        "score": "Match starts soon",
    },
]


def get_mock_matches():
    return MOCK_LIVE_MATCHES


def get_mock_scorecard(match_id: str):
    if match_id == "mock_mi_rcb_20260412":
        return MI_VS_RCB_MOCK
    return None


def get_mock_last5overs(match_id: str):
    if match_id == "mock_mi_rcb_20260412":
        return MI_VS_RCB_MOCK["last_5_overs"]
    return []
