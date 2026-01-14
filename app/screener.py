# screener.py
import pandas as pd

def build_screener(df: pd.DataFrame, line_map: dict, upcoming_team_map: dict = None, debug: bool = False) -> pd.DataFrame:
    """
    Build a prop screener with confidence, streak, and season hit count.

    Parameters:
    - df: DataFrame with player stats (must have 'player' or similar column, numeric prop columns)
    - line_map: dict of prop_type -> line value
    - upcoming_team_map: optional dict of player -> opponent team (for H2H adjustment)
    - debug: if True, prints intermediate calculations

    Returns:
    - DataFrame with player, prop_type, line, avg_last_10, hit_rate_last_10, streak_count, season_hit_count, confidence
    """

    # Detect player column
    possible_player_cols = ['player', 'PLAYER_NAME', 'Player', 'NAME']
    player_col = next((c for c in possible_player_cols if c in df.columns), None)
    if not player_col:
        raise ValueError("No player column found in DataFrame")

    records = []

    # Iterate over players
    for player, pdf in df.groupby(player_col):
        for prop, line in line_map.items():
            # Map prop names to columns
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

            # Convert to Python lists for calculations
            last_10 = pdf[col_name].tail(10).dropna().tolist()
            full_season = pdf[col_name].dropna().tolist()

            # Average and hit rate last 10
            if len(last_10) == 0:
                avg_last_10 = 0
                hit_rate_last_10 = 0
            else:
                avg_last_10 = sum(last_10) / len(last_10)
                hit_rate_last_10 = sum(1 for x in last_10 if x >= line) / len(last_10)

            # Home/Away adjustment
            home_away_factor = 1.0
            if 'Home' in pdf.columns and len(last_10) > 0:
                # Match last_10 indices with Home column
                last_10_home = [
                    val for idx, val in zip(pdf[col_name].tail(10).index, last_10)
                    if pdf['Home'].iloc[idx]
                ]
                if len(last_10_home) >= 1:
                    home_away_factor = sum(last_10_home) / max(avg_last_10, 1)

            # H2H adjustment
            h2h_factor = 1.0
            if upcoming_team_map and player in upcoming_team_map and 'Opp' in pdf.columns and len(last_10) > 0:
                opponent = upcoming_team_map[player]
                last_10_opp = [
                    val for idx, val in zip(pdf[col_name].tail(10).index, last_10)
                    if pdf['Opp'].iloc[idx] == opponent
                ]
                if len(last_10_opp) >= 1:
                    h2h_factor = sum(last_10_opp) / max(avg_last_10, 1)

            # Weighted confidence
            weighted_hit_rate = (
                hit_rate_last_10 * 0.6 +
                (avg_last_10 / max(line, 1)) * 0.2 +
                home_away_factor * 0.1 +
                h2h_factor * 0.1
            )
            weighted_hit_rate = min(max(weighted_hit_rate, 0), 1)
            confidence = round(weighted_hit_rate * 100)

            # Streak count: consecutive games hitting the line (from most recent backwards)
            streak_count = 0
            for val in reversed(full_season):
                if val >= line:
                    streak_count += 1
                else:
                    break

            # Season hit count
            season_hit_count = sum(1 for val in full_season if val >= line)

            # Debug output
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

            # Store results
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
