import pandas as pd
import pytest
from src.temporal_split import temporal_split,PERIODS
from tests.phase5_helpers import model_case

def test_strict_global_chronology_and_whole_calendar_days():
    data,_,_,cfg=model_case();labels,cuts=temporal_split(data,cfg)
    ends=[data.loc[labels.eq(p),'timestamp'] for p in PERIODS]
    assert ends[0].max()<ends[1].min() and ends[1].max()<ends[2].min()
    assert labels.groupby(data.timestamp.dt.normalize()).nunique().max()==1
    assert cuts['same_calendar_day_same_period']

def test_equal_timestamps_kept_together_and_shuffling_is_irrelevant():
    data,_,_,cfg=model_case();data.loc[data.prism_id.eq('B'),'timestamp']=data.loc[data.prism_id.eq('B'),'timestamp']-pd.Timedelta(hours=2)
    labels,_=temporal_split(data,cfg)
    assert labels.groupby(data.timestamp).nunique().max()==1
    shuffled=data.sample(frac=1,random_state=9)
    other,_=temporal_split(shuffled,cfg)
    pd.testing.assert_series_equal(labels,other.sort_index())

def test_uninterpretable_or_insufficient_dates_fail():
    data,_,_,cfg=model_case();data.loc[0,'timestamp']=pd.NaT
    with pytest.raises(ValueError,match='desconocida'):temporal_split(data,cfg)
    with pytest.raises(ValueError,match='cinco días'):temporal_split(data.iloc[1:4],cfg)
