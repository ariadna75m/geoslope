"""Abre el flujo protegido de copias; nunca recibe credenciales en argumentos."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    print("Inicia sesión con 2FA como administrador y selecciona Copias de seguridad.")
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "streamlit", "run", "app.py"],
            cwd=Path(__file__).resolve().parents[1],
        )
    )
