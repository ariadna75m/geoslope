from pathlib import Path
import yaml

APP_ROOT = Path(__file__).resolve().parents[1]
BRAND = yaml.safe_load((APP_ROOT / "config/app_config.yaml").read_text(encoding="utf-8"))
COLORS = BRAND["colors"]
