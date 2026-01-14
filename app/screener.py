import pandas as pd

def predict_player_line(last_10, mp_factor=1.0, eff_factor=1.0, home_away_factor=1.0, h2h_factor=1.0):
    """Return a predicted stat for the next game"""
    if not last_10:
        return 0
    base = sum(last_10)/len(last_10)  # average of last 10 games
    prediction = base * mp_factor * eff_factor * home_away_factor * h2h_factor
    return round(prediction, 1)


def build_screener(df: pd.DataFrame, line_map: dict, upcoming_team_map: dict = None, debug: bool = False) -> pd.DataFrame:
    """
    Build NBA prop screener from game log data.
    df: game logs with one row per game per player
    line_map: {"PTS": 25.5} etc
    upcoming_team_map: optional H2H mapping
    """
    # Normalize column names
    df = df.rename(columns=lambda x: x.strip().lower())
    if 'player' not in df.columns:
        raise ValueError("CSV must have a 'player' column")

    player_col = 'player'
    records = []

    for player, pdf in df.groupby(player_col):
        for prop, line in line_map.items():
            # Map prop to CSV column (lowercase)
            col_map = {"PTS":"pts","REB":"reb","AST":"ast","3PM":"3pm"}
            col_name = col_map.get(prop, prop.lower())
            if col_name not in pdf.columns:
                if debug:
                    print(f"Skipping {prop} for {player}, missing column {col_name}")
                continue

            # Ensure numeric
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce')
            last_10 = pdf[col_name].tail(10).dropna().tolist()
            full_season = pdf[col_name].dropna().tolist()

            # Core metrics
            avg_last_10 = sum(last_10)/len(last_10) if last_10 else 0
            hit_rate_last_10 = sum(1 for x in last_10 if x >= line)/len(last_10) if last_10 else 0

            # Longest streak
            hits = [1 if x >= line else 0 for x in full_season]
            max_streak = 0
            current_streak = 0
            for h in hits:
                if h == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 0
            streak_count = max_streak
            season_hit_count = sum(hits)

            # Minutes factor
            mp_factor = 1.0
            if 'mp' in pdf.columns:
                mp_last_10 = pd.to_numeric(pdf['mp'].tail(10).dropna(), errors='coerce')
                if len(mp_last_10):
                    mp_factor = min(sum(mp_last_10)/len(mp_last_10)/30,1.0)

            # Efficiency factor
            eff_factor = 1.0
            if 'fg%' in pdf.columns:
                fg_pct = pd.to_numeric(pdf['fg%'].tail(10).dropna(), errors='coerce')
                if len(fg_pct):
                    eff_factor *= min(fg_pct.mean()/0.45,1.0)

            # Home/Away factor
            home_away_factor = 1.0
            if 'home' in pdf.columns:
                last_10_home = [v for idx,v in zip(pdf[col_name].tail(10).index,last_10) if pdf['home'].iloc[idx]]
                if last_10_home:
                    home_away_factor = sum(last_10_home)/max(avg_last_10,1)

            # H2H factor
            h2h_factor = 1.0
            if upcoming_team_map and player in upcoming_team_map and 'opp' in pdf.columns:
                opp = upcoming_team_map[player]
                last_10_opp = [v for idx,v in zip(pdf[col_name].tail(10).index,last_10) if pdf['opp'].iloc[idx]==opp]
                if last_10_opp:
                    h2h_factor = sum(last_10_opp)/max(avg_last_10,1)

            # Weighted confidence
            weighted_conf = (
                hit_rate_last_10*0.35 +
                (avg_last_10/max(line,1))*0.2 +
                mp_factor*0.1 +
                eff_factor*0.1 +
                home_away_factor*0.1 +
                h2h_factor*0.1 +
                min(streak_count/5,1.0)*0.05
            )
            weighted_conf = min(max(weighted_conf,0),1)
            confidence = round(weighted_conf*100)

            # Prediction for next game
            prediction = predict_player_line(last_10, mp_factor, eff_factor, home_away_factor, h2h_factor)

            records.append({
                "player": player,
                "prop_type": prop,
                "line": line,
                "avg_last_10": avg_last_10,
                "hit_rate_last_10": hit_rate_last_10,
                "streak_count": streak_count,
                "season_hit_count": season_hit_count,
                "mp_factor": mp_factor,
                "eff_factor": eff_factor,
                "home_away_factor": home_away_factor,
                "h2h_factor": h2h_factor,
                "confidence": confidence,
                "prediction": prediction
            })

    return pd.DataFrame(records)
