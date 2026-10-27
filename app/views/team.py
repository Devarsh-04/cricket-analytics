import altair as alt
import pandas as pd
import streamlit as st

import load
import stats

m_all, d_all = load.matches(), load.deliveries()
st.title("Teams")

q = st.query_params
key = (q.get("comp"), q.get("team"))
if key[0] in load.COMPETITIONS and ("team_name" not in st.session_state
                                   or st.session_state.get("loaded_team") != key):
    comp_teams = m_all[m_all.competition == key[0]]
    if key[1] in set(comp_teams.team1) | set(comp_teams.team2):
        st.session_state.update(team_comp=key[0], team_name=key[1], loaded_team=key)

c1, c2 = st.columns([1, 3])
comp = c1.selectbox("Competition", list(load.COMPETITIONS), format_func=load.COMPETITIONS.get, key="team_comp")
m = m_all[m_all.competition == comp]
teams = sorted(set(m.team1) | set(m.team2))
if st.session_state.get("team_name") not in teams:
    st.session_state.team_name = teams[0]
team = c2.selectbox("Team", teams, key="team_name")
st.session_state.loaded_team = (comp, team)
st.query_params.update(comp=comp, team=team)
d = d_all[d_all.match_id.isin(m.match_id)]


def extras(r: dict) -> str:
    return "".join(f" · {r[k]} {label}" for k, label in (("tied", "tied"), ("nr", "NR")) if r[k])


def record_text(r: dict) -> str:
    return f"{r['won']}–{r['lost']}{extras(r)}"


def win_pct(r: dict) -> str:
    decided = r["played"] - r["nr"]
    share = f"{r['won'] / decided:.0%} of {decided} decided" if decided else f"{r['played']} played"
    return share + extras(r)


summary = stats.team_summary(m, team)
st.header(team)
tiles = [("Overall", "overall"), ("Batting first", "batting_first"), ("Chasing", "chasing"),
         (f"{' & '.join(summary['seasons'])} seasons", "last_two_seasons")]
for col, (label, k) in zip(st.columns(4), tiles):
    col.metric(label, f"{summary[k]['won']}–{summary[k]['lost']}", win_pct(summary[k]), delta_color="off", delta_arrow="off", border=True)
st.caption("Won–lost record in the " + load.COMPETITIONS[comp] + ". Ties and no-results are shown separately "
           "when there are any.")

st.subheader("Wins per season")
seasons = stats.wins_by_season(m, team)
bars = alt.Chart(seasons).mark_bar(color=load.CHASE_COLOUR).encode(
    x=alt.X("season:O", title="Season"), y=alt.Y("won:Q", title="Wins"),
    tooltip=["season", "played", "won"],
).properties(height=260)
st.altair_chart(bars, width="stretch")
st.caption("Matches won each season. Hover a bar for matches played.")

st.subheader("Head to head")
h2h = stats.head_to_head(m, team)
st.dataframe(
    h2h.rename(columns={"opponent": "Opponent", "played": "Played", "won": "Won", "lost": "Lost", "tied": "Tied",
                        "nr": "No result"}),
    hide_index=True, width="stretch",
)
st.caption(f"{team}'s record against every side it has played in the {load.COMPETITIONS[comp]}.")
opponent = st.selectbox("Every meeting with", h2h.opponent.tolist())
tm = stats.team_matches(m, team)
for r in tm[tm.opponent == opponent].sort_values("start_date", ascending=False).itertuples():
    first = load.score(r.inn1_team, r.inn1_runs, r.inn1_wkts, r.inn1_balls) if pd.notna(r.inn1_team) else "No play"
    second = load.score(r.inn2_team, r.inn2_runs, r.inn2_wkts, r.inn2_balls) if pd.notna(r.inn2_team) else ""
    label = (f"{r.start_date:%d %b %Y} · {r.result}{' (DLS)' if pd.notna(r.method) else ''} · {first}"
             + (f" v {second}" if second else "") + f" · {r.venue}")
    load.link_match(r.match_id, label)

st.subheader("Where they win and lose: by phase, since 2023")
pt = stats.phase_table(d, m, team)
if pt.empty:
    st.markdown("No matches since 2023.")
else:
    st.markdown(f"**{stats.phase_note(pt)}**")
    st.dataframe(
        pt.round(2).rename(columns={"phase": "Phase", "team_run_rate": f"{team} run rate",
                                    "rest_run_rate": "Others' run rate", "team_wkts": f"{team} wickets lost",
                                    "rest_wkts": "Others' wickets lost"}),
        hide_index=True, width="stretch",
    )
    st.caption("Run rate and wickets lost per innings when batting. Powerplay = overs 1–6, middle = 7–15, "
               f"death = 16–20. 'Others' = every other team in the {load.COMPETITIONS[comp]} over the same years.")

st.subheader("Key players")
bat, bowl = stats.top_players(d, team)
p1, p2 = st.columns(2)
p1.markdown("**Top run scorers**")
p1.dataframe(bat.round(1).rename(columns={"batter": "Batter", "runs": "Runs", "balls": "Balls",
                                          "strike_rate": "Strike rate"}), hide_index=True, width="stretch")
p2.markdown("**Top wicket takers**")
p2.dataframe(bowl.round(2).rename(columns={"bowler": "Bowler", "wickets": "Wickets", "balls": "Balls",
                                           "economy": "Economy"}), hide_index=True, width="stretch")
st.caption(f"All-time, for {team} only.")

venue, rec = stats.most_played_ground(m, team)
st.subheader("Most-played ground")
st.markdown(f"**{venue}**: {record_text(rec)} in {rec['played']} matches.")
