"""Organize frozen statistical marks; no model fitting or upstream writes."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys
import time
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.phase6_validation import load_phase5_scores, validate_config, verify_frozen, check_protected, sha256
from src.episode_detection import detect_episodes, summarize_episodes
from src.candidate_policies import apply_policies, compare_policies, daily_workload
from src.episode_explanations import attach_evidence, explain_rows, explain_episodes, specialist_template

OUT = ROOT/'reports/phase6'
DATA = ROOT/'data/processed/phase6'


def json_write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def load_inputs(root=ROOT):
    root = Path(root)
    cfg = validate_config(json.loads((root/'config/phase6.json').read_text()))
    scores = load_phase5_scores(root)
    names = ['source_record_id','prism_id','timestamp','reported_3d_movement_mm',
             'historical_robust_z_score','local_trend_72h_slope_mm_per_day','increase_streak_duration_hours']
    features = pd.read_csv(root/'data/processed/phase4/west_wall_features.csv', usecols=names, float_precision='round_trip')
    baseline = json.loads((root/'models/phase5/statistical_baseline.json').read_text())
    model = json.loads((root/'models/phase5/model_metadata.json').read_text())
    thresholds = {name:model['thresholds'][name]['q99'] for name in ('baseline','isolation_forest')}
    evidence = attach_evidence(scores, features, baseline, thresholds)
    available_from = pd.Timestamp(model['split_cutoffs']['train_end_exclusive'])
    evidence['model_available_from_timestamp'] = pd.Series(available_from,index=evidence.index,dtype='datetime64[ns]')
    evidence['model_available_at_observation'] = evidence.timestamp.ge(available_from)
    evidence['phase5_score_scope'] = np.where(evidence.period.eq('entrenamiento'),
                                            'in_sample_retrospective', 'post_training_temporal_evaluation')
    return evidence, cfg


def build_artifacts(inputs, cfg):
    main_rows = main_episodes = None
    sensitivity = []
    window_episodes = []
    for window in cfg['sensitivity_windows_hours']:
        temporal, closures = detect_episodes(inputs, window)
        for minimum in cfg['sensitivity_min_marks']:
            rows = apply_policies(temporal, window, minimum, cfg['primary_policy'])
            episodes = summarize_episodes(rows, closures, window)
            comparison = compare_policies(rows, episodes, window, minimum)
            sensitivity.append(comparison)
            if window == cfg['primary_window_hours'] and minimum == cfg['primary_min_marks']:
                main_rows = explain_rows(rows, window, minimum)
                main_episodes = explain_episodes(episodes)
                primary_comparison = comparison
                primary_daily = daily_workload(rows)
        window_episodes.append({'window_hours':window,'episodes':len(episodes),
                                'marked_rows':int(temporal.union_mark.sum()),
                                'episodes_with_quality_interruption':int(episodes.quality_interruption_flag.sum()),
                                'censored_episodes':int(episodes.closure_status.eq('censurado_fin_del_prisma').sum())})
    if main_rows is None:
        raise ValueError('La configuración principal no está incluida en sensibilidad.')
    state_counts = main_rows.causal_state.value_counts().reindex(
        ['no_evaluable','sin_marca','marca_aislada','episodio_en_observacion','candidato_revision'],fill_value=0).rename_axis('causal_state').reset_index(name='rows')
    isolated = main_rows.loc[main_rows.causal_state.eq('marca_aislada')]
    unselected = main_rows.loc[main_rows.union_mark.fillna(False) & ~main_rows.review_pending]
    detail_cols = ['source_record_id','prism_id','timestamp','period','episode_id','causal_state','baseline_score','isolation_forest_score',
                   'union_marks_last_72h','candidate_reason']
    prism_rows = main_rows.loc[main_rows.prism_id.eq('30-1994')].copy()
    train = main_rows.loc[main_rows.period.eq('entrenamiento') & main_rows.model_eligible]
    distribution = []
    for scope, group in [('entrenamiento_evaluable',train),('30-1994_evaluable',prism_rows.loc[prism_rows.model_eligible])]:
        for model in ('baseline','isolation_forest'):
            x=group[model+'_score']
            distribution.append({'scope':scope,'model':model,'eligible_rows':len(x),'min_score':x.min(),
                                 'median_score':x.median(),'maximum_score':x.max(),'q99_frozen':main_rows[('baseline' if model=='baseline' else 'iforest')+'_threshold_q99'].iloc[0]})
    outputs = {
        'review_candidates.csv':main_rows, 'episodes.csv':main_episodes,
        'policy_comparison.csv':primary_comparison, 'sensitivity_analysis.csv':pd.concat(sensitivity,ignore_index=True),
        'specialist_review_template.csv':specialist_template(main_episodes,cfg['primary_policy']),
        'daily_candidate_workload.csv':primary_daily, 'causal_state_counts.csv':state_counts,
        'episode_window_summary.csv':pd.DataFrame(window_episodes),
        'isolated_marks.csv':isolated[detail_cols], 'marks_not_selected_primary.csv':unselected[detail_cols],
        'prism_30_1994_observations.csv':prism_rows,
        'prism_30_1994_training_comparison.csv':pd.DataFrame(distribution),
    }
    return {name:frame.reset_index(drop=True) for name,frame in outputs.items()}


def write_tables(tables, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in tables.items():
        data.to_csv(output/name, index=False, lineterminator='\n', date_format='%Y-%m-%d %H:%M:%S', float_format='%.17g')


def main():
    start = time.perf_counter()
    OUT.mkdir(parents=True,exist_ok=True)
    protected = check_protected(ROOT,OUT/'protected_before_phase6.json')
    frozen = verify_frozen(ROOT)
    inputs, cfg = load_inputs()
    tables = build_artifacts(inputs,cfg)
    write_tables(tables,DATA)
    from src.phase6_visualizations import make_figures
    figures = make_figures(tables,OUT)
    assert check_protected(ROOT,OUT/'protected_before_phase6.json') == protected
    assert verify_frozen(ROOT) == frozen
    rows,episodes = tables['review_candidates.csv'],tables['episodes.csv']
    assert len(rows)==7178 and rows.prism_id.nunique()==49
    assert rows.model_eligible.sum()==5898 and (~rows.model_eligible).sum()==1280
    metadata = {
        'phase':'phase6','config':cfg,'config_sha256':sha256(ROOT/'config/phase6.json'),
        'source_sha256':sha256(ROOT/'data/processed/phase5/anomaly_scores.csv'),
        'feature_source_sha256':sha256(ROOT/'data/processed/phase4/west_wall_features.csv'),
        'input_rows':len(rows),'eligible_rows':int(rows.model_eligible.sum()),'ineligible_rows':int((~rows.model_eligible).sum()),
        'prisms':49,'union_mark_rows':int(rows.union_mark.sum()),'agreement_rows':int(rows.agreement_same_row.sum()),
        'episodes':len(episodes),'episodes_with_quality_interruption':int(episodes.quality_interruption_flag.sum()),
        'ineligible_rows_with_episode':int((~rows.model_eligible & rows.episode_id.ne('')).sum()),
        'rows_with_quality_flag':int(rows.quality_interruption_flag.sum()),
        'protected_files_intact':protected,'frozen_models':frozen,
        'causal_state_counts':{str(k):int(v) for k,v in rows.causal_state.value_counts().items()},
        'figures':figures,'output_dtypes':{name:{c:str(d) for c,d in table.dtypes.items()} for name,table in tables.items()},
        'files':{str((DATA/name).relative_to(ROOT)):sha256(DATA/name) for name in tables},
        'figure_sha256':{str((OUT/f[k]).relative_to(ROOT)):sha256(OUT/f[k]) for f in figures for k in ('png','html')},
        'decision_inputs_exclude_physical_failure_event':True,
        'production_training_performed':False,
        'causal_row_fields_separate_from_retrospective_episode_table':True,
        'aggregation_causality_scope':'conditional on frozen Phase 5 marks; training scores are retrospective in-sample and not operational at their original timestamps',
        'versions':{name:importlib.metadata.version(name) for name in ('pandas','numpy','scikit-learn','joblib','matplotlib','plotly','pytest')},
    }
    metadata['figure_sha256']['reports/phase6/interactive/plotly.min.js']=sha256(OUT/'interactive/plotly.min.js')
    json_write(OUT/'phase6_metadata.json',metadata)
    json_write(OUT/'execution_stats.json',{'processing_seconds':time.perf_counter()-start,'timing_excluded_from_reproducibility':True})
    print(json.dumps({k:metadata[k] for k in ('input_rows','eligible_rows','ineligible_rows','episodes','union_mark_rows','agreement_rows','episodes_with_quality_interruption')},indent=2))


if __name__=='__main__':
    main()
