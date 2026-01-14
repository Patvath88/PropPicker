# app.py

# ======= Path Patch =======
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ======= Imports =======
import streamlit as st
import pandas as pd
from app.screener import build_screener  # Keep your screener logic here

# ======= Streamlit Config =======
st.set_page_config(layout="wide")

# ======= Data Loading from CSV =======
CSV_FILE = ROOT_DIR / "data" / "nba_player_stats.csv"

@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv(CSV_FILE)
    
    # Ensure numeric columns are correct
    numeric_cols = df.columns.drop(['Player', 'Pos', 'Tm', 'update_date'])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    
    # Optionally rename columns to match your screener
    df.rename(columns={
        "Player": "player",
        "Tm": "team",
        "PTS": "pts",
        "REB": "reb",
        "AST": "ast",
        "3P": "3pm",
        # Add any others needed by your screener
    }, inplace=True)
    
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
