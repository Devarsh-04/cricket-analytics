import altair as alt
import pandas as pd
import streamlit as st

import load
import stats

ALL_TEAMS = "All teams"

m, d = load.matches(), load.deliveries()
st.title("Matches")

qid = st.query_params.get("id")
if qid in set(m.match_id) and st.session_state.get("loaded_id") != qid:
    pre = m[m.match_id == qid].iloc[0]
    st.session_state.update(comp=pre.competition, season=pre.season, team=ALL_TEAMS, match=qid, loaded_id=qid)

c1, c2, c3, c4 = st.columns([1, 1, 2, 4])
comp = c1.selectbox("Competition", list(load.COMPETITIONS), format_func=load.COMPETITIONS.get, key="comp")
pool = m[m.competition == comp]
seasons = sorted(pool.season.unique(), reverse=True)
if st.session_state.get("season") not in seasons:
    st.session_state.season = seasons[0]
season = c2.selectbox("Season", seasons, key="season")
pool = pool[pool.season == season]
teams = [ALL_TEAMS, *sorted(set(pool.team1) | set(pool.team2))]
if st.session_state.get("team") not in teams:
    st.session_state.team = ALL_TEAMS
team = c3.selectbox("Team", teams, key="team")
if team != ALL_TEAMS:
    pool = pool[(pool.team1 == team) | (pool.team2 == team)]
pool = pool.sort_values("start_date", ascending=False)
labels = dict(zip(pool.match_id, pool.start_date.dt.strftime("%d %b %Y") + " · " + pool.team1 + " v " + pool.team2
                  + " · " + pool.venue))
if st.session_state.get("match") not in labels:
    st.session_state.match = next(iter(labels))
match_id = c4.selectbox("Match", list(labels), format_func=labels.get, key="match")
st.session_state.loaded_id = match_id
st.query_params["id"] = match_id

row = m[m.match_id == match_id].iloc[0]
md = d[d.match_id == match_id]
defending = row.inn1_team if pd.notna(row.inn1_team) else row.team1
chasing = row.inn2_team if pd.notna(row.inn2_team) else ({row.team1, row.team2} - {defending}).pop()
colours = alt.Scale(domain=[defending, chasing], range=[load.DEFEND_COLOUR, load.CHASE_COLOUR])

if row.outcome == "tie":
    result = f"Tied — {row.eliminator} won the super over" if pd.notna(row.eliminator) else "Tied"
elif row.outcome == "no result":
    result = "No result"
else:
    result = f"{row.winner} won" + (" (DLS)" if pd.notna(row.method) else "")

st.header(f"{row.team1} v {row.team2}")
st.markdown(f"**{load.COMPETITIONS[row.competition]} · {row.start_date:%d %B %Y} · {row.venue}**")
s1, s2, s3 = st.columns(3)
s1.markdown(f"#### {load.score(defending, row.inn1_runs, row.inn1_wkts, row.inn1_balls)}")
s2.markdown(f"#### {load.score(chasing, row.inn2_runs, row.inn2_wkts, row.inn2_balls)}")
s3.markdown(f"#### {result}")
if row.in_test:
    st.caption("Test-set match — the model never saw it while learning.")

if row.has_wp:
    chase = md[md.innings == 2].copy()
    chase["ball"] = chase.is_legal.cumsum().clip(lower=1)
    chase["score"] = chase.runs_total.cumsum().astype(str) + "/" + chase.is_wicket.cumsum().astype(str)
    chase["over_ball"] = chase.over.astype(str) + "." + chase.groupby("over").is_legal.cumsum().astype(str)

    w1, w2 = st.columns([1, 3])
    w1.metric("Starting win chance", f"{row.start_wp:.0%}", help=f"{chasing}'s chance before the first ball")
    w1.caption(f"Before a ball was bowled, the model gave a side chasing {int(row.inn1_runs) + 1} "
               f"a {row.start_wp:.0%} chance.")
    line = alt.Chart(chase).mark_line(color=load.CHASE_COLOUR, strokeWidth=2.5).encode(
        x=alt.X("ball:Q", title="Legal ball of the chase", scale=alt.Scale(domain=[0, 120])),
        y=alt.Y("wp:Q", title=f"{chasing} win chance", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        tooltip=[alt.Tooltip("over_ball:N", title="Over"), "score", alt.Tooltip("wp:Q", title="Win chance", format=".0%")],
    )
    wickets = alt.Chart(chase[chase.is_wicket].astype({"player_out": str})).mark_point(
        color=load.DEFEND_COLOUR, filled=True, size=90).encode(
        x="ball:Q", y="wp:Q",
        tooltip=[alt.Tooltip("player_out:N", title="Out"), "score", alt.Tooltip("over_ball:N", title="Over")],
    )
    half = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(strokeDash=[4, 4], opacity=0.4).encode(y="y:Q")
    w2.altair_chart(line + wickets + half, width="stretch")
    w2.caption("The line is the chasing side's chance of winning after each ball. Orange dots are wickets.")

    st.subheader("Turning points")
    tp = stats.turning_points(md)
    for col, t in zip(st.columns(len(tp)), tp):
        with col.container(border=True):
            st.markdown(f"**Over {t['over']}** · {t['wp_from']:.0%} → {t['wp_to']:.0%}")
            st.markdown(t["text"])
    st.caption("The overs that moved the win chance the most.")

    st.subheader("Biggest impact")
    for r in stats.match_impact(md).itertuples():
        verb = "batting" if r.role == "bat" else "bowling"
        st.markdown(f"**{r.player}** ({verb}): {r.points:+.0f} points of win chance for "
                    f"{chasing if r.role == 'bat' else defending}")
    st.caption("Each ball's change in win chance, credited to the batter and the bowler.")
else:
    if row.outcome == "tie":
        reason = "the match was tied, so there is no winner of the chase to predict"
    elif row.outcome == "no result":
        reason = "the match had no result"
    elif pd.notna(row.method):
        reason = "rain shortened the match (DLS), so the 120-ball clock doesn't apply"
    else:
        reason = "the chase was shortened or an over was miscounted, so the 120-ball clock doesn't apply"
    st.info(f"No win-chance line: {reason}.")

if len(md):
    st.subheader("Runs per over")
    rpo = stats.runs_per_over(md)
    bars = alt.Chart(rpo).mark_bar().encode(
        x=alt.X("over:O", title="Over"), xOffset="team:N", y=alt.Y("runs:Q", title="Runs"),
        color=alt.Color("team:N", scale=colours, title=None, legend=alt.Legend(orient="top")),
        tooltip=["team", "over", "runs", "wickets"],
    ).properties(height=320)
    st.altair_chart(bars, width="stretch")
    st.caption("Runs scored in each over by both sides. Hover for wickets in that over.")

    st.subheader("Scorecards")
    innings = sorted(md.innings.unique())
    for tab, inn in zip(st.tabs([str(md[md.innings == i].batting_team.iloc[0]) for i in innings]), innings):
        with tab:
            st.dataframe(stats.batting_card(md, inn).round(1).rename(columns=str.capitalize)
                         .rename(columns={"Strike_rate": "Strike rate", "Fours": "4s", "Sixes": "6s"}),
                         hide_index=True, width="stretch")
            b1, b2 = st.columns([3, 2])
            b1.dataframe(stats.bowling_card(md, inn).round(2).rename(columns=str.capitalize), hide_index=True, width="stretch")
            b2.markdown("**Fall of wickets**")
            b2.dataframe(stats.fall_of_wickets(md, inn).rename(columns=str.capitalize), hide_index=True, width="stretch")

st.subheader("Head to head")
h2h = stats.head_to_head(m[m.competition == row.competition], row.team1)
h = h2h[h2h.opponent == row.team2].iloc[0]
extra = "".join(f", {h[k]} {label}" for k, label in (("tied", "tied"), ("nr", "no result")) if h[k])
st.markdown(f"In the {load.COMPETITIONS[row.competition]}, **{row.team1}** have won **{h.won}** and lost "
            f"**{h.lost}** of {h.played} matches against **{row.team2}**{extra}.")
t1, t2 = st.columns(2)
with t1:
    load.link_team(row.competition, row.team1, f"{row.team1} team page →")
with t2:
    load.link_team(row.competition, row.team2, f"{row.team2} team page →")
