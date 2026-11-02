"""Construye el informe descriptivo desde las tablas auditadas de Fase 3."""
from pathlib import Path
import sys,json,re,html
import pandas as pd
from plotly.offline import get_plotlyjs
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.exploratory_analysis import DISCLAIMER,WEST_DESCRIPTION,SOUTH_DESCRIPTION
OUT=ROOT/'reports/phase3'


def table(frame):
    def cell(v):
        if pd.isna(v):return 'desconocido / no definido'
        if isinstance(v,float):return f'{v:.6g}'
        return str(v).replace('|',' / ').replace('\n',' ')
    lines=['| '+' | '.join(map(str,frame.columns))+' |','|'+'|'.join(['---']*len(frame.columns))+'|']
    return '\n'.join(lines+['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])


def statistics(summary,columns):
    names={'min':'Mínimo','max':'Máximo','mean':'Media','median':'Mediana','std_sample':'Desviación muestral','q1':'Cuartil 1','q3':'Cuartil 3','iqr':'Rango intercuartílico','range':'Rango total'}
    return pd.DataFrame([{'Indicador':label,**{c:summary[f'{c}_{k}'] for c in columns}} for k,label in names.items()])


def main():
    def read(name):return pd.read_csv(OUT/name,dtype={'prism_id':str,'station_id':str})
    w=read('west_wall_summary.csv').iloc[0];s=read('south_west_summary.csv').iloc[0]
    r=read('rainfall_summary.csv').iloc[0];e=read('events_summary.csv').iloc[0];v=read('seismic_velocity_summary.csv').iloc[0]
    wp=read('west_wall_prism_profiles.csv');sp=read('south_west_prism_profiles.csv')
    wr=read('west_wall_representative_prisms.csv');sr=read('south_west_representative_prisms.csv');rm=read('rainfall_monthly.csv')
    metadata=json.loads((OUT/'phase3_metadata.json').read_text());notebook=json.loads((OUT/'notebook_execution.json').read_text())
    pytest=(OUT/'pytest-output.txt').read_text().strip().splitlines()[-1]
    repro=json.loads((OUT/'reproducibility.json').read_text()) if (OUT/'reproducibility.json').exists() else {}
    graph_table=pd.DataFrame([{'Figura':a['title'],'PNG':f"[PNG]({a['png']})",'Interactiva':f"[HTML]({a['html']})"} for a in metadata['figures']])
    overview=pd.DataFrame([
      ['West Wall',w['rows'],w['prisms'],w['first_timestamp'],w['last_timestamp'],f"{w['coverage_days']:.3f} días"],
      ['South West',s['rows'],s['prisms'],s['first_timestamp'],s['last_timestamp'],f"{s['coverage_days']:.3f} días"],
      ['Meteorología',r['records'],'estación 029167','2013-01-01','2014-12-31',f"{int(r['measured_days'])}/{int(r['calendar_days'])} días medidos"],
      ['Eventos mixtos',e['rows'],'sin ID prisma',e['first_timestamp'],e['last_timestamp'],'Unix/UTC'],
      ['Cambios sísmicos TXT',v['rows'],'sin ID prisma',v['first_timestamp'],v['last_timestamp'],'48 h 50 min entre muestras'],
    ],columns=['Fuente','Filas','Prismas / estación','Inicio','Fin','Cobertura / base temporal'])
    selection_columns=['prism_id','observations','selection_groups']
    timeline_columns=['prism_id','observations','first_timestamp','last_timestamp','observed_days','max_gap_hours']
    claim_table='''| Afirmación | Evidencia | Nivel de certeza | Uso permitido |
|---|---|---|---|
| Century Mine, tajo abierto, zinc/plomo/plata, Queensland, talud oeste | Artículo PDF p. 2, §2 y figura 1 | Confirmada por autores | Contexto académico, atribuido al PDF |
| 16 geófonos, cuatro perforaciones, 6000 Hz | PDF p. 3, §2 | Confirmada por autores | Descripción de instrumentación original |
| Falla el 23-02-2014 | PDF pp. 3–4 | Fecha documentada; hora no especificada | Referencia visual; no etiqueta, umbral o selección |
| Voladura 11-02-2014 10:40 local | PDF pp. 2 y 5 | Documentada; reloj de prismas pendiente | Contexto condicionado sin asignación a registros |
| Descenso sísmico aproximadamente 12 días antes de la falla | PDF pp. 1 y 6 | Resultado del estudio original | Antecedente; no anticipación del sistema |
| West Wall contiene aumentos y disminuciones | Pares adyacentes ordenados por prisma y timestamp; perfiles CSV | Observado y reproducido | Descripción de la variable reportada, no trayectoria acumulada |
| Unidad de South West | No documentada por columna; radar LOS del PDF no identifica estos campos | Requiere validación | Valores relativos sin conversión ni derivadas físicas |
| TXT es compatible con cambios de velocidad sísmica | Contexto PDF y columnas del TXT; cobertura y cadencia discrepantes | Correspondencia contextual, archivo no autenticado contra Zenodo | Serie separada; nunca velocidad de prisma |
| Siete lluvias desconocidas | Registros preservados y resumen meteorológico | Observado y reproducido | Totales mensuales parciales; no asignar cero |
| Eventos del catálogo son sismos o voladuras concretos | No hay columna de tipo ni reloj de prismas validado | No resuelto | Resumen del catálogo mixto; no clasificación ni alineación automática |
| Extremos equivalen a mediciones erróneas o inestabilidad | Estadísticas no verifican referencia, medición o estado geomecánico | No establecido | Retener registros y solicitar revisión, sin diagnóstico |
| Lluvia o voladura causó movimiento | No se hizo integración ni estudio causal | No establecido | No atribuir causalidad |'''
    text=f'''# Resultado de la Fase 3: exploración descriptiva

## Resumen ejecutivo

Se leyó completo el artículo adjunto (8 páginas) y se prepararon **{metadata['figure_count']} gráficos**, cada uno en PNG y HTML. Se analizaron fuentes por separado; únicamente se concatenaron los dos años de una misma estación meteorológica. Se preservaron los {metadata['protected_files_checked']} archivos protegidos de Fases 1–2. No se hicieron cálculos de velocidad de desplazamiento, aceleración, modelos, niveles de atención, integración con prismas, SQLite o Streamlit.

{table(overview)}

Los datos muestran frecuencias irregulares y cobertura desigual. Todos los prismas West Wall tienen algún hueco >24 h. South West conserva unidades pendientes. La lluvia tiene siete días desconocidos. Las observaciones son registros repetidos, no miles de fallas independientes; el artículo describe un caso real. No se estiman precisión, recall, F1 ni anticipación del MVP.

## Artículo: hechos y límites

Referencia APA 7: de Wit, T., & Snieder, R. (2026). Did they blow it? Time-lapse velocity variations during an open-pit mine slope failure using seismic noise interferometry. *Seismica, 5*(1). https://doi.org/10.26443/seismica.v5i1.1902

La tabla detallada de evidencia, geología, instrumentación, procedimientos, resultados y limitaciones está en [article_context.md](../documentation/article_context.md). El PDF se conserva en [data/context](../../data/context/Articulo_Century_Mine_Slope_Failure_2026.pdf); se leyó su contenido, no solo el nombre. El estudio describe 16 geófonos en cuatro perforaciones bajo el talud oeste y registros a 6000 Hz. Utiliza interferometría MWCS con correlaciones promediadas en períodos de dos días y reporta descenso de velocidad **sísmica** aproximadamente 12 días antes del inicio de falla; ese resultado pertenece a los autores y no se atribuye al MVP.

**Fecha de falla documentada en el artículo: 23-02-2014.** West Wall termina el 20-02-2014 a las 09:17:53: aproximadamente tres días calendario antes. No se calculó anticipación; no se documenta hora exacta de falla ni zona horaria de los prismas. **Voladura documentada en hora local; alineación temporal con prismas pendiente de validar.** El PDF informa 11-02-2014 10:40 local. No se asignó a un registro del catálogo ni a una medición de prisma.

Diferencias preservadas: el artículo presenta correlaciones/figuras hasta 31-03-2014; el TXT adjunto termina 22-03-2014 y tiene cadencia de 48 h 50 min, distinta del promedio de dos días descrito. El ZIP no incluye ondas continuas/correlaciones para repetir la interferometría. El PDF especifica “north-east Queensland”, atribución documental no contrastada geográficamente. Ni su radar LOS en mm ni la licencia CC BY del artículo validan las unidades de South West o la licencia del ZIP. La procedencia exacta del subconjunto frente al depósito Zenodo no se autenticó.

{claim_table}

La [adenda documental](../documentation/phase1_phase2_documentation_update.md) registra qué dudas anteriores resuelve el artículo sin sobrescribir informes históricos.

## West Wall: cobertura y estadísticas

**{WEST_DESCRIPTION}.** Se conservan todos los extremos; las disminuciones no se eliminan ni se tratan automáticamente como errores.

- {int(w['rows'])} filas; {int(w['prisms'])} prismas; {w['coverage_days']:.6f} días entre extremos temporales.
- Entre {int(w['observations_per_prism_min'])} y {int(w['observations_per_prism_max'])} observaciones por prisma.
- Mediana de intervalos dentro de cada prisma, agrupados por observación: {w['median_interval_hours']:.6f} horas. Mayor hueco: {w['max_gap_hours']:.6f} horas ({w['max_gap_hours']/24:.3f} días).
- {int(w['insufficient_prisms'])} prismas con <20 instantes; {int(w['prisms_with_gap_gt24h'])} con algún hueco >24 h; {int(w['zero_intervals'])} intervalos cero.
- {int(w['reported_3d_movement_mm_increases'])} aumentos, {int(w['reported_3d_movement_mm_decreases'])} disminuciones y {int(w['reported_3d_movement_mm_equals'])} iguales entre pares adyacentes; {int(w['reported_3d_movement_mm_unknown_comparisons'])} comparaciones desconocidas. Se cuentan pares, no longitudes máximas de racha.

{table(statistics(w,['reported_3d_movement_mm']))}

Se observó máximo 3243,655339 mm, muy superior a la mediana. El histograma y boxplot conservan ese rango completo; para ver las mediciones cercanas a la mediana se puede ampliar el HTML. Su significado requiere revisar referencia, instrumentación y trazabilidad; el extremo no se convierte en diagnóstico ni se elimina.

Los perfiles de cada prisma incluyen fecha inicial/final, número de instantes, duración, mediana del intervalo, máximo hueco, aumentos/disminuciones/iguales, primer y último valor, diferencia final−inicial, estadística y cobertura insuficiente. Véase [perfiles completos](west_wall_prism_profiles.csv). La disponibilidad diaria mide observaciones por día; cero significa ausencia de medición, no movimiento cero. No se calculó un porcentaje de continuidad para frecuencias de prisma no uniformes.

## Selección representativa reproducible

Se eligen tres mayores conteos; tres mayores rangos por variable; dos menores desviaciones estándar **muestrales, ddof=1**, entre prismas con ≥20 instantes únicos; todos los de <20. Empates por ID ascendente. Si un prisma entra en varios grupos, conserva todas sus etiquetas pero tiene un solo gráfico. La fecha de falla no participa. Los grupos son descriptivos y no clasifican estabilidad geomecánica.

### West Wall: {len(wr)} prismas distintos

{table(wr[selection_columns])}

Cobertura de los dos prismas insuficientes:

{table(wp.loc[wp.coverage_insufficient,timeline_columns])}

El mayor rango de 30-1994 pertenece a su período propio, no a una selección retrospectiva alrededor de la falla. No todos los prismas abarcan las mismas fechas.

### South West: {len(sr)} prismas distintos

La selección por rango y baja desviación se realiza **por separado en cada componente**, después se toma la unión de IDs; no se fuerza una escala conjunta.

{table(sr[selection_columns])}

## South West: fuente independiente

**{SOUTH_DESCRIPTION}.** En el diccionario las unidades siguen “requiere validación”. No se suma a West Wall ni se compara directamente su escala; el DAT no añade observaciones y la norma matemática opcional no se calculó por no ser necesaria en esta fase.

- {int(s['rows'])} observaciones, {int(s['prisms'])} prismas; {s['first_timestamp']} → {s['last_timestamp']}; {s['coverage_days']:.6f} días.
- Conteos por prisma {int(s['observations_per_prism_min'])}–{int(s['observations_per_prism_max'])}; {int(s['insufficient_prisms'])} con <20 instantes; {int(s['prisms_with_gap_gt24h'])} con huecos >24 h.
- Mediana agrupada de intervalos {s['median_interval_hours']:.6f} h; mayor hueco {s['max_gap_hours']:.6f} h ({s['max_gap_hours']/24:.3f} días); {int(s['zero_intervals'])} intervalos cero.

{table(statistics(s,['easting_diff','northing_diff','height_diff']))}

Prismas con cobertura insuficiente:

{table(sp.loc[sp.coverage_insufficient,timeline_columns])}

Se observan componentes con valores positivos y negativos, rangos desiguales y series con saltos o huecos. No se atribuye su origen. El prisma con una sola observación no tiene desviación estándar muestral ni intervalo definibles; su rango observado cero no implica estabilidad. Los tres componentes y valores inicial/final por cada prisma están en [perfiles South West](south_west_prism_profiles.csv).

## Meteorología

Se concatenaron copias analíticas de 2013 y 2014 de la estación **029167**, ordenadas por timestamp, sin unirlas a prismas. Se conservaron año de origen (`source_year`), identificador, fecha original y todas las columnas `original__*`. Se renombran solo en esta copia `product_code` → `weather_product_code`, `quality_code` → `rainfall_quality_code`; se preservan `rainfall_period_days` y `rainfall_mm`.

Calendario: {int(r['calendar_days'])} días; {int(r['measured_days'])} medidos ({r['measured_days_pct']:.6f} %); {int(r['missing_measurement_days'])} mediciones desconocidas; {int(r['absent_calendar_records'])} fechas sin fila. Se observó lluvia >0 en {int(r['rainy_days_observed'])} días y exactamente 0 medido en {int(r['zero_rain_days_observed'])}; los desconocidos no forman parte de ninguno de esos grupos.

Fechas desconocidas: **{r['missing_dates'].replace(';',', ')}**.

{table(pd.DataFrame([{'Indicador':label,'Lluvia reportada (mm)':r[k]} for k,label in [('min','Mínimo'),('max','Máximo'),('mean','Media de días medidos'),('median','Mediana'),('q1','Cuartil 1'),('q3','Cuartil 3')]]))}

Totales mensuales y cobertura (sumas de días medidos; desconocido si todos son desconocidos). Hay {int(rm.incomplete_month.sum())} meses incompletos, marcados en amarillo. Un total parcial 0 mm no demuestra ausencia de lluvia en el día desconocido. El código de calidad se conserva, pero su interpretación y el cierre horario diario requieren validación.

{table(rm[['month','measured_days','missing_days','rainy_days_observed','observed_rainfall_total_mm','warning']])}

No se imputaron ceros, distribuyeron acumulados de varios días, interpolaron huecos ni afirmó causalidad con movimientos.

## Catálogo de eventos: resumen separado

{int(e['rows'])} registros; {e['first_timestamp']} → {e['last_timestamp']}. Timestamps interpretados desde Unix/UTC; el campo epoch original se conserva en `events_records.csv` para auditar precisión y representación. La conversión de epoch decimal a punto flotante puede reflejar redondeo de subsegundos; no implica resolución física nanométrica del tiempo.

{table(pd.DataFrame([{'Campo':c,'Mínimo':e[c+'_min'],'Máximo':e[c+'_max']} for c in ['local_magnitude','potency_m3','loc_e_m','loc_n_m','loc_u_m']]))}

El archivo mezcla eventos y voladuras sin etiqueta de tipo. `Potency [m3]` es la magnitud reportada del encabezado, no potencia en vatios; su definición operacional requiere validación. Las coordenadas en metros reportadas por este catálogo no resuelven CRS/datum ni unidades de prismas. Se conserva el rango completo de coordenadas; una coordenada negativa no se clasifica como imposible sin datum. El gráfico espacial PNG es en planta y el HTML muestra tres componentes. No se identifica la voladura del artículo por magnitud ni por proximidad temporal.

## TXT: cambios de velocidad sísmica

{int(v['rows'])} observaciones; {v['first_timestamp']} → {v['last_timestamp']}; todos los intervalos observados son {v['median_interval_hours']:.6f} h (48 h 50 min). Rango de cambios: {v['reported_velocity_change_pct_min']:.9f} % a {v['reported_velocity_change_pct_max']:.9f} %. Banda superior: {v['reported_velocity_change_plus_sd_pct_min']:.9f} a {v['reported_velocity_change_plus_sd_pct_max']:.9f} %; inferior: {v['reported_velocity_change_minus_sd_pct_min']:.9f} a {v['reported_velocity_change_minus_sd_pct_max']:.9f} %.

No tiene ID de prisma. El contexto del artículo identifica cambios de velocidad sísmica; la correspondencia exacta de esta tabla no se autenticó. Las bandas se muestran tal como se reportan, sin reconstruir intervalos de confianza, error del MVP ni etiquetas de falla. No es velocidad de desplazamiento superficial. Se conserva la discrepancia con la frecuencia y cobertura del artículo.

## Gráficos entregados y lectura

{metadata['figure_count']} pares PNG/HTML: West Wall 18, South West 27, meteorología 5, eventos 4, TXT 1. Los prismas de cobertura insuficiente están incluidos en las series seleccionadas, sin duplicar gráficos. Los segmentos de línea unen observaciones para lectura; no se escriben mediciones interpoladas. South West muestra la unidad pendiente; el diagrama West Wall utiliza primeras posiciones observadas por prisma y advierte: “Las coordenadas, CRS y datum requieren validación. El gráfico representa posiciones relativas del conjunto”.

Abra [Exploracion_Fase3.html](Exploracion_Fase3.html) para una síntesis con cinco gráficos integrados. La carpeta `interactive/` incluye una copia local de Plotly JS; todos los gráficos funcionan sin internet tras descomprimir el paquete. PNG muestra todas las observaciones; HTML permite ampliar y consultar valores. El inventario siguiente enlaza todas las figuras:

{table(graph_table)}

## Pruebas, ejecución e integridad

Resultado de toda la suite: **{pytest}**. Se conservan [salida de pytest](pytest-output.txt) y [JUnit XML](pytest-results.xml). Las 14 pruebas nuevas cubren orden de entrada, ejemplos numéricos, puntos únicos, escasa cobertura, intervalos cero, selección y empates, faltantes, lluvia desconocida, totales parciales, unidades pendientes, gráficos y protección de originales/salidas anteriores. Las 61 pruebas previas también pasaron.

Notebook: **{notebook['code_cells_executed']} celdas de código ejecutadas, {notebook['errors']} errores**; [registro](notebook_execution.json). El arranque convencional de un kernel Jupyter fue bloqueado por puertos TCP en este entorno. El ejecutor suministrado usa IPython en un único proceso local y registra salidas reales en el notebook. No presenta el intento fallido como una ejecución exitosa de Jupyter convencional. El notebook importa las funciones de `src/` y no duplica el procesamiento.

Reproducción completa: {repro.get('tables_identical',False)} para {repro.get('table_count','pendiente')} tablas CSV, comparadas SHA-256 antes/después de repetir el pipeline. Integridad: {metadata['protected_files_checked']} archivos de Fases 1–2, incluidos ocho originales y 32 salidas procesadas, sin cambios. Detalles y validación de las {metadata['figure_count']} imágenes/HTML en [reproducibility.json](reproducibility.json) y [phase3_metadata.json](phase3_metadata.json).

Punto de control previo: `{metadata['checkpoint_before']}`. El commit final se registra en `git_checkpoint.txt`, entregado junto al proyecto. Se revisan diferencias y espacios con `git diff --check` antes de cerrar.

## Archivos creados y modificados

Creados: `src/exploratory_analysis.py`, `src/visualizations.py`, `scripts/run_phase3.py`, `scripts/build_phase3_report.py`, `scripts/execute_phase3_notebook.py`, `scripts/verify_phase3.py`, `tests/test_exploratory_analysis.py`, `requirements-phase3.txt`, `notebooks/exploracion_fase3.ipynb`; PDF contextual conservado en `data/context/`; documentación de evidencia y adenda en `reports/documentation/`; quince tablas CSV, metadatos, informe, HTML de síntesis, 55 PNG/HTML, Plotly local y evidencias de pruebas/reproducción en `reports/phase3/`.

Modificados: `README.md` para instrucciones de Fase 3 y nueva evidencia documental; `.gitignore` para excluir del versionado los gráficos regenerables y el recibo del commit, incluidos en el paquete descargable. Se conservan intactos los módulos, los originales y los resultados de preparación de Fases 1–2. La concatenación meteorológica solo existe en la nueva salida de Fase 3.

## Calidad pendiente y limitaciones

1. Unidades, referencia y ajustes de South West, CRS/datum de coordenadas y relojes de prismas sin validar.
2. Frecuencias irregulares y huecos: la duración entre extremos no equivale a continuidad ni autorización para interpolar.
3. Desigual número de observaciones: estadística global pondera registros, no igual peso por prisma ni fallas independientes.
4. Extremos, saltos y disminuciones requieren revisión de medición/referencia; no se eliminan por magnitud.
5. Lluvia desconocida y código de calidad no resuelto; sumas de meses incompletos permanecen parciales.
6. Eventos sin etiquetas, UTC no alineado a prismas; `Potency`, CRS/datum y precisión de fechas requieren contraste documental.
7. TXT y artículo difieren en cadencia/cobertura; no hay ondas para replicar MWCS ni autenticación contra el depósito completo.
8. Caso único y ausencia de etiquetas independientes: ninguna métrica supervisada o causalidad se deriva de estas tablas.
9. Arranque de Jupyter por puertos restringido en este entorno, resuelto para este notebook con el ejecutor IPython suministrado; no altera datos.

## Recomendaciones para la Fase 4, sin implementar

Validar con documentación del export la referencia del movimiento West Wall, unidades de South West, CRS/datum y relojes. Antes de derivadas temporales, acordar tratamiento de huecos, resets y intervalos, conservar trazabilidad y verificar casos matemáticos pequeños. Trabajar por prisma y timestamp y mantener cada fuente independiente hasta documentar cualquier alineación. Aclarar cierre diario meteorológico, códigos de calidad y semántica de bandas sísmicas. La fecha de falla seguirá como antecedente documental; no participará en selección de características ni ajuste retrospectivo. Esta fase queda detenida a la espera de aprobación.

{DISCLAIMER}
'''
    (OUT/'exploratory_findings.md').write_text(text,encoding='utf-8')
    # Informe estático exportable, con figuras interactivas; no es aplicación ni requiere servidor.
    bodies=[]
    for name in ['west_availability','west_documentary_dates','south_series_31_1500','rainfall_monthly','seismic_velocity_series']:
        source=(OUT/'interactive'/f'{name}.html').read_text()
        body=re.search(r'<body>(.*)</body>',source,re.S).group(1)
        body=re.sub(r'<script[^>]+src="plotly.min.js"[^>]*></script>','',body)
        bodies.append('<section>'+body+'</section>')
    rows=''.join(f'<li><a href="{html.escape(a["html"])}">{html.escape(a["title"])}</a> · <a href="{a["png"]}">PNG</a></li>' for a in metadata['figures'])
    summary_html=overview.to_html(index=False,border=0,escape=True)
    document='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Monitoreo de taludes · Fase 3</title><style>
    body{margin:0;font:16px/1.6 Arial,sans-serif;background:#eef1f4;color:#16324f}header,main{max-width:1200px;margin:auto;padding:30px}header{padding-bottom:10px}h1{font-size:32px;margin:0}h2{font-size:23px}section,.panel{background:white;padding:20px;border-radius:8px;margin:20px 0;overflow:auto}.note{border-left:5px solid #b68412;padding:15px;background:#fff8e0}.eyebrow{color:#6f7c89;font-size:13px;letter-spacing:2px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;text-align:left;border-bottom:1px solid #e0e5ea}a{color:#13617b}li{padding:5px}.plotly-graph-div{min-width:650px}footer{padding:25px 0;color:#6f7c89}</style><script>'''+get_plotlyjs()+'''</script></head><body><header><p class="eyebrow">PROYECTO UNIVERSITARIO · EXPLORACIÓN DESCRIPTIVA</p><h1>Monitoreo de taludes</h1><p>Fase 3 · Fuentes independientes, cobertura y valores reportados.</p></header><main>'''
    document+=f'<p class="note">{html.escape(DISCLAIMER)}</p><div class="panel"><h2>Fuentes revisadas</h2>{summary_html}<p>West Wall: {html.escape(WEST_DESCRIPTION)}.</p><p>South West: {html.escape(SOUTH_DESCRIPTION)}.</p><p>La lluvia conserva siete días desconocidos; los meses en amarillo son parciales. Las 75 pruebas pasaron y las fuentes anteriores permanecen intactas.</p><p><a href="exploratory_findings.md">Informe completo</a> · <a href="../documentation/article_context.md">Artículo y evidencia</a> · <a href="west_wall_representative_prisms.csv">Selección West Wall</a> · <a href="south_west_representative_prisms.csv">Selección South West</a></p></div>'
    document+=''.join(bodies)+f'<div class="panel"><h2>Inventario de los {metadata["figure_count"]} gráficos</h2><ul>{rows}</ul><p>Las figuras enlazadas acompañan al paquete del proyecto. Esta síntesis contiene los cinco gráficos integrados y funciona sin conexión.</p></div><footer>{html.escape(DISCLAIMER)}</footer></main></body></html>'
    (OUT/'Exploracion_Fase3.html').write_text(document,encoding='utf-8')
    print('Informe Markdown y síntesis HTML generados.')

if __name__=='__main__':main()
