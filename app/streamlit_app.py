import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
COMPETITIONS = {"ipl": "IPL", "bbl": "BBL", "t20i": "T20I"}

st.set_page_config(page_title="T20 Win Probability", layout="wide")


@st.cache_data
def load():
    pred = pd.read_parquet(DATA / "predictions.parquet")
    pred["ball"] = pred.groupby("match_id").cumcount() + 1
    return (
        pred,
        json.loads((DATA / "metrics.json").read_text()),
        pd.read_parquet(DATA / "calibration.parquet"),
        pd.read_parquet(DATA / "player_value.parquet"),
    )


pred, metrics, calibration, players = load()
st.title("T20 Chase Win Probability")
st.caption("IPL, BBL and men's T20Is between ICC full members. Data: Cricsheet (cricsheet.org).")
match_tab, model_tab, player_tab = st.tabs(["Match explorer", "Model", "Players"])

with match_tab:
    test_only = st.toggle("Test-set matches only (model never saw these)", value=True)
    pool = pred[pred.in_test] if test_only else pred
    c1, c2, c3 = st.columns(3)
    comp = c1.selectbox("Competition", list(COMPETITIONS), format_func=COMPETITIONS.get)
    pool = pool[pool.competition == comp]
    season = c2.selectbox("Season", sorted(pool.season_year.unique(), reverse=True))
    pool = pool[pool.season_year == season]
    labels = (
        pool.groupby("match_id")
        .agg(date=("start_date", "first"), team=("batting_team", "first"), venue=("venue_clean", "first"))
        .sort_values("date", ascending=False)
    )
    match_id = c3.selectbox(
        "Match", labels.index,
        format_func=lambda m: f"{labels.date[m]:%d %b} · {labels.team[m]} chasing · {labels.venue[m]}",
    )
    m = pool[pool.match_id == match_id].copy()
    m["wpa"] = m.wp - m.wp_before
    m["label"] = "Over " + (m.over + 1).astype(str) + ": " + m.batter + " v " + m.bowler
    swings = m.loc[m.wpa.abs().nlargest(3).index]
    events = pd.concat([m[m.is_wicket].assign(kind="Wicket"), swings.assign(kind="Big swing")])

    result = "won" if m.chase_won.iloc[0] else "lost"
    st.subheader(f"{m.batting_team.iloc[0]} chasing {int(m.target.iloc[0])} — {result}")
    base = alt.Chart(m).encode(x=alt.X("ball:Q", title="Ball of chase"))
    line = base.mark_line().encode(
        y=alt.Y("wp:Q", title="Chasing team win probability", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        tooltip=["label", alt.Tooltip("wp:Q", format=".0%"), "runs_needed", "balls_remaining", "wickets_in_hand"],
    )
    points = alt.Chart(events).mark_point(size=80, filled=True).encode(
        x="ball:Q", y="wp:Q", shape="kind:N", color="kind:N",
        tooltip=["kind", "label", alt.Tooltip("wpa:Q", format="+.0%")],
    )
    rule = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(strokeDash=[4, 4], opacity=0.4).encode(y="y:Q")
    st.altair_chart(line + points + rule, width="stretch")

with model_tab:
    st.write(
        "Trained on matches before 2023, tested on matches from 2023 on. "
        "Baseline = logistic regression on runs needed, balls left and wickets in hand."
    )
    rows = []
    for name in ("baseline", "model"):
        m = metrics[name]
        rows.append({"model": name, "competition": "All", **m["overall"]})
        rows += [{"model": name, "competition": COMPETITIONS[c], **s} for c, s in m["by_competition"].items()]
    st.dataframe(
        pd.DataFrame(rows).rename(columns={"brier": "Brier (lower better)", "log_loss": "Log loss", "auc": "AUC"}),
        hide_index=True,
    )
    diagonal = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(strokeDash=[4, 4], color="gray").encode(x="x", y="y")
    cal = alt.Chart(calibration).mark_line(point=True).encode(
        x=alt.X("mean_pred:Q", title="Predicted win probability", axis=alt.Axis(format="%")),
        y=alt.Y("frac_won:Q", title="Actual win rate", axis=alt.Axis(format="%")),
        color=alt.Color("model_name:N", title="Model"),
        tooltip=["model_name", alt.Tooltip("mean_pred:Q", format=".0%"), alt.Tooltip("frac_won:Q", format=".0%"), "n"],
    )
    st.subheader("Calibration — when the model says 70%, does the team win 70% of the time?")
    st.altair_chart(diagonal + cal, width="stretch")
    st.subheader("Does venue or season help? (validation on 2022, before touching the test set)")
    st.dataframe(
        pd.DataFrame(metrics["ablation_validation_2022"]).T[["brier", "log_loss", "auc"]].round(4)
        .rename(index={"model": "model (situation only)"}),
    )

with player_tab:
    st.subheader("Win probability added — chase-only")
    st.caption(
        "Each ball's change in win probability is credited to the batter (+) and bowler (−). "
        "Chase-only: only batters chasing and bowlers defending a target are counted. Underrated = ranked far higher by win probability added per ball than by raw rate stat."
    )
    role = st.radio("Role", ["bat", "bowl"], format_func={"bat": "Batters", "bowl": "Bowlers"}.get, horizontal=True)
    view = st.radio("View", ["Top by WPA", "Underrated vs raw stats"], horizontal=True)
    min_balls = st.slider("Minimum legal balls", 120, 2000, 120 if view == "Top by WPA" else 500, step=20)
    t = players[(players.role == role) & (players.balls >= min_balls)]
    t = t.sort_values("wpa_total" if view == "Top by WPA" else "rank_gap", ascending=False)
    raw = "Strike rate" if role == "bat" else "Economy"
    st.dataframe(
        t[["player", "balls", "wpa_total", "wpa_per_100", "raw_stat", "raw_rank", "wpa_rank", "rank_gap"]]
        .rename(columns={"wpa_total": "WPA", "wpa_per_100": "WPA / 100 balls", "raw_stat": raw,
                         "raw_rank": f"{raw} rank", "wpa_rank": "WPA rank", "rank_gap": "Rank gap"})
        .round(2),
        hide_index=True,
    )
