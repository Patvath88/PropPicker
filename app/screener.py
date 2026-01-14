# screener.py
import pandas as pd

def build_screener(df: pd.DataFrame, line_map: dict, upcoming_team_map: dict = None) -> pd.DataFrame:
    """
    Build a prop screener with more realistic confidence calculation.
    
    Parameters:
    - df: DataFrame with player stats (must have 'player', prop numeric columns)
    - line_map: dict of prop_type -> line value
    - upcoming_team_map: optional dict of player -> opponent team (for head-to-head adjustment)
    
    Returns:
    - DataFrame with player, prop_type, line, avg_last_10, hit_rate_last_10, confidence
    """

    # Detect player column
    possible_player_cols = ['player', 'PLAYER_NAME', 'Player', 'NAME']
    player_col = next((c for c in possible_player_cols if c in df.columns), None)
    if not player_col:
        raise ValueError("No player column found in DataFrame")

    records = []

    for player, pdf in df.groupby(player_col):
        for prop, line in line_map.items():
            # Map prop names to column names
            col_map = {
                "PTS": "pts",
                "REB": "reb",
                "AST": "ast",
                "3PM": "3pm"
            }
            col_name = col_map.get(prop, prop)

            if col_name not in pdf.columns:
                continue

            # Last 10 games
            last_10 = pdf[col_name].tail(10)
            avg_last_10 = last_10.mean()
            hit_rate_last_10 = (last_10 >= line).mean()  # fraction of times line was hit

            # Optional: home/away adjustment
            home_away_factor = 1.0
            if 'Home' in pdf.columns:
                last_10_home = pdf[col_name].tail(10)[pdf['Home'].tail(10) == True]
                last_10_away = pdf[col_name].tail(10)[pdf['Home'].tail(10) == False]
                if len(last_10_home) >= 3:
                    home_away_factor = last_10_home.mean() / max(avg_last_10, 1)
                elif len(last_10_away) >= 3:
                    home_away_factor = last_10_away.mean() / max(avg_last_10, 1)

            # Optional: head-to-head adjustment
            h2h_factor = 1.0
            if upcoming_team_map and player in upcoming_team_map:
                opponent = upcoming_team_map[player]
                if 'Opp' in pdf.columns:
                    h2h_games = pdf[col_name][pdf['Opp'] == opponent].tail(5)
                    if len(h2h_games) > 0:
                        h2h_factor = h2h_games.mean() / max(avg_last_10, 1)

            # Weighted confidence calculation
            weighted_hit_rate = hit_rate_last_10 * 0.6 + (avg_last_10 / line) * 0.2 + home_away_factor * 0.1 + h2h_factor * 0.1
            weighted_hit_rate = min(max(weighted_hit_rate, 0), 1)  # clamp between 0 and 1
            confidence = round(weighted_hit_rate * 100)

            records.append({
                "player": player,
                "prop_type": prop,
                "line": line,
                "avg_last_10": avg_last_10,
                "hit_rate_last_10": hit_rate_last_10,
                "confidence": confidence
            })

    return pd.DataFrame(records)
