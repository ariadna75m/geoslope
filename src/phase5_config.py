"""Configuración independiente: no modifica políticas de características de Fase 4."""
from pathlib import Path
import json
import math

CANDIDATES = (
    "movement_delta_mm", "absolute_movement_delta_mm", "movement_rate_mm_per_day", "absolute_movement_rate_mm_per_day",
    "local_trend_72h_slope_mm_per_day", "local_trend_7d_slope_mm_per_day", "local_trend_72h_r_squared", "local_trend_7d_r_squared",
    "movement_72h_range_mm", "movement_72h_mad_mm", "movement_7d_range_mm", "movement_7d_mad_mm",
    "delta_72h_absolute_sum", "delta_7d_absolute_sum", "increase_streak_count", "increase_streak_duration_hours",
    "increase_proportion_72h", "increase_proportion_7d", "difference_from_prior_median_mm", "historical_robust_z_score")


def load_model_config(path):
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
        validate_model_config(cfg)
        return cfg
    except (OSError, json.JSONDecodeError, TypeError, KeyError) as error:
        raise ValueError("Configuración de Fase 5 incompleta o inválida.") from error


def validate_model_config(cfg):
    for name in ("train_fraction", "validation_fraction", "spearman_limit", "max_training_missing_fraction", "max_row_missing_fraction"):
        value = cfg[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value < 1:
            raise ValueError("Fracción inválida: " + name)
    if cfg["train_fraction"] + cfg["validation_fraction"] >= 1 or cfg["split_unit"] != "unique_calendar_days":
        raise ValueError("La división debe dejar tres periodos y agrupar días completos.")
    priority = cfg["candidate_priority"]
    if not priority or len(priority) != len(set(priority)) or not set(priority).issubset(CANDIDATES):
        raise ValueError("Solo se admiten candidatos científicos declarados; sin identificadores ni trazabilidad.")
    if not set(cfg["mandatory_features"]).issubset(CANDIDATES):
        raise ValueError("Característica indispensable inválida.")
    if type(cfg["minimum_training_rows"]) is not int or cfg["minimum_training_rows"] < 10:
        raise ValueError("Muy pocas filas mínimas de entrenamiento.")
    if not math.isclose(sum(cfg["baseline_weights"].values()), 1) or any(x < 0 for x in cfg["baseline_weights"].values()):
        raise ValueError("Los pesos de la regla deben ser no negativos y sumar 1.")
    for name in ("threshold_quantiles", "top_fractions"):
        if not cfg[name] or any(not 0 < x < 1 for x in cfg[name]):
            raise ValueError("Cuantiles/fracciones fuera de rango.")
    if not {.95, .98, .99}.issubset(cfg["threshold_quantiles"]):
        raise ValueError("Conserve los cuantiles experimentales 0.95, 0.98 y 0.99.")
    forest = cfg["primary_model"]
    if type(forest["max_features"]) is not float or forest["max_features"] != 1.0:
        raise ValueError("El modelo principal requiere max_features=1.0 (float), con todas las características disponibles.")
    comparison = cfg["max_features_comparison"]
    if [(type(x), x) for x in comparison] != [(int, 1), (float, .5), (float, 1.)]:
        raise ValueError("Conserve la comparación 1 (int), 0.5 (float), 1.0 (float).")
    if type(forest["n_estimators"]) is not int or forest["n_estimators"] < 1:
        raise ValueError("n_estimators debe ser un entero positivo.")
    if type(forest["bootstrap"]) is not bool or type(forest["random_state"]) is not int or forest["random_state"] < 0:
        raise ValueError("bootstrap y random_state inválidos.")
    for name in ("max_samples", "max_features"):
        value = forest[name]
        valid = (type(value) is int and value > 0) or (type(value) is float and math.isfinite(value) and 0 < value <= 1)
        if name == "max_samples" and value == "auto":
            valid = True
        if not valid:
            raise ValueError("Parámetro de Isolation Forest inválido: " + name)
    contamination = forest["contamination"]
    if contamination != "auto" and (type(contamination) not in (int, float) or not math.isfinite(contamination) or not 0 < contamination <= .5):
        raise ValueError("contamination debe ser auto o una fracción entre 0 y 0.5.")
    if len(set(cfg["seeds"])) < 2 or any(type(x) is not int or x < 0 for x in cfg["seeds"]):
        raise ValueError("Se necesitan semillas enteras distintas.")
    for name in ("require_72h_history", "require_7d_history", "exclude_prolonged_gaps"):
        if type(cfg[name]) is not bool:
            raise ValueError("Bandera de configuración inválida: " + name)
    for name in ("synthetic_amplitude_scale", "robust_z_reference"):
        if not math.isfinite(cfg[name]) or cfg[name] <= 0:
            raise ValueError("Referencia técnica inválida.")
    if cfg["synthetic_segment_observations"] < 3 or any(x <= 0 for x in cfg["synthetic_intensities"]):
        raise ValueError("Configuración sintética inválida.")
