"""Ejecuta solo exploración, conservando fuentes y salidas anteriores por SHA-256."""
from pathlib import Path
import sys,json,hashlib,importlib.metadata as versions
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.data_loader import load_file
from src.data_validation import typed_view
from src.exploratory_analysis import (read_prepared,prism_profiles,source_summary,representative_prisms,daily_availability,
 combine_rainfall,rainfall_tables,independent_series_summary,DISCLAIMER,WEST_DESCRIPTION,SOUTH_DESCRIPTION)
from src.visualizations import west_plots,south_plots,rainfall_plots,events_plots,velocity_plot
OUT=ROOT/'reports/phase3'


def check_protected():
    protected=json.loads((ROOT/'reports/documentation/protected_before_phase3.json').read_text())
    for name,digest in protected.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Cambió un archivo protegido de las Fases 1–2: '+name)
    return len(protected)


def write_table(frame,name):frame.to_csv(OUT/name,index=False,float_format='%.12g')


def main(figures=True):
    check_protected();OUT.mkdir(parents=True,exist_ok=True)
    west=read_prepared(ROOT/'data/processed/west_wall','west_wall');south=read_prepared(ROOT/'data/processed/south_west','south_west')
    wcols=['reported_3d_movement_mm'];scols=['easting_diff','northing_diff','height_diff']
    wp=prism_profiles(west,wcols);sp=prism_profiles(south,scols)
    ws=source_summary(west,wp,wcols,WEST_DESCRIPTION);ss=source_summary(south,sp,scols,SOUTH_DESCRIPTION)
    wr=representative_prisms(wp,wcols);sr=representative_prisms(sp,scols);avail=daily_availability(west)
    years=[(year,read_prepared(ROOT/f'data/processed/rainfall_{year}','rainfall')) for year in [2013,2014]]
    rain=combine_rainfall(years);rs,rm=rainfall_tables(rain)
    event_loaded=load_file(ROOT/'data/raw/seismic-event-data/events-and-blasts.csv')
    events=typed_view(event_loaded.frame,'seismic');events['event_epoch_seconds_original']=event_loaded.frame['EventTimeEpochSeconds'];es=independent_series_summary(events,['local_magnitude','potency_m3','loc_e_m','loc_n_m','loc_u_m'])
    es['time_basis']='Interpretación Unix/UTC del encabezado; sin etiqueta sismo/voladura; no asignar evento del artículo.'
    velocity_loaded=load_file(ROOT/'data/raw/velocity-change-measurements/mean-velocity-changes.txt')
    velocity=typed_view(velocity_loaded.frame,'velocity_changes');vs=independent_series_summary(velocity,['reported_velocity_change_pct','reported_velocity_change_plus_sd_pct','reported_velocity_change_minus_sd_pct'])
    vs['description']='Cambios de velocidad sísmica según contexto del artículo; archivo sin prisma; correspondencia exacta no autenticada.'
    vs['cadence_discrepancy']='48 h 50 min observados, frente a apilamientos de dos días descritos por el artículo.'
    tables={'west_wall_summary.csv':ws,'west_wall_prism_profiles.csv':wp,'west_wall_representative_prisms.csv':wr,
            'south_west_summary.csv':ss,'south_west_prism_profiles.csv':sp,'south_west_representative_prisms.csv':sr,
            'rainfall_summary.csv':rs,'rainfall_monthly.csv':rm,'rainfall_daily_concatenated.csv':rain,
            'events_summary.csv':es,'events_records.csv':events,'seismic_velocity_summary.csv':vs,'seismic_velocity_records.csv':velocity}
    for name,frame in tables.items():write_table(frame,name)
    avail.to_csv(OUT/'west_wall_daily_availability.csv',date_format='%Y-%m-%d')
    assets=[]
    if figures:
        assets+=west_plots(west,wp,wr,avail,OUT)
        assets+=south_plots(south,sp,sr,OUT)
        assets+=rainfall_plots(rain,rm,OUT)
        assets+=events_plots(events,OUT)
        assets.append(velocity_plot(velocity,OUT))
    dictionary=[
     ('rows/observations','Conteo de registros conservados','filas','Por fuente o prisma; no número de fallas independientes'),
     ('unique_timestamps','Número de instantes distintos dentro del prisma','instantes','No se toleran duplicados'),
     ('coverage_days/observed_days','(último timestamp − primero)/86400','días','Duración, no porcentaje de continuidad'),
     ('median_interval_hours','Mediana de diferencias temporales consecutivas dentro de ID /3600','horas','No se calculan velocidades'),
     ('max_gap_hours','Máxima diferencia temporal consecutiva dentro de ID /3600','horas','Sin interpolación'),
     ('gaps_gt24h','Número de intervalos >24 h dentro del prisma','intervalos','Criterio informativo de cobertura'),
     ('coverage_insufficient','Instantes únicos <20','booleano','Mínimo operativo, no geotécnico'),
     ('std_sample','Desviación estándar muestral, ddof=1','unidad del campo','NaN para una sola medición; se usa para variabilidad descriptiva'),
     ('q1/q3','Percentiles 25/75, interpolación lineal de cuantiles','unidad del campo','No interpolación de observaciones temporales'),
     ('iqr','q3 − q1','unidad del campo','No excluye atípicos'),
     ('range','máximo − mínimo','unidad del campo','Todas las mediciones, incluidos extremos'),
     ('final_minus_initial','último valor − primero según timestamp','unidad del campo','No velocidad ni trayectoria recorrida'),
     ('increases/decreases/equals','Número de pares consecutivos con diferencia >0/<0/=0','pares','Compara observaciones adyacentes; no longitud máxima de racha'),
     ('unknown_comparisons','Pares consecutivos cuyo campo es desconocido','pares','No se salta un faltante para unir mediciones alejadas'),
     ('reported_3d_movement_mm',WEST_DESCRIPTION,'mm','Variable reportada en West Wall; no acumulación validada'),
     ('easting_diff/northing_diff/height_diff',SOUTH_DESCRIPTION,'requiere validación','Sin conversión ni norma física'),
     ('observed_rainfall_total_mm','Suma de lluvia de días medidos, sum(min_count=1)','mm','Mes incompleto: suma parcial explícita; todos desconocidos -> desconocido'),
     ('measured_days_pct/coverage_pct','100 × días medidos / días calendario','%','Solo continuidad meteorológica de calendario diario explícito'),
     ('rainy_days_observed','Días medidos con lluvia >0','días','Desconocidos no se incluyen'),
     ('zero_rain_days_observed','Días medidos con lluvia exactamente 0','días','No incluye desconocidos'),
     ('selection_groups','3 mayores conteos; 3 mayores rangos por campo; 2 menores std con ≥20; todos <20','categorías','Empates ID ascendente; sin fecha de falla'),
    ]
    write_table(pd.DataFrame(dictionary,columns=['indicator','formula_or_definition','unit','limitations']),'indicator_dictionary.csv')
    metadata={'phase':3,'checkpoint_before':'f64070e','article_doi':'10.26443/seismica.v5i1.1902',
      'article_path':'data/context/Articulo_Century_Mine_Slope_Failure_2026.pdf','article_pages':8,
      'article_context':'reports/documentation/article_context.md','protected_files_checked':check_protected(),
      'documentary_dates_only':{'failure_date':'2014-02-23','failure_time':'not documented','blast_local':'2014-02-11 10:40','prism_timezone':'requires validation'},
      'no_failure_date_in_selection':True,'no_velocity_acceleration':True,'no_models':True,'no_sources_joined_to_prisms':True,
      'rainfall_concat':{'source_years':[2013,2014],'aliases':{'product_code':'weather_product_code','quality_code':'rainfall_quality_code'},
                        'unknowns_preserved':True,'source_year_preserved':True,'writes_only_to_phase3':True},
      'selection':{'threshold':20,'ties':'prism_id ascending','low_variability':'sample std ddof=1; at least 20 unique timestamps',
                   'south_policy':'rank each component separately, union IDs without duplicating per-prism plots'},
      'south_units':'requiere validación','relative_component_norm':'not calculated; optional not necessary for descriptive scope',
      'table_hashes':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in [*tables,'west_wall_daily_availability.csv','indicator_dictionary.csv']},
      'figures':assets,'figure_count':len(assets),'plotly_js':'Local shared asset in interactive/; no internet required',
      'disclaimer':DISCLAIMER,'versions':{m:versions.version(m) for m in ['pandas','numpy','matplotlib','plotly']}}
    (OUT/'phase3_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    print(ws[['rows','prisms','coverage_days','reported_3d_movement_mm_min','reported_3d_movement_mm_max']].to_string(index=False),flush=True)
    print('West selected:',wr.prism_id.tolist(),flush=True);print('South selected:',sr.prism_id.tolist(),flush=True)
    print('Figures:',len(assets),'Protected files intact:',check_protected(),flush=True)

if __name__=='__main__':main()
