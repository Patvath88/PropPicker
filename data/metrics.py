import pandas as pd
import numpy as np

PROP_MAP = {
    "PTS": lambda df: df["PTS"],
    "REB": lambda df: df["REB"],
    "AST": lambda df: df["AST"],
    "3PM": lambda df: df["FG3M"],
    "PRA": lambda df: df["PTS"] + df["REB"] + df["AST"],
    "PR":  lambda df: df["PTS"] + df["REB"],
    "PA":  lambda df: df["PTS"] + df["AST"],
    "RA":  lambda df: df["REB"] + df["AST"],
}

def compute_prop_metrics(player_df):
    rows = []

    for prop, func in PROP_MAP.items():
        vals = func(player_df)

        row = {
            "prop_type": prop,
            "avg_last_5": vals.head(5).mean(),
            "avg_last_10": vals.head(10).mean(),
            "avg_season": vals.mean(),
            "std_last_10": vals.head(10).std(),
            "minutes_avg_last_5": player_df["MIN"].head(5).mean(),
        }

        rows.append(row)

    return pd.DataFrame(rows)
