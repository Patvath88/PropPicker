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

# ===== Player Headshots & BRef URL =====
@st.cache_data(ttl=86400)
def get_player_info(player_name):
    """Return headshot URL and Basketball-Reference URL"""
    try:
        search_name = player_name.replace(" ", "-")
        player_url = f"https://www.basketball-reference.com/players/{search_name[0].lower()}/{search_name[:5].lower()}01.html"
        r = requests.get(player_url)
        if r.status_code != 200:
            return None, None
        soup = BeautifulSoup(r.text, 'html.parser')
        img_tag = soup.find("img", {"itemprop": "image"})
        headshot_url = img_tag['src'] if img_tag else None
        return headshot_url, player_url
    except:
        return None, None

# ===== Sidebar Key =====
with st.sidebar:
    st.header("Metrics Key")
    st.markdown("""
    **Minutes Played Factor (MP Factor):** Percentage of average minutes played over last 10 games compared to 30 MPG.  
    **Efficiency Factor:** Player's efficiency based on shooting (FG%) over last 10 games.  
    **Home/Away Factor:** Performance adjustment based on whether games were home or away.  
    **H2H Factor:** Performance adjustment vs upcoming opponent based on last 10 matchups.  
    **Confidence:** Weighted probability of hitting the line, combining all factors, streaks, averages, and hit rate.
    """)

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

# ===== Helper: Confidence Color =====
def confidence_color(conf):
    if conf >= 75:
        return "#4CAF50"  # Green
    elif conf >= 50:
        return "#FFEB3B"  # Yellow
    else:
        return "#F44336"  # Red

# ===== Display Premium Cards =====
for idx in range(0, len(filtered), 3):
    cols = st.columns(3, gap="small")
    for i, col in enumerate(cols):
        if idx + i >= len(filtered):
            break
        player = filtered.iloc[idx+i]
        headshot_url, bref_url = get_player_info(player['player'])
        conf_color = confidence_color(player['confidence'])

        # Generate AI description
        ai_desc = (f"{player['player']} has averaged {player['avg_last_10']:.1f} {prop.lower()} over "
                   f"the last 10 games while playing {player['mp_factor']*30:.0f} MPG. "
                   f"Against their upcoming opponent, performance metrics suggest high likelihood to hit the line.")

        card_html = f"""
        <div style="
            border:2px solid #ccc; 
            border-radius:12px; 
            padding:12px; 
            margin-bottom:10px; 
            text-align:center;
            background-color:#f9f9f9;
            box-shadow: 3px 3px 8px rgba(0,0,0,0.15);
            ">
            {'<a href="'+bref_url+'" target="_blank">' if bref_url else ''}
            {'<img src="'+headshot_url+'" width="100" style="border-radius:50%; margin-bottom:10px;">' if headshot_url else ''}
            {'</a>' if bref_url else ''}
            <h3 style="margin:5px 0">{player['player']}</h3>
            <div style="font-size:14px; margin-bottom:5px">
            <b>{prop} Line:</b> {player['line']}<br>
            <b>Predicted {prop}:</b> {player['prediction']}<br>
            <b>Confidence:</b> <span style="color:{conf_color};">{player['confidence']}%</span><br>
            <b>Minutes Played Factor:</b> {player['mp_factor']*100:.0f}%<br>
            <b>Efficiency Factor:</b> {player['eff_factor']*100:.0f}%<br>
            <b>Home/Away Factor:</b> {player['home_away_factor']*100:.0f}%<br>
            <b>H2H Factor:</b> {player['h2h_factor']*100:.0f}%
            </div>
            <div style="font-size:13px; color:#555; margin-top:6px; border-top:1px solid #ddd; padding-top:4px;">
            {ai_desc}
            </div>
        </div>
        """
        col.markdown(card_html, unsafe_allow_html=True)
