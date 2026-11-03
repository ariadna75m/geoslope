"""Read-only spatial use cases and existing append-only audit, without SQL in views."""

from gsreview.domain.rules import ValidationError


class SpatialService:
    def __init__(self, container):
        self.c = container

    def points(self, token, cutoff):
        self.c.auth.authorize(token, "read")
        return self.c.reader.spatial(cutoff)

    def series(self, token, prism, cutoff):
        self.c.auth.authorize(token, "read")
        rows = self.c.reader.prism_series(prism)
        return rows.loc[rows.timestamp.le(cutoff)]

    def log_access(self, token, action, object_id=""):
        actor = self.c.auth.authorize(token, "read")
        if action not in ("spatial_view_opened", "episode_opened"):
            raise ValidationError("Acción de consulta no admitida.")
        if action == "episode_opened":
            self.c.reviews.get(token, object_id)
        with self.c.store.tx() as connection:
            self.c.auth.guard(connection, token, "read")
            self.c.auth._audit(connection, actor["id"], action, object_id)
