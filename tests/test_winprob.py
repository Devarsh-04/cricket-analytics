from functools import lru_cache

import numpy as np
import pandas as pd

from winprob import (
    calibration_table, evaluate, fit_baseline, fit_model, predict, start_state, time_split,
)


@lru_cache
def _synthetic():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(200):
        date = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(i * 9))
        target = int(rng.integers(130, 200))
        for ball in range(20):
            balls_remaining = int(rng.integers(1, 120))
            runs_needed = int(rng.integers(1, target))
            wickets = int(rng.integers(1, 11))
            logit = (balls_remaining * 1.3 - runs_needed) / 25 + 0.4 * (wickets - 5)
            rows.append({
                "match_id": f"m{i}",
                "competition": ["ipl", "bbl", "t20i"][i % 3],
                "start_date": date,
                "season_year": date.year,
                "venue_clean": f"Ground {i % 7}",
                "over": ball // 6,
                "ball_seq": ball % 6 + 1,
                "target": target,
                "runs_needed": runs_needed,
                "balls_remaining": balls_remaining,
                "wickets_in_hand": wickets,
                "required_run_rate": runs_needed * 6 / balls_remaining,
                "chase_won": int(rng.random() < 1 / (1 + np.exp(-logit))),
            })
    return pd.DataFrame(rows)


def synthetic_states():
    return _synthetic().copy()


@lru_cache
def fitted_model():
    return fit_model(time_split(synthetic_states())[0])


def test_time_split_no_leakage():
    train, test = time_split(synthetic_states())
    assert train.start_date.max() < pd.Timestamp("2025-01-01") <= test.start_date.min()
    assert set(train.match_id).isdisjoint(test.match_id)


def test_terminal_states_override():
    df = synthetic_states().head(3).assign(
        runs_needed=[0, 5, 5], wickets_in_hand=[3, 0, 3], balls_remaining=[10, 10, 0])
    assert list(predict(fitted_model(), df)) == [1.0, 0.0, 0.0]


def test_predict_unseen_venue():
    df = synthetic_states().head(1).assign(venue_clean="Brand New Oval")
    p = predict(fitted_model(), df)
    assert 0.0 <= p[0] <= 1.0


def test_calibration_table_bins():
    t = calibration_table(np.array([0, 1] * 50), np.linspace(0, 1, 100), bins=10)
    assert len(t) == 10 and t.n.sum() == 100


def test_model_beats_coinflip():
    train, test = time_split(synthetic_states())
    p = predict(fit_model(train), test)
    assert evaluate(test.chase_won, p, test.competition)["overall"]["brier"] < 0.25


def test_baseline_predicts_probabilities():
    train, test = time_split(synthetic_states())
    p = predict(fit_baseline(train), test)
    assert ((p >= 0) & (p <= 1)).all()


def test_start_state_one_row_per_match():
    s = start_state(synthetic_states())
    assert len(s) == 200
    assert (s.balls_remaining == 120).all() and (s.wickets_in_hand == 10).all()
    assert (s.runs_needed == s.target).all()


def test_evaluate_by_competition_keys():
    df = synthetic_states()
    m = evaluate(df.chase_won, np.full(len(df), 0.5), df.competition)
    assert set(m["by_competition"]) == {"ipl", "bbl", "t20i"}
    assert m["overall"]["brier"] == 0.25


def test_monotone_in_match_situation():
    row = synthetic_states().head(1).assign(runs_needed=60, wickets_in_hand=5)
    grid = pd.concat([row.assign(balls_remaining=b, required_run_rate=60 * 6 / b) for b in range(10, 120, 5)])
    p = predict(fitted_model(), grid)
    assert (np.diff(p) >= 0).all()
    more_runs = pd.concat([row.assign(runs_needed=r, balls_remaining=60, required_run_rate=r / 10) for r in range(10, 150, 5)])
    assert (np.diff(predict(fitted_model(), more_runs)) <= 0).all()


def test_cutoff_is_2025():
    import inspect
    import winprob
    assert winprob.CUTOFF == "2025-01-01"
    assert inspect.signature(winprob.ablation).parameters["cutoff"].default == "2024-01-01"
