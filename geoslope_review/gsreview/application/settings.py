from sqlalchemy import select
from gsreview.infrastructure import store as db
from gsreview.domain.rules import ValidationError


class SettingsService:
    def __init__(self, auth):
        self.auth = auth

    def display_rows(self, token):
        self.auth.authorize(token, "read")
        with self.auth.store.engine.connect() as c:
            value = c.scalar(
                select(db.app_metadata.c.value).where(db.app_metadata.c.key == "display_rows")
            )
        return int(value or 20)

    def save(self, token, key, value):
        actor = self.auth.authorize(token, "settings")
        if key != "display_rows" or value not in ("20", "50", "100"):
            raise ValidationError("Solo se permiten preferencias de presentación.")
        with self.auth.store.tx() as c:
            self.auth.guard(c, token, "settings")
            existing = c.scalar(select(db.app_metadata.c.key).where(db.app_metadata.c.key == key))
            if existing:
                c.execute(
                    db.app_metadata.update().where(db.app_metadata.c.key == key).values(value=value)
                )
            else:
                c.execute(db.app_metadata.insert().values(key=key, value=value))
            self.auth._audit(c, actor["id"], "display_setting_changed", key, {"value": value})
