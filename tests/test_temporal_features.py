from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from src.config import FeatureConfig
from src.temporal_features import pair_features, sample_statistics, local_trend, historical_baseline
from src.feature_engineering import engineer_features
from tests.test_feature_engineering import synthetic


def test_pair_zero_and_negative_interval_avoid_division():
    cfg = FeatureConfig()
    for previous in [pd.Timestamp("2014-01-01"), pd.Timestamp("2014-01-02")]:
        f = pair_features(2., 1., pd.Timestamp("2014-01-01"), previous, cfg)
        assert f["is_nonpositive_interval"] and pd.isna(f["movement_rate_mm_per_day"])


@pytest.mark.parametrize("values,expected", [([1., 2., 5.], (8/3, 2., 1., 5., 4., 1.)), ([3.], (3., 3., 3., 3., 0., 0.))])
def test_statistics_manual(values, expected):
    d = sample_statistics(values)
    assert tuple(d[c] for c in ["mean", "median", "min", "max", "range", "mad"]) == pytest.approx(expected)
    if len(values) == 1:assert pd.isna(d["std"])
    else:assert d["std"] == pytest.approx(np.sqrt(13/3))


def test_temporal_boundaries_and_internal_pairs():
    d = engineer_features(synthetic([1., 3., 5.], [0, 24, 25])).data.iloc[2]
    assert d.window_24h_observation_count == 2  # (1h,25h], no primera medición
    assert d.movement_24h_first_mm == 3 and d.movement_24h_net_change_mm == 2
    assert d.delta_24h_valid_count == 1 and d.delta_24h_sum == 2
    assert d.delta_24h_absolute_sum == 2 and d.increase_proportion_24h == 1
    # En t=24h, el valor exactamente en t−24h queda fuera.
    assert engineer_features(synthetic([1., 3.], [0, 24])).data.window_24h_observation_count.iloc[1] == 1


def test_known_linear_slope_irregular_times():
    cfg = FeatureConfig()
    times = pd.to_datetime(["2014-01-01", "2014-01-01 06:00", "2014-01-02"], format="mixed")
    trend = local_trend(times, [2., 3., 6.], cfg, 18)
    assert trend["slope_mm_per_day"] == pytest.approx(4.) and trend["r_squared"] == pytest.approx(1.)
    d = engineer_features(synthetic([2., 3., 6.], [0, 6, 24])).data.iloc[-1]
    assert d.local_trend_72h_slope_mm_per_day == pytest.approx(4.)
    assert not d.local_trend_7d_slope_mm_per_day_available  # solo cubre 24h, mínimo 42h


def test_insufficient_slope_and_flat_r_squared():
    assert pd.isna(local_trend(pd.date_range("2014-01-01", periods=2), [1., 2.], FeatureConfig(), 0)["slope_mm_per_day"])
    flat = local_trend(pd.date_range("2014-01-01", periods=3), [1., 1., 1.], FeatureConfig(), 0)
    assert flat["slope_mm_per_day"] == 0 and pd.isna(flat["r_squared"])


def test_baseline_previous_only_manual_zscores():
    cfg = replace(FeatureConfig(), min_baseline_observations=3, min_baseline_span_hours=0)
    d = engineer_features(synthetic([1., 2., 3., 10.]), cfg).data.iloc[-1]
    assert d.historical_mean_mm == 2 and d.historical_median_mm == 2
    assert d.historical_std_mm == 1 and d.historical_mad_mm == 1
    assert d.historical_z_score == 8 and d.historical_robust_z_score == pytest.approx(8/1.4826)
    assert d.total_prior_observations == 3 and d.prior_valid_observations == 3


def test_baseline_zero_std_and_mad_dont_divide():
    cfg = replace(FeatureConfig(), min_baseline_observations=3, min_baseline_span_hours=0)
    d = engineer_features(synthetic([2., 2., 2., 9.]), cfg).data.iloc[-1]
    assert d.has_sufficient_history and d.historical_std_zero and d.historical_mad_zero
    assert pd.isna(d.historical_z_score) and pd.isna(d.historical_robust_z_score)
    assert not d.historical_z_score_available
    e = engineer_features(synthetic([1., 1., 2., 9.]), cfg).data.iloc[-1]
    assert e.historical_std_mm > 0 and e.historical_mad_zero and pd.isna(e.historical_robust_z_score)


def test_window_single_point_and_duration_rule():
    d = engineer_features(synthetic([3., 4., 5.], [0, 1, 2])).data
    assert d.movement_24h_mean_mm.iloc[0] == 3 and pd.isna(d.movement_24h_std_mm.iloc[0])
    assert not d.has_sufficient_24h_history.iloc[-1]  # tres puntos, duración de solo 2h
    assert not d.local_trend_72h_slope_mm_per_day_available.iloc[-1]


def test_baseline_rejects_current_or_future_and_ignores_unknown():
    cfg = replace(FeatureConfig(), min_baseline_observations=2, min_baseline_span_hours=0)
    times = pd.date_range("2014-01-01", periods=3)
    with pytest.raises(ValueError, match="presente o futuro"):
        historical_baseline(times, [1., 2., 3.], times[-1], 4., cfg)
    b = historical_baseline(times, [1., np.nan, 3.], times[-1]+pd.Timedelta(days=1), 4., cfg)
    assert b["prior_valid_observations"] == 2 and b["historical_mean_mm"] == 2


def test_zero_delta_known_stays_zero():
    d = engineer_features(synthetic([1., 1.], [0, 6])).data.iloc[-1]
    assert d.movement_unchanged and d.movement_delta_mm == 0 and d.movement_rate_mm_per_day == 0
    assert d.movement_rate_mm_per_day_available and d.increase_proportion_24h == 0


def test_custom_dispersion_minimum_and_robust_scale_are_auditable():
    cfg = replace(FeatureConfig(), min_baseline_observations=3, min_baseline_span_hours=0,
                  min_dispersion_observations=4, robust_mad_scale=2.)
    result = engineer_features(synthetic([1., 2., 3., 10.]), cfg)
    d = result.data.iloc[-1]
    assert d.has_sufficient_history and d.historical_dispersion_insufficient
    assert pd.isna(d.historical_std_mm) and pd.isna(d.historical_z_score)
    assert d.historical_robust_z_score == 4
    formula = result.dictionary.set_index('feature_name').loc['historical_robust_z_score', 'formula']
    assert '(2×MAD_previa)' in formula
