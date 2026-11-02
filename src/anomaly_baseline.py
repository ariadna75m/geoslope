"""Regla descriptiva continua; ninguna puntuación es probabilidad de falla."""
from dataclasses import dataclass
import numpy as np


def robust_reference(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x): raise ValueError("Referencia sin valores conocidos de entrenamiento.")
    center = float(np.median(x))
    scale = float(1.4826*np.median(np.abs(x-center)))
    fallback = "MAD escalada"
    if scale == 0:
        scale = float(np.quantile(x, .75)-np.quantile(x, .25)); fallback = "IQR: MAD cero"
    if scale == 0: scale, fallback = 1., "escala unitaria: MAD e IQR cero; interpretación limitada"
    return {"center": center, "scale": scale, "scale_policy": fallback}


@dataclass
class StatisticalBaseline:
    weights: dict
    trend_reference: dict
    persistence_reference: dict

    @classmethod
    def fit(cls, training, config):
        return cls(config["baseline_weights"].copy(),
                   robust_reference(training.local_trend_72h_slope_mm_per_day),
                   robust_reference(training.increase_streak_duration_hours))

    def score(self, data):
        z = np.abs(data.historical_robust_z_score.to_numpy(dtype=float))
        trend = np.abs((data.local_trend_72h_slope_mm_per_day.to_numpy(dtype=float)-self.trend_reference["center"])/self.trend_reference["scale"])
        persistence = np.maximum(0., (data.increase_streak_duration_hours.to_numpy(dtype=float)-self.persistence_reference["center"])/self.persistence_reference["scale"])
        return self.weights["historical_z"]*z + self.weights["trend"]*trend + self.weights["persistence"]*np.log1p(persistence)

    def as_dict(self):
        return {"weights": self.weights, "trend_reference": self.trend_reference, "persistence_reference": self.persistence_reference,
                "formula": "w_z*abs(previous_robust_z) + w_trend*abs(train_robust_trend_deviation) + w_persistence*log1p(positive_train_robust_streak_duration_deviation)",
                "quality_policy": "eligibility gating; no score for ineligible rows", "fit_scope": "training only", "operational_alert": False}
