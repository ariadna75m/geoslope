from pathlib import Path
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from tests.phase6_helpers import sample,evaluate,real_case,ROOT
from src.phase6_validation import verify_frozen,check_protected


def test_identifiers_and_row_order_independent_of_input_order():
    data=sample()
    a,e=evaluate(data);b,f=evaluate(data.sample(frac=1,random_state=123))
    pd.testing.assert_frame_equal(a,b,check_exact=True)
    pd.testing.assert_frame_equal(e,f,check_exact=True)


def test_repeated_files_are_byte_identical(tmp_path):
    from scripts.run_phase6 import write_tables
    _,_,tables=real_case()
    a=tmp_path/'one';b=tmp_path/'two'
    write_tables(tables,a);write_tables(tables,b)
    for name in tables:assert (a/name).read_bytes()==(b/name).read_bytes()


def test_phase6_pipeline_and_verification_never_fit(monkeypatch):
    from scripts.run_phase6 import load_inputs,build_artifacts
    from src.anomaly_baseline import StatisticalBaseline
    def forbidden(*args,**kwargs):raise AssertionError('Phase 6 attempted to fit a model')
    for model in (IsolationForest,RobustScaler,SimpleImputer,StatisticalBaseline):monkeypatch.setattr(model,'fit',forbidden)
    inputs,config=load_inputs()
    output=build_artifacts(inputs,config)
    proof=verify_frozen(ROOT)
    assert len(output['review_candidates.csv'])==7178 and not proof['training_performed']


def test_frozen_models_scores_thresholds_and_previous_files():
    proof=verify_frozen(ROOT)
    assert proof['thresholds']=={'baseline':4.439772224885318,'isolation_forest':.5872931971929567}
    assert proof['available_features_per_tree']==17
    assert check_protected(ROOT,ROOT/'reports/phase6/protected_before_phase6.json')==426
