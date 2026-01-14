# screener.py

import pandas as pd

def build_screener(df: pd.DataFrame, line_map: dict) -> pd.DataFrame:
    # Auto-detect player column
    possible_player_cols = ['player', 'PLAYER_NAME', 'Player', 'NAME']
    player_col = next((c for c in possible_player_cols if c in df.columns), None)
    
    if not player_col:
        raise ValueError("No player column found in the DataFrame")

    records = []
    for player, pdf in df.groupby(player_col):
        for prop, line in line_map.items():
            # Map prop names to your column names if needed
            col_map = {
                "PTS": "pts",
                "REB": "reb",
                "AST": "ast",
                "3PM": "3pm"
            }
            col_name = col_map.get(prop, prop)

            if col_name not in pdf.columns:
                continue

            last_10 = pdf[col_name].tail(10)
            avg_last_10 = last_10.mean()
            hit_rate_last_10 = (last_10 >= line).mean()
            confidence = int(hit_rate_last_10 * 100)

            records.append({
                "player": player,
                "prop_type": prop,
                "line": line,
                "avg_last_10": avg_last_10,
                "hit_rate_last_10": hit_rate_last_10,
                "confidence": confidence
            })

    return pd.DataFrame(records)

