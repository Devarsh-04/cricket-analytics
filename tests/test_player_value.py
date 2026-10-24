import pandas as pd
import pytest

from player_value import ball_deltas, player_value


def balls(**overrides):
    base = {
        "match_id": ["m1"], "batter_id": ["bat1"], "batter": ["Batter One"],
        "bowler_id": ["bowl1"], "bowler": ["Bowler One"], "runs_total": [4], "runs_batter": [4],
        "is_legal": [True], "is_wicket": [False], "wp_before": [0.5], "wp": [0.6],
    }
    return pd.DataFrame({**base, **overrides})


def test_credit_signs():
    pv = player_value(ball_deltas(balls()), min_balls=0)
    assert pv.query("role == 'bat'").wpa_total.iloc[0] == pytest.approx(0.1)
    assert pv.query("role == 'bowl'").wpa_total.iloc[0] == pytest.approx(-0.1)


def test_player_value_keys_on_id():
    df = balls(
        match_id=["m1", "m2"], batter_id=["idA", "idB"], batter=["Same Name", "Same Name"],
        bowler_id=["b1", "b1"], bowler=["Bowler", "Bowler"], runs_total=[1, 2], runs_batter=[1, 2],
        is_legal=[True, True], is_wicket=[False, False], wp_before=[0.5, 0.5], wp=[0.55, 0.6],
    )
    pv = player_value(ball_deltas(df), min_balls=0)
    assert pv.query("role == 'bat'").player_id.nunique() == 2


def test_min_balls_filter():
    assert player_value(ball_deltas(balls()), min_balls=10_000).empty


def test_raw_stats_and_rank_gap():
    df = balls(
        match_id=["m1"] * 4, batter_id=["slow", "slow", "fast", "fast"],
        batter=["Slow", "Slow", "Fast", "Fast"], bowler_id=["b"] * 4, bowler=["B"] * 4,
        runs_total=[1, 1, 6, 6], runs_batter=[1, 1, 6, 6], is_legal=[True] * 4, is_wicket=[False] * 4,
        wp_before=[0.5, 0.6, 0.7, 0.71], wp=[0.6, 0.7, 0.71, 0.72],
    )
    bat = player_value(ball_deltas(df), min_balls=0).query("role == 'bat'").set_index("player_id")
    assert bat.loc["slow", "raw_stat"] == pytest.approx(100.0)
    assert bat.loc["fast", "raw_stat"] == pytest.approx(600.0)
    assert bat.loc["slow", "rank_gap"] > 0


def test_wpa_rank_uses_rate_not_volume():
    n_a, n_b = 1000, 100
    df = balls(
        match_id=["m1"] * (n_a + n_b), batter_id=["a"] * n_a + ["b"] * n_b,
        batter=["A"] * n_a + ["B"] * n_b, bowler_id=["x"] * (n_a + n_b), bowler=["X"] * (n_a + n_b),
        runs_total=[1] * (n_a + n_b), runs_batter=[1] * (n_a + n_b),
        is_legal=[True] * (n_a + n_b), is_wicket=[False] * (n_a + n_b),
        wp_before=[0.5] * (n_a + n_b), wp=[0.502] * n_a + [0.51] * n_b,
    )
    bat = player_value(ball_deltas(df), min_balls=0).query("role == 'bat'").set_index("player_id")
    assert bat.loc["a", "wpa_total"] > bat.loc["b", "wpa_total"]
    assert bat.loc["b", "wpa_rank"] == 1
