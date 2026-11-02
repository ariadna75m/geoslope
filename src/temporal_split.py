"""Cortes globales por cuantiles de días únicos; nunca mezcla filas aleatoriamente."""
import pandas as pd

PERIODS = ("entrenamiento", "validación", "prueba")


def temporal_split(data, config):
    timestamp = pd.to_datetime(data.timestamp, errors="raise")
    if timestamp.isna().any():
        raise ValueError("No se puede dividir una fecha desconocida.")
    days = pd.Series(timestamp.dt.normalize().unique()).sort_values().reset_index(drop=True)
    if len(days) < 5:
        raise ValueError("Se requieren al menos cinco días distintos para tres periodos.")
    first = days.quantile(config["train_fraction"]).floor("D") + pd.Timedelta(days=1)
    second = days.quantile(config["train_fraction"] + config["validation_fraction"]).floor("D") + pd.Timedelta(days=1)
    labels = pd.Series(PERIODS[2], index=data.index, dtype=object)
    labels.loc[timestamp.lt(second)] = PERIODS[1]
    labels.loc[timestamp.lt(first)] = PERIODS[0]
    if set(labels) != set(PERIODS):
        raise ValueError("Un periodo quedó vacío; revisar cortes configurados.")
    return labels, {"train_end_exclusive": str(first), "validation_end_exclusive": str(second),
                    "unique_calendar_days": len(days), "quantile_interpolation": "linear; floor day + 1 day",
                    "same_calendar_day_same_period": True}


def split_summary(data, labels, eligible):
    rows = []
    previous = set()
    for period in PERIODS:
        g = data.loc[labels.eq(period)]
        prisms = set(g.prism_id)
        known = {c: int(g[c].notna().sum()) for c in g if c.endswith("_slope_mm_per_day") or c == "historical_robust_z_score"}
        rows.append({"period": period, "first_timestamp": g.timestamp.min(), "last_timestamp": g.timestamp.max(),
                     "rows": len(g), "prisms": len(prisms), "eligible_rows": int(eligible.loc[g.index].sum()),
                     "eligible_pct": 100 * eligible.loc[g.index].mean(), "calendar_days": g.timestamp.dt.normalize().nunique(),
                     "prisms_new_vs_previous": ";".join(sorted(prisms - previous)),
                     "prisms_disappeared_vs_previous": ";".join(sorted(previous - prisms)),
                     "feature_known_counts": str(known)})
        previous = prisms
    return pd.DataFrame(rows)
