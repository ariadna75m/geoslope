from pathlib import Path
import hashlib
import json
import pandas as pd
import pytest
from src.data_loader import load_file
from src.preprocessing import prepare_source,export_prepared,fingerprint
from src.schemas import WEST,SOUTH,RAIN,MOVEMENT_DESCRIPTION


def test_exact_duplicate_exclusion_with_original_preserved(write_table,west_rows):
    p=write_table('duplicates.csv',WEST,[west_rows[0],west_rows[1],west_rows[0]])
    loaded=load_file(p); before=loaded.frame.copy(deep=True)
    result=prepare_source(loaded,min_observations=2)
    assert len(result.data)==2 and len(result.excluded)==1 and len(result.originals)==3
    e=result.excluded.iloc[0]
    assert e.source_line==4 and e.exclusion_reason=='exact_duplicate'
    assert e.retained_row_id==result.data.loc[result.data.source_line.eq(2),'row_id'].iloc[0]
    assert e.original__reported_3d_movement_mm==west_rows[0][-1]
    assert result.quality_after['metrics']['zero_intervals']==0
    assert result.metadata['summary']['exact_duplicate_excluded_rows']==1
    pd.testing.assert_frame_equal(loaded.frame,before)


def test_sort_and_do_not_force_monotonic_movement(west_file):
    r=prepare_source(load_file(west_file),min_observations=2)
    p=r.data[r.data.prism_id.eq('P-1')]
    assert p.timestamp.is_monotonic_increasing
    assert p.reported_3d_movement_mm.tolist()==[10,8]
    assert len(r.data)==3 and r.data.reported_3d_movement_mm.max()==1e9
    assert MOVEMENT_DESCRIPTION==r.metadata['description']
    assert not any('velocity' in c or 'acceleration' in c for c in r.data.columns)


def test_preserve_unknown_weather_and_zero_prefix(write_table):
    p=write_table('rain.csv',RAIN,[['ID','029167','2013','12','30','3.6','1','N'],['ID','029167','2013','12','29','','','']])
    r=prepare_source(load_file(p))
    assert len(r.data)==2 and r.data.timestamp.is_monotonic_increasing
    assert r.data.station_id.tolist()==['029167','029167']
    unknown=r.data.iloc[0]
    assert pd.isna(unknown.rainfall_mm) and pd.isna(unknown.rainfall_period_days)
    assert unknown.original__rainfall_mm=='' and unknown.quality_code==''
    assert unknown.original__year=='2013' and unknown.original__month=='12' and unknown.original__day=='29'
    assert r.data.iloc[1].quality_code=='N'
    assert r.metadata['summary']['marked_retained_rows']==1


def test_invalid_dates_and_ids_quarantined(write_table,west_rows):
    date_bad=west_rows[0].copy();date_bad[1]='31-Feb-14'
    id_bad=west_rows[0].copy();id_bad[0]=''
    p=write_table('invalid.csv',WEST,[west_rows[1],date_bad,id_bad])
    r=prepare_source(load_file(p))
    assert len(r.data)==1 and len(r.excluded)==2
    assert set(r.excluded.exclusion_reason)=={'invalid_timestamp','missing_identifier'}
    assert r.quality_before['metrics']['invalid_timestamps']==1
    assert r.quality_after['metrics']['invalid_timestamps']==0


def test_conflicting_time_values_all_quarantined(write_table,west_rows):
    conflict=west_rows[0].copy();conflict[-1]='9'
    p=write_table('conflict.csv',WEST,[west_rows[0],conflict,west_rows[1]])
    r=prepare_source(load_file(p))
    assert len(r.data)==1 and len(r.excluded)==2
    assert set(r.excluded.exclusion_reason)=={'conflicting_key_requires_review'}
    assert r.quality_after['metrics']['zero_intervals']==0


def test_new_identifier_collision_after_trim_is_not_selected(write_table,west_rows):
    other=west_rows[0].copy();other[0]=' P-1 ';other[-1]='9'
    p=write_table('trim.csv',WEST,[west_rows[0],other,west_rows[1]])
    r=prepare_source(load_file(p))
    assert len(r.data)==1 and len(r.excluded)==2
    assert r.excluded.original__prism_id.tolist()==['P-1',' P-1 ']


def test_invalid_numeric_kept_with_exact_original(write_table,west_rows):
    bad=west_rows[0].copy();bad[3]='not-a-number'
    p=write_table('type.csv',WEST,[bad])
    r=prepare_source(load_file(p))
    assert len(r.data)==1 and len(r.excluded)==0
    assert pd.isna(r.data.iloc[0].easting)
    assert r.data.iloc[0].original__easting=='not-a-number'
    assert 'invalid_numeric:easting' in r.data.iloc[0].quality_flags
    assert not r.quality_before['ok']


def test_south_units_pending_no_conversions(write_table):
    values=['P1','01-Jan-14','10:00:00','46000','27000','900','-1','-3','1000','2000','-20']
    p=write_table('south.csv',SOUTH,[values])
    r=prepare_source(load_file(p))
    assert r.data.iloc[0].easting_diff==1000
    assert r.data.iloc[0].easting==46000
    assert all(v=='requiere validación' for v in r.metadata['units'].values())
    assert not any(c.endswith('_mm') for c in r.data)


def test_large_gap_preserved_no_interpolation(write_table,west_rows):
    rows=[west_rows[0].copy(),west_rows[1].copy()]; rows[0][1]='01-Aug-14'
    p=write_table('gap.csv',WEST,rows);r=prepare_source(load_file(p))
    assert len(r.data)==2 and r.metadata['interpolation'] is False
    assert r.quality_after['metrics']['max_gap_hours']>200*24


def test_single_prism_point_is_flagged_not_removed(write_table,west_rows):
    p=write_table('one.csv',WEST,[west_rows[0]])
    r=prepare_source(load_file(p))
    assert len(r.data)==1
    assert r.quality_after['metrics']['insufficient_prisms']=={'P-1':1}
    assert 'insufficient_observations' in r.data.iloc[0].quality_flags


def test_reproducible_ids_journal_and_export(west_file,tmp_path):
    loaded=load_file(west_file);r1=prepare_source(loaded);r2=prepare_source(loaded)
    pd.testing.assert_frame_equal(r1.data,r2.data)
    assert r1.journal==r2.journal and r1.metadata==r2.metadata
    assert r1.data.row_id.is_unique and r1.originals.row_id.is_unique
    for event in r1.journal: assert 'before' in event and 'after' in event and 'details' in event
    export_prepared(r1,tmp_path/'a');export_prepared(r2,tmp_path/'b')
    for p in (tmp_path/'a').iterdir(): assert p.read_bytes()==(tmp_path/'b'/p.name).read_bytes()
    assert json.loads((tmp_path/'a/quality_after.json').read_text())['metrics']['zero_intervals']==0


def test_excluded_trace_and_rows_partition(write_table,west_rows):
    bad=west_rows[1].copy();bad[1]='bad'
    p=write_table('partition.csv',WEST,[west_rows[0],west_rows[0],bad])
    r=prepare_source(load_file(p))
    assert set(r.data.row_id).isdisjoint(set(r.excluded.row_id))
    assert set(r.originals.row_id)==set(r.data.row_id)|set(r.excluded.row_id)
    assert r.dispositions.status.value_counts().to_dict()=={'excluded':2,'retained':1}


def test_export_cannot_target_raw(west_file,tmp_path):
    r=prepare_source(load_file(west_file))
    with pytest.raises(ValueError,match='prohibido'):export_prepared(r,tmp_path/'data/raw/illegal')


def test_missing_columns_stop_preprocessing(write_table):
    p=write_table('partial.csv',['Prism','Date'],[['P1','01-Jan-14']])
    with pytest.raises(ValueError,match='obligatorias'):
        prepare_source(load_file(p,source_kind='west_wall',header_row=0))


def test_excel_date_and_time_validated(tmp_path):
    from openpyxl import Workbook
    from datetime import datetime,time
    p=tmp_path/'table.xlsx';w=Workbook();w.active.append(list(WEST))
    w.active.append(['001',datetime(2014,1,1),time(10,0),1,2,3,4]);w.save(p)
    r=prepare_source(load_file(p))
    assert r.data.iloc[0].prism_id=='001'
    assert r.data.iloc[0].timestamp==pd.Timestamp('2014-01-01 10:00:00')


def test_fingerprint_depends_on_order(west_file):
    f=load_file(west_file).frame
    assert fingerprint(f)!=fingerprint(f.iloc[::-1])


def test_full_unknown_record_is_quarantined_not_disappeared(write_table):
    p=write_table('unknown.csv',WEST,[['']*len(WEST)])
    r=prepare_source(load_file(p))
    assert len(r.originals)==1 and len(r.excluded)==1 and len(r.data)==0
    assert r.excluded.source_line.iloc[0]==2
    assert r.quality_after['metrics']['zero_intervals']==0
