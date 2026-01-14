# screener.py
import pandas as pd
import numpy as np

def build_screener(df: pd.DataFrame, line_map: dict, upcoming_team_map: dict = None, debug: bool = False) -> pd.DataFrame:
    """
    Build a fully featured NBA prop screener using all relevant stats.
    Returns:
        DataFrame with detailed stats and confidence rating
    """

    # Detect player column
    player_col = next((c for c in ['player','PLAYER_NAME','Player','NAME'] if c in df.columns), None)
    if not player_col:
        raise ValueError("No player column found in DataFrame")

    records = []

    for player, pdf in df.groupby(player_col):
        for prop, line in line_map.items():

            # Map prop to column
            col_map = {"PTS":"pts","REB":"reb","AST":"ast","3PM":"3pm"}
            col_name = col_map.get(prop, prop)
            if col_name not in pdf.columns:
                continue

            # Numeric
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce')
            last_10 = pdf[col_name].tail(10).dropna().tolist()
            full_season = pdf[col_name].dropna()

            # Core metrics
            avg_last_10 = sum(last_10)/len(last_10) if last_10 else 0
            hit_rate_last_10 = sum(1 for x in last_10 if x >= line)/len(last_10) if last_10 else 0

            # --- Streak calculations ---
            hits = full_season >= line
            # Longest consecutive streak
            streak_count = hits.groupby((hits != hits.shift()).cumsum()).sum().max()
            streak_count = int(streak_count) if not pd.isna(streak_count) else 0
            # Total games hitting the line
            season_hit_count = int(hits.sum())

            # Minutes adjustment
            mp_factor = 1.0
            if 'mp' in pdf.columns:
                mp_last_10 = pd.to_numeric(pdf['mp'].tail(10).dropna(), errors='coerce')
                if len(mp_last_10):
                    mp_factor = min(sum(mp_last_10)/len(mp_last_10)/30, 1.0)  # baseline 30min

            # Efficiency adjustment (FG% and TO)
            eff_factor = 1.0
            if 'fg%' in pdf.columns:
                fg_pct = pd.to_numeric(pdf['fg%'].tail(10).dropna(), errors='coerce')
                if len(fg_pct):
                    eff_factor *= min(fg_pct.mean()/0.45,1.0)
            if 'tov' in pdf.columns:
                tov = pd.to_numeric(pdf['tov'].tail(10).dropna(), errors='coerce')
                if len(tov):
                    avg_tov = sum(tov)/len(tov)
                    eff_factor *= max(1 - avg_tov/5,0)  # penalize turnovers

            # Home/Away factor
            home_away_factor = 1.0
            if 'Home' in pdf.columns:
                last_10_home = [v for idx,v in zip(pdf[col_name].tail(10).index,last_10) if pdf['Home'].iloc[idx]]
                if last_10_home:
                    home_away_factor = sum(last_10_home)/max(avg_last_10,1)

            # H2H factor
            h2h_factor = 1.0
            if upcoming_team_map and player in upcoming_team_map and 'Opp' in pdf.columns:
                opp = upcoming_team_map[player]
                last_10_opp = [v for idx,v in zip(pdf[col_name].tail(10).index,last_10) if pdf['Opp'].iloc[idx]==opp]
                if last_10_opp:
                    h2h_factor = sum(last_10_opp)/max(avg_last_10,1)

            # Weighted confidence
            weighted_conf = (
                hit_rate_last_10 * 0.35 +
                (avg_last_10 / max(line,1)) * 0.2 +
                mp_factor * 0.1 +
                eff_factor * 0.1 +
                home_away_factor * 0.1 +
                h2h_factor * 0.1 +
                min(streak_count/5,1.0) * 0.05  # streak factor
            )
            weighted_conf = min(max(weighted_conf,0),1)
            confidence = round(weighted_conf*100)

            if debug:
                print(f"{player} | {prop} | line {line} | confidence {confidence}%")
                print({
                    'hit_rate_last_10':hit_rate_last_10,
                    'avg_last_10':avg_last_10,
                    'mp_factor':mp_factor,
                    'eff_factor':eff_factor,
                    'home_away_factor':home_away_factor,
                    'h2h_factor':h2h_factor,
                    'streak_count':streak_count,
                    'season_hit_count':season_hit_count
                })
                print('-'*40)

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
                "confidence": confidence
            })

    return pd.DataFrame(records)
