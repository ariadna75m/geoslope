"""Características de West Wall por prefijo temporal, sin modelos ni cruces de fuentes."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .config import FeatureConfig, WINDOWS
from .temporal_features import (pair_features, sample_statistics, change_statistics,
                                historical_baseline, local_trend, directional_streaks)

VALUE = "reported_3d_movement_mm"
RATE_DESCRIPTION = "Tasa observada de cambio entre mediciones consecutivas"
STAT_LABELS = {
    "mean": "media", "median": "mediana", "min": "mínimo", "max": "máximo",
    "range": "rango", "std": "desviación estándar muestral", "mad": "MAD sin escalar",
    "first": "primer valor temporal", "last": "último valor temporal",
    "net_change": "cambio entre extremos temporales", "sum": "suma",
    "absolute_sum": "suma de valores absolutos", "increase_proportion": "proporción de incrementos",
    "decrease_proportion": "proporción de disminuciones", "valid_count": "cantidad de valores conocidos"
}


def statistic_formula(stat, symbol="x"):
    """Fórmula individual para el diccionario; n cuenta valores conocidos."""
    return {
        "mean": f"suma({symbol})/n", "median": f"mediana({symbol})",
        "min": f"mínimo({symbol})", "max": f"máximo({symbol})",
        "range": f"máximo({symbol})−mínimo({symbol})",
        "std": f"sqrt(suma(({symbol}−media({symbol}))²)/(n−1)); ddof=1",
        "mad": f"mediana(|{symbol}−mediana({symbol})|)",
        "first": "x del primer registro temporal; NaN si desconocido",
        "last": "x del último registro temporal; NaN si desconocido",
        "net_change": "x_último−x_primero; ambos extremos conocidos",
        "sum": f"suma({symbol}); NaN si n=0",
        "absolute_sum": f"suma(|{symbol}|); NaN si n=0",
        "increase_proportion": f"cantidad({symbol}>0)/n; ceros incluidos en n",
        "decrease_proportion": f"cantidad({symbol}<0)/n; ceros incluidos en n",
        "valid_count": f"cantidad de {symbol} conocidos"
    }[stat]


@dataclass
class FeatureDataset:
    data: pd.DataFrame
    dictionary: pd.DataFrame
    config: FeatureConfig


class FeatureCatalog:
    def __init__(self):
        self.entries = {}

    def register(self, name, description, formula, unit="no aplica", group="quality",
                 window="actual/anterior", minimum=0, uses_current=True, limitation=""):
        if name not in self.entries:
            self.entries[name] = {
                "feature_name": name, "description": description, "formula": formula, "unit": unit,
                "source": "West Wall; registros preparados Fase 2", "group": group,
                "temporal_window": window, "minimum_observations": minimum,
                "uses_current_observation": uses_current, "uses_only_past_or_present": True,
                "uses_future": False,
                "missing_policy": "Desconocido permanece NaN; no interpolación ni imputación; disponible indica evaluabilidad matemática.",
                "limitations": limitation or "Disponibilidad matemática no valida geomecánica ni completitud de mediciones.",
                "permitted_interpretation": "Descripción del movimiento reportado o calidad del cálculo en el mismo prisma.",
                "prohibited_interpretation": "El talud fallará; probabilidad, causalidad, riesgo o diagnóstico geomecánico."
            }


def _ordered_source(frame):
    needed = {"prism_id", "timestamp", VALUE, "row_id", "source_line", "source_name", "source_sha256"}
    if not needed.issubset(frame):
        raise ValueError("Faltan campos West Wall o trazabilidad: " + ", ".join(sorted(needed - set(frame))))
    if frame.empty:
        raise ValueError("La fuente no contiene observaciones.")
    if frame.columns.duplicated().any():
        raise ValueError("Nombres de columna duplicados.")
    data = frame.copy(deep=True)
    for name in ("prism_id", "row_id", "source_name", "source_sha256"):
        if data[name].isna().any() or data[name].astype(str).str.strip().eq("").any():
            raise ValueError("Falta identificador o procedencia: " + name)
    if not data.row_id.is_unique:
        raise ValueError("Identificadores originales duplicados.")
    data["timestamp"] = pd.to_datetime(data.timestamp, errors="raise")
    if data.timestamp.isna().any():
        raise ValueError("Timestamp desconocido.")
    if data.duplicated(["prism_id", "timestamp"]).any():
        raise ValueError("Timestamp duplicado/intervalo cero: requiere revisión; no se excluyen ni fusionan registros.")
    numeric = pd.to_numeric(data[VALUE], errors="raise")
    if np.isinf(numeric).any():
        raise ValueError("Movimiento infinito: requiere revisión del valor original.")
    data[VALUE] = numeric.astype(float)
    return data.sort_values(["prism_id", "timestamp"], kind="stable").reset_index(drop=True)


def engineer_features(frame: pd.DataFrame, config: FeatureConfig | None = None) -> FeatureDataset:
    cfg = config or FeatureConfig()
    source = _ordered_source(frame)
    catalog = FeatureCatalog()
    for name in source.columns:
        unit = "mm" if name == VALUE else "requiere validación" if name in {"easting", "northing", "rl"} else "no aplica / campo original"
        description = ("Movimiento 3D reportado en milímetros respecto a la referencia indicada en el archivo. "
                       "No se asume que sea una trayectoria acumulativa estrictamente creciente") if name == VALUE else "Campo de entrada conservado: " + name
        catalog.register(name, description, "Copia del campo preparado; sin transformación física", unit,
                         "source", "observación actual", 1,
                         limitation="Texto original, fuente, línea y row_id permiten reconstruir el registro; coordenadas sin convertir.")
    catalog.register("source_record_id", "Identificador original trazable", "row_id", group="source", minimum=1)
    catalog.register("source_file_reference", "Referencia al archivo original", "data/raw/radar-deformation-data/ + source_name", group="source")
    rows = []
    for _, g in source.groupby("prism_id", sort=True):
        g = g.reset_index(drop=True)
        times = pd.DatetimeIndex(g.timestamp)
        values = g[VALUE].to_numpy(dtype=float)
        pairs = [pair_features(values[i], values[i-1] if i else np.nan, times[i], times[i-1] if i else pd.NaT, cfg)
                 for i in range(len(g))]
        deltas = np.array([p["movement_delta_mm"] for p in pairs])
        rates = np.array([p["movement_rate_mm_per_day"] for p in pairs])
        streaks = directional_streaks(times, deltas, [p["is_prolonged_gap"] for p in pairs],
                                     [p["is_nonpositive_interval"] for p in pairs])
        for i in range(len(g)):
            row = {"source_record_id": g.row_id.iloc[i],
                   "source_file_reference": "data/raw/radar-deformation-data/" + str(g.source_name.iloc[i])}
            overflow = False

            def add(name, value, description, formula, unit="no aplica", group="quality", window="actual/anterior",
                    minimum=0, uses_current=True, availability=False, limitation=""):
                nonlocal overflow
                catalog.register(name, description, formula, unit, group, window, minimum, uses_current, limitation)
                if isinstance(value, (float, np.floating)) and np.isinf(value):
                    value = np.nan
                    overflow = True
                row[name] = value
                if availability:
                    flag = name + "_available"
                    row[flag] = bool(pd.notna(value))
                    catalog.register(flag, "Disponibilidad matemática de " + name, name + " no es NaN", "booleano",
                                     "availability", window, minimum, uses_current,
                                     "No garantiza suficiencia temporal, precisión instrumental o estabilidad geomecánica.")

            add("previous_timestamp", times[i-1] if i else pd.NaT, "Fecha anterior del mismo prisma", "timestamp[i−1]",
                "fecha", "interval", "t anterior", 1, False, True)
            add("movement_observation_available", bool(np.isfinite(values[i])), "Movimiento actual conocido", "isfinite(x_t)", "booleano")
            for name, value in pairs[i].items():
                if "rate" in name:
                    unit, group = "mm/día", "rate"
                    formula = "(x_t−x_anterior)/(Δhoras/24); intervalo positivo"
                    description = RATE_DESCRIPTION + (" (valor absoluto)" if name.startswith("absolute") else "")
                    limitation = "Promedio entre extremos, incluso huecos largos marcados; no velocidad física validada del macizo."
                elif "delta" in name:
                    unit, group = "mm", "change"
                    formula, description = "x_t−x_anterior; abs si se indica", "Cambio entre valores reportados consecutivos"
                    limitation = "No se anulan cambios negativos; no representa distancia de trayectoria."
                elif name in {"elapsed_hours", "elapsed_days"}:
                    unit, group = "horas" if name.endswith("hours") else "días", "interval"
                    formula, description = "(timestamp_t−timestamp_anterior)/unidad temporal", "Intervalo real entre mediciones"
                    limitation = "Primera observación: NaN; no frecuencia esperada uniforme."
                else:
                    unit, group = "booleano", "quality"
                    formula = {"is_gap_over_24h": "Δh > 24", "is_gap_over_72h": "Δh > 72", "is_gap_over_7d": "Δh > 168",
                               "is_first_observation": "No existe timestamp anterior del mismo prisma",
                               "is_nonpositive_interval": "Existe timestamp anterior y Δh ≤ 0",
                               "is_prolonged_gap": f"Δh > {cfg.prolonged_gap_hours}",
                               "is_unusually_short_interval": f"0 < Δh < {cfg.short_interval_hours}",
                               "movement_increased": "Δx > 0; False si no evaluable",
                               "movement_decreased": "Δx < 0; False si no evaluable",
                               "movement_unchanged": "Δx = 0; False si no evaluable"}.get(name, name)
                    description, limitation = "Bandera descriptiva: " + name, "Bandera de calidad o signo; no alerta. Consultar disponibilidad del cambio."
                add(name, value, description, formula, unit, group, minimum=2,
                    availability=not isinstance(value, (bool, np.bool_)), limitation=limitation)
            add("total_prior_observations", i, "Cantidad total de filas anteriores", "i dentro del prisma ordenado",
                "observaciones", "historical", "t anterior", uses_current=False)
            baseline = historical_baseline(times[:i], values[:i], times[i], values[i], cfg)
            for name, value in baseline.items():
                current = name.startswith("difference_") or "z_score" in name
                if name.endswith("_z_score"):
                    formula = f"(x_t−mediana_previa)/({cfg.robust_mad_scale:g}×MAD_previa)" if "robust" in name else "(x_t−media_previa)/std_previa"
                    unit = "adimensional"
                elif name.startswith("difference_"):
                    formula, unit = "x_t − estadística del prefijo x_<t", "mm"
                elif name.startswith("historical_") and name.endswith("_mm"):
                    formula, unit = statistic_formula(name.removeprefix("historical_").removesuffix("_mm"), "x_<t"), "mm"
                elif name == "prior_history_duration_hours":
                    formula, unit = "último_timestamp_previo_válido−primero_previo_válido", "horas"
                elif isinstance(value, (bool, np.bool_)):
                    formula, unit = "Criterios de historia/dispersion de config/phase4.json", "booleano"
                else:
                    formula, unit = "Número de valores conocidos estrictamente anteriores", "observaciones"
                add(name, value, "Línea base expansiva previa: " + name, formula, unit, "historical",
                    "[inicio, t)", cfg.min_baseline_observations if name.startswith(("historical_", "difference_")) else 0,
                    current, availability=not isinstance(value, (bool, np.bool_)),
                    limitation="La observación actual no forma su propia referencia; cero dispersión deja z-score NaN. No son alertas.")
            for label, hours in WINDOWS:
                # Extremo inferior abierto, sin acceso a índices posteriores a i.
                start = times.searchsorted(times[i] - pd.Timedelta(hours=hours), side="right")
                wt, wx = times[start:i+1], values[start:i+1]
                span = (wt[-1] - wt[0]).total_seconds() / 3600
                valid_times = wt[np.isfinite(wx)]
                valid_span = (valid_times[-1]-valid_times[0]).total_seconds()/3600 if len(valid_times) else np.nan
                max_gap = float(np.max(np.diff(wt.asi8)/3.6e12)) if len(wt)>1 else np.nan
                window_gap = bool(max_gap > cfg.prolonged_gap_hours)
                enough = len(valid_times) >= cfg.min_window_observations and valid_span >= hours*cfg.min_window_span_fraction and not window_gap
                window = f"(t−{hours:g}h,t]"
                for suffix, value, unit, formula in (
                    ("observation_count", len(wt), "observaciones", "Número de registros en ventana"),
                    ("valid_movement_count", len(valid_times), "observaciones", "Número de movimientos conocidos en ventana"),
                    ("duration_hours", span, "horas", "t_último−t_primero de registros"),
                    ("valid_duration_hours", valid_span, "horas", "t_último−t_primero de movimientos conocidos"),
                    ("max_gap_hours", max_gap, "horas", "máximo intervalo entre registros internos"),
                    ("has_long_gap", window_gap, "booleano", f"max_gap_hours > {cfg.prolonged_gap_hours}")):
                    add(f"window_{label}_{suffix}", value, "Cobertura retrospectiva: " + suffix, formula, unit, "window_"+label,
                        window, availability=not isinstance(value, (bool, np.bool_)))
                add(f"has_sufficient_{label}_history", bool(enough), "Historia suficiente de ventana",
                    f"≥{cfg.min_window_observations} válidos; duración≥{hours*cfg.min_window_span_fraction:g}h; sin hueco>{cfg.prolonged_gap_hours:g}h",
                    "booleano", "window_"+label, window, cfg.min_window_observations)
                statistics = sample_statistics(wx, cfg.min_dispersion_observations)
                for stat, value in statistics.items():
                    if stat == "valid_count":
                        continue
                    minimum = cfg.min_dispersion_observations if stat == "std" else 1
                    add(f"movement_{label}_{stat}_mm", value, f"Movimiento: {STAT_LABELS[stat]} retrospectivo",
                        statistic_formula(stat),
                        "mm", "movement_"+label, window, minimum, availability=True,
                        limitation="Estadísticas no ponderadas por tiempo; se calculan sobre conocidos. Extremos temporales desconocidos siguen NaN; consultar suficiencia.")
                # Un cambio de ventana exige AMBOS extremos en su ventana.
                # Se excluye el par que comenzó antes o justo en el límite inferior.
                for prefix, series, unit in (("delta", deltas, "mm"), ("rate", rates, "mm/día")):
                    changes = series[start+1:i+1]
                    for stat, value in change_statistics(changes, cfg.min_dispersion_observations).items():
                        name = f"{prefix}_{label}_{stat}"
                        if prefix == "delta" and stat == "increase_proportion":
                            name = f"increase_proportion_{label}"
                        measure_unit = "observaciones" if stat == "valid_count" else "proporción 0–1" if "proportion" in stat else unit
                        minimum = cfg.min_dispersion_observations if stat == "std" else 1
                        symbol = "Δx" if prefix == "delta" else "tasa"
                        add(name, value, f"{'Cambio' if prefix == 'delta' else 'Tasa observada'}: {STAT_LABELS[stat]} en pares internos",
                            statistic_formula(stat, symbol) + "; ambos timestamps del par dentro de ventana",
                            measure_unit, prefix+"_"+label, window, minimum, availability=True,
                            limitation="Proporciones dividen entre pares evaluables e incluyen ceros en denominador. Suma de tasas es suma matemática en mm/día, no cambio neto físico; no ponderación temporal.")
                if label in {"72h", "7d"}:
                    trend = local_trend(wt, wx, cfg, hours*cfg.min_window_span_fraction)
                    for stat in ("points", "duration_hours", "slope_mm_per_day", "r_squared"):
                        value = trend[stat]
                        unit = "observaciones" if stat == "points" else "horas" if stat == "duration_hours" else "mm/día" if stat == "slope_mm_per_day" else "adimensional"
                        add(f"local_trend_{label}_{stat}", value, "Tendencia estadística local: " + stat,
                            "OLS: suma((d−media_d)(x−media_x))/suma((d−media_d)²); R²=1−SSE/SST",
                            unit, "trend_"+label, window, cfg.min_slope_observations, availability=True,
                            limitation="≥3 timestamps válidos, duración mínima y sin hueco largo. R² NaN para x constante. Sin pronóstico ni prueba física de inestabilidad.")
            for name, value in streaks[i].items():
                add(name, value, "Persistencia observada: " + name,
                    "Racha de pares evaluables del mismo signo; cero, NaN o hueco prolongado reinician",
                    "booleano" if name == "streak_evaluable" else "horas" if name.endswith("hours") else "cambios consecutivos",
                    "streak", "racha hasta t", 2, availability=name != "streak_evaluable",
                    limitation="Duración incluye el instante anterior al primer cambio; racha de observaciones, no continuidad del macizo.")
            add("has_numeric_overflow", overflow, "Operación fuera del rango numérico", "Operación derivada infinita→NaN", "booleano")
            if pairs[i]["is_first_observation"]:
                status = "sin historia previa"
            elif pairs[i]["is_nonpositive_interval"]:
                status = "intervalo no válido"
            elif not row["movement_delta_mm_available"] or not row["movement_rate_mm_per_day_available"] or overflow:
                status = "características parciales"
            elif pairs[i]["is_prolonged_gap"]:
                status = "hueco prolongado"
            elif pairs[i]["is_unusually_short_interval"]:
                status = "intervalo inusualmente corto"
            elif not row["has_sufficient_history"]:
                status = "historia insuficiente"
            elif not all(row[f"has_sufficient_{label}_history"] for label, _ in WINDOWS) or not all(
                    row[name + "_available"] for name in ("historical_z_score", "historical_robust_z_score", "local_trend_72h_slope_mm_per_day", "local_trend_7d_slope_mm_per_day")):
                status = "características parciales"
            else:
                status = "características disponibles"
            add("feature_quality_status", status, "Resumen de calidad de características", "Prioridad: inicio, intervalo, desconocidos, hueco, corto, historia, parcial, disponible",
                "categoría de calidad", "quality", "prefijo hasta t")
            rows.append(row)
    derived = pd.DataFrame(rows)
    collisions = set(derived).intersection(source)
    if collisions:
        raise ValueError("Columnas de características ya existentes: " + ", ".join(sorted(collisions)))
    result = pd.concat([source, derived], axis=1)
    dictionary = pd.DataFrame([catalog.entries[name] for name in result.columns])
    return FeatureDataset(result, dictionary, cfg)
