import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
COMPETITIONS = {"ipl": "IPL", "bbl": "BBL", "t20i": "T20I"}
CHASE_COLOUR = "#2563eb"
DEFEND_COLOUR = "#ea580c"
MATCH_PAGE = "views/match.py"
TEAM_PAGE = "views/team.py"


@st.cache_data
def matches() -> pd.DataFrame:
    return pd.read_parquet(DATA / "matches.parquet")


@st.cache_data
def deliveries() -> pd.DataFrame:
    return pd.read_parquet(DATA / "deliveries.parquet")


@st.cache_data
def findings() -> dict:
    return json.loads((DATA / "findings.json").read_text())


@st.cache_data
def metrics() -> dict:
    return json.loads((DATA / "metrics.json").read_text())


@st.cache_data
def calibration() -> pd.DataFrame:
    return pd.read_parquet(DATA / "calibration.parquet")


@st.cache_data
def players() -> pd.DataFrame:
    return pd.read_parquet(DATA / "player_value.parquet")


def score(team, runs, wkts, balls) -> str:
    if pd.isna(runs):
        return f"{team} did not bat"
    return f"{team} {runs}/{wkts} ({balls // 6}.{balls % 6} ov)"


def link_match(match_id: str, label: str) -> None:
    st.page_link(MATCH_PAGE, label=label, query_params={"id": match_id})


def link_team(comp: str, team: str, label: str | None = None) -> None:
    st.page_link(TEAM_PAGE, label=label or team, query_params={"comp": comp, "team": team})
