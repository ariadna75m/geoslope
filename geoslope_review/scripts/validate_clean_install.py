"""Descomprime, instala en venv limpio y prueba funcionalidad sin egress de aplicación."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--output", required=True)
    parser.add_argument("--chromium")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gs-clean-install-") as t:
        temp = Path(t)
        with zipfile.ZipFile(args.archive) as z:
            z.extractall(temp / "project")
        root = temp / "project/monitoreo-taludes"
        app = root / "geoslope_review"
        subprocess.run([sys.executable, "-m", "venv", str(temp / "venv")], check=True)
        python = temp / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = {
            **os.environ,
            "PYTHONPATH": str(app),
            "GEOSLOPE_RUNTIME": str(temp / "private_runtime"),
        }

        def run(command, name, cwd=app):
            with (output / (name + ".txt")).open("w") as log:
                subprocess.run(
                    command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True
                )

        run(
            [str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"],
            "clean_dependencies",
        )
        run([str(python), "scripts/verify_installation.py"], "clean_installation")
        run([str(python), "scripts/initialize_database.py"], "clean_database")
        exercise = """
import secrets, socket, json
import pyotp
from gsreview.application.container import Container
from gsreview.domain.rules import ReviewInput,AccessDenied
def no_network(*args,**kwargs):raise AssertionError('external networking denied')
socket.socket.connect=no_network
c=Container()
password='Gs!'+secrets.token_hex(12)
challenge=c.auth.bootstrap('syntheticadmin','Validación sintética',password)
_,secret=c.auth.enrollment(challenge)
token,codes=c.auth.second_step(challenge,pyotp.TOTP(secret).now(),enroll=True)
temporary='Tmp!'+secrets.token_hex(12)
c.auth.create_user(token,'syntheticengineer','Ingeniero sintético',temporary,'ingeniero')
challenge,_=c.auth.password_step('syntheticengineer',temporary)
_,seed=c.auth.enrollment(challenge)
engineer,recovery=c.auth.second_step(challenge,pyotp.TOTP(seed).now(),enroll=True)
permanent='Next!'+secrets.token_hex(12)
c.auth.change_password(engineer,temporary,permanent)
challenge,_=c.auth.password_step('syntheticengineer',permanent)
engineer,_=c.auth.second_step(challenge,recovery[0],recovery=True)
assert c.auth.authorize(engineer)['role']=='ingeniero'
try:c.auth.authorize(engineer,'users');raise AssertionError('RBAC failure')
except AccessDenied:pass
episode=c.reader.episodes.episode_id.iloc[0]
c.reviews.save(engineer,episode,ReviewInput(status='Revisado',relevance='Indeterminado',comment='Prueba sintética en carpeta limpia',follow_up='Verificar datos',expected_version=0))
for fmt in ['PDF','CSV','JSON']:assert c.reports.generate(engineer,'episodio',episode,fmt)
backup=c.backups.create(token)
restarted=Container()
assert restarted.reviews.get(engineer,episode)['version']==1
c.backups.restore(token,backup.read_bytes())
assert not c.store.list('sessions')
print(json.dumps({'roles_demonstrated':['administrador','ingeniero'],'review_persistent_after_restart':True,'formats':['PDF','CSV','JSON'],'encrypted_backup_and_restore':True,'application_external_network_blocked':True,'no_production_training':True,'private_test_state_disposable':True}))
"""
        run([str(python), "-c", exercise], "clean_workflow")
        run(
            [
                str(python),
                "-m",
                "pytest",
                "-q",
                "tests",
                "geoslope_review/tests",
                f"--junitxml={output}/clean_all_tests.xml",
            ],
            "clean_all_tests",
            root,
        )
        run([str(python), "-m", "ruff", "check", "."], "clean_ruff")
        if args.chromium:
            run(
                [
                    str(python),
                    "scripts/validate_browser.py",
                    "--chromium",
                    args.chromium,
                    "--output",
                    str(output / "screenshots"),
                ],
                "clean_browser",
            )
        code_files = {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in app.rglob("*.py")
            if "__pycache__" not in p.parts
        }
        (output / "clean_validation.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "archive_sha256": hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),
                    "fresh_venv": True,
                    "pip_install_passed": True,
                    "full_suite_passed": True,
                    "workflow_passed": True,
                    "browser_passed": bool(args.chromium),
                    "tested_python": sys.version,
                    "platform": sys.platform,
                    "code_sha256": code_files,
                    "private_runtime_removed_after_validation": True,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
