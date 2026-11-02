import pytest
from tests.phase6_helpers import sample,evaluate
from src.candidate_policies import compare_policies,daily_workload,apply_policies


def test_four_policies_select_explicit_known_rows():
    rows,_=evaluate(sample((0,6,12,18),(True,False,True,False),(False,True,True,False)))
    assert rows.candidate_union.tolist()==[True,True,True,False]
    assert rows.candidate_consensus.tolist()==[False,False,True,False]
    assert rows.candidate_persistence.tolist()==[False,True,True,False]
    assert rows.candidate_hybrid.tolist()==[False,True,True,False]
    assert rows.causal_state.tolist()==['marca_aislada','candidato_revision','candidato_revision','sin_marca']


def test_agreement_can_select_first_mark_but_persistence_cannot():
    rows,_=evaluate(sample((0,),(True,),(True,)))
    assert rows.candidate_hybrid.iloc[0] and rows.candidate_consensus.iloc[0]
    assert not rows.candidate_persistence.iloc[0]


def test_minimum_three_and_observation_hierarchy():
    rows,_=evaluate(sample((0,2,4),(True,True,True),(False,False,False)),minimum=3)
    assert rows.causal_state.tolist()==['marca_aislada','episodio_en_observacion','candidato_revision']
    assert rows.candidate_persistence.tolist()==[False,False,True]


def test_nonmarked_current_row_not_selected_after_persistence():
    rows,_=evaluate(sample((0,1,2),(True,True,False),(False,False,False)))
    assert rows.union_marks_last_72h.iloc[2]==2
    assert not rows.candidate_hybrid.iloc[2] and rows.causal_state.iloc[2]=='sin_marca'


def test_workload_reduction_is_descriptive_and_days_with_no_data_included():
    rows,episodes=evaluate(sample((0,72),(True,True),(False,False)))
    comparison=compare_policies(rows,episodes,72,2,include_periods=False).set_index('policy')
    assert comparison.loc['union','candidate_rows']==2
    assert comparison.loc['hybrid','candidate_rows']==1
    assert comparison.loc['hybrid','row_reduction_vs_union_pct']==50
    assert comparison.loc['union','calendar_days']==4
    daily=daily_workload(rows)
    assert len(daily)==16
    assert daily.query("policy=='union'").observed_rows.tolist()==[1,0,0,1]


def test_all_four_policies_are_subsets_of_union_and_quality_unknown():
    rows,_=evaluate(sample(eligible=[True,False,True]))
    for p in ('union','consensus','persistence','hybrid'):
        assert rows.loc[rows['candidate_'+p].fillna(False),'union_mark'].all()
        assert rows.loc[~rows.model_eligible,'candidate_'+p].isna().all()


@pytest.mark.parametrize('window,minimum,policy',[(0,2,'hybrid'),(72,1,'hybrid'),(72,2,'invalid')])
def test_invalid_policy_settings_fail(window,minimum,policy):
    rows,_=evaluate(sample())
    with pytest.raises(ValueError):apply_policies(rows,window,minimum,policy)
