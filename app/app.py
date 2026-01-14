# app.py

import sys
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from app.screener import build_screener

# ===== Path setup =====
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ===== Streamlit config =====
st.set_page_config(layout="wide", page_title="NBA Prop Screener")

# ===== CSV path =====
CSV_FILE = ROOT_DIR / "data" / "nba_player_stats.csv"
CSV_FILE.parent.mkdir(exist_ok=True)

# ===== Scrape Basketball-Reference =====
def scrape_bball_ref(season="2026"):
    st.info("Downloading NBA player stats from Basketball-Reference...")
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html"
    tables = pd.read_html(url)
    df = tables[0]
    df = df[df.Player != "Player"]
    df.reset_index(drop=True, inplace=True)

    # Numeric conversion
    cols_to_drop = [c for c in ['Player', 'Pos', 'Tm'] if c in df.columns]
    numeric_cols = df.columns.drop(cols_to_drop)
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Add update date
    df['update_date'] = datetime.today().strftime('%Y-%m-%d')

    df.to_csv(CSV_FILE, index=False)
    st.success(f"Saved stats to {CSV_FILE}")
    return df

# ===== Load Data =====
@st.cache_data(ttl=86400)
def load_data():
    need_refresh = True
    if CSV_FILE.exists():
        modified_time = datetime.fromtimestamp(CSV_FILE.stat().st_mtime)
        if datetime.now() - modified_time < timedelta(hours=24):
            need_refresh = False

    if need_refresh:
        df = scrape_bball_ref()
    else:
        df = pd.read_csv(CSV_FILE)
        cols_to_drop = [c for c in ['Player', 'Pos', 'Tm', 'update_date'] if c in df.columns]
        numeric_cols = df.columns.drop(cols_to_drop)
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    rename_map = {}
    if 'Player' in df.columns:
        rename_map['Player'] = 'player'
    if 'Tm' in df.columns:
        rename_map['Tm'] = 'team'
    if 'PTS' in df.columns:
        rename_map['PTS'] = 'pts'
    if 'TRB' in df.columns:
        rename_map['TRB'] = 'reb'
    if 'AST' in df.columns:
        rename_map['AST'] = 'ast'
    if '3P' in df.columns:
        rename_map['3P'] = '3pm'
    df.rename(columns=rename_map, inplace=True)

    return df

df = load_data()

# ===== UI =====
st.title("NBA Prop Screener (Basketball-Reference)")

prop = st.selectbox("Prop Type", ["PTS", "REB", "AST", "3PM"])
line = st.number_input("Prop Line", value=20.5)
min_conf = st.slider("Min Confidence (%)", 0, 100, 60)

line_map = {prop: line}

# Optional upcoming team mapping for H2H
upcoming_team_map = {}  # e.g., {"LeBron James":"GSW"}

# Build screener
screener = build_screener(df, line_map, upcoming_team_map=upcoming_team_map, debug=False)

# Filter results
filtered = screener[
    (screener["prop_type"] == prop) &
    (screener["confidence"] >= min_conf)
].sort_values("confidence", ascending=False)

# ===== Display Results =====
st.markdown(f"### Players with {prop} line ≥ {line} and confidence ≥ {min_conf}%")
if filtered.empty:
    st.info("No players meet the criteria.")
else:
    # Mobile-friendly table
    display_cols = [
        "player","line","confidence",
        "avg_last_10","hit_rate_last_10",
        "streak_count","season_hit_count",
        "mp_factor","eff_factor","home_away_factor","h2h_factor"
    ]
    st.dataframe(filtered[display_cols].reset_index(drop=True), use_container_width=True)

    # Optional: expandable per-player details
    for _, row in filtered.iterrows():
        with st.expander(f"{row['player']} details"):
            st.write({
                "Line": row['line'],
                "Confidence (%)": row['confidence'],
                "Avg Last 10 Games": row['avg_last_10'],
                "Hit Rate Last 10": f"{row['hit_rate_last_10']:.0%}",
                "Streak Count": row['streak_count'],
                "Season Hit Count": row['season_hit_count'],
                "Minutes Factor": row['mp_factor'],
                "Efficiency Factor": row['eff_factor'],
                "Home/Away Factor": row['home_away_factor'],
                "H2H Factor": row['h2h_factor']
            })
