"""Estadísticas descriptivas independientes; sin derivadas físicas ni modelos."""
from pathlib import Path
import numpy as np
import pandas as pd
from .schemas import get_schema

WEST_DESCRIPTION=('Movimiento 3D reportado en milímetros respecto a la referencia indicada en el archivo. '
                  'No se asume que sea una trayectoria acumulativa estrictamente creciente')
SOUTH_DESCRIPTION='Valores relativos reportados; unidad pendiente de validación'
DISCLAIMER=('Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla '
            'ni reemplaza la evaluación del ingeniero geomecánico.')


def read_prepared(directory,kind):
    frame=pd.read_csv(Path(directory)/'data.csv',dtype=str,keep_default_na=False)
    frame['timestamp']=pd.to_datetime(frame['timestamp'],errors='raise')
    for name in get_schema(kind).numeric:frame[name]=pd.to_numeric(frame[name],errors='raise') if frame[name].ne('').all() else pd.to_numeric(frame[name].replace('',np.nan),errors='raise')
    return frame


def numeric_stats(series):
    x=pd.to_numeric(series,errors='raise').dropna()
    if (~np.isfinite(x)).any():raise ValueError('No se aceptan valores numéricos infinitos en la exploración.')
    output={'measured_count':len(x),'missing_count':int(series.isna().sum())}
    for key,value in {'min':x.min(),'max':x.max(),'mean':x.mean(),'median':x.median(),'std_sample':x.std(ddof=1),
                      'q1':x.quantile(.25),'q3':x.quantile(.75),'iqr':x.quantile(.75)-x.quantile(.25),'range':x.max()-x.min()}.items():
        output[key]=float(value) if pd.notna(value) else None
    return output


def ordered_prisms(frame):
    if not {'prism_id','timestamp'}.issubset(frame):raise ValueError('Faltan prisma o timestamp.')
    data=frame.copy(deep=True)
    if data.prism_id.isna().any() or data.prism_id.astype(str).str.strip().eq('').any():raise ValueError('Hay prismas sin identificador.')
    data['prism_id']=data.prism_id.astype(str);data['timestamp']=pd.to_datetime(data.timestamp,errors='raise')
    if data.timestamp.isna().any():raise ValueError('Hay fechas desconocidas.')
    if data.duplicated(['prism_id','timestamp']).any():raise ValueError('Hay intervalos cero/claves temporales repetidas; volver a revisar preparación.')
    return data.sort_values(['prism_id','timestamp'],kind='stable').reset_index(drop=True)


def prism_profiles(frame,value_columns,*,min_observations=20):
    if min_observations<1:raise ValueError('Mínimo de observaciones debe ser positivo.')
    data=ordered_prisms(frame);rows=[]
    for prism,g in data.groupby('prism_id',sort=True):
        intervals=g.timestamp.diff().dt.total_seconds().dropna()/3600
        row={'prism_id':prism,'observations':len(g),'unique_timestamps':g.timestamp.nunique(),
             'first_timestamp':g.timestamp.iloc[0],'last_timestamp':g.timestamp.iloc[-1],
             'observed_days':(g.timestamp.iloc[-1]-g.timestamp.iloc[0]).total_seconds()/86400,
             'median_interval_hours':float(intervals.median()) if len(intervals) else None,
             'max_gap_hours':float(intervals.max()) if len(intervals) else None,
             'gaps_gt24h':int(intervals.gt(24).sum()),'coverage_insufficient':g.timestamp.nunique()<min_observations}
        for c in value_columns:
            stats=numeric_stats(g[c]);diff=g[c].diff()
            row.update({c+'_'+k:v for k,v in stats.items()})
            row.update({c+'_initial':float(g[c].iloc[0]) if pd.notna(g[c].iloc[0]) else None,
                        c+'_final':float(g[c].iloc[-1]) if pd.notna(g[c].iloc[-1]) else None,
                        c+'_final_minus_initial':float(g[c].iloc[-1]-g[c].iloc[0]) if pd.notna(g[c].iloc[-1]) and pd.notna(g[c].iloc[0]) else None,
                        c+'_increases':int(diff.gt(0).sum()),c+'_decreases':int(diff.lt(0).sum()),c+'_equals':int(diff.eq(0).sum()),
                        c+'_unknown_comparisons':int(diff.iloc[1:].isna().sum())})
        rows.append(row)
    return pd.DataFrame(rows)


def source_summary(frame,profiles,value_columns,description):
    data=ordered_prisms(frame);interval=data.groupby('prism_id').timestamp.diff().dt.total_seconds().dropna()/3600
    start=data.timestamp.min();end=data.timestamp.max()
    result={'rows':len(data),'prisms':data.prism_id.nunique(),'first_timestamp':start,'last_timestamp':end,
            'coverage_days':(end-start).total_seconds()/86400,'median_interval_hours':float(interval.median()) if len(interval) else None,
            'max_gap_hours':float(interval.max()) if len(interval) else None,'zero_intervals':int(interval.eq(0).sum()),
            'insufficient_prisms':int(profiles.coverage_insufficient.sum()),'prisms_with_gap_gt24h':int(profiles.gaps_gt24h.gt(0).sum()),
            'observations_per_prism_min':int(profiles.observations.min()),'observations_per_prism_max':int(profiles.observations.max()),
            'description':description,'grouped_intervals_policy':'Intervalos dentro de cada prisma, ponderados por observación; sin porcentaje de continuidad inferido.'}
    for c in value_columns:
        result.update({c+'_'+k:v for k,v in numeric_stats(data[c]).items()})
        for field in ['increases','decreases','equals','unknown_comparisons']:result[c+'_'+field]=int(profiles[c+'_'+field].sum())
    return pd.DataFrame([result])


def representative_prisms(profiles,value_columns,*,min_observations=20):
    """Ranking descriptivo; empates por ID ascendente, nunca por fecha de falla."""
    groups={}
    def add(ids,label):
        for prism in ids:groups.setdefault(str(prism),[]).append(label)
    add(profiles.sort_values(['observations','prism_id'],ascending=[False,True]).head(3).prism_id,'mayor_numero_observaciones')
    for c in value_columns:
        add(profiles.sort_values([c+'_range','prism_id'],ascending=[False,True],na_position='last').head(3).prism_id,'mayor_rango:'+c)
        enough=profiles.loc[profiles.unique_timestamps.ge(min_observations)&profiles[c+'_std_sample'].notna()]
        add(enough.sort_values([c+'_std_sample','prism_id'],ascending=[True,True]).head(2).prism_id,'menor_desviacion_muestral:'+c)
    add(profiles.loc[profiles.unique_timestamps.lt(min_observations)].sort_values('prism_id').prism_id,'cobertura_insuficiente')
    result=profiles.loc[profiles.prism_id.isin(groups)].copy().sort_values('prism_id').reset_index(drop=True)
    result['selection_groups']=result.prism_id.map(lambda p:';'.join(groups[str(p)]))
    result['selection_group_count']=result.prism_id.map(lambda p:len(groups[str(p)]))
    result['selection_note']='Descriptivo; desviación estándar muestral con ≥20 instantes; empates por ID. Sin clasificación geomecánica.'
    return result


def daily_availability(frame):
    data=ordered_prisms(frame);dates=pd.date_range(data.timestamp.min().normalize(),data.timestamp.max().normalize(),freq='D')
    table=data.assign(day=data.timestamp.dt.normalize()).groupby(['prism_id','day']).size().unstack(fill_value=0)
    return table.reindex(index=sorted(data.prism_id.unique()),columns=dates,fill_value=0)


def combine_rainfall(sources):
    frames=[]
    for year,frame in sources:
        data=frame.copy(deep=True).rename(columns={'product_code':'weather_product_code','quality_code':'rainfall_quality_code'})
        needed=['timestamp','station_id','weather_product_code','rainfall_quality_code','rainfall_period_days','rainfall_mm']
        if not set(needed).issubset(data):raise ValueError('Faltan metadatos meteorológicos.')
        data['source_year']=int(year);data['timestamp']=pd.to_datetime(data.timestamp,errors='raise')
        if data.timestamp.isna().any() or not data.timestamp.dt.year.eq(year).all():raise ValueError('Fecha de meteorología no corresponde al año de origen.')
        frames.append(data)
    result=pd.concat(frames,ignore_index=True).sort_values(['station_id','timestamp'],kind='stable').reset_index(drop=True)
    if result.station_id.nunique()!=1:raise ValueError('El resumen combina únicamente una estación.')
    if result.duplicated(['station_id','timestamp']).any():raise ValueError('Fechas meteorológicas repetidas; no se combinan automáticamente.')
    if result.rainfall_mm.dropna().lt(0).any():raise ValueError('Lluvia negativa requiere revisión previa.')
    if result.rainfall_period_days.dropna().ne(1).any():raise ValueError('Acumulados de varios días no se distribuyen como lluvia diaria.')
    return result


def rainfall_tables(frame):
    data=frame.copy(deep=True).sort_values('timestamp');rain=data.rainfall_mm
    dates=pd.date_range(data.timestamp.min(),data.timestamp.max(),freq='D')
    calendar_missing=dates.difference(data.timestamp);unknown=data.loc[rain.isna(),'timestamp']
    summary={'calendar_days':len(dates),'records':len(data),'measured_days':int(rain.notna().sum()),
             'measured_days_pct':100*rain.notna().sum()/len(dates),'missing_measurement_days':len(unknown),
             'absent_calendar_records':len(calendar_missing),'rainy_days_observed':int(rain.gt(0).sum()),'zero_rain_days_observed':int(rain.eq(0).sum()),
             'missing_dates':';'.join(d.strftime('%Y-%m-%d') for d in sorted(set(unknown)|set(calendar_missing))),
             **numeric_stats(rain)}
    monthly=[]
    data['month']=data.timestamp.dt.to_period('M')
    for month,g in data.groupby('month',sort=True):
        days=month.days_in_month;measured=int(g.rainfall_mm.notna().sum());missing=days-measured
        total=g.rainfall_mm.sum(min_count=1)
        monthly.append({'month':str(month),'station_id':str(g.station_id.iloc[0]),'calendar_days':days,'recorded_days':len(g),'measured_days':measured,
                        'missing_days':missing,'rainy_days_observed':int(g.rainfall_mm.gt(0).sum()),'zero_rain_days_observed':int(g.rainfall_mm.eq(0).sum()),
                        'observed_rainfall_total_mm':float(total) if pd.notna(total) else None,
                        'coverage_pct':100*measured/days,'incomplete_month':missing>0,
                        'warning':'Total parcial: días desconocidos; no imputados' if missing else 'Total de días observados del mes completo'})
    return pd.DataFrame([summary]),pd.DataFrame(monthly)


def independent_series_summary(frame,columns):
    data=frame.copy(deep=True).sort_values('timestamp');delta=data.timestamp.diff().dt.total_seconds().dropna()/3600
    row={'rows':len(data),'first_timestamp':data.timestamp.min(),'last_timestamp':data.timestamp.max(),
         'median_interval_hours':float(delta.median()) if len(delta) else None,'min_interval_hours':float(delta.min()) if len(delta) else None,
         'max_interval_hours':float(delta.max()) if len(delta) else None}
    for c in columns:row.update({c+'_'+k:v for k,v in numeric_stats(data[c]).items()})
    return pd.DataFrame([row])
