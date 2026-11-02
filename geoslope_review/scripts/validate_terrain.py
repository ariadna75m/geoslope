import sys
import os
import secrets
import tempfile
import subprocess
import time
import json
from pathlib import Path
from urllib.parse import urlsplit
import pyotp
from playwright.sync_api import sync_playwright
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--chromium", required=True)
args = parser.parse_args()
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from gsreview.application.container import Container

OUT = APP / "reports/phase7/terrain_integration"
OUT.mkdir(parents=True, exist_ok=True)
checks = []
external = []
errors = []
with tempfile.TemporaryDirectory(prefix="century-relief-e2e-") as temporary:
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
                "8510",
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
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900}, accept_downloads=True
                )

                def route(r):
                    if urlsplit(r.request.url).hostname not in ("127.0.0.1", "localhost", None):
                        external.append(r.request.url)
                        r.abort()
                    else:
                        r.continue_()

                context.route("**/*", route)
                page = context.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                for _ in range(40):
                    try:
                        page.goto("http://127.0.0.1:8510", timeout=2500)
                        break
                    except Exception:
                        time.sleep(0.25)
                page.get_by_role("heading", name="Crear administrador", exact=True).wait_for(
                    timeout=20000
                )
                password = "Gs!" + secrets.token_hex(12)
                for label, value in [
                    ("Usuario", "terrainadmin"),
                    ("Nombre visible", "Administrador de prueba"),
                    ("Contraseña", password),
                    ("Repetir contraseña", password),
                ]:
                    page.get_by_label(label, exact=True).fill(value)
                page.get_by_role("button", name="Crear administrador", exact=True).click()
                page.get_by_label("Código de seis dígitos", exact=True).wait_for()
                c = Container(runtime=runtime)
                u = next(u for u in c.store.list("users") if u["username"] == "terrainadmin")
                secret = c.cipher.decrypt(u["totp_cipher"])
                page.get_by_label("Código de seis dígitos", exact=True).fill(
                    pyotp.TOTP(secret).now()
                )
                page.get_by_role("button", name="Verificar", exact=True).click()
                page.get_by_role("button", name="Ya guardé mis códigos", exact=True).click()
                page.get_by_test_id("stSidebar").get_by_role(
                    "button", name="Vista espacial", exact=True
                ).click()
                page.get_by_role("heading", name="Vista espacial de prismas", exact=True).wait_for()
                page.get_by_text("Mostrar relieve de Century Mine", exact=True).click()
                page.get_by_text("Relieve real · Copernicus GLO-30", exact=True).wait_for()

                def frame_with(kind):
                    for _ in range(100):
                        for f in page.frames:
                            try:
                                if f.evaluate(
                                    "kind=>{const p=document.getElementById('plot');return !!p&&!!p.data&&p.data.some(t=>t.type===kind)}",
                                    kind,
                                ):
                                    return f
                            except Exception:
                                pass
                        page.wait_for_timeout(150)
                    raise AssertionError("Missing plot " + kind)

                f = frame_with("surface")
                a = f.evaluate(
                    "()=>{let p=document.getElementById('plot');return {type:p.data[0].type,rows:p.data[0].z.length,columns:p.data[0].z[0].length,traceCount:p.data.length,zMin:Math.min(...p.data[0].z.flat()),ratio:p.layout.scene.aspectratio.z}}"
                )
                assert (
                    a["rows"] == 216
                    and a["columns"] == 216
                    and a["traceCount"] == 1
                    and a["zMin"] < 0
                )
                checks.append({"case": "3D real surface, no prism overlay", "result": a})
                assert page.get_by_label("Buscar prisma", exact=True).is_disabled()
                page.screenshot(path=str(OUT / "Relieve_integrado_3D.png"))
                page.get_by_text("2D", exact=True).click()
                f = frame_with("heatmap")
                checks.append(
                    {
                        "case": "2D heatmap",
                        "result": f.evaluate(
                            "()=>({type:document.getElementById('plot').data[0].type,longitude:document.getElementById('plot').data[0].x[0],latitude:document.getElementById('plot').data[0].y[0]})"
                        ),
                    }
                )
                page.wait_for_timeout(900)
                page.get_by_label("Exageración vertical", exact=True).wait_for(state="hidden")
                page.screenshot(path=str(OUT / "Relieve_integrado_2D.png"))
                page.get_by_text("3D", exact=True).click()
                frame_with("surface")
                page.get_by_text("Fuente y archivo de relieve", exact=True).click()
                with page.expect_download() as downloaded:
                    page.get_by_role("button", name="Descargar GeoTIFF", exact=True).click()
                d = downloaded.value
                assert d.suggested_filename == "century_copernicus_dsm_30m.tif"
                d.save_as(str(Path(temporary) / "download.tif"))
                assert (Path(temporary) / "download.tif").read_bytes() == (
                    APP / "assets/terrain/century_copernicus_dsm_30m.tif"
                ).read_bytes()
                checks.append({"case": "GeoTIFF download exact bytes", "passed": True})
                page.get_by_text("Mostrar relieve de Century Mine", exact=True).click()
                frame_with("scatter3d")
                assert page.get_by_label("Buscar prisma", exact=True).is_enabled()
                checks.append({"case": "Return to original prisms", "passed": True})
                assert not external, external
                assert not errors, errors
                browser.close()
            (OUT / "browser_validation.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "checks": checks,
                        "external_requests": external,
                        "page_errors": errors,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            print(json.dumps({"status": "passed", "cases": len(checks)}))
        finally:
            server.terminate()
            server.wait(timeout=15)
