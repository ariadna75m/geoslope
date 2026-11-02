from pathlib import Path
from datetime import datetime,time
import hashlib
import pytest
from openpyxl import Workbook
from src.data_loader import load_file,DataLoadError,safe_filename
from src.schemas import WEST,VELOCITY

@pytest.mark.parametrize('relative,kind,rows,cols,header',[
 ('radar-deformation-data/West Wall Prism Movements - 3 months to 20-Feb-14.csv','west_wall',7178,7,1),
 ('radar-deformation-data/South_West_Corner_06082014.csv','south_west',82401,11,4),
 ('radar-deformation-data/slopeMovement.dat','slope_dat',82401,16,1),
 ('seismic-event-data/events-and-blasts.csv','seismic',1171,7,1),
 ('velocity-change-measurements/mean-velocity-changes.txt','velocity_changes',44,4,1),
 ('weather-data/IDCJAC0009_029167_2013_Data.csv','rainfall',365,8,1),
 ('weather-data/IDCJAC0009_029167_2014_Data.csv','rainfall',365,8,1),
])
def test_all_real_tabular_files(raw_dir,relative,kind,rows,cols,header):
    p=raw_dir/relative; before=hashlib.sha256(p.read_bytes()).hexdigest()
    loaded=load_file(p)
    assert loaded.frame.shape==(rows,cols)
    assert loaded.kind==kind and loaded.metadata['header_line_1based']==header
    assert loaded.source_sha256==before==hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(loaded.source_lines)==rows
    if kind=='rainfall': assert set(loaded.frame['Bureau of Meteorology station number'])=={'029167'}


def test_excel_preamble_and_stored_values(tmp_path):
    p=tmp_path/'input.xlsx';book=Workbook();sheet=book.active
    sheet.append(['Nota de exportación']);sheet.append(list(WEST))
    sheet.append(['001',datetime(2014,1,1),time(10,0),1,2,3,'=1+2'])
    book.save(p)
    loaded=load_file(p)
    assert loaded.kind=='west_wall' and loaded.metadata['header_line_1based']==2
    assert loaded.frame.iloc[0,0]=='001'
    assert loaded.frame.iloc[0,-1]=='=1+2'  # formula is not silently evaluated
    assert loaded.source_lines==(3,)


def test_multiline_fields_trace_physical_start(write_table):
    p=write_table('m.csv',[*WEST,'Note'],[['P1','01-Jan-14','10:00:00','1','2','3','4','a\nb'],['P1','02-Jan-14','10:00:00','1','2','3','4','c']])
    s=load_file(p); assert s.source_lines==(2,4)
    assert s.frame.iloc[0]['Note']=='a\nb'


def test_header_control_and_missing_columns(write_table):
    p=write_table('partial.csv',['Prism','Date'],[['P1','01-Jan-14']])
    with pytest.raises(DataLoadError,match='encabezado'): load_file(p,source_kind='west_wall')
    s=load_file(p,source_kind='west_wall',header_row=0)
    assert list(s.frame)==['Prism','Date']

@pytest.mark.parametrize('suffix',['.zip','.pdf','.exe','.json'])
def test_extension_rejection(tmp_path,suffix):
    p=tmp_path/('bad'+suffix);p.write_text('x')
    with pytest.raises(DataLoadError,match='Extensión'): load_file(p)


def test_oversized_file(west_file):
    with pytest.raises(DataLoadError,match='tamaño'): load_file(west_file,max_file_bytes=2)

@pytest.mark.parametrize('content,message',[(b'','vacío'),(b'\xff','codificar'),(b'not a table','encabezado'),(b'abc\x00','nulos')])
def test_bad_content(tmp_path,content,message):
    p=tmp_path/'bad.csv';p.write_bytes(content)
    with pytest.raises(DataLoadError,match=message): load_file(p)


def test_wrong_width(write_table):
    p=write_table('w.csv',WEST,[['P1','01-Jan-14','10:00:00']])
    with pytest.raises(DataLoadError,match='ancho'): load_file(p)


def test_header_search_limit(write_table):
    p=write_table('p.csv',WEST,[['P1','01-Jan-14','10:00:00','1','2','3','4']],preamble='note\nnote\n')
    with pytest.raises(DataLoadError,match='encabezado'): load_file(p,max_header_lines=2)
    assert load_file(p,max_header_lines=3).metadata['header_line_1based']==3


def test_duplicate_or_blank_header(tmp_path):
    p=tmp_path/'x.csv';p.write_text('Prism,Prism\nA,B\n')
    with pytest.raises(DataLoadError,match='repetidos'):load_file(p,header_row=0)
    p.write_text('Prism,\nA,B\n')
    with pytest.raises(DataLoadError,match='vacíos'):load_file(p,header_row=0)


def test_missing_file(tmp_path):
    with pytest.raises(DataLoadError,match='archivo'):load_file(tmp_path/'missing.csv')


def test_no_data(write_table):
    p=write_table('empty.csv',WEST,[])
    with pytest.raises(DataLoadError,match='filas de datos'):load_file(p)


def test_bad_excel_and_sheet(tmp_path):
    p=tmp_path/'fake.xlsx';p.write_text('csv pretending to be excel')
    with pytest.raises(DataLoadError):load_file(p)
    book=Workbook();book.active.append(list(WEST));book.active.append(['P1','01-Jan-14','10:00:00',1,2,3,4]);book.save(p)
    with pytest.raises(DataLoadError):load_file(p,sheet_name='missing')


def test_safe_name():
    assert safe_filename('../../unsafe name.csv')=='unsafe_name.csv'
    assert safe_filename('..\\..\\unsafe name.csv')=='unsafe_name.csv'
    assert '/' not in safe_filename('../../')


def test_limits_and_explicit_empty_header(west_file):
    with pytest.raises(DataLoadError):load_file(west_file,max_rows=1)
    with pytest.raises(DataLoadError):load_file(west_file,max_columns=2)
    with pytest.raises(DataLoadError):load_file(west_file,header_row=500)
    with pytest.raises(DataLoadError):load_file(west_file,max_header_lines=0)


def test_actual_xls_loader_and_preparation(tmp_path):
    import xlwt
    from src.preprocessing import prepare_source
    book=xlwt.Workbook();sheet=book.add_sheet('Movimientos')
    for i,name in enumerate(WEST):sheet.write(0,i,name)
    date_style=xlwt.easyxf(num_format_str='YYYY-MM-DD')
    time_style=xlwt.easyxf(num_format_str='hh:mm:ss')
    values=['001',datetime(2014,1,1),10/24,1,2,3,4]
    for i,value in enumerate(values):sheet.write(1,i,value,date_style if i==1 else time_style if i==2 else xlwt.Style.default_style)
    p=tmp_path/'sample.xls';book.save(str(p));loaded=load_file(p)
    assert loaded.kind=='west_wall' and loaded.metadata['sheet']=='Movimientos'
    result=prepare_source(loaded)
    assert result.data.iloc[0].prism_id=='001'
    assert str(result.data.iloc[0].timestamp)=='2014-01-01 10:00:00'


def test_full_width_empty_record_is_preserved(write_table):
    p=write_table('empty-record.csv',WEST,[['']*len(WEST)])
    loaded=load_file(p)
    assert len(loaded.frame)==1 and loaded.source_lines==(2,)
