"""Verify the saved Phase 5 artifacts and register documentary hashes; never fit."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys
import tempfile
import xml.etree.ElementTree as ET

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.anomaly_models import tree_feature_metadata
from src.model_validation import learned_pipeline_fingerprint
from scripts.run_phase5 import load_inputs

OUT = ROOT / 'reports/phase5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def verify():
    before = json.loads((OUT / 'audit/before_documentation_closure.json').read_text())
    meta = json.loads((OUT / 'phase5_metadata.json').read_text())
    excluded = {'reports/phase5/model_findings.md', 'reports/phase5/reproducibility.json',
                'reports/phase5/phase5_metadata.json'}
    unchanged = {p: h for p, h in before['files'].items() if p not in excluded}
    for p, expected in unchanged.items():
        assert sha(ROOT / p) == expected, p
    for p, expected in meta['files'].items():
        assert sha(ROOT / p) == expected, p
    bundle = joblib.load(ROOT / 'models/phase5/scoring_bundle.joblib')
    pipeline = joblib.load(ROOT / 'models/phase5/isolation_forest.joblib')
    model_meta = json.loads((ROOT / 'models/phase5/model_metadata.json').read_text())
    actual = tree_feature_metadata(pipeline)
    assert type(pipeline.named_steps['model'].max_features) is float
    assert pipeline.named_steps['model'].max_features == 1.0
    assert type(model_meta['parameters']['max_features']) is float
    assert model_meta['parameters']['max_features'] == 1.0
    assert actual == model_meta['tree_feature_availability'] == meta['tree_feature_availability']
    assert actual['effective_available_features_per_tree'] == [17]
    assert actual['trees_with_all_selected_features'] == actual['tree_count'] == 200
    fingerprint = learned_pipeline_fingerprint(pipeline)
    assert fingerprint == learned_pipeline_fingerprint(bundle.pipeline) == meta['model_state_sha256']
    data, _, _ = load_inputs()
    scores = bundle.score_new(data)
    with tempfile.TemporaryDirectory(prefix='phase5-closure-reload-') as temp:
        target = Path(temp) / 'existing_bundle.joblib'
        joblib.dump(bundle, target, compress=3)
        reloaded = joblib.load(target)
        pd.testing.assert_frame_equal(scores, reloaded.score_new(data), check_exact=True)
        assert learned_pipeline_fingerprint(reloaded.pipeline) == fingerprint
    saved = pd.read_csv(ROOT / 'data/processed/phase5/anomaly_scores.csv')
    future = saved.period.ne('entrenamiento').to_numpy()
    perturbed = data.copy(deep=True)
    perturbed.loc[future, bundle.selected_features] = 1e12
    pd.testing.assert_frame_equal(scores.loc[~future], bundle.score_new(perturbed).loc[~future], check_exact=True)
    proof = json.loads((OUT / 'reproducibility.json').read_text())
    assert proof['model_reload_scores_exact'] and proof['full_reproduction_completed']
    assert proof['model_state_sha256'] == fingerprint
    assert proof['source_sha256'] == meta['source_sha256']
    assert proof['csv_tables_byte_identical'] == 34
    assert all(proof['training_invariance'].values())
    figures = {('reports/phase5/' + item[k]): sha(OUT / item[k])
               for item in meta['figures'] for k in ('png', 'html')}
    write_json(OUT / 'documentation_closure.json', {
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'checkpoint_before_closure': before['checkpoint_before_closure'],
        'production_retraining_performed': False,
        'primary_max_features_value': 1.0, 'primary_max_features_type': 'float',
        'effective_available_features_per_tree': 17, 'tree_count': 200,
        'serialization_reload_scores_exact': True, 'inference_rows_checked': len(scores),
        'future_rows_perturbed_without_fit': int(future.sum()),
        'training_inference_unchanged': True,
        'production_artifacts_unchanged': True,
        'production_artifact_count': len(meta['files']),
        'unchanged_file_count': len(unchanged), 'unchanged_files_sha256': unchanged,
        'figure_file_count': len(figures), 'figure_files_sha256': figures,
        'model_state_sha256': fingerprint,
        'previous_full_reproduction_retained': True,
        'previous_reproduced_csv_count': 34,
        'current_command': 'python scripts/verify_phase5.py (without --reproduce)',
        'unit_suite_may_fit_isolated_test_models': True,
    })
    print('Existing model serialization and inference exact; 200 trees × 17 available features; production unchanged.')


def finalize():
    suites = ET.parse(OUT / 'pytest-results.xml').getroot().findall('testsuite')
    totals = {name: sum(int(s.get(name, 0)) for s in suites)
              for name in ('tests', 'failures', 'errors', 'skipped')}
    assert totals['tests'] > 0 and totals['failures'] == totals['errors'] == totals['skipped'] == 0
    paths = ['reports/phase5/model_findings.md', 'reports/phase5/documentation_closure.json',
             'reports/phase5/pytest-results.xml', 'reports/phase5/pytest-output.txt',
             'reports/phase5/verification-log.txt', 'reports/phase5/reproducibility.json',
             'scripts/build_phase5_report.py', 'scripts/close_phase5_documentation.py',
             'tests/test_max_features_revision.py', 'models/phase5/model_metadata.json']
    write_json(OUT / 'documentation_metadata.json', {
        'finalized_at_utc': datetime.now(timezone.utc).isoformat(), 'test_totals': totals,
        'files_sha256': {p: sha(ROOT / p) for p in paths},
        'report_rebuilt_from_existing_artifacts': True,
        'production_retraining_performed': False,
        'checkpoint_file': 'reports/phase5/git_checkpoint.txt',
        'checkpoint_recorded_after_commit_to_avoid_self_reference': True,
    })
    path = OUT / 'phase5_metadata.json'
    meta = json.loads(path.read_text())
    meta['documentation_closure'] = {
        'metadata_path': 'reports/phase5/documentation_metadata.json',
        'metadata_sha256': sha(OUT / 'documentation_metadata.json'),
        'report_sha256': sha(OUT / 'model_findings.md'), 'test_total': totals['tests'],
        'production_retraining_performed': False,
    }
    write_json(path, meta)
    print(json.dumps(totals))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--finalize', action='store_true')
    finalize() if parser.parse_args().finalize else verify()
