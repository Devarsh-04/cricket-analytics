import json
import zipfile
from pathlib import Path

import duckdb

import ingest
from ingest import flatten_match

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_DELIVERY_COUNT = 20


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


def test_flatten_counts():
    m, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert m["match_id"] == "m1" and m["competition"] == "ipl" and m["overs"] == 20
    assert len(d) == FIXTURE_DELIVERY_COUNT


def test_extras_flags():
    _, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert sum(r["wides"] > 0 for r in d) == 1
    assert sum(r["noballs"] > 0 for r in d) == 1


def test_registry_ids():
    _, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert all(r["batter_id"] and r["bowler_id"] for r in d)
    assert d[0]["batter_id"] == "a1id"


def test_method_captured():
    m, _ = flatten_match(load_fixture("match_dls.json"), "m2", "ipl")
    assert m["method"] == "D/L"


def test_innings_fields():
    m, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert m["winner"] == "Team B" and m["venue"] == "Wankhede Stadium, Mumbai"
    chase = [r for r in d if r["innings"] == 2]
    assert len(chase) == 6 and chase[0]["target_runs"] == 18
    assert sum(r["is_wicket"] for r in d) == 1
    assert d[1]["ball_seq"] == 2 and d[7]["over"] == 1 and d[7]["ball_seq"] == 1


def test_load_replaces_existing_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    (tmp_path / "zips").mkdir()
    with zipfile.ZipFile(tmp_path / "zips" / "ipl_json.zip", "w") as z:
        z.write(FIXTURES / "match_ok.json", "1001.json")
    db = tmp_path / "t.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE raw_matches AS SELECT 'stale' AS match_id")
        con.execute("CREATE TABLE raw_deliveries AS SELECT 'stale' AS match_id")

    ingest.load(["ipl"], db)

    with duckdb.connect(str(db)) as con:
        assert con.sql("SELECT match_id FROM raw_matches").fetchall() == [("1001",)]
        assert con.sql("SELECT count(*) FROM raw_deliveries").fetchall()[0][0] == FIXTURE_DELIVERY_COUNT


def test_penalty_runs_captured():
    match = load_fixture("match_ok.json")
    match["innings"][0]["penalty_runs"] = {"post": 5}
    _, d = flatten_match(match, "m1", "ipl")
    assert {r["penalty_runs"] for r in d if r["innings"] == 1} == {5}
    assert {r["penalty_runs"] for r in d if r["innings"] == 2} == {0}


def test_flatten_captures_season():
    m, _ = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert m["season"] == "2023"


def test_flatten_captures_eliminator():
    match = load_fixture("match_ok.json")
    match["info"]["outcome"] = {"result": "tie", "eliminator": "Mumbai Indians"}
    m, _ = flatten_match(match, "m1", "ipl")
    assert m["eliminator"] == "Mumbai Indians"
    assert m["winner"] is None
