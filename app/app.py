# app.py
import sys
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from app.screener import build_screener

# ===== Paths =====
ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT_DIR / "data" / "nba_player_game_logs.csv"
CSV_FILE.parent.mkdir(exist_ok=True)

# ===== Streamlit config =====
st.set_page_config(layout="wide", page_title="NBA Prop Screener", page_icon="🏀")

# ===== Load CSV =====
@st.cache_data(ttl=86400)
def load_data():
    if not CSV_FILE.exists():
        st.error("Game log CSV not found. Run `scripts/scrape_nba_game_logs.py` first.")
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE)
    for col in ['PTS','TRB','AST','3P','MP']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

df = load_data()
if df.empty:
    st.stop()

# ===== UI =====
st.title("🏀 NBA Prop Screener")
st.markdown("Analyze players and their trends with confidence ratings and streaks.")

prop = st.selectbox("Prop Type", ["PTS","REB","AST","3PM"])
line = st.number_input("Prop Line", value=20.5)
min_conf = st.slider("Min Confidence (%)", 0, 100, 60)
line_map = {prop: line}

upcoming_team_map = {}

# Build screener
screener = build_screener(df, line_map, upcoming_team_map=upcoming_team_map)

# Filter results
filtered = screener[(screener["prop_type"]==prop) & (screener["confidence"]>=min_conf)].sort_values("confidence",ascending=False)

# ===== Display Premium Player Cards =====
st.markdown(f"### Players with {prop} ≥ {line} and confidence ≥ {min_conf}%")

if filtered.empty:
    st.info("No players meet the criteria.")
else:
    for idx in range(0, len(filtered), 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if idx+i >= len(filtered):
                break
            player = filtered.iloc[idx+i]
            with col:
                st.markdown(f"### {player['player']}")
                st.metric(label=f"{prop} Line", value=f"{player['line']}")
                st.metric(label="Confidence (%)", value=player['confidence'])
                st.markdown(f"**Avg Last 10 Games:** {player['avg_last_10']:.1f}")
                st.markdown(f"**Hit Rate Last 10:** {player['hit_rate_last_10']:.0%}")
                st.markdown(f"**Longest Streak:** {player['streak_count']} games")
                st.markdown(f"**Total Hits:** {player['season_hit_count']}")
                st.markdown(f"**MP Factor:** {player['mp_factor']:.2f}")
                st.markdown(f"**Efficiency Factor:** {player['eff_factor']:.2f}")
                st.markdown(f"**Home/Away Factor:** {player['home_away_factor']:.2f}")
                st.markdown(f"**H2H Factor:** {player['h2h_factor']:.2f}")
