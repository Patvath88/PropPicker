import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from screener import build_screener

CSV_FILE = ROOT_DIR / "data" / "nba_player_game_logs.csv"
CSV_FILE.parent.mkdir(exist_ok=True)
CSV_URL = "https://raw.githubusercontent.com/Patvath88/PropPicker/main/data/nba_player_game_logs.csv"

st.set_page_config(layout="wide", page_title="NBA Prop Screener", page_icon="🏀")

# ===== Download CSV if needed =====
def update_csv_if_needed():
    need_download = False
    if not CSV_FILE.exists() or (time.time() - CSV_FILE.stat().st_mtime) > 86400:
        need_download = True
        st.info("Updating game logs...")
    if need_download:
        try:
            r = requests.get(CSV_URL)
            r.raise_for_status()
            CSV_FILE.write_bytes(r.content)
            st.success("Game logs updated!")
        except Exception as e:
            st.error(f"Failed to download CSV: {e}")
            st.stop()

update_csv_if_needed()

# ===== Load CSV =====
@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip().str.lower()
    for col in ['pts','reb','ast','3pm','mp','fg%','home','opp']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce') if col not in ['home','opp'] else df[col]
    return df

df = load_data()
if df.empty:
    st.stop()

# ===== Player Headshots =====
@st.cache_data(ttl=86400)
def get_headshot_url(player_name):
    """Return basketball-reference headshot URL for a player"""
    try:
        search_name = player_name.replace(" ", "-")
        url = f"https://www.basketball-reference.com/players/{search_name[0].lower()}/{search_name[:5].lower()}01.html"
        r = requests.get(url)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        img_tag = soup.find("img", {"itemprop": "image"})
        if img_tag and img_tag['src']:
            return img_tag['src']
    except:
        return None
    return None

# ===== UI =====
st.title("🏀 NBA Prop Screener")
st.markdown("Analyze players and trends with **predicted stats** and **confidence ratings**.")

prop = st.selectbox("Prop Type", ["PTS","REB","AST","3PM"])
line = st.number_input("Prop Line", value=20.5)
min_conf = st.slider("Min Confidence (%)", 0, 100, 60)
line_map = {prop: line}
upcoming_team_map = {}

# ===== Build Screener =====
screener = build_screener(df, line_map, upcoming_team_map=upcoming_team_map)
if screener.empty:
    st.info("No players meet criteria.")
    st.stop()

filtered = screener[(screener["prop_type"]==prop) & (screener["confidence"]>=min_conf)].sort_values("confidence",ascending=False)

st.markdown(f"### Players with {prop} ≥ {line} and confidence ≥ {min_conf}%")

# ===== Display Cards with Headshots =====
for idx in range(0, len(filtered), 3):
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if idx + i >= len(filtered):
            break
        player = filtered.iloc[idx+i]
        headshot_url = get_headshot_url(player['player'])
        with col:
            if headshot_url:
                st.image(headshot_url, width=120)
            st.markdown(f"### {player['player']}", unsafe_allow_html=True)
            st.metric(label=f"{prop} Line", value=f"{player['line']}")
            st.metric(label=f"Predicted {prop}", value=f"{player['prediction']}")
            st.metric(label="Confidence (%)", value=player['confidence'])
            st.markdown(f"""
            <div style="font-size:14px">
            **Avg Last 10 Games:** {player['avg_last_10']:.1f}  <br>
            **Hit Rate Last 10:** {player['hit_rate_last_10']:.0%}  <br>
            **Minutes Played Factor:** {player['mp_factor']*100:.0f}%  <br>
            **Efficiency Factor:** {player['eff_factor']*100:.0f}%  <br>
            **Home/Away Factor:** {player['home_away_factor']*100:.0f}%  <br>
            **H2H Factor:** {player['h2h_factor']*100:.0f}%
            </div>
            """, unsafe_allow_html=True)
