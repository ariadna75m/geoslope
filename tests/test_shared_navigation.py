"""Regression coverage for navigation across modules, roles and forced reset."""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import engineer


SCREENS = (
    ("Inicio", "Panorama de revisión"),
    ("Bandeja de revisión", "Bandeja de revisión"),
    ("Vista espacial", "Vista espacial de prismas"),
    ("Prismas", "Detalle del prisma"),
    ("Calidad de datos", "Calidad y cobertura"),
    ("Reportes", "Reportes y trazabilidad"),
    ("Usuarios", "Usuarios y permisos"),
    ("Auditoría", "Auditoría"),
    ("Mi perfil", "Mi perfil"),
    ("Copias de seguridad", "Copias de seguridad cifradas"),
)


@pytest.mark.parametrize("destination,title", SCREENS)
def test_shared_rail_preserves_destination_when_leaving_another_module(
    app, monkeypatch, destination, title
):
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = app.test_admin
    at.session_state["nav"] = "Prismas" if destination != "Prismas" else "Inicio"
    at.run()
    at.button(key="rail_" + destination).click().run()
    assert not at.error and not at.exception
    assert at.session_state["current_page"] == destination
    assert at.session_state["nav"] == destination
    assert any(t.value == title for t in at.title)
    at.run()  # Subsequent rerender must retain the destination.
    assert at.session_state["current_page"] == destination
    assert at.button(key="rail_logout_button")


def test_engineer_cannot_restore_or_navigate_to_admin_destination(app, monkeypatch):
    _, token, _ = engineer(app)
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = token
    at.session_state["current_page"] = "Usuarios"
    at.run()
    assert not at.error and not at.exception
    assert at.session_state["current_page"] == "Inicio"
    forbidden = {"rail_Usuarios", "rail_Auditoría", "rail_Copias de seguridad"}
    for page in (
        "Inicio",
        "Bandeja de revisión",
        "Vista espacial",
        "Prismas",
        "Calidad de datos",
        "Reportes",
        "Mi perfil",
    ):
        at.button(key="rail_" + page).click().run()
        assert not at.error and not at.exception
        assert not forbidden.intersection(b.key for b in at.button)
    at.button(key="rail_logout_button").click().run()
    assert "token" not in at.session_state


def test_forced_password_change_only_offers_profile(app, monkeypatch):
    app.auth.create_user(
        app.test_admin, "newengineer", "Usuario sintético", app.test_temporary, "ingeniero"
    )
    import pyotp

    challenge, _ = app.auth.password_step("newengineer", app.test_temporary)
    _, secret = app.auth.enrollment(challenge)
    token, _ = app.auth.second_step(
        challenge, pyotp.TOTP(secret).at(app.test_clock[0]), enroll=True
    )
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=20)
    at.session_state["token"] = token
    at.run()
    assert not at.error and not at.exception
    assert at.session_state["current_page"] == "Mi perfil"
    keys = {b.key for b in at.button}
    assert "rail_Mi perfil" in keys
    assert "rail_Inicio" not in keys
