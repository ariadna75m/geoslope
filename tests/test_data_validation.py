import pandas as pd
import pytest
from src.data_loader import load_file
from src.data_validation import validate_data,build_timestamp
from src.schemas import WEST,RAIN


def test_missing_required_columns():
    q=validate_data(pd.DataFrame({'Prism':['P1']}),'west_wall')
    assert not q.ok and 'Date' not in q.metrics['required_missing_columns']
    assert 'date_original' in q.metrics['required_missing_columns']


def test_types_dates_duplicates_and_zero(west_rows):
    rows=[west_rows[0],west_rows[0],['P3','31-Feb-14','25:00:00','oops','2','3','inf']]
    frame=pd.DataFrame(rows,columns=WEST); before=frame.copy(deep=True)
    q=validate_data(frame,'west_wall',min_observations=2)
    assert q.metrics['duplicate_rows_extra']==1
    assert q.metrics['zero_intervals']==1
    assert q.metrics['invalid_timestamps']==1
    assert q.metrics['invalid_numeric_by_column']['easting']==1
    assert q.metrics['invalid_numeric_by_column']['reported_3d_movement_mm']==1
    assert not q.ok
    pd.testing.assert_frame_equal(frame,before)


def test_extreme_and_decreasing_values_are_valid(west_rows):
    q=validate_data(pd.DataFrame(west_rows,columns=WEST),'west_wall',min_observations=2)
    assert q.ok
    assert q.metrics['backward_steps_original']==1
    assert q.metrics['insufficient_prisms']=={'P-2':1}
    assert 'reported_3d_movement_mm' not in [c for c,u in q.metrics['units'].items() if 'requiere validación' in u]


def test_missing_rain_is_unknown():
    frame=pd.DataFrame([['ID','029167','2013','12','29','','',''],['ID','029167','2013','12','30','3.6','1','N']],columns=RAIN)
    q=validate_data(frame,'rainfall'); assert q.ok
    assert q.metrics['rows_with_missing']==1 and q.metrics['missing_cells']==3
    assert q.metrics['missing_by_column']['rainfall_mm']==1


def test_rain_semantic_review_without_erasing():
    frame=pd.DataFrame([['ID','029167','2014','01','01','-2','0','N']],columns=RAIN)
    q=validate_data(frame,'rainfall'); assert q.metrics['invalid_rainfall_semantics']==1
    assert frame.iloc[0]['Rainfall amount (millimetres)']=='-2'


def test_conflicting_keys_and_missing_id(west_rows):
    other=west_rows[0].copy();other[-1]='9'
    third=west_rows[1].copy();third[0]=''
    q=validate_data(pd.DataFrame([west_rows[0],other,third],columns=WEST),'west_wall')
    assert q.metrics['conflicting_key_rows']==2 and q.metrics['missing_identifiers']==1


def test_locale_independent_and_invalid_datetime():
    f=pd.DataFrame({'date_original':['01-Jan-14','2014-01-02 00:00:00','bad','01-Xxx-14'],
                    'time_original':['10:00:00','10:00:00','10:00:00','10:00:00']})
    ts=build_timestamp(f,'west_wall')
    assert ts.iloc[0]==pd.Timestamp('2014-01-01 10:00:00')
    assert ts.iloc[1]==pd.Timestamp('2014-01-02 10:00:00')
    assert ts.iloc[2:].isna().all()


def test_noninteger_date_component_not_normalized():
    f=pd.DataFrame({'year':['2014','2014'],'month':['1','1'],'day':['1.5','31']})
    ts=build_timestamp(f,'rainfall'); assert pd.isna(ts.iloc[0]) and ts.iloc[1]==pd.Timestamp('2014-01-31')


def test_units_of_south_not_attributed(raw_dir):
    s=load_file(raw_dir/'radar-deformation-data/South_West_Corner_06082014.csv')
    q=validate_data(s.frame,'south_west')
    assert all(u=='requiere validación' for u in q.metrics['units'].values())
    assert q.metrics['duplicate_rows_extra']==1 and q.metrics['zero_intervals']==1
    assert q.metrics['insufficient_prisms']['31-1608']==1

@pytest.mark.parametrize('clock',['10:00:60','10:60:00','24:00:00','-1:00:00'])
def test_invalid_clocks_never_silently_normalized(clock):
    f=pd.DataFrame({'date_original':['01-Jan-14'],'time_original':[clock]})
    assert build_timestamp(f,'west_wall').isna().all()


def test_txt_second_60_is_not_normalized():
    f=pd.DataFrame({'date_original':['2014-01-01T10:00:60']})
    assert build_timestamp(f,'velocity_changes').isna().all()


def test_validator_accepts_non_unique_external_index(west_rows):
    f=pd.DataFrame([west_rows[0],west_rows[0],west_rows[1]],columns=WEST,index=['external','external','third'])
    q=validate_data(f,'west_wall')
    assert q.metrics['duplicate_rows_extra']==1
    assert q.metrics['zero_intervals']==1
    assert f.index.tolist()==['external','external','third']
