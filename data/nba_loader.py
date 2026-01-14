from nba_api.stats.endpoints import leaguegamefinder, playergamelog
from nba_api.stats.static import players
import pandas as pd

def get_active_players():
    plist = players.get_active_players()
    return pd.DataFrame(plist)[["id", "full_name"]]

def get_player_games(player_id, season="2024-25", n_games=15):
    gamelog = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season
    ).get_data_frames()[0]

    gamelog = gamelog.sort_values("GAME_DATE", ascending=False).head(n_games)

    gamelog["HOME_AWAY"] = gamelog["MATCHUP"].apply(
        lambda x: "HOME" if "vs." in x else "AWAY"
    )

    return gamelog

def load_all_player_games(season="2024-25"):
    players_df = get_active_players()
    all_games = []

    for _, row in players_df.iterrows():
        try:
            g = get_player_games(row["id"], season)
            g["PLAYER_NAME"] = row["full_name"]
            all_games.append(g)
        except:
            continue

    df = pd.concat(all_games, ignore_index=True)
    return df
