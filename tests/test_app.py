from streamlit.testing.v1 import AppTest

ENTRY = "../app/streamlit_app.py"


def page(path=None, **params):
    at = AppTest.from_file(ENTRY, default_timeout=120)
    at.query_params.update(params)
    at.run()
    if path:
        at.switch_page(path).run()
    return at


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
