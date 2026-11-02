import pandas as pd
import pytest
from tests.phase6_helpers import sample,evaluate,real_case
from src.episode_explanations import explain_rows


@pytest.mark.parametrize('window',[24,48,72])
def test_appending_future_preserves_every_old_causal_field(window):
    full=sample((0,1,2,window+1,window+2),(True,False,True,True,False),(False,False,False,True,False),eligible=[True,False,True,True,True])
    before,old_episodes=evaluate(full.iloc[:3],window)
    after,new_episodes=evaluate(full,window)
    pd.testing.assert_frame_equal(before,after.loc[after.source_record_id.isin(before.source_record_id)].reset_index(drop=True),check_exact=True)
    assert old_episodes.last_observed_timestamp.iloc[0] < new_episodes.last_observed_timestamp.iloc[0]


def test_explanations_use_only_episode_evidence_available_at_row_time():
    full=sample((0,1,2),(True,True,True),(False,False,False))
    before,_=evaluate(full.iloc[:1]);after,_=evaluate(full)
    for data in (before,after):
        data['baseline_threshold_q99']=4.439772224885318
        data['iforest_threshold_q99']=.5872931971929567
    a=explain_rows(before,72,2);b=explain_rows(after,72,2)
    assert a.candidate_reason.iloc[0]==b.candidate_reason.iloc[0]
    assert '1 marcas y 0 registros' in a.candidate_reason.iloc[0]
    assert '3 marcas y' not in a.candidate_reason.iloc[0]


def test_real_timestamp_prefix_including_partition_boundary_is_invariant():
    inputs,config,_=real_case()
    cutoff=pd.Timestamp('2014-02-02')
    prefix=inputs.loc[inputs.timestamp.lt(cutoff)]
    before,_=evaluate(prefix)
    after,_=evaluate(inputs)
    pd.testing.assert_frame_equal(before,after.loc[after.timestamp.lt(cutoff)].reset_index(drop=True),check_exact=True)


def test_future_changes_cannot_rewrite_previous_states_or_episode_ids():
    data=sample((0,1,90),(True,True,True),(False,False,False))
    a,_=evaluate(data)
    changed=data.copy();changed.loc[2,'baseline_marked_q99']=False;changed.loc[2,'baseline_score']=1.
    b,_=evaluate(changed)
    pd.testing.assert_frame_equal(a.iloc[:2],b.iloc[:2],check_exact=True)
