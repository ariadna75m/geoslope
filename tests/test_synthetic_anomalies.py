import numpy as np
import pandas as pd
import pytest
from src.synthetic_anomalies import inject_anomaly,KINDS
from src.feature_engineering import engineer_features,VALUE
from tests.phase5_helpers import model_case,trained_case

@pytest.mark.parametrize('kind',KINDS)
def test_synthetic_generation_audit_and_original_preservation(kind):
    _,_,raw,_=model_case();source=raw[raw.prism_id.eq('A')].reset_index(drop=True);before=source.copy(deep=True)
    times=source.timestamp.iloc[210:217]
    copy,audit=inject_anomaly(source,times,kind,500.,2026)
    pd.testing.assert_frame_equal(source,before,check_exact=True)
    assert len(copy)==len(source) and len(audit)>0
    assert np.allclose(audit.synthetic_movement_mm-audit.original_movement_mm,audit.injected_delta_mm)
    same=~copy.row_id.isin(audit.source_record_id)
    pd.testing.assert_frame_equal(copy.loc[same],source.loc[same],check_exact=True)
    if kind=='positive_jump':assert audit.injected_delta_mm.iloc[0]>0
    if kind=='negative_jump':assert audit.injected_delta_mm.iloc[0]<0
    if kind=='persistent_increases':assert copy.loc[copy.timestamp.isin(times),VALUE].diff().dropna().gt(0).all()
    if kind=='artificial_acceleration':assert np.diff(np.diff(audit.injected_delta_mm)) .min()>0

def test_noise_is_reproducible():
    _,_,raw,_=model_case();source=raw[raw.prism_id.eq('A')].reset_index(drop=True);times=source.timestamp.iloc[210:217]
    a,log_a=inject_anomaly(source,times,'increased_variability',100.,7)
    b,log_b=inject_anomaly(source,times,'increased_variability',100.,7)
    pd.testing.assert_frame_equal(a,b);pd.testing.assert_frame_equal(log_a,log_b)

@pytest.mark.parametrize('kind',['positive_jump','negative_jump','sustained_level','artificial_acceleration'])
def test_model_sensitivity_to_strong_artificial_cases(kind):
    _,_,raw,_=model_case();source=raw[raw.prism_id.eq('A')].reset_index(drop=True)
    modified,audit=inject_anomaly(source,source.timestamp.iloc[210:217],kind,5000.,2026)
    features=engineer_features(modified).data
    scores=trained_case().bundle.score_new(features).set_index('source_record_id')
    target=scores.loc[audit.source_record_id]
    assert target.model_eligible.all()
    assert target.isolation_forest_marked_q99.astype(bool).any()
