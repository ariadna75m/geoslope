"""Validación de conservación, disponibilidad y exportación de Fase 4."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .feature_engineering import FeatureDataset, _ordered_source
from .config import WINDOWS


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_protected(root, manifest_path):
    root = Path(root)
    manifest = json.loads(Path(manifest_path).read_text())
    for name, expected in manifest.items():
        if not (root/name).is_file() or sha256(root/name) != expected:
            raise RuntimeError("Cambió un archivo protegido: " + name)
    return len(manifest)


def validate_feature_dataset(original: pd.DataFrame, result: FeatureDataset):
    data, dictionary = result.data, result.dictionary
    original = _ordered_source(original)
    if len(data) != len(original) or data.prism_id.nunique() != original.prism_id.nunique():
        raise ValueError("Cambió la cantidad de registros o prismas.")
    if not data.source_record_id.is_unique or not data.source_record_id.equals(data.row_id):
        raise ValueError("La clave de registro no conserva la trazabilidad.")
    pd.testing.assert_frame_equal(original, data[list(original)], check_dtype=False)
    if data.duplicated(["prism_id", "timestamp"]).any():
        raise ValueError("Claves temporales duplicadas.")
    if not all(g.timestamp.is_monotonic_increasing for _, g in data.groupby("prism_id")):
        raise ValueError("Los timestamps no están ordenados.")
    if data.is_nonpositive_interval.any():
        raise ValueError("Intervalos no positivos en la salida activa.")
    if list(dictionary.feature_name) != list(data.columns):
        raise ValueError("El diccionario no cubre todas las columnas.")
    numeric = data.select_dtypes(include="number")
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError("Se encontró un infinito.")
    for column in dictionary.loc[dictionary.unit.eq("booleano"), "feature_name"]:
        if data[column].dtype != bool or data[column].isna().any():
            raise ValueError("Bandera de tipo inválido: " + column)
    for column in data:
        if column.endswith("_available") and column.removesuffix("_available") in data:
            if not data[column].equals(data[column.removesuffix("_available")].notna()):
                raise ValueError("Bandera de disponibilidad no coincide: " + column)
    summary = {"input_rows": len(original), "output_rows": len(data), "prisms": int(data.prism_id.nunique()),
               "source_ids_preserved": True, "input_values_preserved": True, "temporal_order_valid": True,
               "zero_intervals": 0, "infinite_values": 0, "source_negative_values": int(original.reported_3d_movement_mm.lt(0).sum()),
               "negative_changes_preserved": int(data.movement_delta_mm.lt(0).sum()),
               "original_min": float(original.reported_3d_movement_mm.min()),
               "original_max": float(original.reported_3d_movement_mm.max()),
               "fully_empty_columns": [c for c in data if data[c].isna().all()],
               "constant_columns": [c for c in data if data[c].dropna().nunique() == 1],
               "derived_columns": len(data.columns)-len(original.columns), "total_columns": len(data.columns)}
    return summary


def feature_quality_tables(result: FeatureDataset):
    data = result.data
    quality = result.dictionary[["feature_name", "group", "unit", "temporal_window"]].copy()
    quality["dtype"] = quality.feature_name.map(lambda c: str(data[c].dtype))
    quality["row_count"] = len(data)
    quality["available_count"] = quality.feature_name.map(lambda c: int(data[c].notna().sum()))
    quality["nan_count"] = len(data)-quality.available_count
    quality["nan_pct"] = 100*quality.nan_count/len(data)
    quality["available_pct"] = 100-quality.nan_pct
    quality["fully_empty"] = quality.available_count.eq(0)
    quality["constant_among_known"] = quality.feature_name.map(lambda c: data[c].dropna().nunique() == 1)
    flags = {"consecutive_change": "movement_delta_mm_available", "observed_rate": "movement_rate_mm_per_day_available",
             "prior_baseline": "has_sufficient_history", "conventional_z": "historical_z_score_available",
             "robust_z": "historical_robust_z_score_available", "streak": "streak_evaluable"}
    for label, _ in WINDOWS:
        flags.update({"movement_descriptive_"+label: f"movement_{label}_mean_mm_available",
                      "movement_dispersion_"+label: f"movement_{label}_std_mm_available",
                      "internal_changes_"+label: f"delta_{label}_mean_available",
                      "sufficient_window_"+label: f"has_sufficient_{label}_history"})
    for label in ("72h", "7d"):
        flags["local_trend_"+label] = f"local_trend_{label}_slope_mm_per_day_available"
    groups = pd.DataFrame([{"feature_group": name, "availability_flag": flag, "available_rows": int(data[flag].sum()),
                            "total_rows": len(data), "available_pct": 100*data[flag].mean()}
                           for name, flag in flags.items()])
    prisms = []
    for prism, g in data.groupby("prism_id", sort=True):
        row = {"prism_id": prism, "rows": len(g), "first_timestamp": g.timestamp.min(), "last_timestamp": g.timestamp.max(),
               "insufficient_for_baseline_at_end": not bool(g.has_sufficient_history.iloc[-1]),
               "gap_over_24h_rows": int(g.is_gap_over_24h.sum()), "gap_over_72h_rows": int(g.is_gap_over_72h.sum()),
               "gap_over_7d_rows": int(g.is_gap_over_7d.sum()), "first_history_available_timestamp": g.loc[g.has_sufficient_history, "timestamp"].min()}
        for name, flag in flags.items():
            row[name+"_available_pct"] = 100*g[flag].mean()
        prisms.append(row)
    distributions = []
    for column in ("elapsed_hours", "movement_delta_mm", "movement_rate_mm_per_day", "local_trend_72h_slope_mm_per_day", "local_trend_7d_slope_mm_per_day"):
        x = data[column].dropna()
        distributions.append({"feature_name": column, "known_rows": len(x), "missing_rows": int(data[column].isna().sum()),
                              "min": x.min(), "max": x.max(), "mean": x.mean(), "median": x.median(),
                              "q1": x.quantile(.25), "q3": x.quantile(.75), "std_sample": x.std(ddof=1)})
    status = data.feature_quality_status.value_counts().rename_axis("quality_status").reset_index(name="rows")
    status["rows_pct"] = 100*status.rows/len(data)
    return quality, groups, pd.DataFrame(prisms), pd.DataFrame(distributions), status


def export_feature_dataset(result: FeatureDataset, directory):
    directory = Path(directory).resolve()
    if "raw" in directory.parts or ("processed" in directory.parts and directory.name != "phase4"):
        raise ValueError("Destino prohibido: conservar fuentes y preparación anterior; usar nueva carpeta phase4.")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/"west_wall_features.csv"
    result.data.to_csv(path, index=False, float_format="%.17g", na_rep="")
    return path


def read_feature_dataset(path, dtypes):
    numeric_bool = {c: kind for c, kind in dtypes.items() if kind not in {"object", "string"} and not kind.startswith("datetime")}
    text = {c: str for c, kind in dtypes.items() if kind in {"object", "string"}}
    data = pd.read_csv(path, converters=text, dtype=numeric_bool, float_precision="round_trip")
    for column, kind in dtypes.items():
        if kind.startswith("datetime"):
            data[column] = pd.to_datetime(data[column], errors="raise")
    return data
