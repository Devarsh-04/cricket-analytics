import pandas as pd
import pytest

from stats import (
    head_to_head, most_played_ground, phase_note, phase_table, team_summary, top_players, wins_by_season,
)


def _m(match_id, date, season, team1, team2, winner, outcome, bat_first, venue):
    return {"match_id": match_id, "start_date": pd.Timestamp(date), "season": season, "team1": team1,
            "team2": team2, "winner": winner, "outcome": outcome, "bat_first": bat_first, "venue": venue}


def matches():
    return pd.DataFrame([
        _m("1", "2023-04-01", "2023", "R", "C", "R", "won", "R", "V1"),
        _m("2", "2024-04-10", "2024", "C", "R", None, "tie", "C", "V1"),
        _m("3", "2025-04-01", "2025", "R", "M", None, "no result", None, "V2"),
        _m("4", "2025-04-05", "2025", "M", "R", "M", "won", "M", "V1"),
        _m("5", "2025-04-20", "2025", "R", "C", "R", "won", "C", "V1"),
        _m("6", "2022-04-01", "2022", "C", "M", "C", "won", "C", "V3"),
        _m("7", "2023-05-01", "2023", "K", "C", "C", "won", "K", "V3"),
    ])


def _ball(match_id, innings, team, over, batter, bowler, runs=0, out=False, wides=0):
    return {"match_id": match_id, "innings": innings, "batting_team": team, "over": over,
            "batter": batter, "bowler": bowler, "runs_batter": runs, "runs_total": runs + wides,
            "wides": wides, "noballs": 0, "is_legal": wides == 0, "is_wicket": out,
            "wicket_kind": "caught" if out else None}


def deliveries():
    rows = [_ball("1", 1, "R", 0, "R1", "C1", runs=2) for _ in range(5)]
    rows += [_ball("1", 1, "R", 0, "R1", "C1", runs=2, out=True)]
    rows += [_ball("1", 2, "C", 0, "C2", "RB1", runs=1, out=i < 2) for i in range(6)]
    rows += [_ball("6", 1, "C", 0, "C3", "MB", runs=6) for _ in range(6)]
    return pd.DataFrame(rows)


def test_team_summary_counts_ties_and_no_results():
    s = team_summary(matches(), "R")
    assert s["overall"] == {"played": 5, "won": 2, "lost": 1, "tied": 1, "nr": 1}
    assert s["batting_first"] == {"played": 1, "won": 1, "lost": 0, "tied": 0, "nr": 0}
    assert s["chasing"] == {"played": 3, "won": 1, "lost": 1, "tied": 1, "nr": 0}
    assert s["seasons"] == ["2024", "2025"]
    assert s["last_two_seasons"] == {"played": 4, "won": 1, "lost": 1, "tied": 1, "nr": 1}


def test_head_to_head():
    h = head_to_head(matches(), "R")
    assert h.opponent.tolist() == ["C", "M"]
    assert h.iloc[0][["played", "won", "lost", "tied", "nr"]].tolist() == [3, 2, 0, 1, 0]
    assert h.iloc[1][["played", "won", "lost", "tied", "nr"]].tolist() == [2, 0, 1, 0, 1]


def test_wins_by_season_uses_season_label():
    m = pd.DataFrame([_m("1", "2025-01-05", "2024/25", "R", "C", "R", "won", "R", "V1")])
    w = wins_by_season(m, "R")
    assert w.values.tolist() == [["2024/25", 1, 1]]


def test_phase_table():
    pt = phase_table(deliveries(), matches(), "R", since="2023-01-01").set_index("phase")
    assert list(pt.index) == ["Powerplay", "Middle", "Death"]
    assert pt.loc["Powerplay", "team_run_rate"] == pytest.approx(12.0)
    assert pt.loc["Powerplay", "rest_run_rate"] == pytest.approx(6.0)
    assert pt.loc["Powerplay", "team_wkts"] == pytest.approx(1.0)
    assert pt.loc["Powerplay", "rest_wkts"] == pytest.approx(2.0)


def test_phase_table_empty_when_no_recent_matches():
    assert phase_table(deliveries(), matches(), "R", since="2030-01-01").empty


def test_phase_note():
    pt = pd.DataFrame({
        "phase": ["Powerplay", "Middle", "Death"],
        "team_run_rate": [9.93, 9.25, 11.28], "rest_run_rate": [9.46, 8.86, 10.80],
        "team_wkts": [1.17, 2.47, 2.16], "rest_wkts": [1.55, 2.46, 2.21],
    })
    assert phase_note(pt) == (
        "Best in the powerplay: 0.5 runs an over faster than other teams, losing a quarter fewer wickets.")
    worse = pt.assign(team_run_rate=[9.0, 8.86, 10.80], team_wkts=[2.0, 2.46, 2.21])
    assert phase_note(worse) == (
        "Weakest in the powerplay: 0.5 runs an over slower than other teams, losing about a quarter more wickets.")


def test_top_players():
    bat, bowl = top_players(deliveries(), "R")
    assert bat.iloc[0][["batter", "runs", "balls"]].tolist() == ["R1", 12, 6]
    assert bat.iloc[0].strike_rate == pytest.approx(200.0)
    assert bowl.bowler.tolist() == ["RB1"]
    assert bowl.iloc[0][["wickets", "balls"]].tolist() == [2, 6]
    assert bowl.iloc[0].economy == pytest.approx(6.0)


def test_most_played_ground():
    venue, rec = most_played_ground(matches(), "R")
    assert venue == "V1"
    assert rec == {"played": 4, "won": 2, "lost": 1, "tied": 1, "nr": 0}


def test_brief_team_renders_stats():
    m, d = matches(), deliveries()
    assert team_summary(m, "K")["overall"]["played"] == 1
    assert len(head_to_head(m, "K")) == 1
    assert phase_table(d, m, "K").empty
    bat, bowl = top_players(d, "K")
    assert bat.empty and bowl.empty
    assert most_played_ground(m, "K")[0] == "V3"
