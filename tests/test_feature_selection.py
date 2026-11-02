import numpy as np
import pytest
from src.feature_selection import select_features
from src.phase5_config import validate_model_config
from tests.phase5_helpers import model_case,trained_case

def test_selector_excludes_identifiers_audit_and_position():
    result=trained_case(); names=result.bundle.selected_features
    assert not {'prism_id','timestamp','source_record_id','source_sha256','total_prior_observations'} & set(names)
    assert not any(name.startswith('original__') or name.endswith('_available') for name in names)
    excluded=result.selection.excluded.set_index('feature_name')
    assert 'prohibido' in excluded.loc['prism_id','reason']
    assert 'temporal' in excluded.loc['total_prior_observations','reason']

def test_constants_empty_missing_and_duplicate_candidates():
    data,dictionary,_,cfg=model_case();data=data.iloc[:100].copy()
    cfg['candidate_priority']=['movement_rate_mm_per_day','movement_delta_mm','movement_72h_mad_mm','movement_7d_mad_mm','historical_robust_z_score']
    data['movement_rate_mm_per_day']=np.arange(100,dtype=float)
    data['movement_delta_mm']=2*data.movement_rate_mm_per_day
    data['movement_72h_mad_mm']=1.
    data['movement_7d_mad_mm']=np.nan
    data['historical_robust_z_score']=np.sin(np.arange(100))
    result=select_features(data,dictionary,cfg)
    assert result.selected==['movement_rate_mm_per_day','historical_robust_z_score']
    table=result.candidates.set_index('feature_name')
    assert table.loc['movement_delta_mm','spearman_with_retained']==pytest.approx(1)
    assert 'constante' in table.loc['movement_72h_mad_mm','reason']
    assert 'vacía' in table.loc['movement_7d_mad_mm','reason']

def test_predictor_identifiers_rejected_by_configuration():
    _,_,_,cfg=model_case();cfg['candidate_priority'].append('prism_id')
    with pytest.raises(ValueError,match='identificadores'):validate_model_config(cfg)

def test_absolute_and_signed_pairs_are_reported():
    pairs=trained_case().selection.pairs
    assert pairs.absolute_vs_signed.sum()==2
    assert {'spearman','pearson','known_pairs'}.issubset(pairs)

@pytest.mark.parametrize('name,value', [('n_estimators',0),('max_samples',0),('max_features',1.5),('contamination',.7),('bootstrap','yes')])
def test_invalid_forest_configuration_is_rejected(name,value):
    _,_,_,cfg=model_case();cfg['primary_model'][name]=value
    with pytest.raises(ValueError):validate_model_config(cfg)

def test_required_experimental_quantiles_are_preserved():
    _,_,_,cfg=model_case();cfg['threshold_quantiles']=[.98]
    with pytest.raises(ValueError,match='cuantiles'):validate_model_config(cfg)
