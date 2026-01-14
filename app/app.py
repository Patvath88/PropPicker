# app.py

# ======= Path Patch =======
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ======= Imports =======
import streamlit as st
import pandas as pd
from app.screener import build_screener

# ======= Streamlit Config =======
st.set_page_config(layout="wide")

# ======= CSV Path =======
CSV_FILE = ROOT_DIR / "data" / "nba_player_stats.csv"
CSV_FILE.parent.mkdir(exist_ok=True)

# ======= Function to scrape Basketball-Reference =======
def scrape_bball_ref(season="2026"):
    st.info("Downloading NBA player stats from Basketball-Reference...")
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html"
    tables = pd.read_html(url)
    df = tables[0]
    df = df[df.Player != "Player"]  # Remove repeated header rows
    df.reset_index(drop=True, inplace=True)

    # Safely convert numeric columns
    cols_to_drop = [c for c in ['Player', 'Pos', 'Tm'] if c in df.columns]
    numeric_cols = df.columns.drop(cols_to_drop)
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Add update date
    df['update_date'] = datetime.today().strftime('%Y-%m-%d')

    # Save CSV
    df.to_csv(CSV_FILE, index=False)
    st.success(f"Downloaded and saved stats to {CSV_FILE}")
    return df

# ======= Data Loading with Daily Refresh =======
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
        # Safely convert numeric columns
        cols_to_drop = [c for c in ['Player', 'Pos', 'Tm', 'update_date'] if c in df.columns]
        numeric_cols = df.columns.drop(cols_to_drop)
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Rename columns to match screener expectations
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

# ======= UI =======
st.title("NBA Prop Screener (Basketball-Reference)")

prop = st.selectbox("Prop Type", ["PTS", "REB", "AST", "3PM", "PRA", "PR", "PA", "RA"])
line = st.number_input("Prop Line", value=20.5)
min_score = st.slider("Min Confidence", 0, 100, 60)

line_map = {prop: line}

screener = build_screener(df, line_map)

filtered = screener[
    (screener["prop_type"] == prop) &
    (screener["confidence"] >= min_score)
].sort_values("confidence", ascending=False)

# ======= Display Results =======
for _, r in filtered.iterrows():
    st.markdown(f"""
    **{r['player']}**  
    {r['prop_type']} {r['line']}  
    Avg L10: {r['avg_last_10']:.1f}  
    Hit Rate L10: {r['hit_rate_last_10']:.0%}  
    Confidence: {r['confidence']}
    """)
