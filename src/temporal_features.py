"""Fórmulas temporales puras, sin imputación ni acceso a observaciones futuras."""
import numpy as np
import pandas as pd
from .config import FeatureConfig


def sample_statistics(values, min_dispersion=2):
    """Momentos no ponderados, MAD sin escalar y extremos originales de ventana."""
    raw = np.asarray(values, dtype=float)
    x = raw[np.isfinite(raw)]
    count = len(x)
    names = ("mean", "median", "min", "max", "range", "std", "mad", "first", "last", "net_change")
    result = {key: np.nan for key in names}
    result["valid_count"] = count
    if not count:
        return result
    with np.errstate(over="ignore", invalid="ignore"):
        median = np.median(x)
        result.update(mean=np.mean(x), median=median, min=np.min(x), max=np.max(x),
                      range=np.max(x) - np.min(x), mad=np.median(np.abs(x - median)))
        if count >= min_dispersion:
            result["std"] = np.std(x, ddof=1)
        # No saltar un dato desconocido para redefinir los extremos temporales.
        result["first"] = raw[0]
        result["last"] = raw[-1]
        result["net_change"] = raw[-1] - raw[0]
    return result


def change_statistics(values, min_dispersion=2):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    result = {key: np.nan for key in ("mean", "median", "std", "min", "max", "sum", "absolute_sum",
                                     "increase_proportion", "decrease_proportion")}
    result["valid_count"] = len(x)
    if len(x):
        with np.errstate(over="ignore", invalid="ignore"):
            result.update(mean=np.mean(x), median=np.median(x), min=np.min(x), max=np.max(x),
                          sum=np.sum(x), absolute_sum=np.sum(np.abs(x)),
                          increase_proportion=np.mean(x > 0), decrease_proportion=np.mean(x < 0))
            if len(x) >= min_dispersion:
                result["std"] = np.std(x, ddof=1)
    return result


def pair_features(current, previous, timestamp, previous_timestamp, config: FeatureConfig):
    first = pd.isna(previous_timestamp)
    hours = np.nan if first else (pd.Timestamp(timestamp) - pd.Timestamp(previous_timestamp)).total_seconds() / 3600
    evaluable = not first and np.isfinite(current) and np.isfinite(previous)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        delta = np.float64(current) - np.float64(previous) if evaluable else np.nan
        rate = delta / (hours / 24) if evaluable and hours > 0 else np.nan
    return {"elapsed_hours": hours, "elapsed_days": hours / 24,
            "is_first_observation": first, "is_nonpositive_interval": bool(not first and hours <= 0),
            "is_gap_over_24h": bool(hours > 24), "is_gap_over_72h": bool(hours > 72),
            "is_gap_over_7d": bool(hours > 168),
            "is_unusually_short_interval": bool(0 < hours < config.short_interval_hours),
            "is_prolonged_gap": bool(hours > config.prolonged_gap_hours),
            "movement_delta_mm": delta, "absolute_movement_delta_mm": abs(delta),
            "movement_increased": bool(delta > 0), "movement_decreased": bool(delta < 0),
            "movement_unchanged": bool(delta == 0), "movement_rate_mm_per_day": rate,
            "absolute_movement_rate_mm_per_day": abs(rate)}


def local_trend(times, values, config: FeatureConfig, required_span_hours: float):
    timestamps = pd.DatetimeIndex(times)
    y = np.asarray(values, dtype=float)
    valid = np.isfinite(y)
    timestamps, y = timestamps[valid], y[valid]
    points = len(y)
    span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600 if points else np.nan
    result = {"points": points, "duration_hours": span, "slope_mm_per_day": np.nan,
              "r_squared": np.nan, "fitted_current_mm": np.nan}
    if timestamps.nunique() < config.min_slope_observations or span < required_span_hours:
        return result
    if points > 1 and np.max(np.diff(timestamps.asi8) / 3.6e12) > config.prolonged_gap_hours:
        return result
    x = np.asarray((timestamps - timestamps[0]).total_seconds() / 86400, dtype=float)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        xc, yc = x - x.mean(), y - y.mean()
        denominator = np.dot(xc, xc)
        if denominator <= 0:
            return result
        slope = np.dot(xc, yc) / denominator
        fitted = y.mean() + slope * xc
        total = np.dot(yc, yc)
        r2 = 1 - np.sum((y - fitted) ** 2) / total if total > 0 else np.nan
        result.update(slope_mm_per_day=slope, r_squared=r2,
                      fitted_current_mm=y.mean() + slope * (x[-1] - x.mean()))
    return result


def historical_baseline(previous_times, previous_values, current_time, current_value, config: FeatureConfig):
    timestamps = pd.DatetimeIndex(previous_times)
    if (timestamps >= pd.Timestamp(current_time)).any():
        raise ValueError("La línea base contiene el presente o futuro; solo admite t anterior.")
    values = np.asarray(previous_values, dtype=float)
    valid = np.isfinite(values)
    timestamps, values = timestamps[valid], values[valid]
    count = len(values)
    span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600 if count else np.nan
    enough = count >= config.min_baseline_observations and span >= config.min_baseline_span_hours
    result = {"prior_valid_observations": count, "prior_history_duration_hours": span,
              "has_sufficient_history": bool(enough), "historical_mean_mm": np.nan,
              "historical_median_mm": np.nan, "historical_std_mm": np.nan, "historical_mad_mm": np.nan,
              "difference_from_prior_mean_mm": np.nan, "difference_from_prior_median_mm": np.nan,
              "historical_z_score": np.nan, "historical_robust_z_score": np.nan,
              "historical_std_zero": False, "historical_mad_zero": False,
              "historical_dispersion_insufficient": bool(not enough)}
    if not enough:
        return result
    stats = sample_statistics(values, config.min_dispersion_observations)
    result.update(historical_mean_mm=stats["mean"], historical_median_mm=stats["median"],
                  historical_std_mm=stats["std"], historical_mad_mm=stats["mad"],
                  historical_std_zero=bool(stats["std"] <= config.dispersion_epsilon),
                  historical_mad_zero=bool(stats["mad"] <= config.dispersion_epsilon),
                  historical_dispersion_insufficient=bool(not np.isfinite(stats["std"]) or not np.isfinite(stats["mad"])))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if np.isfinite(current_value):
            result["difference_from_prior_mean_mm"] = current_value - stats["mean"]
            result["difference_from_prior_median_mm"] = current_value - stats["median"]
            if stats["std"] > config.dispersion_epsilon:
                result["historical_z_score"] = (current_value - stats["mean"]) / stats["std"]
            if stats["mad"] > config.dispersion_epsilon:
                result["historical_robust_z_score"] = (current_value - stats["median"]) / (config.robust_mad_scale * stats["mad"])
    return result


def directional_streaks(times, deltas, prolonged, nonpositive):
    """Cero reinicia ambas rachas; desconocido/hueco largo rompe la continuidad."""
    up = down = 0
    anchor_up = anchor_down = None
    result = []
    for i, (delta, gap, invalid) in enumerate(zip(deltas, prolonged, nonpositive)):
        available = i > 0 and np.isfinite(delta) and not gap and not invalid
        row = {"increase_streak_count": np.nan, "decrease_streak_count": np.nan,
               "increase_streak_duration_hours": np.nan, "decrease_streak_duration_hours": np.nan,
               "streak_evaluable": bool(available)}
        if not available:
            up = down = 0
            anchor_up = anchor_down = None
        else:
            if delta > 0:
                anchor_up = times[i-1] if up == 0 else anchor_up
                up += 1
                down = 0
                anchor_down = None
            elif delta < 0:
                anchor_down = times[i-1] if down == 0 else anchor_down
                down += 1
                up = 0
                anchor_up = None
            else:
                up = down = 0
                anchor_up = anchor_down = None
            row.update(increase_streak_count=up, decrease_streak_count=down,
                       increase_streak_duration_hours=(times[i]-anchor_up).total_seconds()/3600 if up else 0.0,
                       decrease_streak_duration_hours=(times[i]-anchor_down).total_seconds()/3600 if down else 0.0)
        result.append(row)
    return result
