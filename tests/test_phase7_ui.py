import secrets
import pyotp
import pytest
from streamlit.testing.v1 import AppTest
from gsreview.application.container import Container
from gsreview.presentation.views import NAV


def test_initial_setup_totp_dashboard_and_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(tmp_path))
    appfile = __import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"
    at = AppTest.from_file(str(appfile), default_timeout=15).run()
    assert not at.error and not at.exception
    password = "Gs!" + secrets.token_hex(12)
    at.text_input(key="setup_username").set_value("sampleadmin")
    at.text_input(key="setup_name").set_value("Administrador sintético")
    at.text_input(key="setup_password").set_value(password)
    at.text_input(key="setup_repeat").set_value(password)
    at.button[0].click().run()
    c = Container(runtime=tmp_path)
    _, secret = c.auth.enrollment(at.session_state["challenge"])
    at.text_input(key="otp_code").set_value(pyotp.TOTP(secret).now())
    at.button[0].click().run()
    assert "token" in at.session_state and len(at.session_state["recovery_once"]) == 10
    at.button[0].click().run()
    assert not at.error and not at.exception
    assert at.metric[0].value == "49"
    at.button(key="rail_logout_button").click().run()
    assert "token" not in at.session_state and not at.error


@pytest.mark.parametrize("page", NAV)
def test_every_screen_has_auth_guard_and_renders_for_admin(app, monkeypatch, page):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    appfile = app.app_root / "app.py"
    at = AppTest.from_file(str(appfile), default_timeout=15)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = page
    at.run()
    assert not at.exception and not at.error
    assert any(
        x.value
        in (
            page,
            "GeoSlope Review",
            "Panorama de revisión",
            "Vista espacial instrumental",
            "Vista espacial de prismas",
            "Detalle del prisma",
            "Calidad y cobertura",
            "Reportes y trazabilidad",
            "Usuarios y permisos",
            "Copias de seguridad cifradas",
            "Mi perfil",
        )
        for x in at.title
    )


def test_ui_no_access_with_invalid_session_and_unknown_nav(app, monkeypatch):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=15)
    at.session_state["token"] = "invalid"
    at.session_state["nav"] = "Usuarios"
    at.run()
    assert not at.exception and "token" not in at.session_state
    assert not at.metric
