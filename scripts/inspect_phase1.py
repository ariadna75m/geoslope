"""Fase 1 solamente: auditoría de lectura; no limpia ni modifica datos originales."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json, platform
import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'reports'
OUT.mkdir(exist_ok=True)
TABLES = {}; TIMES = {}; KEYS = {}; PROFILES = []; COLUMN_ROWS = []; PRISMS = []

def safe(v):
    if isinstance(v, (np.integer,np.floating)): return v.item()
    if isinstance(v, (pd.Timestamp,Path)): return str(v)
    raise TypeError(type(v).__name__)

def parse_time(df, name):
    if name.endswith('.dat'):
        text = '20'+df['year']+'-'+df['month']+'-'+df['day']+' '+df['hour']+':'+df['minute']+':'+df['second']
        return pd.to_datetime(text,format='%Y-%m-%d %H:%M:%S',errors='coerce'), 'prism_part_1', 'requiere validación: año 14 interpretado como 2014 por equivalencia con CSV'
    if 'Prism' in df:
        return pd.to_datetime(df['Date']+' '+df['Time'],format='%d-%b-%y %H:%M:%S',errors='coerce'), 'Prism', 'fecha/hora sin zona horaria documentada'
    if 'EventTimeEpochSeconds' in df:
        return pd.to_datetime(pd.to_numeric(df['EventTimeEpochSeconds'],errors='coerce'),unit='s',utc=True,errors='coerce'), None, 'UTC bajo interpretación Unix del nombre; requiere validación de la exportación'
    if 'Year' in df:
        return pd.to_datetime(df['Year']+'-'+df['Month']+'-'+df['Day'],format='%Y-%m-%d',errors='coerce'), None, 'día calendario; hora de cierre/intervalo de lluvia requiere validación'
    return pd.to_datetime(df['Date'],format='%Y-%m-%dT%H:%M:%S',errors='coerce'), None, 'fecha/hora sin zona horaria documentada'

for p in sorted(RAW.rglob('*')):
    if not p.is_file(): continue
    rel=p.relative_to(RAW).as_posix(); content=p.read_bytes()
    record={'file':rel,'size_bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
    if p.suffix=='.pdf':
        reader=PdfReader(p); texts=[page.extract_text() for page in reader.pages]
        (OUT/'station_metadata_extracted.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{t}' for i,t in enumerate(texts)),encoding='utf-8')
        record.update(format='PDF',pages=len(reader.pages),rows=None,columns_count=None,prisms=None,coverage_start=None,coverage_end=None,reading_notes='Texto extraído de las 17 páginas; no es tabla de mediciones. Metadatos compilados 28 JUL 2021. Advertencias del PDF sobre completitud/calidad histórica.')
        PROFILES.append(record); continue
    text=content.decode('utf-8-sig'); lines=text.splitlines(); sep='\t' if p.suffix=='.txt' else ','
    header_line=next(i for i,line in enumerate(lines) if line.startswith(('Prism,','%Prism,','#Index,','Date\t','Product code,')))
    parsed=list(csv.reader(lines[header_line:],delimiter=sep)); header=parsed[0]; rows=parsed[1:]; widths=Counter(len(row) for row in rows)
    notes=[]
    if header_line: notes.append(f'Encabezado en línea {header_line+1}; {header_line} líneas previas no tabulares.')
    if p.suffix=='.dat':
        notes.append('Encabezado: 15 nombres; todas las filas: 16 campos. Se proponen dos partes del ID del prisma, corroboradas fila a fila con CSV. No aceptar lectura silenciosa desplazada.')
        names=['prism_part_1','prism_part_2']+header[1:]
    else: names=header
    if any(len(row)!=len(names) for row in rows): raise ValueError(f'Ancho inesperado {rel}: {widths}')
    df=pd.DataFrame(rows,columns=names); TABLES[rel]=df
    missing=df.apply(lambda s:s.str.strip().eq(''))
    non_numeric=[]
    for col in names:
        s=df[col]; n=pd.to_numeric(s.where(~missing[col]),errors='coerce')
        failures=int((~missing[col]&n.isna()).sum())
        numeric=failures==0 and bool((~missing[col]).any())
        COLUMN_ROWS.append({'file':rel,'column':col,'type_observed':'numeric-string' if numeric else 'text','missing':int(missing[col].sum()),'unique_nonempty':int(s[~missing[col]].nunique()),'numeric_min':float(n.min()) if numeric else None,'numeric_max':float(n.max()) if numeric else None,'nonfinite_numeric':int((n.notna()&~np.isfinite(n)).sum()),'example':s[~missing[col]].iloc[0] if (~missing[col]).any() else ''})
        if not numeric: non_numeric.append(col)
    ts,idcol,time_note=parse_time(df,rel); TIMES[rel]=ts
    key=df['prism_part_1']+'-'+df['prism_part_2'] if p.suffix=='.dat' else df[idcol] if idcol else None
    KEYS[rel]=key
    valid=ts.notna(); keydf=pd.DataFrame({'timestamp':ts})
    if key is not None: keydf['prism']=key
    key_duplicated=keydf.loc[valid].duplicated(keep=False)
    conflicts=0; disorder=0; intervals=[]
    if key is not None:
        temp=pd.DataFrame({'prism':key,'timestamp':ts})
        disorder=int((temp.groupby('prism',sort=False)['timestamp'].diff().dt.total_seconds()<0).sum())
        groups=keydf.loc[valid].groupby(['prism','timestamp'],sort=False).indices
        valid_positions=np.flatnonzero(valid)
        for positions in groups.values():
            if len(positions)>1 and len(df.iloc[valid_positions[positions]].drop_duplicates())>1: conflicts+=1
        for prism,positions in temp.groupby('prism',sort=True).groups.items():
            pts=ts.loc[positions].dropna().sort_values(); dif=pts.diff().dt.total_seconds().dropna(); positive=dif[dif>0]/3600; intervals.extend(positive.tolist())
            PRISMS.append({'file':rel,'prism':prism,'rows':len(positions),'start':str(pts.min()),'end':str(pts.max()),'coverage_days':(pts.max()-pts.min()).total_seconds()/86400 if len(pts) else None,'unique_timestamps':pts.nunique(),'median_interval_hours':positive.median() if len(positive) else None,'min_interval_hours':positive.min() if len(positive) else None,'max_gap_hours':positive.max() if len(positive) else None,'duplicate_key_extra':len(pts)-pts.nunique(),'backward_steps_original':int((ts.loc[positions].diff().dt.total_seconds()<0).sum())})
    else:
        disorder=int((ts.diff().dt.total_seconds()<0).sum()); intervals=(ts.dropna().sort_values().diff().dt.total_seconds().dropna()/3600).tolist()
    record.update(format='TSV' if sep=='\t' else 'CSV-like DAT' if p.suffix=='.dat' else 'CSV',encoding='UTF-8',physical_lines=len(lines),header_line_1based=header_line+1,declared_columns=header,columns=names,columns_count=len(names),rows=len(df),field_widths=dict(widths),prisms=int(key.nunique()) if key is not None else None,coverage_start=str(ts.min()),coverage_end=str(ts.max()),coverage_days=(ts.max()-ts.min()).total_seconds()/86400,invalid_timestamps=int((~valid).sum()),timestamp_note=time_note,missing_cells=int(missing.sum().sum()),rows_with_missing=int(missing.any(axis=1).sum()),missing_by_column={k:int(v) for k,v in missing.sum().items()},duplicate_rows_extra=int(df.duplicated().sum()),duplicate_key_extra=int(keydf.loc[valid].duplicated().sum()),duplicate_key_affected_rows=int(key_duplicated.sum()),conflicting_key_groups=conflicts,backward_steps_original=disorder,median_interval_hours=float(np.median(intervals)) if len(intervals) else None,min_positive_interval_hours=float(min(x for x in intervals if x>0)) if any(x>0 for x in intervals) else None,max_gap_hours=float(max(intervals)) if len(intervals) else None,reading_notes=' '.join(notes) or 'Lectura rectangular sin errores de codificación o ancho.')
    PROFILES.append(record)

main_name='radar-deformation-data/South_West_Corner_06082014.csv'
dat_name='radar-deformation-data/slopeMovement.dat'
west_name='radar-deformation-data/West Wall Prism Movements - 3 months to 20-Feb-14.csv'
a=TABLES[main_name]; b=TABLES[dat_name]; w=TABLES[west_name]
numeric_cols=list(a.columns[3:]); numeric_equal=np.array_equal(a[numeric_cols].astype(float).to_numpy(),b[numeric_cols].astype(float).to_numpy())
extras={'csv_dat_equivalence':{'same_row_count':len(a)==len(b),'same_prism_order':KEYS[main_name].equals(KEYS[dat_name]),'same_timestamp_order':TIMES[main_name].equals(TIMES[dat_name]),'numeric_exact_float_equal':numeric_equal,'columns_compared':numeric_cols},'main_west_prism_overlap':sorted(set(KEYS[main_name])&set(KEYS[west_name]))}
checks=[]
for name in [main_name,west_name]:
    df=TABLES[name]; numeric=df.iloc[:,3:].astype(float)
    details={'file':name,'nonfinite_numeric_cells':int((~np.isfinite(numeric)).sum().sum()),'coordinate_ranges':{c:[float(numeric[c].min()),float(numeric[c].max())] for c in numeric.columns[:3]}}
    if name==main_name:
        scale={}
        for coord,diff in [('Easting','Easting Diff'),('Northing','Northing Diff'),('Height','Height Diff')]:
            base=numeric[coord].groupby(KEYS[name],sort=False).transform('first')
            residual=(numeric[diff]-(numeric[coord]-base)*1000).abs()
            bad=residual>1e-5
            scale[coord]={'hypothesis':'component_diff = (coordinate - first_coordinate_of_prism) * 1000','within_abs_1e_5_rows':int((~bad).sum()),'max_abs_residual':float(residual.max()),'exceptions':int(bad.sum())}
        details['component_scale_evidence']=scale
    else:
        c=numeric.columns[-1]; change=numeric[c].groupby(KEYS[name],sort=False).diff()
        details.update(negative_displacement_rows=int((numeric[c]<0).sum()),movement_decreases=int((change<0).sum()),movement_increases=int((change>0).sum()))
    checks.append(details)
extras['numeric_checks']=checks
extras['rainfall']=[]
for name,df in TABLES.items():
    if 'Rainfall amount (millimetres)' not in df: continue
    rain=pd.to_numeric(df['Rainfall amount (millimetres)'],errors='coerce'); period=pd.to_numeric(df['Period over which rainfall was measured (days)'],errors='coerce')
    extras['rainfall'].append({'file':name,'missing_rain_dates':TIMES[name][rain.isna()].dt.strftime('%Y-%m-%d').tolist(),'negative_rain':int((rain<0).sum()),'multi_day_measurements':int((period>1).sum()),'period_values':df['Period over which rainfall was measured (days)'].value_counts().to_dict(),'quality_values':df['Quality'].value_counts().to_dict(),'max_daily_or_period_amount_mm':float(rain.max()),'missing_period_dates':TIMES[name][period.isna()].dt.strftime('%Y-%m-%d').tolist()})
# Verificación adicional entre archivos y casos concretos, sin normalizar fuentes.
shared=a.merge(w,on=['Prism','Date','Time'],suffixes=('_main','_west'))
main_prisms=pd.DataFrame(PRISMS).query('file == @main_name')
extras['cross_file_checks']={'shared_prism_count':len(extras['main_west_prism_overlap']), 'shared_keys':len(shared), 'shared_easting_exact_equal':bool((shared['Easting_main']==shared['Easting_west']).all()), 'shared_northing_exact_equal':bool((shared['Northing_main']==shared['Northing_west']).all()), 'shared_height_RL_exact_equal':bool((shared['Height']==shared['RL']).all()), 'union_prism_count':len(set(KEYS[main_name])|set(KEYS[west_name]))}
extras['main_duplicate_records']=a[a.duplicated(keep=False)].to_dict('records')
extras['main_duplicate_source_lines']=(np.flatnonzero(a.duplicated(keep=False))+5).tolist()
extras['main_prism_summary']={'rows_min':int(main_prisms.rows.min()),'rows_max':int(main_prisms.rows.max()),'prisms_lt20_rows':int((main_prisms.rows<20).sum()),'prisms_gap_gt24h':int((main_prisms.max_gap_hours>24).sum()),'longest_gaps':main_prisms.nlargest(3,'max_gap_hours')[['prism','rows','start','end','max_gap_hours']].to_dict('records')}
extras['runtime']={'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__}
(OUT/'audit.json').write_text(json.dumps({'files':PROFILES,'checks':extras},ensure_ascii=False,indent=2,default=safe),encoding='utf-8')
pd.DataFrame(COLUMN_ROWS).to_csv(OUT/'column_profile.csv',index=False)
pd.DataFrame(PRISMS).to_csv(OUT/'prism_coverage.csv',index=False)
pd.DataFrame([{k:v for k,v in x.items() if k not in ['columns','declared_columns','missing_by_column','field_widths']} for x in PROFILES]).to_csv(OUT/'inventory.csv',index=False)
print(json.dumps({'files':[{k:x.get(k) for k in ['file','rows','columns_count','prisms','coverage_start','coverage_end','missing_cells','rows_with_missing','duplicate_rows_extra','duplicate_key_extra','conflicting_key_groups','backward_steps_original','median_interval_hours','max_gap_hours']} for x in PROFILES],'checks':extras},ensure_ascii=False,indent=2,default=safe))
