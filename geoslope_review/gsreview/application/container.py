"""Composition root: rutas configurables; datos aprobados permanecen en su lugar."""

import os
from pathlib import Path
import yaml
from gsreview.infrastructure.store import Store
from gsreview.infrastructure.security import LocalCipher
from gsreview.application.auth import AuthService
from gsreview.analytics.artifacts import FrozenReader
from gsreview.application.review import ReviewService
from gsreview.application.reports import ReportService
from gsreview.application.backup import BackupService
from gsreview.application.settings import SettingsService

APP_ROOT = Path(__file__).resolve().parents[2]


class Container:
    def __init__(self, runtime=None, source=None, clock=None):
        self.app_root = APP_ROOT
        self.source = Path(source or os.environ.get("GEOSLOPE_SOURCE", APP_ROOT.parent)).resolve()
        self.runtime = Path(
            runtime or os.environ.get("GEOSLOPE_RUNTIME", APP_ROOT / "data/runtime")
        ).resolve()
        self.brand = yaml.safe_load((APP_ROOT / "config/app_config.yaml").read_text())
        self.store = Store(self.runtime / "geoslope_review.db")
        self.cipher = LocalCipher(
            os.environ.get("GEOSLOPE_KEY_FILE", str(self.runtime / "master.key"))
        )
        self.auth = AuthService(self.store, self.cipher, **({"clock": clock} if clock else {}))
        self.reader = FrozenReader(self.source, APP_ROOT / "config/frozen_manifest.json")
        self.reviews = ReviewService(self.auth, self.reader)
        self.reviews.import_initial()
        self.reports = ReportService(self.auth, self.reader, self.reviews)
        self.backups = BackupService(self.auth, self.reader, self.runtime / "backups")
        self.settings = SettingsService(self.auth)
