import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/verify_installation.py")], cwd=root
    )
    if result.returncode:
        raise SystemExit("Revisa las dependencias y la integridad antes de iniciar.")
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "streamlit", "run", "app.py"], cwd=root)
    )
