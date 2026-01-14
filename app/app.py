# ======= Path Patch =======
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ======= Imports =======
import streamlit as st
from data.nba_loader import load_all_player_games
from app.screener import build_screener

# ======= Streamlit Config =======
st.set_page_config(layout="wide")

# ======= Data Loading =======
@st.cache_data(ttl=86400)
def load_data():
    return load_all_player_games()

df = load_data()

# ======= UI =======
st.title("NBA Prop Screener")

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
