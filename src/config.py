"""Criterios técnicos de disponibilidad; sin parámetros de falla o alerta."""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math

WINDOWS = (("24h", 24.0), ("72h", 72.0), ("7d", 168.0))


@dataclass(frozen=True)
class FeatureConfig:
    min_dispersion_observations: int = 2
    min_window_observations: int = 3
    min_window_span_fraction: float = 0.25
    min_slope_observations: int = 3
    min_baseline_observations: int = 20
    min_baseline_span_hours: float = 24.0
    short_interval_hours: float = 1 / 60
    prolonged_gap_hours: float = 72.0
    dispersion_epsilon: float = 0.0
    robust_mad_scale: float = 1.4826

    def __post_init__(self):
        for name, minimum in (("min_dispersion_observations", 2),
                              ("min_window_observations", 2),
                              ("min_slope_observations", 3),
                              ("min_baseline_observations", 2)):
            value = getattr(self, name)
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} debe ser entero y ≥{minimum}.")
        for name in ("min_window_span_fraction", "min_baseline_span_hours", "short_interval_hours",
                     "prolonged_gap_hours", "dispersion_epsilon", "robust_mad_scale"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} debe ser numérico y finito.")
        if not 0 < self.min_window_span_fraction <= 1:
            raise ValueError("La fracción mínima de duración debe estar entre 0 y 1.")
        if self.min_baseline_span_hours < 0 or self.dispersion_epsilon < 0:
            raise ValueError("Duración y tolerancia de dispersión no pueden ser negativas.")
        if self.short_interval_hours <= 0 or self.prolonged_gap_hours <= self.short_interval_hours:
            raise ValueError("Intervalos de calidad inconsistentes.")
        if self.robust_mad_scale <= 0:
            raise ValueError("Escala MAD debe ser positiva.")

    def as_dict(self):
        return asdict(self)


def load_feature_config(path: str | Path | None = None) -> FeatureConfig:
    if path is None:
        return FeatureConfig()
    try:
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("La configuración debe ser un objeto JSON.")
        return FeatureConfig(**values)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise ValueError("No se pudo leer una configuración de características válida.") from error
