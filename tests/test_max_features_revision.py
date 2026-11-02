"""Regresión de la diferencia entero/fracción y comparación controlada real."""
from functools import lru_cache
from pathlib import Path
from copy import deepcopy
import json
import joblib
import numpy as np
import pandas as pd
import pytest
from scripts.run_phase5 import load_inputs
from src.anomaly_models import train_models, tree_feature_metadata
from src.anomaly_evaluation import max_features_sensitivity
from src.model_validation import learned_pipeline_fingerprint
from src.phase5_config import validate_model_config

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def real_case():
    data, dictionary, cfg = load_inputs()
    result = train_models(data, dictionary, cfg)
    tables, variants = max_features_sensitivity(result, data)
    return data, result, tables, variants


def test_primary_float_and_all_seventeen_features_available():
    _, result, _, _ = real_case()
    meta = tree_feature_metadata(result.bundle.pipeline)
    assert type(meta['configured_max_features']) is float
    assert meta['configured_max_features'] == 1.0
    assert meta['selected_feature_count'] == meta['model_input_feature_count'] == 17
    assert meta['effective_available_features_per_tree'] == [17]
    assert meta['trees_with_all_selected_features'] == 200
    assert len(set(meta['selected_feature_names'])) == 17


def test_integer_one_cannot_accidentally_become_primary():
    _, _, cfg = load_inputs()
    cfg['primary_model']['max_features'] = 1
    with pytest.raises(ValueError, match='float'):
        validate_model_config(cfg)


def test_three_variants_and_csv_preserve_literal_and_type(tmp_path):
    _, _, tables, _ = real_case()
    frame = tables['max_features_sensitivity.csv']
    path = tmp_path/'sensitivity.csv'
    frame.to_csv(path,index=False)
    loaded = pd.read_csv(path,dtype={'max_features_literal':str})
    actual = loaded[['max_features_literal','max_features_type','effective_features_per_tree']].drop_duplicates()
    assert actual.to_records(index=False).tolist() == [('1','int',1),('0.5','float',8),('1.0','float',17)]
    assert frame.groupby(['variant','period']).top_fraction.apply(set).map(lambda x:x=={.01,.02,.05}).all()


def test_training_and_frozen_preprocessing_are_identical():
    _, result, tables, variants = real_case()
    frame = tables['max_features_sensitivity.csv']
    assert frame.training_signature.nunique() == frame.preprocessing_sha256.nunique() == 1
    assert frame.training_rows.eq(2909).all()
    reference = result.bundle.pipeline[:-1].transform(result.training)
    for variant in variants.values():
        np.testing.assert_array_equal(reference,variant.bundle.pipeline[:-1].transform(variant.training))
        assert variant.training.source_record_id.tolist() == result.training.source_record_id.tolist()
        a = result.bundle.pipeline.named_steps['model'].get_params()
        b = variant.bundle.pipeline.named_steps['model'].get_params()
        assert {k:v for k,v in a.items() if k!='max_features'} == {k:v for k,v in b.items() if k!='max_features'}


def test_each_variant_threshold_uses_only_its_training_scores():
    _, _, tables, variants = real_case()
    scores = tables['max_features_scores.csv']
    for label, variant in variants.items():
        training = scores.query("variant == @label and period == 'entrenamiento' and model_eligible")
        expected = np.quantile(training.isolation_forest_score,.99)
        assert variant.bundle.thresholds['isolation_forest']['q99'] == expected
        assert tables['max_features_sensitivity.csv'].query('variant == @label').training_q99_threshold.eq(expected).all()


def test_all_rows_and_unknowns_remain_in_comparison():
    _, _, tables, _ = real_case()
    for _, frame in tables['max_features_scores.csv'].groupby('variant'):
        assert len(frame)==7178 and frame.prism_id.nunique()==49
        assert (~frame.model_eligible).sum()==1280
        assert frame.loc[~frame.model_eligible,['isolation_forest_score','training_percentile','marked_q99']].isna().all().all()


def test_saved_primary_and_reload_are_exact(tmp_path):
    data, result, _, _ = real_case()
    saved = joblib.load(ROOT/'models/phase5/isolation_forest.joblib')
    assert type(saved.named_steps['model'].max_features) is float
    assert saved.named_steps['model'].max_features==1.0
    assert tree_feature_metadata(saved)['trees_with_all_selected_features']==200
    path=tmp_path/'bundle.joblib';joblib.dump(result.bundle,path,compress=3)
    loaded=joblib.load(path)
    pd.testing.assert_frame_equal(result.bundle.score_new(data),loaded.score_new(data),check_exact=True)
    assert learned_pipeline_fingerprint(saved)==learned_pipeline_fingerprint(result.bundle.pipeline)


def test_future_values_do_not_change_any_variant_training():
    data, result, _, variants = real_case()
    shadow=data.copy(deep=True)
    future=result.periods.ne('entrenamiento')
    shadow.loc[future,result.bundle.selected_features]=1e10
    _, changed=max_features_sensitivity(result,shadow)
    for name, first in variants.items():
        second=changed[name]
        assert learned_pipeline_fingerprint(first.bundle.pipeline)==learned_pipeline_fingerprint(second.bundle.pipeline)
        assert first.bundle.thresholds==second.bundle.thresholds
        mask=result.periods.eq('entrenamiento')
        pd.testing.assert_frame_equal(first.scores.loc[mask],second.scores.loc[mask],check_exact=True)


def test_revised_report_disambiguates_integer_and_fraction():
    report=(ROOT/'reports/phase5/model_findings.md').read_text()
    assert '## Corrección de `max_features`' in report
    assert '1.0 (float)' in report
    assert 'ya utilizaba' in report
    assert 'una característica por árbol' in report
    assert 'no demuestra mayor precisión' in report
    principal = report.split('## 10. Isolation Forest', 1)[1].split('Biblioteca:', 1)[0]
    assert 'max_features_type' in principal
    assert 'effective_available_features_per_tree' in principal
    assert '| 1.0 |' in principal and '| float | 17 | 17 |' in principal


def test_principal_parameter_table_preserves_decimal_type_and_available_count():
    from scripts.build_phase5_report import primary_parameter_display, md_table
    metadata = json.loads((ROOT/'models/phase5/model_metadata.json').read_text())
    table = md_table(pd.DataFrame([primary_parameter_display(metadata)]))
    assert '| 1.0 |' in table and '| float | 17 | 17 |' in table


def test_principal_parameter_table_rejects_integer_one():
    from scripts.build_phase5_report import primary_parameter_display
    metadata = json.loads((ROOT/'models/phase5/model_metadata.json').read_text())
    metadata['parameters']['max_features'] = 1
    with pytest.raises(AssertionError):
        primary_parameter_display(metadata)
