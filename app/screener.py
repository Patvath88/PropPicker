import pandas as pd
from data.metrics import compute_prop_metrics
from data.confidence import confidence_score

def build_screener(df, line_map):
    screener_rows = []

    for player, pdf in df.groupby("PLAYER_NAME"):
        metrics = compute_prop_metrics(pdf)

        for _, m in metrics.iterrows():
            line = line_map.get(m["prop_type"], None)
            if line is None:
                continue

            vals = pdf.head(10)
            prop_vals = (
                vals["PTS"] if m["prop_type"] == "PTS" else
                vals["PTS"] + vals["REB"] + vals["AST"]
            )

            hit_rate = (prop_vals > line).mean()

            row = {
                "player": player,
                "prop_type": m["prop_type"],
                "line": line,
                "avg_last_10": m["avg_last_10"],
                "hit_rate_last_10": hit_rate,
                "minutes_avg_last_5": m["minutes_avg_last_5"],
                "confidence": confidence_score({
                    **m,
                    "hit_rate_last_10": hit_rate,
                    "home_away_delta": 0  # placeholder
                }, line)
            }

            screener_rows.append(row)

    return pd.DataFrame(screener_rows)
