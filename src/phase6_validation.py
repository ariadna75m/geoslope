"""Read-only checks of Phase 5 inputs, frozen artifacts and Phase 6 contracts."""
from pathlib import Path
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from src.model_validation import learned_pipeline_fingerprint
from src.anomaly_models import tree_feature_metadata

REQUIRED = ['source_record_id', 'prism_id', 'timestamp', 'period', 'model_eligible',
            'model_ineligibility_reason', 'baseline_score', 'isolation_forest_score',
            'baseline_marked_q99', 'isolation_forest_marked_q99',
            'feature_quality_status', 'descriptive_explanation', 'feature_deviation_details']


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_protected(root, manifest):
    paths = json.loads(Path(manifest).read_text())
    for name, expected in paths.items():
        if not (Path(root)/name).is_file() or sha256(Path(root)/name) != expected:
            raise ValueError('Archivo de fase anterior alterado: ' + name)
    return len(paths)


def load_phase5_scores(root):
    root = Path(root)
    metadata = json.loads((root/'reports/phase5/phase5_metadata.json').read_text())
    dtypes = {name: dtype for name, dtype in metadata['score_dtypes'].items()
              if dtype != 'datetime64[ns]'}
    unknowns = {name: [''] for name, dtype in dtypes.items() if dtype in ('float64', 'boolean')}
    scores = pd.read_csv(root/'data/processed/phase5/anomaly_scores.csv', dtype=dtypes,
                         float_precision='round_trip', keep_default_na=False,
                         na_values=unknowns, parse_dates=['timestamp'])
    return validate_scores(scores)


def validate_scores(scores):
    missing = set(REQUIRED)-set(scores.columns)
    if missing:
        raise ValueError('Columnas obligatorias ausentes: ' + ', '.join(sorted(missing)))
    data = scores.copy(deep=True)
    if data.source_record_id.isna().any() or data.source_record_id.eq('').any() or data.source_record_id.duplicated().any():
        raise ValueError('Identificadores vacíos o duplicados.')
    if data.prism_id.isna().any() or data.prism_id.eq('').any():
        raise ValueError('Prisma ausente.')
    data['timestamp'] = pd.to_datetime(data.timestamp, errors='raise')
    if data.timestamp.isna().any() or data.duplicated(['prism_id', 'timestamp']).any():
        raise ValueError('Timestamp ausente o repetido dentro de un prisma.')
    if not pd.api.types.is_bool_dtype(data.model_eligible) or data.model_eligible.isna().any():
        raise ValueError('La elegibilidad debe ser booleana conocida.')
    eligible = data.model_eligible
    if data.loc[~eligible, 'model_ineligibility_reason'].isna().any() or data.loc[~eligible, 'model_ineligibility_reason'].eq('').any():
        raise ValueError('Registro no evaluable sin motivo original.')
    for score, mark in [('baseline_score', 'baseline_marked_q99'), ('isolation_forest_score', 'isolation_forest_marked_q99')]:
        if not pd.api.types.is_bool_dtype(data[mark]):
            raise ValueError('Las marcas deben ser booleanas o desconocidas.')
        if data.loc[eligible, mark].isna().any() or not np.isfinite(data.loc[eligible, score].to_numpy(dtype=float)).all():
            raise ValueError('Registro evaluable con score o marca desconocidos.')
        if data.loc[~eligible, [score, mark]].notna().any().any():
            raise ValueError('No evaluables deben conservar scores y marcas desconocidos.')
    return data.sort_values(['prism_id', 'timestamp', 'source_record_id'], kind='stable').reset_index(drop=True)


def validate_config(config):
    if config.get('primary_window_hours') not in (24, 48, 72):
        raise ValueError('Ventana principal debe ser 24, 48 o 72 horas.')
    if config.get('primary_min_marks') not in (2, 3):
        raise ValueError('Persistencia mínima debe ser 2 o 3 marcas.')
    if config.get('primary_policy') not in ('union', 'consensus', 'persistence', 'hybrid'):
        raise ValueError('Política no admitida.')
    if config.get('sensitivity_windows_hours') != [24, 48, 72] or config.get('sensitivity_min_marks') != [2, 3]:
        raise ValueError('El análisis debe incluir las seis combinaciones temporales solicitadas.')
    if config.get('candidate_requires_current_union_mark') is not True:
        raise ValueError('Las políticas actuales requieren marca en el registro actual.')
    if config.get('episode_continuity_across_partitions') is not True:
        raise ValueError('La configuración actual conserva continuidad temporal entre particiones.')
    if config.get('quality_records_do_not_reset_episode') is not True or config.get('policies') != ['union','consensus','persistence','hybrid']:
        raise ValueError('Se deben conservar las políticas y la gestión de calidad solicitadas.')
    return config


def verify_frozen(root):
    root = Path(root)
    metadata = json.loads((root/'reports/phase5/phase5_metadata.json').read_text())
    for name, expected in metadata['files'].items():
        if sha256(root/name) != expected:
            raise ValueError('Artefacto de Fase 5 alterado: ' + name)
    model_meta = json.loads((root/'models/phase5/model_metadata.json').read_text())
    pipeline = joblib.load(root/'models/phase5/isolation_forest.joblib')
    bundle = joblib.load(root/'models/phase5/scoring_bundle.joblib')
    params = pipeline.named_steps['model'].get_params()
    expected = dict(n_estimators=200, max_samples=256, max_features=1.0,
                    bootstrap=False, random_state=42, contamination=0.02, n_jobs=1)
    assert type(params['max_features']) is float
    assert {k: params[k] for k in expected} == expected
    assert model_meta['execution_parameters'] == expected
    available = tree_feature_metadata(pipeline)
    assert available == model_meta['tree_feature_availability']
    assert available['effective_available_features_per_tree'] == [17]
    assert available['trees_with_all_selected_features'] == 200
    assert learned_pipeline_fingerprint(pipeline) == metadata['model_state_sha256'] == learned_pipeline_fingerprint(bundle.pipeline)
    data = pd.read_csv(root/'data/processed/phase4/west_wall_features.csv', float_precision='round_trip', low_memory=False)
    data['timestamp'] = pd.to_datetime(data.timestamp)
    scores = load_phase5_scores(root)
    regenerated = bundle.score_new(data)
    pd.testing.assert_frame_equal(scores[regenerated.columns], regenerated, check_exact=True)
    for name in ('baseline', 'isolation_forest'):
        threshold = model_meta['thresholds'][name]['q99']
        assert round(threshold, 4) == {'baseline': 4.4398, 'isolation_forest': 0.5873}[name]
        actual = scores.loc[scores.model_eligible, name+'_score'].gt(threshold)
        pd.testing.assert_series_equal(actual.astype('boolean'), scores.loc[scores.model_eligible, name+'_marked_q99'], check_names=False)
    return {'model_reload_predictions_unchanged': True, 'max_features': 1.0,
            'max_features_type': 'float', 'available_features_per_tree': 17,
            'tree_count': 200, 'training_performed': False,
            'model_state_sha256': metadata['model_state_sha256'],
            'artifact_sha256': {name: sha256(root/name) for name in metadata['files']},
            'thresholds': {k: model_meta['thresholds'][k]['q99'] for k in ('baseline', 'isolation_forest')}}


def read_outputs(root, metadata):
    """Restore nullable types and blank human fields without inventing labels."""
    frames = {}
    for name, all_types in metadata['output_dtypes'].items():
        dates = [c for c,d in all_types.items() if d.startswith('datetime64')]
        dtypes = {c:d for c,d in all_types.items() if c not in dates}
        unknowns = {c:[''] for c,d in dtypes.items() if d in ('float64','boolean')}
        frames[name] = pd.read_csv(Path(root)/'data/processed/phase6'/name,
                                  dtype=dtypes, parse_dates=dates, keep_default_na=False,
                                  na_values=unknowns, float_precision='round_trip')
    return frames
