"""Verifica integridad, recarga, reproducción de tablas y ausencia de fuga."""
from pathlib import Path
import sys,json,argparse,tempfile
import numpy as np
import pandas as pd
import joblib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_phase5 import OUT,DATA,MODELS,PROTECTED,CONFIG,load_inputs,build_artifacts,write_tables,write_models
from src.feature_validation import check_protected,sha256
from src.anomaly_models import train_models,tree_feature_metadata
from src.model_validation import learned_pipeline_fingerprint


def assert_training_invariant(first,second):
    pd.testing.assert_frame_equal(first.selection.candidates,second.selection.candidates,check_exact=True)
    pd.testing.assert_frame_equal(first.selection.excluded,second.selection.excluded,check_exact=True)
    assert first.bundle.selected_features==second.bundle.selected_features
    assert first.preprocessing==second.preprocessing
    assert first.bundle.pipeline.named_steps['model'].get_params()==second.bundle.pipeline.named_steps['model'].get_params()
    assert first.bundle.thresholds==second.bundle.thresholds
    assert first.bundle.baseline.as_dict()==second.bundle.baseline.as_dict()
    assert first.bundle.training_signature==second.bundle.training_signature
    assert learned_pipeline_fingerprint(first.bundle.pipeline)==learned_pipeline_fingerprint(second.bundle.pipeline)
    training=first.periods.eq('entrenamiento')
    pd.testing.assert_frame_equal(first.scores.loc[training],second.scores.loc[training],check_exact=True)
    return {'selected_features_identical':True,'imputer_identical':True,'scaler_identical':True,
            'forest_parameters_identical':True,'all_tree_fields_identical':True,'baseline_identical':True,
            'training_thresholds_identical':True,'training_scores_identical':True,'training_rows_checked':int(training.sum())}


def main(reproduce=False):
    metadata=json.loads((OUT/'phase5_metadata.json').read_text())
    assert check_protected(ROOT,PROTECTED)==metadata['protected_files_intact']
    assert sha256(CONFIG)==metadata['config_file_sha256']
    for name,expected in metadata['files'].items():assert sha256(ROOT/name)==expected,name
    data,dictionary,config=load_inputs()
    bundle=joblib.load(MODELS/'scoring_bundle.joblib')
    pipeline=joblib.load(MODELS/'isolation_forest.joblib')
    preprocessing=joblib.load(MODELS/'preprocessing_pipeline.joblib')
    available=tree_feature_metadata(pipeline)
    assert type(pipeline.named_steps['model'].max_features) is float and pipeline.named_steps['model'].max_features==1.0
    assert available['selected_feature_count']==available['model_input_feature_count']==17
    assert available['effective_available_features_per_tree']==[17] and available['trees_with_all_selected_features']==200
    assert available==metadata['tree_feature_availability']
    assert learned_pipeline_fingerprint(pipeline)==metadata['model_state_sha256']==learned_pipeline_fingerprint(bundle.pipeline)
    rescored=bundle.score_new(data)
    eligible=rescored.model_eligible
    dtypes={name:kind for name,kind in metadata['score_dtypes'].items() if kind!='datetime64[ns]'}
    empty_unknown={name:[''] for name,kind in dtypes.items() if kind in {'float64','boolean'}}
    restored=pd.read_csv(DATA/'anomaly_scores.csv',dtype=dtypes,float_precision='round_trip',
                         keep_default_na=False,na_values=empty_unknown,parse_dates=['timestamp'])
    pd.testing.assert_frame_equal(restored[rescored.columns],rescored,check_exact=True)
    assert len(restored)==len(data)==7178 and restored.source_record_id.tolist()==data.source_record_id.tolist()
    assert restored.prism_id.nunique()==49
    assert restored.loc[~eligible,['baseline_score','isolation_forest_score']].isna().all().all()
    assert restored.loc[~eligible,'model_ineligibility_reason'].str.len().gt(0).all()
    classification=[name for name in restored if '_marked_' in name or name=='baseline_robust_z_reference_marked']
    assert restored.loc[~eligible,classification].isna().all().all()
    assert restored.loc[~eligible,['baseline_training_percentile','isolation_forest_training_percentile']].isna().all().all()
    for model in ['baseline','isolation_forest']:
        np.testing.assert_array_equal(restored[model+'_score'],rescored[model+'_score'])
        percentile=restored.loc[eligible,model+'_training_percentile']
        assert percentile.between(0,100).all()
    np.testing.assert_array_equal(preprocessing.transform(data.loc[eligible]),pipeline[:-1].transform(data.loc[eligible]))
    np.testing.assert_array_equal(-pipeline.score_samples(data.loc[eligible]),rescored.loc[eligible,'isolation_forest_score'])
    day= pd.to_datetime(restored.timestamp).dt.normalize()
    assert restored.groupby(day).period.nunique().max()==1
    for figure in metadata['figures']:
        with Image.open(OUT/figure['png']) as image:image.verify()
        text=(OUT/figure['html']).read_text();assert 'src="plotly.min.js"' in text and 'Plotly.newPlot' in text
    assert (OUT/'interactive/plotly.min.js').is_file()
    sensitivity=pd.read_csv(OUT/'max_features_sensitivity.csv',dtype={'max_features_literal':str},float_precision='round_trip')
    typed=sensitivity[['max_features_literal','max_features_type','effective_features_per_tree']].drop_duplicates()
    assert typed.to_records(index=False).tolist()==[('1','int',1),('0.5','float',8),('1.0','float',17)]
    assert sensitivity.training_signature.nunique()==sensitivity.preprocessing_sha256.nunique()==1
    assert sensitivity.training_rows.eq(2909).all()
    assert sensitivity.groupby(['variant','period']).top_fraction.apply(set).map(lambda x:x=={.01,.02,.05}).all()
    tree_table=pd.read_csv(OUT/'tree_feature_availability.csv')
    assert len(tree_table)==600
    for variant,count in [('1 (int)',1),('0.5 (float)',8),('1.0 (float)',17)]:
        assert tree_table.loc[tree_table.variant.eq(variant),'available_feature_count'].eq(count).all()
    audit=json.loads((OUT/'audit/before_revision.json').read_text())
    assert sha256(ROOT/audit['previous_report_copy'])==audit['previous_report_sha256']
    assert audit['previous_selected_features']==metadata['selected_features']
    assert audit['previous_preprocessing']==metadata['preprocessing']
    assert audit['previous_cutoffs']==metadata['cutoffs']
    assert sha256(OUT/'synthetic_injection_audit.csv')==audit['files_before_revision']['reports/phase5/synthetic_injection_audit.csv']
    revision=json.loads((OUT/'max_features_revision.json').read_text())
    assert revision['learned_state_unchanged'] and all(revision['previous_numeric_and_marking_columns_unchanged'].values())
    proof={'protected_files_intact':check_protected(ROOT,PROTECTED),'rows_preserved':len(data),'prisms':49,
           'model_reload_scores_exact':True,'preprocessing_reload_exact':True,'all_tree_fields_reload_exact':True,
           'ineligible_rows_unknown':True,'whole_calendar_days_preserved':True,'validated_png_html_pairs':len(metadata['figures']),
           'full_reproduction_completed':False,'source_sha256':metadata['source_sha256'],'model_state_sha256':metadata['model_state_sha256'],
           'primary_max_features_value':1.0,'primary_max_features_type':'float','effective_features_per_tree':17,
           'max_features_variants_verified':['1 (int)','0.5 (float)','1.0 (float)'],'frozen_preprocessing_verified':True,
           'previous_report_preserved':True,'synthetic_injections_unchanged':True,'existing_primary_numeric_results_unchanged':True}
    if reproduce:
        result,tables=build_artifacts(data,dictionary,config)
        with tempfile.TemporaryDirectory(prefix='phase5-reproduction-') as directory:
            directory=Path(directory);reports=directory/'reports';output=directory/'data';models=directory/'models'
            write_tables(result,tables,reports,output);write_models(result,models)
            csv_count=0
            for name,expected in metadata['files'].items():
                path=Path(name)
                if path.suffix=='.csv':
                    replica=output/path.name if path.name=='anomaly_scores.csv' else reports/path.name
                    assert sha256(replica)==expected,'Tabla no reproducible: '+name
                    csv_count+=1
                elif path.suffix=='.json' and 'models' in path.parts:
                    assert sha256(models/path.name)==expected,'Metadatos no reproducibles: '+name
            clone=joblib.load(models/'scoring_bundle.joblib')
            assert learned_pipeline_fingerprint(clone.pipeline)==metadata['model_state_sha256']
            pd.testing.assert_frame_equal(result.bundle.score_new(data),clone.score_new(data),check_exact=True)
        shadow=data.copy(deep=True)
        future=result.periods.ne('entrenamiento')
        for i,name in enumerate(config['candidate_priority']):shadow.loc[future,name]=1e12 if i%2 else -1e12
        altered=train_models(shadow,dictionary,config)
        # Explicaciones se comparan por separado en entrenamiento, al mismo alcance.
        from src.model_explanations import add_explanations
        altered.scores=add_explanations(altered,shadow,dictionary)
        invariant=assert_training_invariant(result,altered)
        proof.update(full_reproduction_completed=True,csv_tables_byte_identical=csv_count,
                     training_invariance=invariant,future_rows_modified=int(future.sum()),
                     model_serialization_policy='CSV/JSON byte-identical; Joblib reloaded learned fields and scores exact; object alias/padding not treated as learned state')
    target=OUT/'reproducibility.json'
    if target.exists() and not reproduce:
        old=json.loads(target.read_text())
        if old.get('full_reproduction_completed') and old.get('model_state_sha256')==metadata['model_state_sha256'] and old.get('source_sha256')==metadata['source_sha256']:
            proof.update(old)
    proof['protected_files_intact']=check_protected(ROOT,PROTECTED)
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2,allow_nan=False))
    print(json.dumps(proof,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reproduce',action='store_true')
    main(parser.parse_args().reproduce)
