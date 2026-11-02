import joblib
import pandas as pd
from src.anomaly_models import train_models
from src.feature_validation import check_protected
from src.model_validation import learned_pipeline_fingerprint
from pathlib import Path
from tests.phase5_helpers import model_case,trained_case

def test_future_modification_cannot_change_any_learned_training_artifact():
    data,dictionary,_,cfg=model_case();first=trained_case()
    future=first.periods.ne('entrenamiento')
    for index,name in enumerate(cfg['candidate_priority']):data.loc[future,name]=1e12 if index%2 else -1e12
    second=train_models(data,dictionary,cfg)
    pd.testing.assert_frame_equal(first.selection.candidates,second.selection.candidates,check_exact=True)
    assert first.preprocessing==second.preprocessing
    assert first.bundle.thresholds==second.bundle.thresholds
    assert first.bundle.baseline.as_dict()==second.bundle.baseline.as_dict()
    assert first.bundle.training_signature==second.bundle.training_signature
    assert learned_pipeline_fingerprint(first.bundle.pipeline)==learned_pipeline_fingerprint(second.bundle.pipeline)
    pd.testing.assert_frame_equal(first.scores.loc[~future],second.scores.loc[~future],check_exact=True)

def test_all_historical_files_remain_intact():
    root=Path(__file__).resolve().parents[1]
    assert check_protected(root,root/'reports/phase5/protected_before_phase5.json')==294
