import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsreview.analytics.artifacts import FrozenReader
from gsreview.application.container import APP_ROOT

if __name__ == "__main__":
    if sys.version_info < (3, 11):
        raise SystemExit("Se necesita Python 3.11 o posterior.")
    modules = (
        "streamlit",
        "sqlalchemy",
        "pandas",
        "numpy",
        "plotly",
        "pydantic",
        "argon2",
        "pyotp",
        "cryptography",
        "qrcode",
        "reportlab",
    )
    for module in modules:
        importlib.import_module(module)
    reader = FrozenReader(APP_ROOT.parent, APP_ROOT / "config/frozen_manifest.json")
    print(
        json.dumps(
            {
                "python": sys.version,
                "modules_verified": list(modules),
                "metrics": reader.metrics(),
                "integrity_files": reader.verify(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
