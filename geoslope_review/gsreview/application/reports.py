"""Exportación autorizada con evaluación humana y firma de los datos congelados."""

import hashlib
import json
from datetime import datetime, timezone
from gsreview.infrastructure import store as db
from gsreview.infrastructure.reporting import make_pdf
from gsreview.domain.rules import NOTICE, ValidationError


class ReportService:
    def __init__(self, auth, reader, reviews):
        self.auth, self.reader, self.reviews = auth, reader, reviews

    def generate(self, token, scope, object_id, fmt):
        actor = self.auth.authorize(token, "export")
        self.reader.assert_current()
        if scope not in ("general", "prisma", "episodio") or fmt not in ("PDF", "CSV", "JSON"):
            raise ValidationError("Reporte no admitido.")
        rows = self.reader.rows
        episodes = self.reviews.listing(token)
        if scope == "prisma":
            rows = rows.loc[rows.prism_id.eq(object_id)]
            episodes = episodes.loc[episodes.prism_id.eq(object_id)]
        elif scope == "episodio":
            rows = rows.loc[rows.episode_id.eq(object_id)]
            episodes = episodes.loc[episodes.episode_id.eq(object_id)]
        if rows.empty:
            raise ValidationError("No hay registros para el reporte.")
        human = []
        for episode in episodes.episode_id:
            review = self.reviews.get(token, episode)
            if review["version"]:
                human.append({"episode_id": episode, **review})
        manifest_hash = hashlib.sha256(
            json.dumps(self.reader.manifest, sort_keys=True).encode()
        ).hexdigest()
        payload = {
            "title": f"Reporte {scope}: {object_id or 'conjunto completo'}",
            "notice": NOTICE,
            "generated_at": datetime.fromtimestamp(self.auth.clock(), timezone.utc).isoformat(),
            "generated_by": actor["display_name"],
            "manifest_hash": manifest_hash,
            "summary": {
                "Registros": len(rows),
                "Prismas": rows.prism_id.nunique(),
                "Episodios": len(episodes),
                "Candidatos híbridos": int(rows.candidate_hybrid.sum()),
                "No evaluables": int((~rows.model_eligible).sum()),
            },
            "reviews": human,
            "artifacts": self.reader.manifest["files"],
            "policy": {
                "strategy": "hybrid",
                "window_hours": 72,
                "minimum_marks": 2,
                "baseline_q99": 4.439772224885318,
                "iforest_q99": 0.5872931971929567,
            },
        }
        payload["summary"].update(
            {
                "Periodo observado": f"{rows.timestamp.min()} a {rows.timestamp.max()}",
                "Marcas de unión": int(rows.union_mark.sum()),
                "Coincidencias": int(rows.agreement_same_row.sum()),
                "Episodios con interrupciones": int(episodes.quality_interruption_flag.sum()),
                "Puntaje base máximo": float(rows.baseline_score.max()),
                "Puntaje IF máximo": float(rows.isolation_forest_score.max()),
                "Estados de revisión": str(episodes.human_status.value_counts().to_dict()),
            }
        )
        if scope != "general":
            payload["summary"]["Prisma"] = str(rows.prism_id.iloc[0])
            payload["summary"]["Episodios incluidos"] = "; ".join(episodes.episode_id)
        if scope == "episodio":
            payload["summary"]["Motivo y calidad"] = episodes.episode_explanation.iloc[0]
            payload["summary"]["Duración retrospectiva (horas)"] = float(
                episodes.duration_hours.iloc[0]
            )
        payload["episodes"] = (
            episodes.astype(object).where(episodes.notna(), None).to_dict("records")
        )
        payload["review_history"] = [
            item for episode in episodes.episode_id for item in self.reviews.history(token, episode)
        ]
        if fmt == "PDF":
            selected = (
                rows
                if scope != "general"
                else rows.loc[rows.prism_id.eq(sorted(rows.prism_id.unique())[0])]
            )
            if scope == "general":
                payload["summary"]["Prisma del gráfico de ejemplo"] = selected.prism_id.iloc[0]
            content = make_pdf(payload, selected)
        elif fmt == "JSON":
            payload["records"] = rows.astype(object).where(rows.notna(), None).to_dict("records")
            content = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
                default=lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x),
            ).encode()
        else:
            exported = rows.copy()
            current = {
                r["episode_id"]: {
                    **json.loads(r["payload"]),
                    "reviewer": r["reviewer"] or "",
                    "updated_at": r["updated_at"] or "",
                }
                for r in self.auth.store.list("episode_reviews")
            }
            for field in (
                "status",
                "relevance",
                "comment",
                "quality_comment",
                "follow_up",
                "reviewer",
                "updated_at",
            ):
                exported["human_" + field] = [
                    current.get(x, {}).get(field, "") for x in exported.episode_id
                ]
            exported["report_notice"] = NOTICE
            for c in exported.select_dtypes(include=["object", "string"]):
                exported[c] = exported[c].map(
                    lambda v: (
                        "'" + v
                        if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                        else v
                    )
                )
            content = exported.to_csv(index=False).encode("utf-8-sig")
        h = hashlib.sha256(content).hexdigest()
        with self.auth.store.tx() as c:
            c.execute(
                db.report_history.insert().values(
                    id=db.uid(),
                    actor=actor["id"],
                    scope=scope,
                    format=fmt,
                    sha256=h,
                    timestamp=self.auth.clock(),
                )
            )
            self.auth._audit(
                c,
                actor["id"],
                "report_generated" if fmt == "PDF" else "data_exported",
                object_id,
                {"format": fmt, "sha256": h},
            )
        return content
