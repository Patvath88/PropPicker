# scripts/update_daily_nba_stats.py

import pandas as pd
from pathlib import Path
from datetime import datetime

# Output CSV path
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "nba_player_stats.csv"
OUTPUT_FILE.parent.mkdir(exist_ok=True)

# NBA season (adjust dynamically if needed)
current_season = "2026"  # e.g., 2025-26 season -> 2026

# Basketball-Reference per-game stats URL
url = f"https://www.basketball-reference.com/leagues/NBA_{current_season}_per_game.html"

print("Fetching NBA player stats from Basketball-Reference...")
tables = pd.read_html(url)
df = tables[0]

# Remove repeated header rows
df = df[df.Player != "Player"]

# Reset index
df.reset_index(drop=True, inplace=True)

# Convert numeric columns
numeric_cols = df.columns.drop(['Player', 'Pos', 'Tm'])
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

# Optional: Add date of update
df['update_date'] = datetime.today().strftime('%Y-%m-%d')

# Save CSV
df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved NBA player stats to {OUTPUT_FILE}")
