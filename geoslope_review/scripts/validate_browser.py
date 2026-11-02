"""Prueba E2E local opcional. Usa una base efímera; nunca cuentas reales."""

import argparse
import json
import os
import secrets
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
import pyotp
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from gsreview.application.container import Container


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", default=None)
    parser.add_argument("--output", default=str(APP / "reports/phase7/screenshots"))
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    observations = []
    with tempfile.TemporaryDirectory(prefix="gs-browser-test-") as temporary:
        runtime = Path(temporary) / "runtime"
        env = {**os.environ, "GEOSLOPE_RUNTIME": str(runtime)}
        log = open(Path(temporary) / "server.log", "w")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(APP / "app.py"),
                "--server.port",
                "8502",
            ],
            cwd=APP,
            env=env,
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
                context = browser.new_context(
                    viewport={"width": 1440, "height": 1050}, accept_downloads=True
                )
                denied = []

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
                        page.goto("http://127.0.0.1:8502", timeout=3000)
                        break
                    except Exception:
                        time.sleep(0.3)
                page.get_by_role("heading", name="Crear administrador", exact=True).wait_for(
                    timeout=20000
                )
                password = "Gs!" + secrets.token_hex(12)
                page.get_by_label("Usuario", exact=True).fill("sampleadmin")
                page.get_by_label("Nombre visible", exact=True).fill("Administrador sintético")
                page.get_by_label("Contraseña", exact=True).fill(password)
                page.get_by_label("Repetir contraseña", exact=True).fill(password)
                page.get_by_role("button", name="Crear administrador", exact=True).click()
                page.get_by_role("heading", name="Configurar segundo factor", exact=True).wait_for()
                page.get_by_label("Código de seis dígitos", exact=True).wait_for()
                page.wait_for_timeout(600)
                page.screenshot(
                    path=str(output / "02_totp_setup.png"),
                    mask=[page.get_by_test_id("stImage")],
                    mask_color="#8995a2",
                )
                c = Container(runtime=runtime)
                user = c.store.list("users")[0]
                secret = c.cipher.decrypt(user["totp_cipher"])
                page.get_by_label("Código de seis dígitos", exact=True).fill(
                    pyotp.TOTP(secret).now()
                )
                page.get_by_role("button", name="Verificar", exact=True).click()
                page.get_by_role("button", name="Ya guardé mis códigos", exact=True).wait_for()
                page.get_by_role("button", name="Ya guardé mis códigos", exact=True).click()
                page.get_by_role("heading", name="Panorama de revisión").wait_for()
                page.get_by_test_id("stMetricValue").first.wait_for()
                page.locator(".js-plotly-plot").first.wait_for()
                page.wait_for_timeout(700)
                page.screenshot(path=str(output / "03_inicio.png"))
                observations.append("Bootstrap, TOTP y dashboard correctos")
                page.get_by_role("button", name="Revisar candidatos pendientes", exact=True).click()
                page.get_by_role("heading", name="Bandeja de revisión", exact=True).wait_for()
                for label, filename, title in [
                    ("Bandeja de revisión", "04_bandeja.png", "Bandeja de revisión"),
                    ("Vista espacial", "07_espacial.png", "Vista espacial de prismas"),
                    ("Prismas", "08_prisma.png", "Detalle del prisma"),
                    ("Calidad de datos", "09_calidad.png", "Calidad y cobertura"),
                    ("Usuarios", "10_usuarios.png", "Usuarios y permisos"),
                    ("Auditoría", "11_auditoria.png", "Auditoría"),
                    ("Reportes", "12_reportes.png", "Reportes y trazabilidad"),
                ]:
                    rail = page.get_by_test_id("stSidebar")
                    nav_button = rail.get_by_role("button", name=re.compile(re.escape({"Bandeja de revisión":"Revisión","Calidad de datos":"Datos"}.get(label,label)) + "$"))
                    if nav_button.count():
                        nav_button.click()
                    else:
                        rail.get_by_text(label, exact=True).first.click()
                    page.wait_for_timeout(400)
                    page.get_by_role("heading", name=title, exact=True).wait_for()
                    page.get_by_text("No se pudo completar la operación.", exact=False).wait_for(
                        state="hidden", timeout=1000
                    )
                    page.get_by_role("heading", name=title, exact=True).scroll_into_view_if_needed()
                    page.wait_for_timeout(900)
                    page.screenshot(path=str(output / filename))
                    observations.append(label + " visible y sin errores")
                    if label == "Vista espacial":
                        page.get_by_label("Prisma seleccionado", exact=True).click()
                        page.get_by_role("option", name="22-1917", exact=True).click()
                        page.get_by_role("button", name="Centrar", exact=True).click()
                        page.wait_for_timeout(900)
                        frame3d = [f for f in page.frames if "geoslope_spatial_scene" in f.url][0]
                        frame3d.wait_for_function(
                            "document.getElementById('plot')._fullLayout.scene"
                        )
                        frame3d.evaluate(
                            "document.getElementById('plot').on('plotly_click', e=>window.gsTestClick=e.points[0].customdata[0])"
                        )
                        size = frame3d.evaluate("document.getElementById('plot')._fullLayout._size")
                        box = frame3d.locator("#plot").bounding_box()
                        for dx, dy in [(0, 0), (0, 10), (0, -10), (10, 0), (-10, 0)]:
                            page.mouse.move(
                                box["x"] + size["l"] + size["w"] / 2 + dx,
                                box["y"] + size["t"] + size["h"] / 2 + dy,
                            )
                            page.wait_for_timeout(600)
                            page.mouse.down()
                            page.wait_for_timeout(100)
                            page.mouse.up()
                            page.wait_for_timeout(300)
                            if frame3d.evaluate("window.gsTestClick || null"):
                                break
                        clicked3d = frame3d.evaluate("window.gsTestClick || null")
                        assert clicked3d, "Clic 3D real no recibido"
                        page.get_by_role(
                            "heading", name="Prisma " + clicked3d, exact=True
                        ).wait_for()
                        observations.append("Clic real sobre prisma 3D actualiza la ficha")
                        full = frame3d.get_by_role("button", name="Pantalla completa", exact=True)
                        if full.is_visible():
                            full.click()
                            frame3d.wait_for_function("document.fullscreenElement !== null")
                            full.click()
                            frame3d.wait_for_function("document.fullscreenElement === null")
                            observations.append("Pantalla completa local comprobada")
                        page.mouse.move(5, 5)
                        page.screenshot(path=str(output / "13_espacial_centrada.png"))
                        page.get_by_role("button", name="Vista completa", exact=True).click()
                        frames = [f for f in page.frames if "geoslope_spatial_scene" in f.url]
                        assert frames, "Componente espacial local no disponible"
                        frame = frames[0]
                        frame.wait_for_function("document.getElementById('plot').data.length > 0")
                        for width, height in [(1366, 768), (1440, 900), (1920, 1080)]:
                            page.set_viewport_size({"width": width, "height": height})
                            page.wait_for_timeout(600)
                            rail = page.get_by_test_id("stSidebar").bounding_box()
                            scene = page.locator(".st-key-spatial_scene_panel").bounding_box()
                            assert rail["width"] <= 90
                            assert scene["width"] >= (width - rail["width"]) * 0.60
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth"
                            )
                            page.get_by_role("button", name="Vista completa", exact=True).evaluate(
                                "el=>el.blur()"
                            )
                            page.mouse.move(5, 5)
                            page.wait_for_timeout(1200)
                            page.screenshot(path=str(output / f"compact_3d_{width}.png"))
                        page.set_viewport_size({"width": 1440, "height": 900})
                        page.get_by_text("2D", exact=True).click()
                        page.wait_for_timeout(900)
                        frame.locator(".scatterlayer .points path.point").first.click(force=True)
                        page.wait_for_timeout(800)
                        page.get_by_role("heading", name=re.compile("^Prisma ")).wait_for()
                        page.screenshot(path=str(output / "14_espacial_2d.png"))
                        page.get_by_label("Buscar prisma", exact=True).fill("30-1994")
                        page.get_by_label("Buscar prisma", exact=True).press("Enter")
                        page.wait_for_timeout(500)
                        page.get_by_label("Prisma seleccionado", exact=True).click()
                        page.get_by_role("option", name="30-1994", exact=True).click()
                        page.wait_for_timeout(600)
                        assert (
                            page.get_by_role("heading", name="Prisma 30-1994", exact=True).count()
                            == 1
                        )
                        page.get_by_text("Solo candidatos", exact=True).click()
                        page.wait_for_timeout(500)
                        page.get_by_text("Etiquetas", exact=True).click()
                        page.wait_for_timeout(500)
                        page.screenshot(path=str(output / "compact_filtered.png"))
                        page.get_by_label("Buscar prisma", exact=True).fill("NO-EXISTE")
                        page.get_by_label("Buscar prisma", exact=True).press("Enter")
                        page.get_by_text(
                            "No existen prismas con los filtros aplicados.", exact=False
                        ).wait_for()
                        page.screenshot(path=str(output / "compact_empty.png"))
                        page.get_by_role("button", name="filter_alt_off", exact=False).click()
                        page.wait_for_timeout(500)
                        observations.append(
                            "Prismas, filtros, selección de punto y tres resoluciones validados"
                        )
                        assert (
                            page.get_by_text(
                                "No se pudo completar la operación.", exact=False
                            ).count()
                            == 0
                        )
                        observations.append("Centrado, vista completa y plano 2D comprobados")
                    if label == "Bandeja de revisión":
                        page.get_by_role("heading", name="Episodio ·", exact=False).evaluate(
                            "(e) => e.scrollIntoView({block: 'start'})"
                        )
                        page.wait_for_timeout(500)
                        page.screenshot(path=str(output / "05_detalle.png"))
                        page.get_by_role(
                            "heading", name="Evaluación del especialista", exact=True
                        ).scroll_into_view_if_needed()
                        page.get_by_label("Comentario técnico", exact=True).fill(
                            "Revisión sintética exclusivamente para validar persistencia."
                        )
                        page.get_by_role("button", name="Guardar evaluación", exact=True).click()
                        page.get_by_text(
                            "Evaluación guardada con historial y auditoría.", exact=True
                        ).wait_for()
                        page.screenshot(path=str(output / "06_evaluacion.png"))
                        assert len(c.store.list("review_history")) == 1
                    if label == "Reportes":
                        page.get_by_role("button", name="Generar reporte", exact=True).click()
                        page.get_by_role("button", name="Descargar reporte", exact=True).wait_for()
                        with page.expect_download() as download:
                            page.get_by_role("button", name="Descargar reporte", exact=True).click()
                        download.value.save_as(str(Path(temporary) / "example.pdf"))
                        assert (Path(temporary) / "example.pdf").read_bytes().startswith(b"%PDF")
                page.get_by_test_id("stSidebar").get_by_role("button", name="Administrador", exact=True).click()
                page.get_by_role("button", name="Copias de seguridad", exact=True).click()
                page.get_by_role("button", name="Crear copia de seguridad", exact=True).click()
                page.get_by_text("Copia cifrada creada y registrada.", exact=True).wait_for()
                assert list((runtime / "backups").glob("*.gsbackup"))
                page.get_by_role("button", name="Salir", exact=True).click()
                page.get_by_role("heading", name="Iniciar sesión", exact=True).wait_for()
                page.screenshot(path=str(output / "01_login.png"))
                assert not page.get_by_role("heading", name="Panorama de revisión").count()
                assert not denied, "Solicitudes externas: " + str(denied)
                observations.extend(
                    [
                        "Revisión persistida",
                        "PDF descargado",
                        "Backup cifrado creado",
                        "Logout elimina acceso",
                        "Cero solicitudes externas",
                    ]
                )
                (output.parent / "browser_validation.json").write_text(
                    json.dumps(
                        {
                            "status": "passed",
                            "observations": observations,
                            "external_requests": denied,
                            "synthetic_runtime_removed": True,
                            "screenshots_redact_totp": True,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)
            log.close()


if __name__ == "__main__":
    main()
