import numpy as np
from scipy.stats import zscore

def confidence_score(row, line):
    if row["minutes_avg_last_5"] < 24:
        return min(60, 100 * row["hit_rate_last_10"])

    z = (row["avg_last_10"] - row["avg_season"]) / max(row["std_last_10"], 1)

    score = (
        0.35 * z +
        0.30 * row["hit_rate_last_10"] +
        0.15 * row["home_away_delta"] +
        0.10 * row["minutes_avg_last_5"] / 36 +
        0.10 * (1 - min(row["std_last_10"] / 10, 1))
    )

    return round(np.clip(score * 100, 0, 100), 1)
