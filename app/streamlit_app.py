import streamlit as st

st.set_page_config(page_title="T20 Win Probability", layout="wide")
st.navigation([
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/match.py", title="Matches", url_path="match"),
    st.Page("views/team.py", title="Teams", url_path="team"),
    st.Page("views/about.py", title="About the model", url_path="about"),
]).run()
