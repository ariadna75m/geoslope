"""Paquete completo, sin estado privado ni entornos de ejecución."""

import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def package(target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as z:
        for path in sorted(ROOT.rglob("*")):
            rel = path.relative_to(ROOT)
            if not path.is_file() or any(
                p in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "runtime"}
                for p in rel.parts
            ):
                continue
            if path.suffix in (".key", ".db", ".gsbackup") or path.name in (".env",):
                continue
            z.write(path, Path("monitoreo-taludes") / rel)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    args = parser.parse_args()
    print(package(args.output))
