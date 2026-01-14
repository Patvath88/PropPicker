# main.py
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import subprocess
import time

# ===== Add app folder to path for imports =====
ROOT_DIR = Path(__file__).resolve().parents[1]  # proppicker/
sys.path.append(str(ROOT_DIR / "app"))

from screener import build_screener

# ===== Paths =====
CSV_FILE = ROOT_DIR / "app" / "data" / "nba_player_game_logs.csv"
SCRAPER_FILE = ROOT_DIR / "scripts" / "scrape_nba_game_logs.py"

# ===== Streamlit config =====
st.set_page_config(layout="wide", page_title="NBA Prop Screener", page_icon="🏀")

# ===== Debugging paths =====
st.write("CSV path:", CSV_FILE)
st.write("CSV exists?", CSV_FILE.exists())
st.write("Scraper path:", SCRAPER_FILE)
st.write("Scraper exists?", SCRAPER_FILE.exists())

# ===== Scraper helper =====
def update_csv_if_needed():
    """Check if CSV exists or is older than 24h and run scraper if needed"""
    need_scrape = False
    if not CSV_FILE.exists():
        need_scrape = True
        st.info("Game logs not found. Scraping now...")
    else:
        modified_time = CSV_FILE.stat().st_mtime
        if (time.time() - modified_time) > 86400:  # older than 24h
            need_scrape = True
            st.info("Game logs are outdated. Updating now...")

    if need_scrape:
        if not SCRAPER_FILE.exists():
            st.error("Scraper not found! Please make sure 'scrape_nba_game_logs.py' exists.")
            return
        try:
            with st.spinner("Downloading NBA game logs..."):
                subprocess.run([sys.executable, str(SCRAPER_FILE)], check=True)
            st.success("Game logs updated successfully!")
        except subprocess.CalledProcessError:
            st.error("Scraper failed! Please run manually.")

# ===== Load CSV =====
@st.cache_data(ttl=86400)
def load_data():
    if not CSV_FILE.exists():
        st.warning("No game logs found. Please run scraper first.")
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE)
    # Ensure numeric columns
    for col in ['PTS','REB','AST','3PM','MP','FG%']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# ===== Ensure CSV is up-to-date =====
update_csv_if_needed()

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
upcoming_team_map = {}  # optional H2H mapping

# Build screener
screener = build_screener(df, line_map, upcoming_team_map=upcoming_team_map)

# Filter results
filtered = screener[(screener["prop_type"]==prop) & (screener["confidence"]>=min_conf)].sort_values("confidence",ascending=False)

# ===== Display Player Cards =====
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
