from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from src.config import FeatureConfig, load_feature_config
from src.feature_engineering import engineer_features
from src.feature_validation import validate_feature_dataset, export_feature_dataset, read_feature_dataset, check_protected


def synthetic(values, hours=None, prism="A"):
    hours = list(range(len(values))) if hours is None else hours
    return pd.DataFrame({"prism_id": prism, "timestamp": [pd.Timestamp("2014-01-01") + pd.Timedelta(hours=h) for h in hours],
                         "reported_3d_movement_mm": values, "row_id": [f"{prism}-{i}" for i in range(len(values))],
                         "source_line": [str(i+2) for i in range(len(values))], "source_name": "synthetic-test.csv", "source_sha256": "test-only"})


def test_first_row_unavailable():
    d = engineer_features(synthetic([3])).data.iloc[0]
    assert d.is_first_observation and pd.isna(d.previous_timestamp) and pd.isna(d.elapsed_hours)
    assert pd.isna(d.movement_delta_mm) and pd.isna(d.movement_rate_mm_per_day)
    assert not d.movement_rate_mm_per_day_available and not d.has_sufficient_history
    assert d.feature_quality_status == "sin historia previa" and d.window_24h_observation_count == 1


def test_positive_interval_negative_delta_and_extreme_retained():
    f = synthetic([10., -2., 1e9], [0, 12, 24]); before = f.copy(deep=True)
    result = engineer_features(f); d = result.data
    assert len(d) == len(f) and d.reported_3d_movement_mm.tolist() == [10., -2., 1e9]
    assert d.movement_delta_mm.iloc[1] == -12 and d.movement_rate_mm_per_day.iloc[1] == -24
    assert d.absolute_movement_rate_mm_per_day.iloc[1] == 24 and d.movement_decreased.iloc[1]
    pd.testing.assert_frame_equal(f, before)
    assert validate_feature_dataset(f, result)["input_values_preserved"]


@pytest.mark.parametrize("gap,flags", [(25, [True, False, False]), (73, [True, True, False]), (169, [True, True, True])])
def test_gap_flags_no_interpolation(gap, flags):
    d = engineer_features(synthetic([1., 2.], [0, gap])).data
    assert len(d) == 2
    assert d.iloc[1][["is_gap_over_24h", "is_gap_over_72h", "is_gap_over_7d"]].tolist() == flags
    assert d.movement_rate_mm_per_day.iloc[1] == pytest.approx(24/gap)


def test_short_interval_is_flagged_kept():
    d = engineer_features(synthetic([1., 2.], [0, 1/120])).data.iloc[1]
    assert d.is_unusually_short_interval and d.movement_rate_mm_per_day_available
    assert d.movement_rate_mm_per_day == pytest.approx(2880)


def test_order_identifiers_and_prism_separation():
    f = pd.concat([synthetic([10., 9., 8.], prism="001"), synthetic([1., 4., 6.], prism="B")], ignore_index=True)
    a = engineer_features(f); b = engineer_features(f.sample(frac=1, random_state=42))
    pd.testing.assert_frame_equal(a.data, b.data)
    assert a.data.source_record_id.tolist() == a.data.row_id.tolist()
    assert a.data.groupby("prism_id").movement_delta_mm.first().tolist() == [-1., 3.]
    assert a.data.is_first_observation.sum() == 2


def test_duplicate_timestamp_rejected_not_silently_excluded():
    f = synthetic([1., 2.], [0, 0])
    with pytest.raises(ValueError, match="duplicado/intervalo cero"):
        engineer_features(f)
    assert len(f) == 2


def test_missing_current_not_imputed_and_pairs_not_bridged():
    f = synthetic([1., np.nan, 3., 4.])
    d = engineer_features(f).data
    assert pd.isna(d.reported_3d_movement_mm.iloc[1])
    assert d.movement_delta_mm.isna().tolist() == [True, True, True, False]
    assert d.movement_delta_mm.iloc[3] == 1 and pd.isna(d.increase_streak_count.iloc[2])
    assert d.increase_streak_count.iloc[3] == 1


def test_all_unknown_rolling_sums_stay_unknown():
    d = engineer_features(synthetic([np.nan, np.nan, np.nan])).data
    assert d.delta_24h_sum.isna().all() and d.movement_24h_mean_mm.isna().all()
    assert not d.movement_24h_mean_mm_available.any()


def test_streak_reset_zero_missing_and_long_gap():
    d = engineer_features(synthetic([0., 1., 2., 2., 1., 0., np.nan, 3., 4., 5.], [0, 1, 2, 3, 4, 5, 6, 7, 8, 90])).data
    assert d.increase_streak_count.iloc[2] == 2 and d.increase_streak_duration_hours.iloc[2] == 2
    assert d.increase_streak_count.iloc[3] == 0 and d.decrease_streak_count.iloc[3] == 0
    assert d.decrease_streak_count.iloc[5] == 2 and d.decrease_streak_duration_hours.iloc[5] == 2
    assert pd.isna(d.increase_streak_count.iloc[9]) and not d.streak_evaluable.iloc[9]


def test_export_reproducibility_and_roundtrip(tmp_path):
    f = synthetic([0., 1.23456789012345, -2., 1e9], [0, 1, 12, 36])
    result = engineer_features(f)
    a = export_feature_dataset(result, tmp_path/"a"); b = export_feature_dataset(engineer_features(f), tmp_path/"b")
    assert a.read_bytes() == b.read_bytes()
    restored = read_feature_dataset(a, {c: str(result.data[c].dtype) for c in result.data})
    pd.testing.assert_frame_equal(result.data, restored, check_exact=True)
    with pytest.raises(ValueError, match="prohibido"):
        export_feature_dataset(result, tmp_path/"data/raw")
    with pytest.raises(ValueError):
        export_feature_dataset(result, tmp_path/"data/processed/west_wall")


def test_dictionary_has_every_field_and_policy():
    result = engineer_features(synthetic([1., 2., 3.]))
    dictionary = result.dictionary
    assert dictionary.feature_name.tolist() == result.data.columns.tolist()
    assert dictionary.uses_only_past_or_present.all() and not dictionary.uses_future.any()
    baseline = dictionary[dictionary.feature_name.eq("historical_mean_mm")].iloc[0]
    assert not baseline.uses_current_observation
    assert "física validada" in dictionary[dictionary.feature_name.eq("movement_rate_mm_per_day")].limitations.iloc[0]


@pytest.mark.parametrize("options", [{"min_slope_observations": 2}, {"min_baseline_observations": 1},
                                      {"short_interval_hours": 0}, {"min_window_span_fraction": 1.1},
                                      {"robust_mad_scale": 0}, {"prolonged_gap_hours": float("inf")},
                                      {"min_dispersion_observations": True}])
def test_invalid_configuration(options):
    with pytest.raises(ValueError):
        FeatureConfig(**options)


def test_configuration_loaded_without_source_code_changes(tmp_path):
    path = tmp_path/"policy.json"; path.write_text(json.dumps({"min_baseline_observations": 3}))
    assert load_feature_config(path).min_baseline_observations == 3


def test_previous_files_intact_phase4():
    root = Path(__file__).resolve().parents[1]
    assert check_protected(root, root/"reports/phase4/protected_before_phase4.json") == 226


def test_empty_infinite_or_missing_provenance_rejected():
    with pytest.raises(ValueError):engineer_features(synthetic([]))
    with pytest.raises(ValueError, match="infinito"):engineer_features(synthetic([1., np.inf]))
    with pytest.raises(ValueError, match="trazabilidad"):engineer_features(synthetic([1.]).drop(columns="row_id"))
