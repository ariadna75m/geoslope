import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from gsreview.presentation.spatial_controller import filter_points, accept_selection
from gsreview.application.spatial import SpatialService
from gsreview.domain.rules import AccessDenied


def test_filters_preserve_coordinates_and_candidates(app):
    points = app.reader.spatial("2014-02-20 23:59:59")
    assert len(points) == 49
    filtered = filter_points(points, only_candidates=True)
    assert filtered.candidate_hybrid.fillna(False).all()
    pd.testing.assert_frame_equal(filtered, points.loc[filtered.index])
    assert filter_points(points, "30-1994").prism_id.tolist() == ["30-1994"]
    assert filter_points(points, "missing").empty
    assert (
        filter_points(points, state="Marca estadística")
        .causal_state.isin(["marca_aislada", "episodio_en_observacion"])
        .all()
    )


def test_click_event_rejects_invented_id_duplicates_and_invalid_camera():
    assert accept_selection(
        {"prism_id": "22-1917", "nonce": 1, "camera": None}, ["22-1917"], None
    ) == ("22-1917", None, 1)
    assert accept_selection({"prism_id": "invented", "nonce": 2}, ["22-1917"], 1) is None
    assert accept_selection({"prism_id": "22-1917", "nonce": 1}, ["22-1917"], 1) is None
    assert (
        accept_selection(
            {"prism_id": "22-1917", "nonce": 2, "camera": {"eye": {"x": float("inf")}}},
            ["22-1917"],
            1,
        )
        is None
    )


def test_spatial_service_requires_auth_and_logs_once_per_explicit_access(app):
    service = SpatialService(app)
    with pytest.raises(AccessDenied):
        service.points("invalid", pd.Timestamp("2014-02-20"))
    count = len(app.store.list("audit_log"))
    service.log_access(app.test_admin, "spatial_view_opened")
    assert len(app.store.list("audit_log")) == count + 1
    rows = service.series(app.test_admin, "30-1994", pd.Timestamp("2014-01-01"))
    assert rows.timestamp.le(pd.Timestamp("2014-01-01")).all()


def test_no_arbitrary_selection_and_linked_histories(app, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = "Vista espacial"
    at.run()
    assert not at.error and not at.exception
    assert at.selectbox(key="sx_selected").value is None
    at.selectbox(key="sx_selected").set_value("30-1994").run()
    assert any(x.value == "Prisma 30-1994" for x in at.subheader)
    assert at.metric[1].value == "15"
    at.button(key="sx_history").click().run()
    assert (
        at.session_state["nav"] == "Prismas" and at.selectbox(key="detail_prism").value == "30-1994"
    )


def test_review_action_opens_same_prism_episode(app, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = "Vista espacial"
    at.run()
    at.selectbox(key="sx_selected").set_value("30-1994").run()
    at.button(key="sx_review").click().run()
    assert not at.exception and not at.error
    assert at.session_state["nav"] == "Bandeja de revisión"
    ep = app.reader.episodes.set_index("episode_id").loc[
        at.selectbox(key="inbox_open_episode").value
    ]
    assert ep.prism_id == "30-1994"


def test_compact_rail_opens_real_page(app, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = "Vista espacial"
    at.run()
    at.button(key="rail_Prismas").click().run()
    assert not at.error and not at.exception
    assert at.session_state["nav"] == "Prismas"
    assert any(x.value == "Detalle del prisma" for x in at.title)
    at.button(key="rail_Inicio").click().run()
    [button for button in at.button if button.label == "Revisar candidatos pendientes"][
        0
    ].click().run()
    assert not at.error and at.session_state["current_page"] == "Bandeja de revisión"


def test_engineer_compact_navigation_has_no_administrative_actions(app, monkeypatch):
    import pyotp

    app.auth.create_user(
        app.test_admin, "sampleengineer", "Ingeniero sintético", app.test_temporary, "ingeniero"
    )
    challenge, _ = app.auth.password_step("sampleengineer", app.test_temporary)
    _, secret = app.auth.enrollment(challenge)
    token, _ = app.auth.second_step(
        challenge, pyotp.TOTP(secret).at(app.test_clock[0]), enroll=True
    )
    app.auth.change_password(token, app.test_temporary, app.test_permanent)
    app.test_clock[0] += 31
    challenge, _ = app.auth.password_step("sampleengineer", app.test_permanent)
    token, _ = app.auth.second_step(challenge, pyotp.TOTP(secret).at(app.test_clock[0]))
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = token
    at.session_state["nav"] = "Vista espacial"
    at.run()
    assert not at.error and not at.exception
    keys = {button.key for button in at.button}
    assert "rail_Prismas" in keys
    assert not keys.intersection({"rail_Usuarios", "rail_Auditoría", "rail_Copias de seguridad"})
