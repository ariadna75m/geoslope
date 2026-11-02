from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
import pytest
from src.exploratory_analysis import (numeric_stats,prism_profiles,source_summary,representative_prisms,daily_availability,combine_rainfall,rainfall_tables,
                                     SOUTH_DESCRIPTION,read_prepared)

@pytest.fixture
def measurements():
    return pd.DataFrame({'prism_id':['A']*5+['B'],'timestamp':pd.to_datetime(['2014-01-05','2014-01-01','2014-01-02','2014-01-03','2014-01-04','2014-01-01']),
                         'value':[9.,1.,3.,3.,2.,100.]})


def test_statistics_known_numbers():
    s=numeric_stats(pd.Series([1.,2.,3.,4.,5.,np.nan]))
    assert s['min']==1 and s['max']==5 and s['mean']==3 and s['median']==3
    assert s['q1']==2 and s['q3']==4 and s['iqr']==2 and s['range']==4
    assert s['missing_count']==1 and s['std_sample']==pytest.approx(np.sqrt(2.5))


def test_order_invariance_and_changes(measurements):
    a=prism_profiles(measurements,['value'],min_observations=2)
    b=prism_profiles(measurements.sample(frac=1,random_state=8),['value'],min_observations=2)
    pd.testing.assert_frame_equal(a,b)
    row=a[a.prism_id.eq('A')].iloc[0]
    assert row.value_initial==1 and row.value_final==9 and row.value_final_minus_initial==8
    assert row.value_increases==2 and row.value_decreases==1 and row.value_equals==1
    assert row.median_interval_hours==24 and row.max_gap_hours==24
    pd.testing.assert_frame_equal(source_summary(measurements,a,['value'],'test'),source_summary(measurements.iloc[::-1],b,['value'],'test'))


def test_single_point_insufficient_and_undefined_variability(measurements):
    p=prism_profiles(measurements,['value']);row=p[p.prism_id.eq('B')].iloc[0]
    assert row.coverage_insufficient and row.observed_days==0 and pd.isna(row.value_std_sample)
    assert row.value_range==0 and row.value_equals==0 and pd.isna(row.max_gap_hours)


def test_zero_intervals_are_rejected(measurements):
    with pytest.raises(ValueError,match='cero'):prism_profiles(pd.concat([measurements,measurements.iloc[[0]]]),['value'])


def test_representatives_and_ties_are_reproducible():
    frames=[]
    for i,prism in enumerate(['D','C','B','A']):
        frames.append(pd.DataFrame({'prism_id':prism,'timestamp':pd.date_range('2014-01-01',periods=20),'value':np.arange(20)}))
    frames.append(pd.DataFrame({'prism_id':['X'],'timestamp':[pd.Timestamp('2014-01-01')],'value':[0.]}))
    p=prism_profiles(pd.concat(frames,ignore_index=True),['value']);r=representative_prisms(p,['value'])
    pd.testing.assert_frame_equal(r,representative_prisms(p.sample(frac=1,random_state=3),['value']))
    assert set(r.prism_id)=={'A','B','C','X'} and r.prism_id.is_unique
    assert 'menor_desviacion_muestral:value' not in r[r.prism_id.eq('X')].selection_groups.iloc[0]


def test_missing_values_not_skipped_in_consecutive_pairs():
    f=pd.DataFrame({'prism_id':['A']*3,'timestamp':pd.date_range('2014-01-01',periods=3),'v':[1.,np.nan,3.]})
    p=prism_profiles(f,['v']).iloc[0]
    assert p.v_increases==0 and p.v_unknown_comparisons==2


def test_daily_availability_has_calendar_zeros(measurements):
    t=daily_availability(measurements);assert t.shape==(2,5) and t.loc['B'].tolist()==[1,0,0,0,0]


def weather():
    return pd.DataFrame({'timestamp':pd.date_range('2014-01-01',periods=31),'station_id':'029167','product_code':'ID','quality_code':'N',
                         'rainfall_period_days':1.,'rainfall_mm':[np.nan]+[0.]*29+[5.]})


def test_unknown_rain_preserved_metadata_and_monthly_partial():
    f=weather();before=f.copy();d=combine_rainfall([(2014,f)]);s,m=rainfall_tables(d)
    assert d.rainfall_mm.isna().sum()==1 and set(d.station_id)=={'029167'}
    assert 'weather_product_code' in d and 'rainfall_quality_code' in d and set(d.source_year)=={2014}
    assert s.measured_days.iloc[0]==30 and s.zero_rain_days_observed.iloc[0]==29
    assert m.observed_rainfall_total_mm.iloc[0]==5 and m.missing_days.iloc[0]==1
    assert m.incomplete_month.iloc[0] and 'parcial' in m.warning.iloc[0]
    pd.testing.assert_frame_equal(f,before)


def test_month_all_unknown_keeps_total_unknown():
    f=weather();f.rainfall_mm=np.nan;_,m=rainfall_tables(combine_rainfall([(2014,f)]))
    assert pd.isna(m.observed_rainfall_total_mm.iloc[0]) and m.measured_days.iloc[0]==0


def test_weather_duplicates_or_multiday_require_review():
    f=weather()
    with pytest.raises(ValueError,match='repetidas'):combine_rainfall([(2014,f),(2014,f)])
    f.rainfall_period_days=2
    with pytest.raises(ValueError,match='varios'):combine_rainfall([(2014,f)])


def test_prism_statistics_do_not_mutate_input(measurements):
    before=measurements.copy(deep=True);p=prism_profiles(measurements,['value']);representative_prisms(p,['value']);daily_availability(measurements)
    pd.testing.assert_frame_equal(measurements,before)


def test_tables_bytes_invariant(measurements,tmp_path):
    a=prism_profiles(measurements,['value']);b=prism_profiles(measurements.iloc[::-1],['value'])
    a.to_csv(tmp_path/'a.csv',index=False);b.to_csv(tmp_path/'b.csv',index=False)
    assert (tmp_path/'a.csv').read_bytes()==(tmp_path/'b.csv').read_bytes()


def test_plot_does_not_mutate_or_write_raw(tmp_path):
    from src.visualizations import histogram
    x=pd.Series([1.,2.,3.,np.nan]);before=x.copy(deep=True)
    asset=histogram(x,'test','Valores relativos reportados; unidad pendiente de validación',tmp_path,'Unidad pendiente')
    pd.testing.assert_series_equal(x,before)
    assert (tmp_path/asset['png']).is_file() and (tmp_path/asset['html']).is_file()
    from PIL import Image
    with Image.open(tmp_path/asset['png']) as picture:picture.verify()
    assert not list((tmp_path/'figures').glob('*.tmp'))
    assert (tmp_path/'interactive/plotly.min.js').is_file()
    with pytest.raises(ValueError):histogram(x,'bad','test',tmp_path/'data/raw','x')


def test_previous_files_intact_and_units_pending():
    root=Path(__file__).resolve().parents[1]
    for name,digest in json.loads((root/'reports/documentation/protected_before_phase3.json').read_text()).items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    f=read_prepared(root/'data/processed/south_west','south_west')
    p=prism_profiles(f,['easting_diff','northing_diff','height_diff']);s=source_summary(f,p,['easting_diff'],SOUTH_DESCRIPTION)
    assert 'unidad pendiente' in s.description.iloc[0]
    metadata=json.loads((root/'data/processed/south_west/metadata.json').read_text())
    assert all(v=='requiere validación' for v in metadata['units'].values())
