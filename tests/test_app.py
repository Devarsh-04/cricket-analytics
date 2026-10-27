import pandas as pd
from streamlit.testing.v1 import AppTest

ENTRY = "../app/streamlit_app.py"


def page(path=None, **params):
    at = AppTest.from_file(ENTRY, default_timeout=120).run()
    if path:
        at.switch_page(path)
    at.query_params.update(params)
    return at.run()


def text(at):
    return " ".join(e.value for e in [*at.markdown, *at.caption, *at.title, *at.header, *at.subheader])


def test_entry_renders():
    at = page()
    assert not at.exception


def test_home_renders():
    at = page()
    assert not at.exception
    assert "%" in text(at)
    assert "200+" in text(at)


def test_about_renders():
    at = page("views/about.py")
    assert not at.exception
    at.radio[0].set_value("bowl").run()
    at.radio[1].set_value("Underrated vs raw stats").run()
    assert not at.exception


def test_match_page_with_wp():
    at = page("views/match.py", id="1535465")
    assert not at.exception
    assert "Starting win chance" in [m.label for m in at.metric]


def test_match_page_tie():
    m = pd.read_parquet("app/data/matches.parquet")
    tie = m[(m.outcome == "tie") & m.inn2_runs.notna()].match_id.iloc[0]
    at = page("views/match.py", id=tie)
    assert not at.exception
    assert any("No win-chance line" in i.value for i in at.info)


def test_match_page_bad_id():
    at = page("views/match.py", id="nope")
    assert not at.exception
    assert len(at.selectbox) >= 4


def test_team_page_rcb():
    at = page("views/team.py", comp="ipl", team="Royal Challengers Bengaluru")
    assert not at.exception
    assert len(at.dataframe) >= 1
    assert "Chennai Super Kings" in text(at) or any("Chennai" in str(df.value) for df in at.dataframe)


def test_team_page_short_lived_team():
    at = page("views/team.py", comp="ipl", team="Kochi Tuskers Kerala")
    assert not at.exception
    assert "No matches since 2023" in text(at)


def test_team_page_bad_team():
    at = page("views/team.py", comp="ipl", team="Foo")
    assert not at.exception
    assert len(at.selectbox) >= 2


def test_match_link_reopened_after_other_page():
    at = page("views/match.py", id="897697")
    at.switch_page("views/home.py").run()
    at.switch_page("views/match.py")
    at.query_params.clear()
    at.query_params.update(id="897697")
    at.run()
    assert at.header[0].value == "Adelaide Strikers v Melbourne Stars"


def test_team_link_reopened_after_other_page():
    at = page("views/team.py", comp="bbl", team="Hobart Hurricanes")
    at.switch_page("views/home.py").run()
    at.switch_page("views/team.py")
    at.query_params.clear()
    at.query_params.update(comp="bbl", team="Hobart Hurricanes")
    at.run()
    assert at.header[0].value == "Hobart Hurricanes"


def test_win_pct_names_its_denominator():
    at = page("views/team.py", comp="ipl", team="Royal Challengers Bengaluru")
    overall = next(m for m in at.metric if m.label == "Overall")
    assert "of 283 decided" in overall.delta
