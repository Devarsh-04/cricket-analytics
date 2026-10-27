import pandas as pd
import pytest

from stats import batting_card, bowling_card, fall_of_wickets, match_impact, runs_per_over, turning_points


def _b(inn, over, batter, bowler, bat=0, wides=0, noballs=0, out=None, kind=None, wp=None, wpb=None):
    return {
        "match_id": "m", "innings": inn, "batting_team": "A" if inn == 1 else "B", "over": over,
        "batter": batter, "bowler": bowler, "runs_batter": bat, "runs_extras": wides + noballs,
        "runs_total": bat + wides + noballs, "wides": wides, "noballs": noballs,
        "is_legal": wides == 0 and noballs == 0, "is_wicket": out is not None and kind != "retired hurt",
        "player_out": out, "wicket_kind": kind, "wp": wp, "wp_before": wpb,
    }


def match():
    rows = [
        _b(1, 0, "A1", "X", 4), _b(1, 0, "A1", "X", wides=1), _b(1, 0, "A1", "X", 1),
        _b(1, 0, "A2", "X", out="A2", kind="bowled"), _b(1, 0, "A3", "X", 6),
        _b(1, 0, "A3", "X", 1, noballs=1), _b(1, 0, "A3", "X"), _b(1, 0, "A3", "X", 1),
        _b(1, 1, "A1", "Y", 2), _b(1, 1, "A1", "Y", out="A3", kind="run out"),
        _b(1, 1, "A4", "Y", 4), _b(1, 1, "A4", "Y"),
        _b(2, 0, "B1", "P", 1, wp=.52, wpb=.50), _b(2, 0, "B1", "P", out="B1", kind="caught", wp=.40, wpb=.52),
        _b(2, 0, "B2", "P", 4, wp=.45, wpb=.40), _b(2, 0, "B2", "P", wp=.44, wpb=.45),
        _b(2, 0, "B2", "P", 1, wp=.46, wpb=.44), _b(2, 0, "B3", "P", wp=.45, wpb=.46),
        _b(2, 1, "B3", "Q", 6, wp=.60, wpb=.45), _b(2, 1, "B3", "Q", 4, wp=.70, wpb=.60),
        _b(2, 1, "B2", "Q", 1, wp=.72, wpb=.70),
    ]
    return pd.DataFrame(rows)


def test_batting_card():
    card = batting_card(match(), 1).set_index("batter")
    assert list(card.index) == ["A1", "A2", "A3", "A4"]
    assert card.loc["A1", ["runs", "balls", "fours", "dismissal"]].tolist() == [7, 4, 1, "not out"]
    assert card.loc["A2", "dismissal"] == "b X"
    assert card.loc["A3", ["runs", "balls", "sixes", "dismissal"]].tolist() == [8, 4, 1, "run out"]
    assert card.loc["A3", "strike_rate"] == pytest.approx(200.0)


def test_bowling_card_excludes_run_outs():
    card = bowling_card(match(), 1).set_index("bowler")
    assert card.loc["X", ["overs", "runs", "wickets"]].tolist() == ["1.0", 15, 1]
    assert card.loc["Y", ["overs", "runs", "wickets"]].tolist() == ["0.4", 6, 0]
    assert card.loc["Y", "economy"] == pytest.approx(9.0)


def test_fall_of_wickets():
    fow = fall_of_wickets(match(), 1)
    assert fow[["wicket", "score", "batter", "over"]].values.tolist() == [[1, 6, "A2", "0.3"], [2, 17, "A3", "1.2"]]


def test_runs_per_over_adds_up():
    rpo = runs_per_over(match())
    assert rpo[rpo.innings == 1][["over", "runs", "wickets"]].values.tolist() == [[1, 15, 1], [2, 6, 1]]
    assert rpo[rpo.innings == 2].runs.sum() == 17
    assert set(rpo.team) == {"A", "B"}


def test_turning_points():
    tp = turning_points(match(), 2)
    assert [t["over"] for t in tp] == [1, 2]
    assert tp[0]["text"] == "P took 1 wicket (B1) for 6 runs"
    assert tp[1]["text"] == "B3 scored 10 of the 11 runs off Q"
    assert tp[1]["wp_from"] == pytest.approx(.45) and tp[1]["wp_to"] == pytest.approx(.72)
    assert [t["over"] for t in turning_points(match(), 1)] == [2]


def test_match_impact():
    imp = match_impact(match())
    assert imp.player.tolist() == ["B3", "B2", "P"]
    assert imp.role.tolist() == ["bat", "bat", "bowl"]
    assert imp.points.iloc[0] == pytest.approx(24.0)


def test_card_handles_missing_innings():
    first_only = match().query("innings == 1")
    assert batting_card(first_only, 2).empty
    assert bowling_card(first_only, 2).empty
    assert fall_of_wickets(first_only, 2).empty


def test_turning_points_empty_without_wp():
    first_only = match().query("innings == 1")
    assert turning_points(first_only) == []
    assert match_impact(first_only).empty
