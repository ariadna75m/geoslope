import numpy as np
import pandas as pd
import joblib
import pytest
from src.anomaly_models import train_models,train_percentile
from src.model_explanations import add_explanations
from src.model_validation import learned_pipeline_fingerprint
from tests.phase5_helpers import model_case,trained_case

def test_fixed_seed_scores_repeat_and_controlled_seed_change():
    data,dictionary,_,cfg=model_case();first=trained_case();second=train_models(data,dictionary,cfg)
    pd.testing.assert_frame_equal(first.scores,second.scores,check_exact=True)
    assert learned_pipeline_fingerprint(first.bundle.pipeline)==learned_pipeline_fingerprint(second.bundle.pipeline)
    cfg['primary_model']['random_state']=7;other=train_models(data,dictionary,cfg)
    assert not np.array_equal(first.scores.isolation_forest_score.dropna(),other.scores.isolation_forest_score.dropna())
    assert first.bundle.selected_features==other.bundle.selected_features

def test_ineligible_rows_preserved_without_scores_or_normal_labels():
    result=trained_case();scores=result.scores;bad=~scores.model_eligible
    assert len(scores)==520 and bad.any()
    assert scores.loc[bad,'model_ineligibility_reason'].str.len().gt(0).all()
    assert scores.loc[bad,['baseline_score','isolation_forest_score']].isna().all().all()
    assert scores.loc[bad,'isolation_forest_marked_q99'].isna().all()
    assert scores.loc[scores.model_eligible,'isolation_forest_score'].notna().all()

def test_serialization_reload_and_new_observation(tmp_path):
    data,_,_,_=model_case();result=trained_case()
    path=tmp_path/'bundle.joblib';joblib.dump(result.bundle,path,compress=3)
    restored=joblib.load(path)
    pd.testing.assert_frame_equal(result.bundle.score_new(data),restored.score_new(data),check_exact=True)
    single=data.loc[result.scores.model_eligible].iloc[[-1]]
    score=restored.score_new(single)
    assert len(score)==1 and score.isolation_forest_score.notna().all()

def test_ecdf_percentiles_ties_and_unknowns():
    assert train_percentile([1.,2.,2.,4.],[-1.,2.,9.,np.nan])[:3].tolist()==[0.,75.,100.]
    assert np.isnan(train_percentile([1.,2.],[np.nan])[0])
    with pytest.raises(ValueError):train_percentile([],[1.])

def test_training_thresholds_and_explanations_are_descriptive():
    data,dictionary,_,_=model_case();result=trained_case()
    train=result.scores.query("period=='entrenamiento' and model_eligible")
    assert result.bundle.thresholds['isolation_forest']['q99']==np.quantile(train.isolation_forest_score,.99)
    explained=add_explanations(result,data,dictionary)
    assert explained.descriptive_explanation.str.len().gt(0).all()
    forbidden=['va a fallar','riesgo alto','colapso seguro','probabilidad de colapso']
    assert not any(explained.descriptive_explanation.str.lower().str.contains(word).any() for word in forbidden)
    assert explained.loc[explained.model_eligible,'descriptive_explanation'].str.contains('aproximada').all()
