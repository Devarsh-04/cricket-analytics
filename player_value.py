from pathlib import Path

import pandas as pd

DATA_DIR = Path("app/data")


def ball_deltas(pred: pd.DataFrame) -> pd.DataFrame:
    return pred.assign(wpa=pred.wp - pred.wp_before)


def _role_table(df: pd.DataFrame, role: str, min_balls: int) -> pd.DataFrame:
    who = "batter" if role == "bat" else "bowler"
    sign = 1 if role == "bat" else -1
    g = (
        df.assign(credit=sign * df.wpa, legal=df.is_legal.astype(int))
        .groupby(f"{who}_id")
        .agg(
            player=(who, "last"),
            balls=("legal", "sum"),
            wpa_total=("credit", "sum"),
            runs=("runs_batter" if role == "bat" else "runs_total", "sum"),
        )
        .reset_index()
        .rename(columns={f"{who}_id": "player_id"})
    )
    g = g[(g.balls >= min_balls) & (g.balls > 0)].copy()
    if role == "bat":
        g["raw_stat"] = g.runs / g.balls * 100
    else:
        g["raw_stat"] = g.runs / g.balls * 6
    g["wpa_per_100"] = g.wpa_total / g.balls * 100
    g["raw_rank"] = g.raw_stat.rank(ascending=(role == "bowl"), method="min")
    g["wpa_rank"] = g.wpa_per_100.rank(ascending=False, method="min")
    g["rank_gap"] = g.raw_rank - g.wpa_rank
    g["role"] = role
    return g.drop(columns="runs")


def player_value(deltas: pd.DataFrame, min_balls: int = 120) -> pd.DataFrame:
    return pd.concat(
        [_role_table(deltas, role, min_balls) for role in ("bat", "bowl")], ignore_index=True)


if __name__ == "__main__":
    pred = pd.read_parquet(DATA_DIR / "predictions.parquet")
    pv = player_value(ball_deltas(pred))
    pv.to_parquet(DATA_DIR / "player_value.parquet", index=False)
    for role in ("bat", "bowl"):
        print(pv.query("role == @role").nlargest(10, "wpa_total")[["player", "balls", "wpa_total", "raw_stat"]])
