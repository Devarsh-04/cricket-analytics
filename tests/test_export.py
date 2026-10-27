import pandas as pd

from export_app import findings, innings_totals


def _ball(match_id, innings, over, runs=1, wides=0, wicket=False, wp=None, wp_before=None):
    return {
        "match_id": match_id, "innings": innings, "batting_team": f"T{innings}", "over": over,
        "runs_total": runs, "wides": wides, "noballs": 0, "is_legal": wides == 0,
        "is_wicket": wicket, "penalty_runs": 0, "wp": wp, "wp_before": wp_before,
    }


def test_innings_totals():
    d = pd.DataFrame([
        _ball("m1", 1, 0, runs=4), _ball("m1", 1, 0, runs=1, wides=1), _ball("m1", 1, 0, runs=0, wicket=True),
        _ball("m1", 2, 0, runs=6), _ball("m1", 2, 0, runs=2),
        _ball("m2", 1, 0, runs=3),
    ])
    t = innings_totals(d).set_index("match_id")
    assert t.loc["m1", "inn1_team"] == "T1"
    assert (t.loc["m1", "inn1_runs"], t.loc["m1", "inn1_wkts"], t.loc["m1", "inn1_balls"]) == (5, 1, 2)
    assert (t.loc["m1", "inn2_runs"], t.loc["m1", "inn2_wkts"], t.loc["m1", "inn2_balls"]) == (8, 0, 2)
    assert t.loc["m2", "inn1_runs"] == 3
    assert pd.isna(t.loc["m2", "inn2_runs"]) and pd.isna(t.loc["m2", "inn2_team"])


def _matches(rows):
    return pd.DataFrame(rows, columns=[
        "match_id", "competition", "start_date", "has_wp", "in_test", "inn1_runs", "inn2_team", "winner"])


def test_findings_counts_200_chases():
    m = _matches([
        ("a", "ipl", pd.Timestamp("2022-04-01"), True, False, 198, "X", "X"),
        ("b", "ipl", pd.Timestamp("2022-04-02"), True, False, 199, "X", "X"),
        ("c", "ipl", pd.Timestamp("2024-04-01"), True, False, 209, "X", "Y"),
        ("d", "bbl", pd.Timestamp("2024-04-01"), True, False, 220, "X", "X"),
    ])
    d = pd.DataFrame([_ball("a", 2, 0, wp=0.5, wp_before=0.5)])
    f = findings(m, d)["ipl_200_chases"]
    assert f["before_2023"] == {"won": 1, "n": 1}
    assert f["since_2023"] == {"won": 0, "n": 1}


def test_findings_wicket_cost():
    m = _matches([
        ("a", "ipl", pd.Timestamp("2025-04-01"), True, True, 150, "X", "X"),
        ("b", "ipl", pd.Timestamp("2022-04-01"), True, False, 150, "X", "X"),
    ])
    d = pd.DataFrame([
        _ball("a", 2, 3, wicket=True, wp=0.40, wp_before=0.50),
        _ball("a", 2, 17, wicket=True, wp=0.56, wp_before=0.60),
        _ball("a", 2, 18, wp=0.70, wp_before=0.56),
        _ball("b", 2, 4, wicket=True, wp=0.0, wp_before=0.9),
    ])
    f = findings(m, d)
    assert f["wicket_cost"] == 7.0
    assert f["swing_per_ball"]["death"] == 9.0
    assert f["swing_per_ball"]["powerplay"] == 10.0
