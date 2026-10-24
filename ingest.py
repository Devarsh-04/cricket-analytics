import json
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

URLS = {
    "ipl": "https://cricsheet.org/downloads/ipl_json.zip",
    "bbl": "https://cricsheet.org/downloads/bbl_json.zip",
    "t20i": "https://cricsheet.org/downloads/t20s_male_json.zip",
}
DATA_DIR = Path("data")


def flatten_match(match: dict, match_id: str, competition: str) -> tuple[dict, list[dict]]:
    info = match["info"]
    outcome = info.get("outcome", {})
    people = info.get("registry", {}).get("people", {})
    row = {
        "match_id": match_id,
        "competition": competition,
        "start_date": info["dates"][0],
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team1": info["teams"][0],
        "team2": info["teams"][1],
        "winner": outcome.get("winner"),
        "result": outcome.get("result"),
        "method": outcome.get("method"),
        "overs": info.get("overs"),
        "gender": info.get("gender"),
    }

    deliveries = []
    for innings_no, innings in enumerate(match.get("innings", []), start=1):
        target = innings.get("target", {})
        for over in innings.get("overs", []):
            for ball_seq, d in enumerate(over["deliveries"], start=1):
                extras = d.get("extras", {})
                wickets = d.get("wickets", [])
                deliveries.append({
                    "match_id": match_id,
                    "innings": innings_no,
                    "batting_team": innings["team"],
                    "over": over["over"],
                    "ball_seq": ball_seq,
                    "batter": d["batter"],
                    "batter_id": people.get(d["batter"]),
                    "bowler": d["bowler"],
                    "bowler_id": people.get(d["bowler"]),
                    "runs_batter": d["runs"]["batter"],
                    "runs_extras": d["runs"]["extras"],
                    "runs_total": d["runs"]["total"],
                    "wides": extras.get("wides", 0),
                    "noballs": extras.get("noballs", 0),
                    "is_wicket": bool(wickets),
                    "player_out": wickets[0]["player_out"] if wickets else None,
                    "wicket_kind": wickets[0]["kind"] if wickets else None,
                    "target_runs": target.get("runs"),
                    "target_overs": target.get("overs"),
                    "is_super_over": bool(innings.get("super_over", False)),
                })
    return row, deliveries


def fetch(competition: str) -> Path:
    zip_path = DATA_DIR / "zips" / URLS[competition].rsplit("/", 1)[1]
    if not zip_path.exists():
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URLS[competition], zip_path)
    out = DATA_DIR / "json" / competition
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)
    return out


def load(competitions: list[str], db_path: Path) -> None:
    matches, deliveries = [], []
    for comp in competitions:
        for f in sorted(fetch(comp).glob("*.json")):
            m, d = flatten_match(json.loads(f.read_text()), f.stem, comp)
            matches.append(m)
            deliveries.extend(d)

    with duckdb.connect(str(db_path)) as con:
        con.register("matches_df", pd.DataFrame(matches).assign(
            start_date=lambda df: pd.to_datetime(df.start_date).dt.date))
        con.register("deliveries_df", pd.DataFrame(deliveries))
        con.execute("CREATE OR REPLACE TABLE raw_matches AS SELECT * FROM matches_df")
        con.execute("CREATE OR REPLACE TABLE raw_deliveries AS SELECT * FROM deliveries_df")


if __name__ == "__main__":
    load(list(URLS), DATA_DIR / "cricket.duckdb")
