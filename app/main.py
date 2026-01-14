import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import time
import requests

ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))
from screener import build_screener

CSV_FILE = ROOT_DIR / "data" / "nba_player_game_logs.csv"
CSV_FILE.parent.mkdir(exist_ok=True)
CSV_URL = "https://raw.githubusercontent.com/Patvath88/PropPicker/main/data/nba_player_game_logs.csv"

st.set_page_config(layout="wide", page_title="NBA Prop Screener", page_icon="🏀")

def update_csv_if_needed():
    if not CSV_FILE.exists() or (time.time() - CSV_FILE.stat().st_mtime) > 86400:
        try:
            r = requests.get(CSV_URL)
            r.raise_for_status()
            CSV_FILE.write_bytes(r.content)
            st.success("Game logs updated!")
        except Exception as e:
            st.error(f"Failed to download CSV: {e}")
            st.stop()

update_csv_if_needed()

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

# Example upcoming opponents
upcoming_team_map = {
    "Donovan Mitchell": "MIL",
    "Luka Doncic": "PHI",
}

# Example defensive ratings
def_ratings = {
    "MIL": {"overall":0.98,"PG":0.95,"SG":1.02,"SF":0.99,"PF":1.03,"C":0.98},
    "PHI": {"overall":0.99,"PG":1.01,"SG":1.00,"SF":0.97,"PF":1.05,"C":0.99},
}

def get_player_headshot(player_name):
    names = player_name.split()
    if len(names) < 2:
        return None
    first, last = names[0], names[-1]
    player_id = f"{last[:5].lower()}{first[:2].lower()}01"
    return f"https://www.basketball-reference.com/req/202301121/images/players/{player_id}.jpg"

with st.sidebar:
    st.header("Metrics Key")
    st.markdown("""
    **Minutes Played Factor (MP Factor):** % of average minutes played over last 10 games vs 30 MPG.  
    **Efficiency Factor:** Shooting efficiency (FG%) over last 10 games.  
    **Home/Away Factor:** Adjustment based on whether recent games were home or away.  
    **H2H Factor:** Adjustment based on last 10 games vs upcoming opponent.  
    **Opponent Defense Factor:** Opponent's defensive rating vs player's position.  
    **Confidence:** Weighted probability of hitting the line based on all factors.
    """)

st.title("🏀 NBA Prop Screener")
st.markdown("Analyze players with **predicted stats**, **confidence ratings**, **AI insights**, and **upcoming opponent matchups**.")

prop = st.selectbox("Prop Type", ["PTS","REB","AST","3PM"])
line = st.number_input("Prop Line", value=20.5)
min_conf = st.slider("Min Confidence (%)", 0, 100, 60)

line_map = {prop: line}
screener = build_screener(df, line_map, upcoming_team_map=upcoming_team_map, def_ratings=def_ratings)
filtered = screener[(screener["prop_type"]==prop) & (screener["confidence"]>=min_conf)].sort_values("confidence",ascending=False)

# Player search
search_name = st.text_input("Search Player by Name", "")
if search_name.strip():
    filtered = filtered[filtered['player'].str.contains(search_name.strip(), case=False, na=False)]

if filtered.empty:
    st.info("No players meet criteria.")
    st.stop()

st.markdown(f"### Players with {prop} ≥ {line} and confidence ≥ {min_conf}%")

def confidence_color(conf):
    if conf >= 75:
        return "#4CAF50"
    elif conf >= 50:
        return "#FFEB3B"
    else:
        return "#F44336"

for idx in range(0, len(filtered), 3):
    cols = st.columns(3, gap="small")
    for i, col in enumerate(cols):
        if idx+i >= len(filtered):
            break
        player = filtered.iloc[idx+i]
        headshot_url = get_player_headshot(player['player'])
        conf_color = confidence_color(player['confidence'])
        ai_desc = (
            f"{player['player']} has averaged {player['avg_last_10']:.1f} {prop.lower()} "
            f"over the last 10 games while playing {player['mp_factor']*30:.0f} MPG. "
            f"Next up: {player['upcoming_opp']}. "
            f"The team has an overall defensive rating of {player['opp_def_overall']*100:.0f}% "
            f"and a positional defense rating of {player['opp_factor']*100:.0f}% against {player['position']}. "
            f"Based on recent form and matchup metrics, they have a high likelihood to hit their line."
        )

        card_html = f"""
        <div style="border:2px solid #ccc; border-radius:12px; padding:12px; margin-bottom:10px;
                    text-align:center; background:linear-gradient(145deg,#fff,#f2f2f2); color:#111;
                    box-shadow:3px 3px 15px rgba(0,0,0,0.15); font-family:Arial, sans-serif;">
            <h3 style="margin:5px 0; font-weight:bold; color:#222;">{player['player']}</h3>
            {'<img src="'+headshot_url+'" width="100" style="border-radius:50%; margin-bottom:5px;">' if headshot_url else ''}
            <div style="font-size:14px; font-weight:bold; margin-bottom:10px; color:#555;">{player['team']}</div>
            <div style="font-size:14px; margin-bottom:5px; color:#111;">
                <b>{prop} Line:</b> {player['line']}<br>
                <b>Predicted {prop}:</b> {player['prediction']}<br>
                <b>Confidence:</b> <span style="color:{conf_color};">{player['confidence']}%</span><br>
                <b>Minutes Played
