from dataclasses import replace
import pandas as pd
import numpy as np
from src.config import FeatureConfig
from src.feature_engineering import engineer_features
from tests.test_feature_engineering import synthetic


def test_future_extremes_do_not_change_any_past_feature():
    cfg = replace(FeatureConfig(), min_baseline_observations=3, min_baseline_span_hours=0)
    before = synthetic([1., 3., 2., 4., 6., np.nan, 5., 5.], [0, 6, 12, 24, 48, 72, 90, 100])
    until = before.timestamp.max()
    expected = engineer_features(before, cfg).data
    future = synthetic([1e12, -1e12, 1e15], [110, 120, 140]); future.row_id = ["future-1", "future-2", "future-3"]
    full = engineer_features(pd.concat([before, future], ignore_index=True), cfg).data
    pd.testing.assert_frame_equal(expected, full.loc[full.timestamp.le(until)].reset_index(drop=True), check_exact=True)


def test_repeated_single_observation_arrivals_match_batch_every_prefix():
    f = synthetic([1., 2., -1., 4., 4., 0., 10., 3.], [0, 1, 4, 6, 24, 48, 75, 80])
    full = engineer_features(f).data
    for time in f.timestamp:
        prefix = f.loc[f.timestamp.le(time)]
        expected = engineer_features(prefix).data
        pd.testing.assert_frame_equal(expected, full.loc[full.timestamp.le(time)].reset_index(drop=True), check_exact=True)


def test_other_prism_future_does_not_change_reference():
    a = synthetic([1., 2., 3.], prism="A")
    b = synthetic([1e12, -1e12, 1e15], [100, 110, 120], prism="B")
    full = engineer_features(pd.concat([a, b], ignore_index=True)).data
    pd.testing.assert_frame_equal(engineer_features(a).data, full[full.prism_id.eq("A")].reset_index(drop=True), check_exact=True)
