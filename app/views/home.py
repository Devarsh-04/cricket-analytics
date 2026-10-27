import streamlit as st

import load

FEATURED = "1535465"

st.title("What decides a T20 chase?")
st.markdown(
    "Ball-by-ball win chance for every IPL, BBL and men's T20I chase since 2005, built from "
    "Cricsheet data. Pick any match to see how the chase swung, or any team to see its record."
)

f = load.findings()
before, since = f["ipl_200_chases"]["before_2023"], f["ipl_200_chases"]["since_2023"]
swing, wicket = f["swing_per_ball"], f["wicket_cost"]

c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.metric("IPL chases of 200+ won", f"{since['won'] / since['n']:.0%}",
              f"up from {before['won'] / before['n']:.0%} before 2023", delta_color="off")
    st.caption(
        f"Since 2023, IPL teams chasing 200+ have won {since['won']} of {since['n']}. "
        f"Before that it was {before['won']} of {before['n']}. Big totals are no longer safe."
    )
with c2.container(border=True):
    st.metric("Win-chance swing per death-over ball", f"{swing['death']} pts",
              f"vs {swing['powerplay']} in the powerplay, {swing['middle']} in the middle",
              delta_color="off", delta_arrow="off")
    st.caption("Each ball in overs 16–20 moves the chasing side's win chance the most. "
               "Measured on 2025–26 matches the model never trained on.")
with c3.container(border=True):
    st.metric("Cost of losing a wicket", f"{wicket} pts")
    st.caption(f"On average, a wicket knocks {wicket} percentage points off the chasing side's win chance.")

st.subheader("Featured match")
m = load.matches()
row = m[m.match_id == FEATURED]
row = (row if len(row) else m[m.has_wp].tail(1)).iloc[0]
with st.container(border=True):
    st.markdown(f"**{load.COMPETITIONS[row.competition]} · {row.start_date:%d %b %Y} · {row.venue}**")
    st.markdown(f"{load.score(row.inn1_team, row.inn1_runs, row.inn1_wkts, row.inn1_balls)}  \n"
                f"{load.score(row.inn2_team, row.inn2_runs, row.inn2_wkts, row.inn2_balls)}")
    st.markdown(f"{row.inn2_team} started the chase with a **{row.start_wp:.0%}** win chance. {row.winner} won.")
    load.link_match(row.match_id, "See how the chase unfolded →")

st.subheader("Explore")
c1, c2 = st.columns(2)
c1.page_link(load.MATCH_PAGE, label="Browse matches", icon="🏏")
c2.page_link(load.TEAM_PAGE, label="Browse teams", icon="📊")
