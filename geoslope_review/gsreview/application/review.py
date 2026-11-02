"""Casos de uso de revisión humana y consulta; nunca cambia resultados estadísticos."""

import json
from sqlalchemy import select
from gsreview.domain.rules import ValidationError, ReviewInput
from gsreview.infrastructure import store as db


class ReviewService:
    def __init__(self, auth, reader):
        self.auth, self.reader, self.store = auth, reader, auth.store

    def import_initial(self):
        # Únicamente inicialización idempotente; reemplazos requieren backup y administrador.
        self.reader.verify()
        from gsreview.infrastructure.security import digest

        manifest_hash = digest(json.dumps(self.reader.manifest, sort_keys=True))
        with self.store.tx() as c:
            existing = c.execute(select(db.data_imports)).mappings().first()
            if existing:
                if existing["manifest_hash"] != manifest_hash:
                    raise ValidationError(
                        "La base pertenece a otro conjunto. Restaura una copia compatible antes de reemplazar."
                    )
                return
            for row in self.reader.episodes.to_dict("records"):
                payload = json.dumps(row, default=str, ensure_ascii=False)
                c.execute(
                    db.episodes.insert().values(
                        id=row["episode_id"], prism_id=row["prism_id"], payload=payload
                    )
                )
                c.execute(
                    db.episode_reviews.insert().values(
                        episode_id=row["episode_id"], version=0, payload="{}"
                    )
                )
            c.execute(
                db.data_imports.insert().values(
                    id=db.uid(),
                    manifest_hash=manifest_hash,
                    created_at=self.auth.clock(),
                    rows=len(self.reader.rows),
                )
            )
            for path, h in self.reader.manifest["files"].items():
                c.execute(
                    db.artifact_integrity.insert().values(
                        path=path, sha256=h, verified_at=self.auth.clock()
                    )
                )
            self.auth._audit(
                c,
                None,
                "data_imported",
                detail={"rows": len(self.reader.rows), "manifest": manifest_hash},
            )

    def listing(self, token):
        self.auth.authorize(token)
        self.reader.assert_current()
        reviews = {r["episode_id"]: r for r in self.store.list("episode_reviews")}
        output = self.reader.episodes.copy()
        output["human_status"] = [
            json.loads(reviews[x]["payload"]).get("status", "Pendiente") for x in output.episode_id
        ]
        output["reviewer_id"] = [reviews[x]["reviewer"] or "" for x in output.episode_id]
        return output

    def get(self, token, episode_id):
        self.auth.authorize(token)
        with self.store.engine.connect() as c:
            r = (
                c.execute(
                    select(db.episode_reviews).where(db.episode_reviews.c.episode_id == episode_id)
                )
                .mappings()
                .first()
            )
        if not r:
            raise ValidationError("Episodio no disponible.")
        return {
            **json.loads(r["payload"]),
            "version": r["version"],
            "reviewer": r["reviewer"],
            "updated_at": r["updated_at"],
        }

    def save(self, token, episode_id, review: ReviewInput):
        actor = self.auth.authorize(token, "review")
        self.reader.assert_current()
        review.validate_choices()
        with self.store.tx() as c:
            self.auth.guard(c, token, "review")
            current = (
                c.execute(
                    select(db.episode_reviews).where(db.episode_reviews.c.episode_id == episode_id)
                )
                .mappings()
                .first()
            )
            if not current or current["version"] != review.expected_version:
                raise ValidationError("La revisión cambió. Recarga el episodio antes de guardar.")
            payload = review.model_dump(exclude={"expected_version"})
            encoded = json.dumps(payload, ensure_ascii=False)
            version = current["version"] + 1
            c.execute(
                db.episode_reviews.update()
                .where(db.episode_reviews.c.episode_id == episode_id)
                .values(
                    version=version,
                    payload=encoded,
                    reviewer=actor["id"],
                    updated_at=self.auth.clock(),
                )
            )
            c.execute(
                db.review_history.insert().values(
                    id=db.uid(),
                    episode_id=episode_id,
                    version=version,
                    payload=encoded,
                    reviewer=actor["id"],
                    timestamp=self.auth.clock(),
                )
            )
            self.auth._audit(
                c,
                actor["id"],
                "review_created" if version == 1 else "review_modified",
                episode_id,
                {"version": version},
            )

    def history(self, token, episode_id=None):
        actor = self.auth.authorize(token, "read")
        data = self.store.list("review_history")
        if episode_id:
            return [r for r in data if r["episode_id"] == episode_id]
        return [r for r in data if r["reviewer"] == actor["id"]]

    def audit(self, token):
        self.auth.authorize(token, "audit")
        return sorted(self.store.list("audit_log"), key=lambda r: r["timestamp"], reverse=True)

    def verify_integrity(self, token):
        actor = self.auth.authorize(token, "integrity")
        count = self.reader.verify()
        with self.store.tx() as c:
            self.auth._audit(c, actor["id"], "integrity_verified", detail={"files": count})
        return count
