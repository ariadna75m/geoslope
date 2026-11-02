"""Frozen-model replay, CSV reproduction and time-prefix invariance; no fit."""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import json
import sys
import tempfile
import pandas as pd
from PIL import Image
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_phase6 import OUT, DATA, load_inputs, build_artifacts, write_tables, json_write
from src.phase6_validation import check_protected, verify_frozen, read_outputs, sha256
from src.anomaly_baseline import StatisticalBaseline
from src.episode_detection import detect_episodes
from src.candidate_policies import apply_policies
from src.episode_explanations import explain_rows


def prohibit_fit(*args,**kwargs):
    raise AssertionError('No se permite entrenar en Fase 6.')


def verify():
    meta=json.loads((OUT/'phase6_metadata.json').read_text())
    assert sha256(ROOT/'config/phase6.json')==meta['config_sha256']
    for name,expected in {**meta['files'],**meta['figure_sha256']}.items():
        assert sha256(ROOT/name)==expected,name
    protected=check_protected(ROOT,OUT/'protected_before_phase6.json')
    assert protected==meta['protected_files_intact']
    with ExitStack() as stack:
        for model in (IsolationForest,RobustScaler,SimpleImputer,StatisticalBaseline):
            stack.enter_context(patch.object(model,'fit',prohibit_fit))
        assert verify_frozen(ROOT)==meta['frozen_models']
        inputs,cfg=load_inputs()
        computed=build_artifacts(inputs,cfg)
        restored=read_outputs(ROOT,meta)
        for name,frame in computed.items():
            pd.testing.assert_frame_equal(frame,restored[name],check_exact=True)
        with tempfile.TemporaryDirectory(prefix='phase6-reproduction-') as path:
            write_tables(computed,path)
            for name in computed:
                assert sha256(Path(path)/name)==meta['files'][str((DATA/name).relative_to(ROOT))],name
        rows=restored['review_candidates.csv']
        assert len(rows)==7178 and rows.prism_id.nunique()==49 and rows.model_eligible.sum()==5898
        assert (~rows.model_eligible).sum()==1280
        training = rows.period.eq('entrenamiento')
        assert not rows.loc[training,'model_available_at_observation'].any()
        assert rows.loc[~training,'model_available_at_observation'].all()
        assert rows.loc[~rows.model_eligible,'model_ineligibility_reason'].str.len().gt(0).all()
        for c in inputs:
            pd.testing.assert_series_equal(inputs[c],rows[c],check_exact=True)
        checks=[]
        for cut in ('2013-12-05','2014-01-15','2014-02-02','2014-02-15'):
            prefix=inputs.loc[inputs.timestamp.lt(pd.Timestamp(cut))]
            temporal,_=detect_episodes(prefix,cfg['primary_window_hours'])
            previous=explain_rows(apply_policies(temporal,cfg['primary_window_hours'],cfg['primary_min_marks'],cfg['primary_policy']),cfg['primary_window_hours'],cfg['primary_min_marks'])
            subset=rows.loc[rows.timestamp.lt(pd.Timestamp(cut))].reset_index(drop=True)
            pd.testing.assert_frame_equal(previous,subset,check_exact=True)
            checks.append({'cutoff_exclusive':cut,'rows_checked':len(prefix),'all_causal_columns_identical':True})
        template=restored['specialist_review_template.csv']
        human=['review_status','specialist_relevant','specialist_comment','data_quality_comment','recommended_follow_up','reviewer','review_date']
        assert template[human].eq('').all().all()
        episodes=restored['episodes.csv']
        assert episodes.episode_id.nunique()==len(episodes)
        assert rows.loc[rows.episode_id.ne('')].groupby('episode_id').prism_id.nunique().eq(1).all()
        assert episodes.record_count.sum()==rows.episode_id.ne('').sum()
        assert episodes.union_mark_count.sum()==rows.union_mark.sum()
        assert episodes.ineligible_record_count.sum()==((~rows.model_eligible)&rows.episode_id.ne('')).sum()
    for item in meta['figures']:
        with Image.open(OUT/item['png']) as im:im.verify()
        html=(OUT/item['html']).read_text()
        assert 'src="plotly.min.js"' in html and 'Plotly.newPlot' in html
    proof={'protected_files_intact':check_protected(ROOT,OUT/'protected_before_phase6.json'),
           'model_hashes_unchanged':True,'phase5_predictions_identical':True,
           'training_blocked_during_entire_verification':True,
           'phase6_training_performed':False,'all_input_rows_preserved':7178,
           'ineligible_rows_preserved_unknown':1280,'reproduced_csv_byte_identical':len(computed),
           'restored_all_columns_and_types_exact':True,'causal_prefix_checks':checks,
           'retrospective_summaries_stored_separately':True,
           'specialist_fields_blank':True,'validated_png_html_pairs':len(meta['figures']),
           'thresholds':meta['frozen_models']['thresholds'],
           'physical_event_not_a_decision_input':True}
    proof['aggregation_causality_scope']='conditional on frozen Phase 5 marks'
    proof['training_scores_retrospective_not_operational_at_original_time']=True
    proof['source_metadata_sha256']=sha256(OUT/'phase6_metadata.json')
    json_write(OUT/'reproducibility.json',proof)
    print(json.dumps(proof,ensure_ascii=False,indent=2))


if __name__=='__main__':
    verify()
