from streamlit.testing.v1 import AppTest


def test_app_renders_every_tab_without_errors():
    at = AppTest.from_file("../app/streamlit_app.py", default_timeout=120).run()
    assert not at.exception
    at.radio[0].set_value("bowl").run()
    at.radio[1].set_value("Underrated vs raw stats").run()
    assert not at.exception
