"""Entrena y evalúa exclusivamente Fase 5; preserva artefactos anteriores."""
from pathlib import Path
import sys,json,time,importlib.metadata as versions
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.phase5_config import load_model_config
from src.config import load_feature_config
from src.feature_validation import read_feature_dataset,check_protected,sha256
from src.exploratory_analysis import read_prepared,DISCLAIMER
from src.anomaly_models import train_models,tree_feature_metadata
from src.model_explanations import add_explanations
from src.anomaly_evaluation import evaluation_tables,seed_stability,hyperparameter_sensitivity,max_features_sensitivity
from src.synthetic_anomalies import synthetic_experiments
from src.model_validation import learned_pipeline_fingerprint

OUT=ROOT/'reports/phase5';DATA=ROOT/'data/processed/phase5';MODELS=ROOT/'models/phase5'
CONFIG=ROOT/'config/phase5.json';PROTECTED=OUT/'protected_before_phase5.json'


def load_inputs():
    metadata=json.loads((ROOT/'reports/phase4/phase4_metadata.json').read_text())
    path=ROOT/metadata['feature_dataset']
    if sha256(path)!=metadata['feature_dataset_sha256']:raise ValueError('Cambió el dataset protegido de Fase 4.')
    features=read_feature_dataset(path,metadata['feature_dtypes'])
    dictionary=pd.read_csv(ROOT/'reports/phase4/feature_dictionary.csv')
    return features,dictionary,load_model_config(CONFIG)


def build_artifacts(data,dictionary,config,*,sensitivity=True,synthetics=True):
    result=train_models(data,dictionary,config)
    result.scores=add_explanations(result,data,dictionary)
    tables=evaluation_tables(result,data)
    tables.update({'selected_features.csv':result.selection.candidates[result.selection.candidates.included].copy(),
                   'candidate_features.csv':result.selection.candidates,
                   'excluded_features.csv':result.selection.excluded,'temporal_split_summary.csv':result.split_table,
                   'spearman_training.csv':result.selection.spearman.rename_axis('feature_name').reset_index(),
                   'pearson_training.csv':result.selection.pearson.rename_axis('feature_name').reset_index(),
                   'pair_redundancy.csv':result.selection.pairs})
    if sensitivity:
        seeds,variability=seed_stability(result,data)
        tables['seed_stability.csv'],tables['seed_score_variability.csv']=seeds,variability
        tables['seed_rank_changes.csv']=variability.sort_values(['rank_range_across_seeds','source_record_id'],ascending=[False,True]).copy()
        instability=variability.groupby(['period','prism_id'],sort=True).agg(
            eligible_rows=('source_record_id','size'),mean_rank_range=('rank_range_across_seeds','mean'),
            maximum_rank_range=('rank_range_across_seeds','max'),mean_score_std=('score_std_across_seeds','mean'),
            maximum_score_std=('score_std_across_seeds','max')).reset_index()
        tables['seed_prism_instability.csv']=instability.sort_values(['period','mean_rank_range','prism_id'],ascending=[True,False,True])
        hyper=hyperparameter_sensitivity(result,data)
        tables['hyperparameter_sensitivity.csv']=hyper
        tables['contamination_sensitivity.csv']=hyper.loc[hyper.family.eq('contamination')].copy()
        comparison,variants=max_features_sensitivity(result,data)
        tables.update(comparison)
    if synthetics:
        prepared=read_prepared(ROOT/'data/processed/west_wall','west_wall')
        metrics,audit,targets=synthetic_experiments(result,data,prepared,load_feature_config(ROOT/'config/phase4.json'))
        tables['synthetic_anomaly_results.csv'],tables['synthetic_injection_audit.csv'],tables['synthetic_target_scores.csv']=metrics,audit,targets
        if sensitivity:
            comparisons=[]
            for label,variant in variants.items():
                if label=='1.0 (float)':variant_metrics=metrics
                else:
                    variant_metrics,variant_audit,_=synthetic_experiments(variant,data,prepared,load_feature_config(ROOT/'config/phase4.json'))
                    pd.testing.assert_frame_equal(audit,variant_audit,check_exact=True)
                frame=variant_metrics.loc[variant_metrics.model.eq('isolation_forest')].copy()
                frame['variant']=label;comparisons.append(frame)
            combined=pd.concat(comparisons,ignore_index=True)
            reference=combined.loc[combined.variant.eq('1 (int)')].set_index('scenario')
            for column in ['synthetic_marked_fraction','mean_score_change','mean_training_percentile','unlabelled_background_marked_fraction']:
                combined[column+'_difference_vs_int1']=combined[column]-combined.scenario.map(reference[column])
            tables['max_features_synthetic_results.csv']=combined
    top=result.scores.loc[result.scores.model_eligible].sort_values(['isolation_forest_score','timestamp','source_record_id'],ascending=[False,True,True]).head(30)
    context=[c for c in ['reported_3d_movement_mm','movement_rate_mm_per_day','local_trend_72h_slope_mm_per_day','local_trend_7d_slope_mm_per_day','historical_robust_z_score','increase_streak_count','increase_streak_duration_hours'] if c not in top]
    tables['top_scored_observations.csv']=top.join(data[context])
    transformed=np.abs(result.bundle.pipeline[:-1].transform(data.loc[top.head(20).index]))
    tables['feature_descriptive_deviations.csv']=pd.DataFrame({'feature_name':result.bundle.selected_features,
        'mean_absolute_training_scaled_deviation':transformed.mean(axis=0)}).sort_values('mean_absolute_training_scaled_deviation',ascending=False)
    reasons=result.scores.loc[~result.scores.model_eligible,'model_ineligibility_reason'].str.split('; ').explode().value_counts().rename_axis('reason').reset_index(name='affected_rows')
    tables['ineligibility_summary.csv']=reasons
    if sensitivity:
        variant_scores=tables['max_features_scores.csv']
        special=[]
        for (variant,period),block in variant_scores.loc[variant_scores.model_eligible].groupby(['variant','period'],sort=False):
            prism=block.loc[block.prism_id.eq('30-1994')]
            top_ids=block.sort_values(['isolation_forest_score','timestamp','source_record_id'],ascending=[False,True,True]).head(30).source_record_id
            special.append({'variant':variant,'period':period,'prism_id':'30-1994','eligible_rows':len(prism),
                            'marked_q99_rows':int(prism.marked_q99.sum()),'marked_q99_pct':100*prism.marked_q99.mean() if len(prism) else np.nan,
                            'maximum_score':prism.isolation_forest_score.max(),'prism_rows_in_top30':int(prism.source_record_id.isin(top_ids).sum()),
                            'top30_prism_share_pct':100*prism.source_record_id.isin(top_ids).sum()/len(top_ids) if len(top_ids) else np.nan})
        tables['prism_30_1994_max_features.csv']=pd.DataFrame(special)
        tables['prism_30_1994_observations.csv']=result.scores.loc[result.scores.prism_id.eq('30-1994')].join(data[context])
    return result,tables


def write_tables(result,tables,output,data_output):
    output,data_output=Path(output),Path(data_output)
    if 'raw' in output.parts or 'raw' in data_output.parts:raise ValueError('Destino original prohibido.')
    output.mkdir(parents=True,exist_ok=True);data_output.mkdir(parents=True,exist_ok=True)
    result.scores.to_csv(data_output/'anomaly_scores.csv',index=False,float_format='%.17g',na_rep='')
    for name,table in tables.items():table.to_csv(output/name,index=False,float_format='%.17g',na_rep='')


def write_models(result,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    bundle=result.bundle
    joblib.dump(bundle.pipeline[:-1],directory/'preprocessing_pipeline.joblib',compress=3)
    joblib.dump(bundle.pipeline,directory/'isolation_forest.joblib',compress=3)
    joblib.dump(bundle,directory/'scoring_bundle.joblib',compress=3)
    (directory/'statistical_baseline.json').write_text(json.dumps(bundle.baseline.as_dict(),ensure_ascii=False,indent=2,allow_nan=False))
    (directory/'selected_features.json').write_text(json.dumps({'selected_features':bundle.selected_features,'selection_scope':'eligible training only'},ensure_ascii=False,indent=2))
    metadata={'model_version':bundle.version,'training_signature':bundle.training_signature,
              'learned_pipeline_state_sha256':learned_pipeline_fingerprint(bundle.pipeline),
              'training_rows':len(result.training),'training_prisms':int(result.training.prism_id.nunique()),
              'training_first_timestamp':str(result.training.timestamp.min()),'training_last_timestamp':str(result.training.timestamp.max()),
              'split_cutoffs':result.cutoffs,'features':bundle.selected_features,'parameters':bundle.config['primary_model'],
              'execution_parameters':{**bundle.config['primary_model'],'n_jobs':1},
              'tree_feature_availability':tree_feature_metadata(bundle.pipeline),
              'preprocessing':result.preprocessing,'thresholds':bundle.thresholds,'score_direction':'-score_samples; higher more statistically atypical; not probability',
              'percentiles':'training empirical CDF, right-inclusive ties; no validation/test fitting',
              'experimental_marking':'strictly score > threshold; noneligible stays unknown',
              'forest_global_justification':'training pool supports stable fitting; per-prism models too sparse; scales/frequencies audited separately',
              'optional_model':'LOF omitted: two required complementary methods already implemented',
              'versions':{name:versions.version(name) for name in ['scikit-learn','numpy','pandas','scipy','joblib']},
              'disclaimer':DISCLAIMER}
    (directory/'model_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False))
    return metadata


def main():
    start=time.perf_counter();protected=check_protected(ROOT,PROTECTED)
    data,dictionary,config=load_inputs()
    print('Entrenamiento y evaluación temporal...',flush=True)
    result,tables=build_artifacts(data,dictionary,config)
    write_tables(result,tables,OUT,DATA);model_metadata=write_models(result,MODELS)
    print(result.split_table[['period','rows','prisms','eligible_rows','eligible_pct']].to_string(index=False),flush=True)
    from src.phase5_visualizations import phase5_plots
    figures=phase5_plots(result,data,tables,OUT)
    sample=data.loc[result.scores.model_eligible].tail(100)
    before=time.perf_counter();result.bundle.score_new(sample);inference_seconds=time.perf_counter()-before
    audit=json.loads((OUT/'audit/before_revision.json').read_text())
    assert audit['previous_selected_features']==result.bundle.selected_features
    assert audit['previous_preprocessing']==result.preprocessing
    assert audit['previous_cutoffs']==result.cutoffs
    assert audit['previous_eligible_rows']==int(result.scores.model_eligible.sum())
    exported=pd.read_csv(DATA/'anomaly_scores.csv',float_precision='round_trip')
    import hashlib
    unchanged={name:hashlib.sha256(pd.util.hash_pandas_object(exported[name],index=False).values.tobytes()).hexdigest()==expected
               for name,expected in audit['previous_score_column_fingerprints'].items()}
    # Recomputación efectiva: nunca se copian scores del modelo anterior.
    revision={'previous_checkpoint':audit['checkpoint_before_revision'],'previous_report_sha256':audit['previous_report_sha256'],
              'previous_actual_max_features':audit['actual_previous_max_features'],
              'previous_actual_max_features_type':audit['actual_previous_max_features_type'],
              'current_max_features':config['primary_model']['max_features'],'current_max_features_type':type(config['primary_model']['max_features']).__name__,
              'primary_scores_recomputed':True,'previous_numeric_and_marking_columns_unchanged':unchanged,
              'learned_state_unchanged':model_metadata['learned_pipeline_state_sha256']==audit['previous_model_state_sha256'],
              'synthetic_injections_unchanged':sha256(OUT/'synthetic_injection_audit.csv')==audit['files_before_revision']['reports/phase5/synthetic_injection_audit.csv'],
              'selection_unchanged':True,'preprocessing_unchanged':True,'split_unchanged':True,'eligibility_unchanged':True,
              'finding':'Existing artifact already had float 1.0; report presentation corrected, controls int 1 / float 0.5 / float 1.0 added.'}
    (OUT/'max_features_revision.json').write_text(json.dumps(revision,ensure_ascii=False,indent=2))
    files=[DATA/'anomaly_scores.csv',*(OUT/name for name in tables),*sorted(MODELS.iterdir()),OUT/'max_features_revision.json']
    metadata={'phase':5,'checkpoint_initial':(OUT/'git_initial.txt').read_text().strip(),
              'source_path':'data/processed/phase4/west_wall_features.csv','source_sha256':sha256(ROOT/'data/processed/phase4/west_wall_features.csv'),
              'input_rows':len(data),'output_rows':len(result.scores),'prisms':int(data.prism_id.nunique()),
              'eligible_rows':int(result.scores.model_eligible.sum()),'eligible_pct':100*result.scores.model_eligible.mean(),
              'selected_features':result.bundle.selected_features,'candidate_count':len(result.selection.candidates),
              'cutoffs':result.cutoffs,'config':config,'config_path':'config/phase5.json','config_file_sha256':sha256(CONFIG),
              'config_canonical_sha256':result.scores.model_config_sha256.iloc[0],
              'preprocessing':result.preprocessing,'model_state_sha256':model_metadata['learned_pipeline_state_sha256'],
              'tree_feature_availability':model_metadata['tree_feature_availability'],
              'revision_audit':'reports/phase5/audit/before_revision.json','checkpoint_before_revision':audit['checkpoint_before_revision'],
              'files':{str(path.relative_to(ROOT)):sha256(path) for path in files},
              'score_dtypes':{name:str(result.scores[name].dtype) for name in result.scores},
              'figures':figures,'figure_count':len(figures),'protected_files_intact':check_protected(ROOT,PROTECTED),
              'terminology':'Características temporalmente válidas, calculadas sin información futura y respetando el orden cronológico.',
              'no_failure_date_used':True,'no_operational_alerts':True,'no_risk_classification':True,'no_source_joins':True,
              'real_labels_available':False,'model_version':result.bundle.version,'disclaimer':DISCLAIMER}
    (OUT/'phase5_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False))
    (OUT/'execution_stats.json').write_text(json.dumps({'pipeline_seconds':time.perf_counter()-start,
         'inference_100_observations_seconds':inference_seconds,'model_artifact_bytes':(MODELS/'isolation_forest.joblib').stat().st_size,
         'timing_excluded_from_reproducibility':True},indent=2))
    print('Conservadas:',len(result.scores),'Elegibles:',metadata['eligible_rows'],'Características:',len(result.bundle.selected_features),'Protegidos:',protected,'Figuras:',len(figures),flush=True)
    return result,tables

if __name__=='__main__':main()
