import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import re
from pathlib import Path

SEASON = 2026
OUTPUT_FILE = Path("data/nba_player_game_logs.csv")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

# Step 1: Get list of all players
players_url = f"https://www.basketball-reference.com/leagues/NBA_{SEASON}_per_game.html"
tables = pd.read_html(players_url)
df_players = tables[0]
df_players = df_players[df_players.Player != "Player"]

# Extract player names and BBRef IDs
players = []
for _, row in df_players.iterrows():
    player_name = row['Player']
    link_tag = row['Player']
    # Build BBRef player ID: e.g., LeBron James -> jamesle01
    # We'll scrape from the player index pages instead to get correct IDs
    players.append(player_name)

# Step 2: Scrape player index to get IDs
index_url = "https://www.basketball-reference.com/players/"
player_ids = {}

for letter in "abcdefghijklmnopqrstuvwxyz":
    url = f"https://www.basketball-reference.com/players/{letter}/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.select("th a[href^='/players/']"):
        pid = a['href'].split("/")[3].replace(".html","")
        name = a.text.strip()
        if name in players:
            player_ids[name] = pid

# Step 3: Scrape game logs
all_games = []

for player, pid in tqdm(player_ids.items(), desc="Scraping players"):
    url = f"https://www.basketball-reference.com/players/{pid[0]}/{pid}/gamelog/{SEASON}"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="pgl_basic")
    if table is None:
        continue
    df = pd.read_html(str(table))[0]
    df = df[df.Rk != 'Rk']  # remove repeated headers
    df = df[df['G'] != '']   # drop empty rows

    # Clean numeric columns
    for col in ['PTS','TRB','AST','3P','MP']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Home/Away
    df['Home'] = df['Unnamed: 5'].apply(lambda x: True if x != '@' else False) if 'Unnamed: 5' in df.columns else True

    # Opponent
    df['Opp'] = df['Opp']

    df['player'] = player
    all_games.append(df[['player','Date','PTS','TRB','AST','3P','MP','Home','Opp']])

    time.sleep(1)  # polite scraping

# Step 4: Combine and save
game_logs = pd.concat(all_games, ignore_index=True)
game_logs.to_csv(OUTPUT_FILE, index=False)
print(f"Saved {len(game_logs)} games to {OUTPUT_FILE}")
