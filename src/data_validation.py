"""Informes de calidad sin modificar el DataFrame recibido."""
from dataclasses import dataclass, asdict
import re
import numpy as np
import pandas as pd
from .schemas import get_schema, column_mapping, PENDING

MONTHS={m:i+1 for i,m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}


def text_series(series):
    return series.astype('string').fillna('').str.strip()


def missing_mask(series):
    return series.isna() | text_series(series).eq('')


def _date_text(series):
    def convert(value):
        match=re.fullmatch(r'(\d{1,2})-([A-Za-z]{3})-(\d{2})',value)
        if match:
            day,month,year=match.groups()
            if month.lower() not in MONTHS: return ''
            return f'20{year}-{MONTHS[month.lower()]:02d}-{int(day):02d}'
        # Excel date stored as midnight datetime: Date is a date, Time is separate.
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?: 00:00:00(?:\.0+)?)?',value): return value[:10]
        return ''
    return text_series(series).map(convert)


def _valid_clock(series):
    clock=text_series(series).str.extract(r'^(\d{2}):(\d{2}):(\d{2})$')
    numbers=clock.apply(pd.to_numeric,errors='coerce')
    return numbers[0].between(0,23)&numbers[1].between(0,59)&numbers[2].between(0,59)


def build_timestamp(frame,kind):
    """Deterministic formats; DD-Mon-YY policy 2000–2099 explicitly documented.

    No timezone is assigned to prism/weather/TXT sources. Epoch events use UTC
    under the interpretation documented in their header, never joined here.
    """
    if kind in {'west_wall','south_west'}:
        s=_date_text(frame['date_original'])+' '+text_series(frame['time_original'])
        return pd.to_datetime(s,format='%Y-%m-%d %H:%M:%S',errors='coerce').mask(~_valid_clock(frame['time_original']))
    if kind in {'rainfall','slope_dat'}:
        parts={}
        for key in ['year','month','day']:
            number=pd.to_numeric(frame[key],errors='coerce')
            number=number.where(np.isfinite(number)&number.eq(number.round()))
            if key=='year' and kind=='slope_dat':
                # DAT explicitly equivalent to 2014 CSV; only 2-digit years accepted.
                number=(number+2000).where(number.between(0,99))
            parts[key]=number
        if kind=='slope_dat':
            for key in ['hour','minute','second']:
                number=pd.to_numeric(frame[key],errors='coerce')
                parts[key]=number.where(np.isfinite(number)&number.eq(number.round()))
            # pandas timedelta assembly could normalize hours >= 24: reject them.
            bad=~parts['hour'].between(0,23)|~parts['minute'].between(0,59)|~parts['second'].between(0,59)
        else: bad=pd.Series(False,index=frame.index)
        timestamp=pd.to_datetime(pd.DataFrame(parts,index=frame.index),errors='coerce')
        return timestamp.mask(bad)
    if kind=='velocity_changes':
        raw=text_series(frame['date_original'])
        correct_shape=raw.str.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        return pd.to_datetime(raw,format='%Y-%m-%dT%H:%M:%S',errors='coerce').mask(~correct_shape|~_valid_clock(raw.str[11:]))
    if kind=='seismic':
        values=pd.to_numeric(frame['event_epoch_seconds'],errors='coerce')
        return pd.to_datetime(values.where(np.isfinite(values)),unit='s',utc=True,errors='coerce')
    raise ValueError('Tipo de fuente no reconocido para fechas.')


def typed_view(frame,kind,normalized=False):
    result=frame.copy(deep=True)
    if not normalized: result=result.rename(columns=column_mapping(result.columns,kind))
    schema=get_schema(kind)
    if kind=='slope_dat' and {'prism_part_1','prism_part_2'}.issubset(result.columns):
        result['prism_id']=text_series(result['prism_part_1'])+'-'+text_series(result['prism_part_2'])
        result.loc[missing_mask(result['prism_part_1'])|missing_mask(result['prism_part_2']),'prism_id']=pd.NA
    if 'timestamp' not in result:
        try: result['timestamp']=build_timestamp(result,kind)
        except KeyError: result['timestamp']=pd.NaT
    for name in schema.numeric:
        if name in result:
            values=pd.to_numeric(result[name],errors='coerce')
            result[name]=values.where(np.isfinite(values))
    return result


@dataclass
class QualityReport:
    source_kind: str
    metrics: dict
    errors: list[dict]
    warnings: list[dict]

    @property
    def ok(self): return not self.errors

    def to_dict(self): return {**asdict(self),'ok':self.ok}


def validate_data(frame,source_kind,*,normalized=False,min_observations=20):
    if min_observations<1: raise ValueError('El mínimo de observaciones debe ser positivo.')
    schema=get_schema(source_kind)
    data=frame.copy(deep=True) if normalized else frame.rename(columns=column_mapping(frame.columns,source_kind)).copy(deep=True)
    data=data.reset_index(drop=True)
    required=list(schema.columns.values())
    absent=[c for c in required if c not in data]
    errors=[]; warnings=[]
    issue=lambda code,message,count=0,**kw: {'code':code,'message':message,'count':int(count),**kw}
    if absent: errors.append(issue('missing_columns','Faltan columnas obligatorias.',len(absent),columns=absent))
    original_columns=[c for c in required if c in data]
    metrics={'rows':len(data),'required_missing_columns':absent,'missing_by_column':{c:int(missing_mask(data[c]).sum()) for c in original_columns},
             'units':schema.units,'description':schema.description,'time_basis':schema.time_basis,'min_observations':min_observations,
             'discarded_source_columns':[], 'unmapped_source_columns':[c for c in data if c not in required and not c.startswith(('original__','_')) and c not in ['timestamp','row_id','source_sha256','source_name','source_line','quality_flags','prism_id']]}
    metrics['missing_cells']=sum(metrics['missing_by_column'].values())
    if metrics['missing_cells']: warnings.append(issue('missing_values','Hay valores desconocidos; no se rellenan.',metrics['missing_cells']))
    pending=[c for c,u in schema.units.items() if PENDING in u]
    if pending: warnings.append(issue('units_pending',PENDING,len(pending),columns=pending))
    warnings.append(issue('time_basis_pending',schema.time_basis))
    if absent:
        return QualityReport(source_kind,metrics,errors,warnings)
    numeric_invalid={}
    for c in schema.numeric:
        values=pd.to_numeric(data[c],errors='coerce')
        bad=~missing_mask(data[c]) & (values.isna()|~np.isfinite(values))
        numeric_invalid[c]=int(bad.sum())
        if bad.any(): errors.append(issue('invalid_numeric','Hay valores no numéricos o no finitos.',bad.sum(),column=c,row_positions=np.flatnonzero(bad).tolist()))
    metrics['invalid_numeric_by_column']=numeric_invalid
    view=typed_view(data,source_kind,normalized=True)
    valid_time=view['timestamp'].notna()
    metrics['invalid_timestamps']=int((~valid_time).sum())
    if (~valid_time).any(): errors.append(issue('invalid_timestamp','Hay fechas u horas no interpretables.',(~valid_time).sum(),row_positions=np.flatnonzero(~valid_time).tolist()))
    identity='prism_id' if 'prism_id' in schema.keys else 'station_id' if 'station_id' in schema.keys else None
    identity_valid=~missing_mask(view[identity]) if identity else pd.Series(True,index=view.index)
    metrics['missing_identifiers']=int((~identity_valid).sum())
    if (~identity_valid).any(): errors.append(issue('missing_identifier','Falta el identificador de prisma/estación.',(~identity_valid).sum(),row_positions=np.flatnonzero(~identity_valid).tolist()))
    # Exactness is determined from all original cell values, never coercions.
    raw_columns=[c for c in data if c.startswith('original__')]
    payload=raw_columns or [c for c in data if c not in ['row_id','source_name','source_sha256','source_line','timestamp','quality_flags'] and not c.startswith('_')]
    exact=data[payload].duplicated(keep='first')
    metrics['duplicate_rows_extra']=int(exact.sum())
    if exact.any(): warnings.append(issue('exact_duplicates','Filas idénticas adicionales; gestionar conservando trazabilidad.',exact.sum()))
    eligible=view.loc[valid_time&identity_valid]
    keys=list(schema.keys)
    key_extra=eligible.duplicated(keys,keep='first')
    metrics['duplicate_key_extra']=int(key_extra.sum())
    conflicts=[]
    if key_extra.any():
        for _,positions in eligible.groupby(keys,sort=False).groups.items():
            if len(positions)>1 and len(data.loc[positions,payload].drop_duplicates())>1: conflicts.extend(positions)
    metrics['conflicting_key_rows']=len(conflicts)
    if conflicts: warnings.append(issue('conflicting_keys','Misma clave con valores distintos; conservar en cuarentena para revisión.',len(conflicts),row_positions=[int(i) for i in conflicts]))
    order=([identity] if identity else [])+['timestamp']
    sorted_view=eligible.sort_values(order,kind='stable')
    delta=(sorted_view.groupby(identity,sort=False)['timestamp'].diff() if identity else sorted_view['timestamp'].diff()).dt.total_seconds()
    metrics['zero_intervals']=int(delta.eq(0).sum())
    if metrics['zero_intervals']: warnings.append(issue('zero_intervals','Hay instantes repetidos dentro del identificador.',metrics['zero_intervals']))
    original_delta=(eligible.groupby(identity,sort=False)['timestamp'].diff() if identity else eligible['timestamp'].diff()).dt.total_seconds()
    metrics['backward_steps_original']=int(original_delta.lt(0).sum())
    if metrics['backward_steps_original']: warnings.append(issue('unordered_timestamps','Hay retrocesos temporales en el orden recibido.',metrics['backward_steps_original']))
    metrics['prisms']=int(view['prism_id'].nunique()) if 'prism_id' in view else None
    small={}
    if identity=='prism_id':
        counts=eligible.groupby('prism_id')['timestamp'].nunique()
        small={str(k):int(v) for k,v in counts[counts<min_observations].items()}
        if small: warnings.append(issue('insufficient_observations','Prismas con menos instantes únicos que el mínimo operativo configurable; no es umbral geotécnico.',len(small),prisms=small))
    metrics['insufficient_prisms']=small
    positive=delta[delta>0]
    metrics['median_interval_hours']=float(positive.median()/3600) if len(positive) else None
    metrics['max_gap_hours']=float(positive.max()/3600) if len(positive) else None
    metrics['gaps_gt24h']=int(delta.gt(86400).sum())
    if identity=='prism_id' and metrics['gaps_gt24h']: warnings.append(issue('long_gaps','Intervalos mayores a 24 h; criterio informativo, sin interpolación.',metrics['gaps_gt24h']))
    metrics['coverage_start']=str(view.loc[valid_time,'timestamp'].min()) if valid_time.any() else None
    metrics['coverage_end']=str(view.loc[valid_time,'timestamp'].max()) if valid_time.any() else None
    metrics['rows_with_missing']=int(pd.concat([missing_mask(data[c]) for c in original_columns],axis=1).any(axis=1).sum())
    if source_kind=='rainfall':
        rain=view['rainfall_mm']; periods=view['rainfall_period_days']
        invalid=(rain.notna()&rain.lt(0))|(periods.notna()&(~periods.gt(0)|~periods.eq(periods.round())))
        metrics['invalid_rainfall_semantics']=int(invalid.sum())
        if invalid.any(): warnings.append(issue('rainfall_semantics','Precipitación negativa o período no positivo/entero; se marca sin sustituir.',invalid.sum()))
        warnings.append(issue('quality_code_pending','Significado del código de calidad requiere validación.'))
    return QualityReport(source_kind,metrics,errors,warnings)
