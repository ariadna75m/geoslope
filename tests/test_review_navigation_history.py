import json

import pytest
from streamlit.testing.v1 import AppTest

from conftest import engineer
from gsreview.application.container import Container


@pytest.mark.parametrize("role", ["administrador", "ingeniero"])
def test_saved_review_and_selected_episode_survive_module_navigation(app, monkeypatch, role):
    token = app.test_admin if role == "administrador" else engineer(app)[1]
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = token
    at.session_state["nav"] = "Bandeja de revisión"
    at.run()
    at.selectbox(key="inbox_prism").set_value("30-1993").run()
    episode = "ep_ddc5d76ce43498aa61c16919"
    at.selectbox(key="inbox_open_episode").set_value(episode).run()
    comment = "Ejercicio sintético: comprobar la persistencia de la revisión al navegar."
    next(s for s in at.selectbox if s.label == "Estado de revisión").set_value(
        "Requiere más información"
    )
    next(t for t in at.text_area if t.label == "Comentario técnico").set_value(comment)
    next(b for b in at.button if b.label == "Guardar evaluación").click().run()
    assert not at.error and not at.exception
    assert len(app.reviews.history(token, episode)) == 1
    at.button(key="rail_Reportes").click().run()
    assert len(app.reviews.history(token, episode)) == 1
    at.button(key="rail_Bandeja de revisión").click().run()
    assert not at.error and not at.exception
    assert at.selectbox(key="inbox_prism").value == "30-1993"
    assert at.selectbox(key="inbox_open_episode").value == episode
    assert next(t for t in at.text_area if t.label == "Comentario técnico").value == comment
    assert any(
        episode in d.value.get("episode_id", []).tolist()
        for d in at.dataframe
        if "episode_id" in d.value.columns and "version" in d.value.columns
    )
    restarted = Container(runtime=app.runtime, clock=app.auth.clock)
    assert restarted.reviews.get(token, episode)["comment"] == comment
    assert len(restarted.reviews.history(token, episode)) == 1
    report = json.loads(restarted.reports.generate(token, "episodio", episode, "JSON"))
    assert report["reviews"][0]["comment"] == comment


def test_spatial_episode_link_overrides_saved_review_context(app, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = "Bandeja de revisión"
    at.run()
    at.selectbox(key="inbox_prism").set_value("30-1993").run()
    at.selectbox(key="inbox_open_episode").set_value("ep_ddc5d76ce43498aa61c16919").run()
    at.button(key="rail_Reportes").click().run()
    # The spatial module supplies these keys when opening a different episode.
    at.session_state["inbox_prism"] = "22-1917"
    at.session_state["inbox_open_episode"] = "ep_7fae3c3a154b2f4ec76e44c3"
    at.button(key="rail_Bandeja de revisión").click().run()
    assert not at.error and not at.exception
    assert at.selectbox(key="inbox_prism").value == "22-1917"
    assert at.selectbox(key="inbox_open_episode").value == "ep_7fae3c3a154b2f4ec76e44c3"
