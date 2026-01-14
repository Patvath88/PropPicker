# screener.py
import pandas as pd

def build_screener(df: pd.DataFrame, line_map: dict, upcoming_team_map: dict = None, debug: bool = False) -> pd.DataFrame:
    """
    Build a prop screener with realistic confidence levels, streak count, and season hit count.

    Parameters:
    - df: DataFrame with player stats (must have 'player' or similar column, prop numeric columns)
    - line_map: dict of prop_type -> line value
    - upcoming_team_map: optional dict of player -> opponent team (for head-to-head adjustment)
    - debug: if True, prints all intermediate calculations for each player

    Returns:
    - DataFrame with player, prop_type, line, avg_last_10, hit_rate_last_10, streak_count, season_hit_count, confidence
    """

    # 1️⃣ Detect player column automatically
    possible_player_cols = ['player', 'PLAYER_NAME', 'Player', 'NAME']
    player_col = next((c for c in possible_player_cols if c in df.columns), None)
    if not player_col:
        raise ValueError("No player column found in DataFrame")

    records = []

    # 2️⃣ Iterate over players
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

            # Ensure numeric values
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce')
            last_10 = pdf[col_name].tail(10).dropna()
            full_season = pdf[col_name].dropna()

            # 3️⃣ Safely calculate averages
            if len(last_10) == 0:
                avg_last_10 = 0
                hit_rate_last_10 = 0
            else:
                avg_last_10 = last_10.mean()
                hit_rate_last_10 = (last_10 >= line).mean()

            # 4️⃣ Home/Away adjustment (optional)
            home_away_factor = 1.0
            if 'Home' in pdf.columns:
                last_10_home = last_10[pdf['Home'].tail(len(last_10)) == True]
                if len(last_10_home) >= 1:
                    home_away_factor = last_10_home.mean() / max(avg_last_10, 1)

            # 5️⃣ Head-to-Head adjustment (optional)
            h2h_factor = 1.0
            if upcoming_team_map and player in upcoming_team_map and 'Opp' in pdf.columns:
                opponent = upcoming_team_map[player]
                h2h_games = last_10[pdf['Opp'].tail(len(last_10)) == opponent]
                if len(h2h_games) >= 1:
                    h2h_factor = h2h_games.mean() / max(avg_last_10, 1)

            # 6️⃣ Weighted confidence calculation
            weighted_hit_rate = (
                hit_rate_last_10 * 0.6 +
                (avg_last_10 / max(line, 1)) * 0.2 +
                home_away_factor * 0.1 +
                h2h_factor * 0.1
            )
            weighted_hit_rate = min(max(weighted_hit_rate, 0), 1)
            confidence = round(weighted_hit_rate * 100)

            # 7️⃣ Streak count: consecutive games hitting the line (from most recent backwards)
            streak_count = 0
            for val in reversed(full_season):
                if val >= line:
                    streak_count += 1
                else:
                    break

            # 8️⃣ Season hit count: total games hitting the line
            season_hit_count = (full_season >= line).sum()

            # 9️⃣ Debug output
            if debug:
                print(f"Player: {player}")
                print(f"Prop: {prop}, Line: {line}")
                print(f"Hit rate L10: {hit_rate_last_10:.2f}")
                print(f"Avg last 10 / Line: {avg_last_10 / max(line,1):.2f}")
                print(f"Home/Away factor: {home_away_factor:.2f}")
                print(f"H2H factor: {h2h_factor:.2f}")
                print(f"Weighted confidence: {confidence}%")
                print(f"Streak count: {streak_count}")
                print(f"Season hit count: {season_hit_count}")
                print("-" * 40)

            # 10️⃣ Store results
            records.append({
                "player": player,
                "prop_type": prop,
                "line": line,
                "avg_last_10": avg_last_10,
                "hit_rate_last_10": hit_rate_last_10,
                "streak_count": streak_count,
                "season_hit_count": season_hit_count,
                "confidence": confidence
            })

    return pd.DataFrame(records)
