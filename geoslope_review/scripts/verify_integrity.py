import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gsreview.analytics.artifacts import FrozenReader
from gsreview.application.container import APP_ROOT

if __name__ == "__main__":
    reader = FrozenReader(APP_ROOT.parent, APP_ROOT / "config/frozen_manifest.json")
    print("Artefactos íntegros:", reader.verify())
    print(reader.metrics())
