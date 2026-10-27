import altair as alt
import pandas as pd
import streamlit as st

import load

st.title("About the model")
st.markdown(
    "**How the win chance works.** At every ball of a chase, the model looks at four things: runs needed, "
    "balls left, wickets in hand and the required rate. It learned from every chase before 2025 how often "
    "teams in that position went on to win. It never sees the team names, the ground or the players, so "
    "the win chance is about the situation alone. It is tested on 2025–26 matches it never trained on."
)

metrics = load.metrics()
rows = []
for name in ("baseline", "model"):
    m = metrics[name]
    rows.append({"model": name, "competition": "All", **m["overall"]})
    rows += [{"model": name, "competition": load.COMPETITIONS[c], **s} for c, s in m["by_competition"].items()]
st.subheader("Accuracy on 2025–26 matches")
st.caption("Brier score and log loss: lower is better. AUC: higher is better. "
           "Baseline = logistic regression on runs needed, balls left and wickets in hand.")
st.dataframe(
    pd.DataFrame(rows).rename(columns={"brier": "Brier", "log_loss": "Log loss", "auc": "AUC", "n": "Balls"}),
    hide_index=True,
)

diagonal = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(strokeDash=[4, 4], color="gray").encode(x="x", y="y")
cal = alt.Chart(load.calibration()).mark_line(point=True).encode(
    x=alt.X("mean_pred:Q", title="Predicted win chance", axis=alt.Axis(format="%")),
    y=alt.Y("frac_won:Q", title="Actual win rate", axis=alt.Axis(format="%")),
    color=alt.Color("model_name:N", title="Model",
                    scale=alt.Scale(range=[load.DEFEND_COLOUR, load.CHASE_COLOUR])),
    tooltip=["model_name", alt.Tooltip("mean_pred:Q", format=".0%"), alt.Tooltip("frac_won:Q", format=".0%"), "n"],
)
st.subheader("When the model says 70%, does the team win 70% of the time?")
st.altair_chart(diagonal + cal, width="stretch")
st.caption("Points close to the dashed line mean the stated win chance matches what actually happened.")

st.subheader("Does venue or season help? (checked on 2024, before touching the test set)")
st.dataframe(
    pd.DataFrame(metrics["ablation_validation_2024"]).T[["brier", "log_loss", "auc"]].round(4)
    .rename(index={"model": "model (situation only)"}),
)
st.caption("Adding the ground or the season made predictions worse, so the final model leaves them out. "
           "Adding the competition helped slightly; it is the next thing to try.")

st.subheader("Which players move chases the most?")
st.caption(
    "Each ball's change in win chance is credited to the batter (+) and the bowler (−). Only batters chasing "
    "and bowlers defending a target count. Underrated = ranked far higher on win chance added per ball than "
    "on strike rate or economy."
)
players = load.players()
role = st.radio("Role", ["bat", "bowl"], format_func={"bat": "Batters", "bowl": "Bowlers"}.get, horizontal=True)
view = st.radio("View", ["Top by win chance added", "Underrated vs raw stats"], horizontal=True)
min_balls = st.slider("Minimum legal balls", 120, 2000, 120 if view == "Top by win chance added" else 500, step=20)
t = players[(players.role == role) & (players.balls >= min_balls)]
t = t.sort_values("wpa_total" if view == "Top by win chance added" else "rank_gap", ascending=False)
raw = "Strike rate" if role == "bat" else "Economy"
st.dataframe(
    t[["player", "balls", "wpa_total", "wpa_per_100", "raw_stat", "raw_rank", "wpa_rank", "rank_gap"]]
    .rename(columns={"wpa_total": "Win chance added", "wpa_per_100": "Per 100 balls", "raw_stat": raw,
                     "raw_rank": f"{raw} rank", "wpa_rank": "Win-chance rank", "rank_gap": "Rank gap"})
    .round(2),
    hide_index=True,
)
