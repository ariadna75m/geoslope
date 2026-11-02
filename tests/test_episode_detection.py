import pandas as pd
import pytest
from tests.phase6_helpers import sample,evaluate
from src.episode_detection import detect_episodes


@pytest.mark.parametrize('window',[24,48,72])
def test_inclusive_boundary_and_one_second_beyond(window):
    data=sample((0,window,2*window+1/3600),(True,True,True),(False,False,False))
    rows,episodes=evaluate(data,window)
    assert rows.episode_id.iloc[0]==rows.episode_id.iloc[1]
    assert rows.episode_id.iloc[2]!=rows.episode_id.iloc[1]
    assert len(episodes)==2
    assert rows[f'union_marks_last_{window}h'].tolist()==[1,2,1]
    assert episodes.closure_status.tolist()==['cerrado_por_ventana','censurado_fin_del_prisma']


def test_prisms_never_share_episode_or_counts():
    data=sample((0,1,2,3),(True,True,True,True),(False,False,False,False),prisms=['A','B','A','B'])
    rows,episodes=evaluate(data)
    assert episodes.episode_id.nunique()==2
    assert rows.groupby('episode_id').prism_id.nunique().eq(1).all()
    assert rows.groupby('prism_id').union_marks_last_72h.apply(list).tolist()==[[1,2],[1,2]]


def test_unmarked_row_between_marks_does_not_split():
    rows,episodes=evaluate(sample())
    assert rows.episode_id.nunique()==1 and episodes.union_mark_count.iloc[0]==2
    assert rows.causal_state.tolist()==['marca_aislada','sin_marca','candidato_revision']


def test_quality_interruption_preserved_not_counted_and_does_not_close():
    rows,episodes=evaluate(sample(eligible=[True,False,True]))
    assert rows.episode_id.nunique()==1
    assert rows.causal_state.iloc[1]=='no_evaluable'
    assert rows.model_ineligibility_reason.iloc[1]=='motivo original de calidad'
    assert pd.isna(rows.union_mark.iloc[1]) and pd.isna(rows.candidate_hybrid.iloc[1])
    assert rows.union_marks_last_72h.tolist()==[1,1,2]
    assert rows.episode_ineligible_records_to_date.tolist()==[0,1,1]
    assert episodes.ineligible_record_count.iloc[0]==1
    assert episodes.quality_interruption_flag.iloc[0]


def test_quality_after_expiry_closes_by_time_without_new_evidence():
    data=sample((0,73),(True,True),(False,False),eligible=[True,False])
    rows,episodes=evaluate(data)
    assert rows.episode_id.iloc[1]=='' and rows.quality_interruption_flag.iloc[1]
    assert episodes.closure_status.iloc[0]=='cerrado_por_ventana'
    assert episodes.ineligible_record_count.iloc[0]==0


def test_current_quality_has_no_earlier_episode_and_unknown_previous_mark():
    rows,_=evaluate(sample((0,1),(False,True),(False,False),eligible=[False,True]))
    assert rows.episode_id.iloc[0]==''
    assert rows.quality_interruption_flag.iloc[0]
    assert pd.isna(rows.hours_since_previous_mark.iloc[1])


def test_episode_chain_can_last_longer_than_window_without_future_merging():
    rows,episodes=evaluate(sample((0,60,120),(True,True,True),(False,False,False)))
    assert len(episodes)==1 and episodes.mark_span_hours.iloc[0]==120
    assert rows.union_marks_last_72h.tolist()==[1,2,2]


def test_irregular_intervals_use_timestamps():
    rows,_=evaluate(sample((0,1,80),(True,True,True),(False,False,False)))
    assert rows.hours_since_previous_observation.iloc[1:].tolist()==[1.,79.]
    assert rows.union_marks_last_72h.tolist()==[1,2,1]


def test_equal_timestamp_within_prism_rejected():
    data=sample((0,0),(True,True),(False,False))
    with pytest.raises(ValueError,match='repetido'):detect_episodes(data)


def test_empty_input_has_no_episodes():
    rows,episodes=evaluate(sample().iloc[:0])
    assert rows.empty and episodes.empty
