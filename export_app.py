import json
from pathlib import Path

import duckdb
import pandas as pd

from winprob import CUTOFF

OUT_DIR = Path("app/data")
PHASES = {"powerplay": range(0, 6), "middle": range(6, 15), "death": range(15, 20)}
DELIVERY_COLUMNS = [
    "match_id", "innings", "batting_team", "over", "ball_seq", "batter", "batter_id", "bowler",
    "bowler_id", "runs_batter", "runs_extras", "runs_total", "wides", "noballs", "is_legal",
    "is_wicket", "player_out", "wicket_kind", "wp", "wp_before",
]
CATEGORIES = ["match_id", "batting_team", "batter", "batter_id", "bowler", "bowler_id", "player_out", "wicket_kind"]


def innings_totals(deliveries: pd.DataFrame) -> pd.DataFrame:
    per = (
        deliveries.groupby(["match_id", "innings"])
        .agg(team=("batting_team", "first"), runs=("runs_total", "sum"), penalty=("penalty_runs", "max"),
             wkts=("is_wicket", "sum"), balls=("is_legal", "sum"))
        .reset_index()
    )
    per["runs"] += per.pop("penalty")
    wide = per.pivot(index="match_id", columns="innings", values=["team", "runs", "wkts", "balls"])
    wide.columns = [f"inn{i}_{c}" for c, i in wide.columns]
    for i in (1, 2):
        for c in ("runs", "wkts", "balls"):
            col = f"inn{i}_{c}"
            wide[col] = wide[col].astype("Int64") if col in wide else pd.array([pd.NA] * len(wide), "Int64")
        if f"inn{i}_team" not in wide:
            wide[f"inn{i}_team"] = None
    return wide.reset_index()


def findings(matches: pd.DataFrame, deliveries: pd.DataFrame) -> dict:
    chases = matches[(matches.competition == "ipl") & matches.has_wp & (matches.inn1_runs + 1 >= 200)]
    won = chases.winner == chases.inn2_team
    before = chases.start_date < pd.Timestamp("2023-01-01")
    test_ids = set(matches.match_id[matches.in_test])
    balls = deliveries[(deliveries.innings == 2) & deliveries.match_id.isin(test_ids) & deliveries.wp.notna()]
    swing = (balls.wp - balls.wp_before).abs() * 100
    return {
        "ipl_200_chases": {
            "before_2023": {"won": int(won[before].sum()), "n": int(before.sum())},
            "since_2023": {"won": int(won[~before].sum()), "n": int((~before).sum())},
        },
        "swing_per_ball": {
            name: round(float(swing[balls.over.isin(overs)].mean()), 1) for name, overs in PHASES.items()
        },
        "wicket_cost": round(float(((balls.wp_before - balls.wp) * 100)[balls.is_wicket].mean()), 1),
    }


def main() -> None:
    with duckdb.connect("data/cricket.duckdb", read_only=True) as con:
        matches = con.sql("select * from stg_all_matches").df()
        deliveries = con.sql("select * from stg_all_deliveries order by match_id, innings, over, ball_seq").df()

    pred = pd.read_parquet(OUT_DIR / "predictions.parquet", columns=["match_id", "over", "ball_seq", "wp", "wp_before"])
    deliveries = deliveries.merge(pred.assign(innings=2), on=["match_id", "innings", "over", "ball_seq"], how="left")

    matches["start_date"] = pd.to_datetime(matches.start_date)
    matches["in_test"] = matches.start_date >= pd.Timestamp(CUTOFF)
    matches = matches.merge(innings_totals(deliveries), on="match_id", how="left")
    start = pred.groupby("match_id", as_index=False).wp_before.first().rename(columns={"wp_before": "start_wp"})
    matches = matches.merge(start, on="match_id", how="left").sort_values("start_date", ignore_index=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matches.to_parquet(OUT_DIR / "matches.parquet", index=False)
    deliveries[DELIVERY_COLUMNS].astype({c: "category" for c in CATEGORIES}).to_parquet(
        OUT_DIR / "deliveries.parquet", index=False)
    result = findings(matches, deliveries)
    (OUT_DIR / "findings.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
