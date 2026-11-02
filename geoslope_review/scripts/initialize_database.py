"""Inicializa roles y datos aprobados; no crea cuentas ni contraseñas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsreview.application.container import Container

if __name__ == "__main__":
    c = Container()
    print("SQLite inicializado; importación verificada:", c.reader.metrics())
    print("Abre la aplicación para crear el administrador y configurar TOTP.")
