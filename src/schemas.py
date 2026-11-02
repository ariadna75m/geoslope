"""Esquemas explícitos basados en los encabezados inspeccionados en Fase 1."""
from dataclasses import dataclass
import re

MOVEMENT_DESCRIPTION = ('Movimiento 3D reportado en milímetros respecto a la referencia indicada en el encabezado. '
                        'No se asume que sea una trayectoria acumulativa estrictamente creciente')
PENDING = 'requiere validación'

@dataclass(frozen=True)
class Schema:
    kind: str
    columns: dict[str, str]
    numeric: tuple[str, ...]
    keys: tuple[str, ...]
    units: dict[str, str]
    description: str
    time_basis: str = 'Zona horaria requiere validación; no se aplica conversión.'

WEST = {'Prism':'prism_id','Date':'date_original','Time':'time_original','Easting':'easting',
        'Northing':'northing','RL':'rl','Cumulative 3D Movement (mm) Since 20th Nov':'reported_3d_movement_mm'}
SOUTH = {'Prism':'prism_id','Date':'date_original','Time':'time_original','Easting':'easting',
         'Northing':'northing','Height':'height','Adjusted Distance Diff':'adjusted_distance_diff',
         'Unadjusted Slope Distance Diff':'unadjusted_slope_distance_diff','Easting Diff':'easting_diff',
         'Northing Diff':'northing_diff','Height Diff':'height_diff'}
DAT = {'prism_part_1':'prism_part_1','prism_part_2':'prism_part_2',
       **{x:x for x in ['day','month','year','hour','minute','second']},
       **{k:v for k,v in SOUTH.items() if k not in ['Prism','Date','Time']}}
RAIN = {'Product code':'product_code','Bureau of Meteorology station number':'station_id',
        'Year':'year','Month':'month','Day':'day','Rainfall amount (millimetres)':'rainfall_mm',
        'Period over which rainfall was measured (days)':'rainfall_period_days','Quality':'quality_code'}
EVENTS = {'#Index':'event_id','EventTimeEpochSeconds':'event_epoch_seconds','Local Magnitude':'local_magnitude',
          'Potency [m^3]':'potency_m3','LocE [m]':'loc_e_m','LocN [m]':'loc_n_m','LocU [m]':'loc_u_m'}
VELOCITY = {'Date':'date_original','Velocity Change (%)':'reported_velocity_change_pct',
            'Velocity Change plus Standard Deviation (%)':'reported_velocity_change_plus_sd_pct',
            'Velocity Change minus Standard Deviation (%)':'reported_velocity_change_minus_sd_pct'}

def make_schema(kind, columns, numeric, keys, units, description, **kwargs):
    return Schema(kind, columns, tuple(numeric), tuple(keys), units, description, **kwargs)

SCHEMAS = {
 'west_wall': make_schema('west_wall',WEST,list(WEST.values())[3:],['prism_id','timestamp'],
                         {**{x:PENDING for x in ['easting','northing','rl']},'reported_3d_movement_mm':'mm (explícito en encabezado)'},MOVEMENT_DESCRIPTION),
 'south_west': make_schema('south_west',SOUTH,list(SOUTH.values())[3:],['prism_id','timestamp'],
                          {x:PENDING for x in list(SOUTH.values())[3:]},'Diferencias y coordenadas reportadas sin unidades documentadas; no se convierten.'),
 'slope_dat': make_schema('slope_dat',DAT,list(SOUTH.values())[3:],['prism_id','timestamp'],
                         {x:PENDING for x in list(SOUTH.values())[3:]},'Representación alternativa de South West; no sumar como fuente independiente.'),
 'rainfall': make_schema('rainfall',RAIN,['year','month','day','rainfall_mm','rainfall_period_days'],['station_id','timestamp'],
                        {'rainfall_mm':'mm (explícito en encabezado)','rainfall_period_days':'días (explícito en encabezado)'},
                        'Precipitación reportada; ausencias desconocidas, código N requiere validación.',
                        time_basis='Fecha calendario de la medición; hora de cierre y disponibilidad requieren validación.'),
 'seismic': make_schema('seismic',EVENTS,list(EVENTS.values())[1:],['timestamp'],
                       {'event_epoch_seconds':'s (según encabezado)','local_magnitude':PENDING,'potency_m3':'m³','loc_e_m':'m','loc_n_m':'m','loc_u_m':'m'},
                       'Catálogo mixto sin etiqueta sismo/voladura; referencia de coordenadas requiere validación.',
                       time_basis='Interpretación Unix UTC del encabezado; exportación requiere validación.'),
 'velocity_changes': make_schema('velocity_changes',VELOCITY,list(VELOCITY.values())[1:],['timestamp'],
                                {x:'% (encabezado); tipo de velocidad requiere validación' for x in list(VELOCITY.values())[1:]},
                                'Cambio de velocidad de tipo no documentado, sin ID de prisma; no usar como velocidad de desplazamiento.')
}

def clean_header(value):
    return re.sub(r'\s+', ' ', str(value).lstrip('\ufeff').strip())

def normalized_name(value):
    return re.sub(r'[^a-z0-9]+','_',clean_header(value).lower()).strip('_')

def get_schema(kind):
    if kind not in SCHEMAS:
        raise ValueError('Tipo de fuente no reconocido: '+str(kind))
    return SCHEMAS[kind]

def infer_kind(columns):
    names={clean_header(c) for c in columns}
    matches=[kind for kind,schema in SCHEMAS.items() if set(schema.columns).issubset(names)]
    if len(matches)==1: return matches[0]
    return None

def column_mapping(columns,kind):
    schema=get_schema(kind)
    mapping={c:schema.columns.get(clean_header(c), normalized_name(c)) for c in columns}
    if len(set(mapping.values()))!=len(mapping):
        raise ValueError('La normalización produciría nombres de columna repetidos.')
    return mapping
