"""Lectura verificada sin entrenamiento ni modificación de artefactos."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from gsreview.domain.rules import ValidationError


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FrozenReader:
    def __init__(self, source, manifest):
        self.source = Path(source)
        self.manifest = json.loads(Path(manifest).read_text())
        self.verify()
        meta = json.loads((self.source / "reports/phase6/phase6_metadata.json").read_text())
        self.tables = {}
        for name in (
            "review_candidates.csv",
            "episodes.csv",
            "policy_comparison.csv",
            "sensitivity_analysis.csv",
            "specialist_review_template.csv",
        ):
            schema = meta["output_dtypes"][name]
            dates = [c for c, t in schema.items() if t.startswith("datetime")]
            dtype = {c: t for c, t in schema.items() if c not in dates}
            unknowns = {c: [""] for c, t in dtype.items() if t in ("float64", "boolean")}
            self.tables[name] = pd.read_csv(
                self.source / "data/processed/phase6" / name,
                dtype=dtype,
                parse_dates=dates,
                keep_default_na=False,
                na_values=unknowns,
                float_precision="round_trip",
            )
        self.rows, self.episodes = self.tables["review_candidates.csv"], self.tables["episodes.csv"]
        self.validate()
        names = [
            "source_record_id",
            "prism_id",
            "timestamp",
            "easting",
            "northing",
            "rl",
            "movement_rate_mm_per_day",
            "elapsed_hours",
        ]
        self.features = pd.read_csv(
            self.source / "data/processed/phase4/west_wall_features.csv",
            usecols=names,
            parse_dates=["timestamp"],
            float_precision="round_trip",
        )
        if self.features.source_record_id.duplicated().any() or set(
            self.features.source_record_id
        ) != set(self.rows.source_record_id):
            raise ValidationError("Correspondencia de coordenadas incompatible.")
        joined = self.rows[["source_record_id", "prism_id", "timestamp"]].merge(
            self.features, on="source_record_id", validate="one_to_one", suffixes=("", "_feature")
        )
        if (
            not joined.prism_id.eq(joined.prism_id_feature).all()
            or not joined.timestamp.eq(joined.timestamp_feature).all()
        ):
            raise ValidationError("La identidad espacial no coincide con las mediciones.")

    def verify(self):
        for relative, expected in self.manifest["files"].items():
            path = self.source / relative
            if not path.is_file() or sha256(path) != expected:
                raise ValidationError("Artefacto incompatible o alterado: " + relative)
        self.signature = self._signature()
        return len(self.manifest["files"])

    def _signature(self):
        return tuple(
            (p, (self.source / p).stat().st_mtime_ns, (self.source / p).stat().st_size)
            for p in self.manifest["files"]
        )

    def assert_current(self):
        try:
            changed = self._signature() != self.signature
        except OSError as e:
            raise ValidationError("Falta un artefacto congelado.") from e
        if changed:
            self.verify()

    def validate(self):
        r, e = self.rows, self.episodes
        expected = (
            len(r),
            r.prism_id.nunique(),
            int(r.model_eligible.sum()),
            len(e),
            int(r.candidate_hybrid.sum()),
            int(r.union_mark.sum()),
            int(r.agreement_same_row.sum()),
        )
        if expected != (7178, 49, 5898, 48, 102, 136, 66):
            raise ValidationError("Las cantidades no corresponden a la Fase 6 aprobada.")
        if (
            r.source_record_id.duplicated().any()
            or e.episode_id.duplicated().any()
            or r.timestamp.isna().any()
        ):
            raise ValidationError("Identificadores o fechas incompatibles.")
        if r.duplicated(["prism_id", "timestamp"]).any() or set(
            r.loc[r.episode_id.ne(""), "episode_id"]
        ) != set(e.episode_id):
            raise ValidationError("Relaciones de episodios incompatibles.")
        if (
            r.loc[~r.model_eligible, ["baseline_score", "isolation_forest_score", "union_mark"]]
            .notna()
            .any()
            .any()
        ):
            raise ValidationError("No evaluables deben conservar resultados desconocidos.")
        if (
            int(e.candidate_policies.str.contains("hybrid").sum()) != 20
            or int(e.quality_interruption_flag.sum()) != 4
        ):
            raise ValidationError("Episodios candidatos o calidad incompatibles.")
        if (
            not r.baseline_threshold_q99.eq(4.439772224885318).all()
            or not r.iforest_threshold_q99.eq(0.5872931971929567).all()
        ):
            raise ValidationError("Umbrales modificados.")

    def metrics(self):
        self.assert_current()
        return {
            "prismas": self.rows.prism_id.nunique(),
            "registros": len(self.rows),
            "episodios": len(self.episodes),
            "episodios candidatos": int(
                self.episodes.candidate_policies.str.contains("hybrid").sum()
            ),
            "registros candidatos": int(self.rows.candidate_hybrid.sum()),
            "interrupciones de calidad": int(self.episodes.quality_interruption_flag.sum()),
        }

    def spatial(self, cutoff):
        self.assert_current()
        cutoff = pd.Timestamp(cutoff)
        f = (
            self.features.loc[self.features.timestamp.le(cutoff)]
            .sort_values(["prism_id", "timestamp"])
            .groupby("prism_id")
            .tail(1)
        )
        r = self.rows[
            [
                "source_record_id",
                "causal_state",
                "model_eligible",
                "candidate_hybrid",
                "quality_interruption_flag",
                "episode_id",
            ]
        ]
        result = f.merge(r, on="source_record_id", validate="one_to_one")
        finite = np.isfinite(result[["easting", "northing", "rl"]]).all(axis=1)
        return result.loc[finite].reset_index(drop=True)

    def prism_series(self, prism):
        self.assert_current()
        f = self.features[
            [
                "source_record_id",
                "easting",
                "northing",
                "rl",
                "movement_rate_mm_per_day",
                "elapsed_hours",
            ]
        ]
        return (
            self.rows.loc[self.rows.prism_id.eq(prism)]
            .merge(f, on="source_record_id", validate="one_to_one")
            .sort_values("timestamp")
        )
