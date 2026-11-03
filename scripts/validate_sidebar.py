"""Local E2E navigation/responsive check using disposable synthetic accounts."""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

import pyotp
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from gsreview.application.container import Container

SCREENS = (
    ("Inicio", "Panorama de revisión"),
    ("Revisión", "Bandeja de revisión"),
    ("Vista espacial", "Vista espacial de prismas"),
    ("Prismas", "Detalle del prisma"),
    ("Datos", "Calidad y cobertura"),
    ("Reportes", "Reportes y trazabilidad"),
    ("Usuarios", "Usuarios y permisos"),
    ("Auditoría", "Auditoría"),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--output", default=str(APP / "reports/phase7/shared_sidebar"))
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    checks, denied = [], []
    with tempfile.TemporaryDirectory(prefix="gs-shared-sidebar-") as temporary:
        runtime = Path(temporary) / "runtime"
        with open(Path(temporary) / "server.log", "w") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(APP / "app.py"),
                    "--server.port",
                    "8504",
                ],
                cwd=APP,
                env={**os.environ, "GEOSLOPE_RUNTIME": str(runtime)},
                stdout=log,
                stderr=log,
            )
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        executable_path=args.chromium,
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--use-gl=angle",
                            "--use-angle=swiftshader",
                            "--enable-unsafe-swiftshader",
                        ],
                    )
                    context = browser.new_context(viewport={"width": 1366, "height": 768})

                    def route(r):
                        if urlsplit(r.request.url).hostname not in ("127.0.0.1", "localhost", None):
                            denied.append(r.request.url)
                            r.abort()
                        else:
                            r.continue_()

                    context.route("**/*", route)
                    page = context.new_page()
                    for _ in range(30):
                        try:
                            page.goto("http://127.0.0.1:8504", timeout=3000)
                            break
                        except Exception:
                            time.sleep(0.3)
                    page.get_by_role("heading", name="Crear administrador", exact=True).wait_for(
                        timeout=20000
                    )
                    password = "Gs!" + secrets.token_hex(12)
                    for label, value in [
                        ("Usuario", "sampleadmin"),
                        ("Nombre visible", "Administrador sintético"),
                        ("Contraseña", password),
                        ("Repetir contraseña", password),
                    ]:
                        page.get_by_label(label, exact=True).fill(value)
                    page.get_by_role("button", name="Crear administrador", exact=True).click()
                    c = Container(runtime=runtime)

                    def enroll(username):
                        page.get_by_label("Código de seis dígitos", exact=True).wait_for()
                        user = next(u for u in c.store.list("users") if u["username"] == username)
                        secret = c.cipher.decrypt(user["totp_cipher"])
                        page.get_by_label("Código de seis dígitos", exact=True).fill(
                            pyotp.TOTP(secret).now()
                        )
                        page.get_by_role("button", name="Verificar", exact=True).click()
                        page.get_by_role("button", name="Ya guardé mis códigos", exact=True).click()

                    enroll("sampleadmin")
                    rail = page.get_by_test_id("stSidebar")

                    def open_profile(label):
                        button = rail.get_by_role("button", name=label, exact=True)
                        if button.get_attribute("aria-expanded") != "true":
                            button.click()

                    def go(label, title):
                        rail.get_by_role("button", name=label, exact=True).click()
                        page.get_by_role("heading", name=title, exact=True).wait_for()
                        page.wait_for_timeout(450)
                        assert not page.get_by_text(
                            "No se pudo completar la operación.", exact=False
                        ).count()
                        assert (
                            rail.get_by_role("button", name=label, exact=True).get_attribute("kind")
                            == "primary"
                        )

                    def geometry(role, label, width, height):
                        box = rail.bounding_box()
                        main = page.locator(".block-container").bounding_box()
                        logout = rail.get_by_role("button", name="Salir", exact=True).bounding_box()
                        assert box["width"] == 88 and box["height"] == height
                        assert main["x"] >= box["x"] + box["width"]
                        assert logout["y"] >= 0 and logout["y"] + logout["height"] <= height
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        assert rail.get_by_role(
                            "button",
                            name="Administrador" if role == "administrador" else "Ingeniero",
                            exact=True,
                        ).is_visible()
                        if label == "Vista espacial":
                            scene = page.locator(".st-key-spatial_scene_panel").bounding_box()
                            assert scene["width"] >= (width - 88) * 0.60
                        checks.append(
                            {
                                "role": role,
                                "screen": label,
                                "resolution": [width, height],
                                "sidebar_width": box["width"],
                                "logout_visible": True,
                                "no_overlap": True,
                            }
                        )

                    temporary_password = "Tmp!" + secrets.token_hex(12)
                    permanent = "Next!" + secrets.token_hex(12)
                    for role in ("administrador", "ingeniero"):
                        available = SCREENS if role == "administrador" else SCREENS[:6]
                        for label, title in available:
                            go(label, title)
                            geometry(role, label, 1366, 768)
                        for width, height in [(1366, 768), (1440, 900), (1920, 1080)]:
                            page.set_viewport_size({"width": width, "height": height})
                            for label, title in SCREENS[:3]:
                                go(label, title)
                                geometry(role, label, width, height)
                                rail.get_by_role("button", name=label, exact=True).hover()
                                assert rail.bounding_box()["width"] == 88
                                page.mouse.move(width - 5, 5)
                                page.wait_for_timeout(700)
                                name = {
                                    "Inicio": "inicio",
                                    "Revisión": "revision",
                                    "Vista espacial": "vista_espacial",
                                }[label]
                                page.screenshot(path=str(output / f"{role}_{name}_{width}.png"))
                        if role == "administrador":
                            page.set_viewport_size({"width": 1366, "height": 768})
                            go("Usuarios", "Usuarios y permisos")
                            page.get_by_text("Crear usuario", exact=True).first.click()
                            page.get_by_label("Nuevo usuario", exact=True).fill("sampleengineer")
                            page.get_by_label("Nombre visible", exact=True).fill(
                                "Ingeniero sintético"
                            )
                            page.get_by_label("Contraseña temporal", exact=True).fill(
                                temporary_password
                            )
                            page.get_by_role("button", name="Crear usuario", exact=True).click()
                            page.get_by_text(
                                "Usuario creado. Debe configurar TOTP al iniciar sesión.",
                                exact=True,
                            ).wait_for()
                            open_profile("Administrador")
                            page.get_by_role("button", name="Mi perfil", exact=True).click()
                            page.get_by_role("heading", name="Mi perfil", exact=True).wait_for()
                            open_profile("Administrador")
                            page.get_by_role(
                                "button", name="Copias de seguridad", exact=True
                            ).click()
                            page.get_by_role(
                                "heading", name="Copias de seguridad cifradas", exact=True
                            ).wait_for()
                        else:
                            for restricted in ("Usuarios", "Auditoría"):
                                assert (
                                    rail.get_by_role("button", name=restricted, exact=True).count()
                                    == 0
                                )
                            open_profile("Ingeniero")
                            assert (
                                page.get_by_role(
                                    "button", name="Copias de seguridad", exact=True
                                ).count()
                                == 0
                            )
                            page.get_by_role("button", name="Mi perfil", exact=True).click()
                            page.get_by_role("heading", name="Mi perfil", exact=True).wait_for()
                            page.set_viewport_size({"width": 1366, "height": 500})
                            assert (
                                rail.get_by_role("button", name="Salir", exact=True).bounding_box()[
                                    "y"
                                ]
                                < 580
                            )
                            assert page.locator(".st-key-rail_links").evaluate(
                                "el=>el.scrollHeight>el.clientHeight"
                            )
                        rail.get_by_role("button", name="Salir", exact=True).click()
                        page.get_by_role("heading", name="Iniciar sesión", exact=True).wait_for()
                        assert not page.get_by_role("heading", name="Mi perfil", exact=True).count()
                        if role == "administrador":
                            page.get_by_label("Usuario", exact=True).fill("sampleengineer")
                            page.get_by_label("Contraseña", exact=True).fill(temporary_password)
                            page.get_by_role("button", name="Iniciar sesión", exact=True).click()
                            enroll("sampleengineer")
                            page.get_by_role("heading", name="Mi perfil", exact=True).wait_for()
                            assert (
                                rail.get_by_role("button", name="Inicio", exact=True).count() == 0
                            )
                            page.get_by_label("Contraseña actual", exact=True).fill(
                                temporary_password
                            )
                            page.get_by_label("Nueva contraseña", exact=True).fill(permanent)
                            page.get_by_label("Confirmar nueva contraseña", exact=True).fill(
                                permanent
                            )
                            page.get_by_role(
                                "button", name="Cambiar contraseña", exact=True
                            ).click()
                            page.get_by_role(
                                "heading", name="Iniciar sesión", exact=True
                            ).wait_for()
                            # New TOTP interval; wait in short increments only for replay protection.
                            wait = 31 - time.time() % 30
                            page.wait_for_timeout(int(wait * 1000))
                            page.get_by_label("Usuario", exact=True).fill("sampleengineer")
                            page.get_by_label("Contraseña", exact=True).fill(permanent)
                            page.get_by_role("button", name="Iniciar sesión", exact=True).click()
                            page.get_by_label("Código de seis dígitos", exact=True).wait_for()
                            user = next(
                                u
                                for u in c.store.list("users")
                                if u["username"] == "sampleengineer"
                            )
                            secret = c.cipher.decrypt(user["totp_cipher"])
                            page.get_by_label("Código de seis dígitos", exact=True).fill(
                                pyotp.TOTP(secret).now()
                            )
                            page.get_by_role("button", name="Verificar", exact=True).click()
                            page.get_by_role(
                                "heading", name="Panorama de revisión", exact=True
                            ).wait_for()
                    assert not denied, denied
                    browser.close()
                (output / "navigation_validation.json").write_text(
                    json.dumps(
                        {
                            "status": "passed",
                            "checks": checks,
                            "external_requests": denied,
                            "roles": ["administrador", "ingeniero"],
                            "logout_both_roles": True,
                            "forced_password_change": True,
                            "short_height_scroll": True,
                            "synthetic_runtime_removed": True,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            finally:
                server.terminate()
                server.wait(timeout=15)


if __name__ == "__main__":
    main()
