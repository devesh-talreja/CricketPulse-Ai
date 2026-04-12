import streamlit as st
import asyncio
import sys

# Windows compatibility for asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import data_bridge
import utils
import agent_brain
from win_probability import calculate_win_probability

st.set_page_config(page_title="CricketPulse War Room", layout="wide", page_icon="🏏")

# Neon Dark Mode CSS
st.markdown("""
    <style>
    /* Global Background and Neon Fonts */
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
    }
    h1, h2, h3 {
        color: #66fcf1 !important;
        text-shadow: 0 0 10px #66fcf1, 0 0 20px #45a29e;
    }
    
    /* Metrics Neon Styling */
    [data-testid="stMetricValue"] {
        color: #ff3366 !important;
        text-shadow: 0 0 8px #ff3366;
    }
    [data-testid="stMetricLabel"] {
        color: #45a29e !important;
        font-weight: bold;
    }
    
    /* Coach's Info Box */
    .stAlert {
        background-color: rgba(102, 252, 241, 0.1) !important;
        border: 1px solid #66fcf1;
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #1f2833;
        color: #66fcf1;
        border: 2px solid #66fcf1;
        box-shadow: 0 0 5px #66fcf1;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #66fcf1;
        color: #0b0c10;
        box-shadow: 0 0 15px #66fcf1;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #ff3366, #66fcf1);
    }
    
    /* Text Area (Sledge Wall) */
    textarea {
        background-color: #1f2833 !important;
        color: #66fcf1 !important;
        border: 1px solid #66fcf1 !important;
    }
    </style>
""", unsafe_allow_html=True)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

st.title("🏏 CricketPulse: AI Strategy War Room")

# Session state for Sledge Wall history
if "sledges" not in st.session_state:
    st.session_state.sledges = []

@st.cache_data(ttl=90)
def sync_live_data():
    async def _fetch():
        matches = await data_bridge.get_live_matches()
        if not matches: return None, None
        m = matches[0]
        mid = m.get("match_id", "")
        sc = await data_bridge.get_scorecard(mid) if mid else m
        last5 = await data_bridge.get_last_5_overs(mid) if mid else []
        return sc, last5
    return loop.run_until_complete(_fetch())

@st.cache_data(ttl=90)
def get_ai_context():
    async def _fetch_ai():
        return {
            "predict": await agent_brain.analyze_predict("STRATEGY"),
            "coach": await agent_brain.analyze_coach("STRATEGY"),
            "meme": await agent_brain.process_message("Meme roast karo", "MEME")
        }
    return loop.run_until_complete(_fetch_ai())

# -- Auto-Refresh Button Logic --
col_l, col_r = st.columns([8, 2])
with col_r:
    if st.button("🚀 Refresh Intelligence"):
        st.cache_data.clear()
        
sc, last5 = sync_live_data()
ai_data = get_ai_context()

# Ensure current sledge is tracked
if not st.session_state.sledges or st.session_state.sledges[-1] != ai_data["meme"]:
    st.session_state.sledges.append(ai_data["meme"])
if len(st.session_state.sledges) > 5:
    st.session_state.sledges.pop(0)

if not sc:
    st.warning("No live matches available.")
    st.stop()

# ----- 3 COLUMN LIVE STATS -----
st.markdown("### 📊 Live Operations")
col1, col2, col3 = st.columns(3)

i1 = sc.get("innings1") or {}
i2 = sc.get("innings2") or {}
active = i2 if (i2 and i2.get("runs") is not None) else i1
team = active.get("team_short", "BAT")
runs = active.get("runs", 0)
wkts = active.get("wickets", 0)
ovs  = active.get("overs", 0)
crr  = float(active.get("run_rate", 8.0) or 0.0)

rrr = i2.get("required_run_rate", "-") if active == i2 else "-"
proj = int(round((crr / 6.0) * 120)) if active == i1 else i2.get("target", "-")

col1.metric("Current Score", f"{team} {runs}/{wkts}", f"{ovs} Ovs")
col2.metric("Required RR" if active == i2 else "Current RR", rrr if active == i2 else f"{crr:.2f}")
col3.metric("Projected Total" if active == i1 else "Target Score", proj)

st.divider()

# ----- IN-DEPTH MATCHUP & MOMENTUM (Zero AI Limit Features) -----
colA, colB = st.columns([1.5, 1])

with colA:
    st.markdown("#### 🤺 Active Matchup")
    batters = [b for b in active.get("batsmen", []) if "batting*" in b.get("status", "")]
    if batters:
        bcols = st.columns(len(batters))
        for idx, b in enumerate(batters):
            sr = round(b.get("sr") or (b.get("runs",0)/max(b.get("balls",1),1)*100), 1)
            bcols[idx].metric(f"🏏 {b['name']}", f"{b.get('runs',0)} ({b.get('balls',0)}b)", f"SR: {sr}", delta_color="off")
    
    bowlers = sorted(i2.get("bowlers", []) if active == i2 else i1.get("bowlers", []), 
                     key=lambda x: (x.get("wickets", 0), -x.get("economy", 99)), reverse=True)
    if bowlers:
        bw = bowlers[0]
        st.metric(f"🎳 {bw['name']} (Attack)", f"{bw.get('wickets',0)}/{bw.get('runs',0)}", f"Eco: {bw.get('economy',0)}", delta_color="inverse")

with colB:
    st.markdown("#### 📈 Over-by-Over Worm")
    if last5:
        import pandas as pd
        over_nums = [f"Ov {o.get('over','')}" for o in last5]
        runs_per_ov = [int(o.get('runs',0)) for o in last5]
        df = pd.DataFrame({"Runs": runs_per_ov}, index=over_nums)
        st.bar_chart(df, height=180, use_container_width=True)
    else:
        st.info("Awaiting over data...")

# Raw Terminal view for deep detail ("how it was before")
with st.expander("📟 Raw Telemetry Feed (Classic View)", expanded=False):
    dash = utils.format_match_dashboard(sc, last5)
    dash = dash.replace("<b>", "**").replace("</b>", "**").replace("<i>", "*").replace("</i>", "*")
    dash = dash.replace("<code>", "").replace("</code>", "")
    st.code(dash, language="markdown")

st.divider()

# ----- PANIC METER -----
st.markdown("### 🚨 The Panic Meter (Win Probability)")
bat = active.get("team_short", "BAT")
bwl = i1.get("team_short", "BWL") if active == i2 else "BWL"
target = i2.get("target", 180) if active == i2 else 180

try:
    wp = calculate_win_probability(target, runs, wkts, ovs)
    batting_pct = wp["batting_team_pct"]
except Exception:
    batting_pct = 50.0

cols = st.columns([1, 10, 1])
cols[0].markdown(f"**{bat}**")
cols[1].progress(int(batting_pct))
cols[2].markdown(f"**{bwl}**")
st.caption(f"📈 {bat} Momentum: **{batting_pct}%**")

# ----- AI COACH'S CORNER -----
st.markdown("### 🗣️ AI Coach's Corner")
# Convert HTML to Markdown
coach_nudge = ai_data['coach'].replace("<b>", "**").replace("</b>", "**").replace("<i>", "*").replace("</i>", "*")
st.info(f"**Tactical Nudge in Play:**\n\n{coach_nudge}")

st.markdown("---")

# ----- LOWER SECTION -----
c_left, c_right = st.columns(2)

with c_left:
    st.markdown("### 😂 The Sledge Wall")
    sledge_text = "\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join([f"🔥 {m}" for m in reversed(st.session_state.sledges)])
    sledge_text = sledge_text.replace("<b>", "**").replace("</b>", "**")
    st.text_area("Last 5 Generated Roasts", value=sledge_text, height=250, disabled=True)

with c_right:
    st.markdown("### 🦋 What-If Sandbox")
    st.caption("Change the timeline. Gemini AI will evaluate the fallout.")
    sim_prompt = st.text_input("Enter Scenario:", placeholder="What if Maxwell hits consecutive sixes here?")
    if st.button("🔮 Simulate Scenario"):
        if sim_prompt:
            with st.spinner("Calculating Alternative Timeline..."):
                async def _run_sim():
                    return await agent_brain.process_message(f"/simulate {sim_prompt}", "STRATEGY")
                result = loop.run_until_complete(_run_sim())
                result = result.replace("<b>", "**").replace("</b>", "**").replace("<i>", "*").replace("</i>", "*")
                st.success(result)
        else:
            st.error("Please enter a scenario first.")
