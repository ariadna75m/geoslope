import json
import pandas as pd
import pytest
from tests.phase6_helpers import sample,real_case,ROOT
from src.phase6_validation import validate_scores,validate_config
from src.episode_explanations import specialist_template


def test_all_input_rows_prisms_original_scores_and_unknowns_preserved():
    inputs,_,tables=real_case();rows=tables['review_candidates.csv']
    assert len(rows)==7178 and rows.prism_id.nunique()==49
    assert rows.model_eligible.sum()==5898 and (~rows.model_eligible).sum()==1280
    for c in inputs:pd.testing.assert_series_equal(inputs[c],rows[c],check_exact=True)
    assert rows.loc[~rows.model_eligible,'causal_state'].eq('no_evaluable').all()
    assert rows.loc[~rows.model_eligible,['baseline_mark_q99','iforest_mark_q99','union_mark','agreement_same_row']].isna().all().all()
    assert not rows.source_record_id.duplicated().any()


def test_each_row_has_exactly_one_main_state_and_no_retrospective_fields():
    _,_,tables=real_case();rows=tables['review_candidates.csv']
    allowed={'no_evaluable','sin_marca','marca_aislada','episodio_en_observacion','candidato_revision'}
    assert rows.causal_state.isin(allowed).all()
    assert 'last_observed_timestamp' not in rows and 'closure_status' not in rows
    assert rows.loc[rows.review_pending,'causal_state'].eq('candidato_revision').all()


def test_sensitivity_covers_all_twenty_four_combinations_and_four_scopes():
    _,_,tables=real_case();s=tables['sensitivity_analysis.csv']
    assert len(s)==96
    assert len(s.query("period=='total'"))==24
    assert set(s.window_hours)=={24,48,72} and set(s.min_marks)=={2,3}
    assert set(s.policy)=={'union','consensus','persistence','hybrid'}
    assert (s.candidate_rows<=s.union_reference_rows).all()


def test_specialist_fields_all_blank_and_selected_episode_set_exact():
    _,_,tables=real_case();t=tables['specialist_review_template.csv'];ep=tables['episodes.csv']
    for c in ('review_status','specialist_relevant','specialist_comment','data_quality_comment','recommended_follow_up','reviewer','review_date'):
        assert t[c].eq('').all()
    assert set(t.episode_id)==set(ep.loc[ep.candidate_policies.str.contains('hybrid',regex=False),'episode_id'])
    assert ep.review_status.eq('').all()


def test_prism_30_1994_kept_training_only_and_all_eligible_marked():
    _,_,tables=real_case();p=tables['prism_30_1994_observations.csv']
    assert len(p)==35 and p.model_eligible.sum()==15
    assert p.period.eq('entrenamiento').all()
    assert p.baseline_mark_q99.sum()==p.iforest_mark_q99.sum()==15
    assert p.loc[~p.model_eligible,'model_ineligibility_reason'].str.len().gt(0).all()


def test_explanations_and_rule_components_retain_specialist_notice():
    _,_,tables=real_case();r=tables['review_candidates.csv'];e=tables['episodes.csv']
    assert r.candidate_reason.str.len().gt(0).all()
    assert r.professional_notice.str.contains('No constituye una predicción definitiva').all()
    assert e.episode_explanation.str.contains('Resumen retrospectivo').all()
    assert r.loc[r.review_pending,'candidate_reason'].str.contains('no son contribuciones causales').all()


def test_missing_required_column_rejected():
    with pytest.raises(ValueError,match='Columnas'):validate_scores(sample().drop(columns='baseline_score'))


def test_invalid_quality_cannot_be_reinterpreted_as_unmarked():
    data=sample(eligible=[True,False,True]);data.loc[1,'baseline_marked_q99']=False
    with pytest.raises(ValueError,match='desconocidos'):validate_scores(data)


def test_duplicate_id_rejected():
    data=sample();data.loc[1,'source_record_id']=data.source_record_id.iloc[0]
    with pytest.raises(ValueError,match='duplicados'):validate_scores(data)


def test_config_requires_complete_sensitivity_and_fixed_current_mark_semantics():
    cfg=json.loads((ROOT/'config/phase6.json').read_text());cfg['candidate_requires_current_union_mark']=False
    with pytest.raises(ValueError,match='marca'):validate_config(cfg)


def test_training_scores_are_not_presented_as_operational_before_model_fit_cutoff():
    _,_,tables=real_case();rows=tables['review_candidates.csv']
    assert str(rows.model_available_from_timestamp.dtype)=='datetime64[ns]'
    train=rows.period.eq('entrenamiento')
    assert not rows.loc[train,'model_available_at_observation'].any()
    assert rows.loc[~train,'model_available_at_observation'].all()
    assert rows.loc[train,'phase5_score_scope'].eq('in_sample_retrospective').all()
    assert rows.loc[train,'candidate_reason'].str.contains('no estaba disponible').all()
