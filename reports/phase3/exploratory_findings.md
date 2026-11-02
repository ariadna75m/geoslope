# Resultado de la Fase 3: exploración descriptiva

## Resumen ejecutivo

Se leyó completo el artículo adjunto (8 páginas) y se prepararon **55 gráficos**, cada uno en PNG y HTML. Se analizaron fuentes por separado; únicamente se concatenaron los dos años de una misma estación meteorológica. Se preservaron los 59 archivos protegidos de Fases 1–2. No se hicieron cálculos de velocidad de desplazamiento, aceleración, modelos, niveles de atención, integración con prismas, SQLite o Streamlit.

| Fuente | Filas | Prismas / estación | Inicio | Fin | Cobertura / base temporal |
|---|---|---|---|---|---|
| West Wall | 7178 | 49 | 2013-11-20 12:41:22 | 2014-02-20 09:17:53 | 91.859 días |
| South West | 82400 | 160 | 2014-01-01 08:02:27 | 2014-08-06 06:11:33 | 216.923 días |
| Meteorología | 730 | estación 029167 | 2013-01-01 | 2014-12-31 | 723/730 días medidos |
| Eventos mixtos | 1171 | sin ID prisma | 2013-12-25 11:24:21.901587486+00:00 | 2014-03-31 15:11:36.451744080+00:00 | Unix/UTC |
| Cambios sísmicos TXT | 44 | sin ID prisma | 2013-12-25 00:25:00 | 2014-03-22 12:15:00 | 48 h 50 min entre muestras |

Los datos muestran frecuencias irregulares y cobertura desigual. Todos los prismas West Wall tienen algún hueco >24 h. South West conserva unidades pendientes. La lluvia tiene siete días desconocidos. Las observaciones son registros repetidos, no miles de fallas independientes; el artículo describe un caso real. No se estiman precisión, recall, F1 ni anticipación del MVP.

## Artículo: hechos y límites

Referencia APA 7: de Wit, T., & Snieder, R. (2026). Did they blow it? Time-lapse velocity variations during an open-pit mine slope failure using seismic noise interferometry. *Seismica, 5*(1). https://doi.org/10.26443/seismica.v5i1.1902

La tabla detallada de evidencia, geología, instrumentación, procedimientos, resultados y limitaciones está en [article_context.md](../documentation/article_context.md). El PDF se conserva en [data/context](../../data/context/Articulo_Century_Mine_Slope_Failure_2026.pdf); se leyó su contenido, no solo el nombre. El estudio describe 16 geófonos en cuatro perforaciones bajo el talud oeste y registros a 6000 Hz. Utiliza interferometría MWCS con correlaciones promediadas en períodos de dos días y reporta descenso de velocidad **sísmica** aproximadamente 12 días antes del inicio de falla; ese resultado pertenece a los autores y no se atribuye al MVP.

**Fecha de falla documentada en el artículo: 23-02-2014.** West Wall termina el 20-02-2014 a las 09:17:53: aproximadamente tres días calendario antes. No se calculó anticipación; no se documenta hora exacta de falla ni zona horaria de los prismas. **Voladura documentada en hora local; alineación temporal con prismas pendiente de validar.** El PDF informa 11-02-2014 10:40 local. No se asignó a un registro del catálogo ni a una medición de prisma.

Diferencias preservadas: el artículo presenta correlaciones/figuras hasta 31-03-2014; el TXT adjunto termina 22-03-2014 y tiene cadencia de 48 h 50 min, distinta del promedio de dos días descrito. El ZIP no incluye ondas continuas/correlaciones para repetir la interferometría. El PDF especifica “north-east Queensland”, atribución documental no contrastada geográficamente. Ni su radar LOS en mm ni la licencia CC BY del artículo validan las unidades de South West o la licencia del ZIP. La procedencia exacta del subconjunto frente al depósito Zenodo no se autenticó.

| Afirmación | Evidencia | Nivel de certeza | Uso permitido |
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
| Lluvia o voladura causó movimiento | No se hizo integración ni estudio causal | No establecido | No atribuir causalidad |

La [adenda documental](../documentation/phase1_phase2_documentation_update.md) registra qué dudas anteriores resuelve el artículo sin sobrescribir informes históricos.

## West Wall: cobertura y estadísticas

**Movimiento 3D reportado en milímetros respecto a la referencia indicada en el archivo. No se asume que sea una trayectoria acumulativa estrictamente creciente.** Se conservan todos los extremos; las disminuciones no se eliminan ni se tratan automáticamente como errores.

- 7178 filas; 49 prismas; 91.858692 días entre extremos temporales.
- Entre 4 y 348 observaciones por prisma.
- Mediana de intervalos dentro de cada prisma, agrupados por observación: 8.125278 horas. Mayor hueco: 357.168056 horas (14.882 días).
- 2 prismas con <20 instantes; 49 con algún hueco >24 h; 0 intervalos cero.
- 3755 aumentos, 3370 disminuciones y 4 iguales entre pares adyacentes; 0 comparaciones desconocidas. Se cuentan pares, no longitudes máximas de racha.

| Indicador | reported_3d_movement_mm |
|---|---|
| Mínimo | 0 |
| Máximo | 3243.66 |
| Media | 29.97 |
| Mediana | 18.6522 |
| Desviación muestral | 116.329 |
| Cuartil 1 | 12.1861 |
| Cuartil 3 | 28.8674 |
| Rango intercuartílico | 16.6814 |
| Rango total | 3243.66 |

Se observó máximo 3243,655339 mm, muy superior a la mediana. El histograma y boxplot conservan ese rango completo; para ver las mediciones cercanas a la mediana se puede ampliar el HTML. Su significado requiere revisar referencia, instrumentación y trazabilidad; el extremo no se convierte en diagnóstico ni se elimina.

Los perfiles de cada prisma incluyen fecha inicial/final, número de instantes, duración, mediana del intervalo, máximo hueco, aumentos/disminuciones/iguales, primer y último valor, diferencia final−inicial, estadística y cobertura insuficiente. Véase [perfiles completos](west_wall_prism_profiles.csv). La disponibilidad diaria mide observaciones por día; cero significa ausencia de medición, no movimiento cero. No se calculó un porcentaje de continuidad para frecuencias de prisma no uniformes.

## Selección representativa reproducible

Se eligen tres mayores conteos; tres mayores rangos por variable; dos menores desviaciones estándar **muestrales, ddof=1**, entre prismas con ≥20 instantes únicos; todos los de <20. Empates por ID ascendente. Si un prisma entra en varios grupos, conserva todas sus etiquetas pero tiene un solo gráfico. La fecha de falla no participa. Los grupos son descriptivos y no clasifican estabilidad geomecánica.

### West Wall: 10 prismas distintos

| prism_id | observations | selection_groups |
|---|---|---|
| 22-1917 | 142 | menor_desviacion_muestral:reported_3d_movement_mm |
| 30-1994 | 35 | mayor_rango:reported_3d_movement_mm |
| 30-1995 | 4 | cobertura_insuficiente |
| 31-1930 | 17 | cobertura_insuficiente |
| 31-2007 | 348 | mayor_numero_observaciones |
| 31-2010 | 70 | mayor_rango:reported_3d_movement_mm |
| 36-1969 | 343 | mayor_numero_observaciones |
| 40-1928 | 333 | mayor_numero_observaciones |
| 40-1933 | 332 | menor_desviacion_muestral:reported_3d_movement_mm |
| 40-1938 | 326 | mayor_rango:reported_3d_movement_mm |

Cobertura de los dos prismas insuficientes:

| prism_id | observations | first_timestamp | last_timestamp | observed_days | max_gap_hours |
|---|---|---|---|---|---|
| 30-1995 | 4 | 2013-11-20 15:49:21 | 2013-11-28 22:32:23 | 8.27988 | 178.759 |
| 31-1930 | 17 | 2013-11-20 20:31:19 | 2013-12-08 03:08:37 | 17.2759 | 79.3456 |

El mayor rango de 30-1994 pertenece a su período propio, no a una selección retrospectiva alrededor de la falla. No todos los prismas abarcan las mismas fechas.

### South West: 20 prismas distintos

La selección por rango y baja desviación se realiza **por separado en cada componente**, después se toma la unión de IDs; no se fuerza una escala conjunta.

| prism_id | observations | selection_groups |
|---|---|---|
| 24-1115 | 10 | cobertura_insuficiente |
| 31-1464 | 78 | menor_desviacion_muestral:northing_diff |
| 31-1478 | 188 | mayor_rango:easting_diff |
| 31-1481 | 14 | cobertura_insuficiente |
| 31-1499 | 155 | mayor_rango:height_diff |
| 31-1500 | 614 | mayor_rango:easting_diff;mayor_rango:height_diff |
| 31-1502 | 452 | mayor_rango:northing_diff;mayor_rango:height_diff |
| 31-1504 | 34 | menor_desviacion_muestral:northing_diff |
| 31-1530 | 1049 | mayor_rango:easting_diff |
| 31-1608 | 1 | cobertura_insuficiente |
| 31-1633 | 37 | menor_desviacion_muestral:easting_diff |
| 31-1867 | 1075 | mayor_rango:northing_diff |
| 31-1868 | 863 | mayor_rango:northing_diff |
| 31-1871 | 7 | cobertura_insuficiente |
| 31-1910 | 1560 | mayor_numero_observaciones |
| 31-1911 | 1577 | mayor_numero_observaciones |
| 31-1913 | 1575 | mayor_numero_observaciones |
| 31-1957 | 86 | menor_desviacion_muestral:easting_diff |
| 31-2132 | 274 | menor_desviacion_muestral:height_diff |
| 40-1934 | 63 | menor_desviacion_muestral:height_diff |

## South West: fuente independiente

**Valores relativos reportados; unidad pendiente de validación.** En el diccionario las unidades siguen “requiere validación”. No se suma a West Wall ni se compara directamente su escala; el DAT no añade observaciones y la norma matemática opcional no se calculó por no ser necesaria en esta fase.

- 82400 observaciones, 160 prismas; 2014-01-01 08:02:27 → 2014-08-06 06:11:33; 216.922986 días.
- Conteos por prisma 1–1577; 4 con <20 instantes; 158 con huecos >24 h.
- Mediana agrupada de intervalos 4.011389 h; mayor hueco 1932.479722 h (80.520 días); 0 intervalos cero.

| Indicador | easting_diff | northing_diff | height_diff |
|---|---|---|---|
| Mínimo | -231.902 | -8277.33 | -14376.5 |
| Máximo | 18255.7 | 269.86 | 2770.66 |
| Media | 997.767 | -298.257 | -374.006 |
| Mediana | 61 | -10.3441 | -23.1253 |
| Desviación muestral | 2543.06 | 1066.96 | 1628.11 |
| Cuartil 1 | 10.7 | -83.0672 | -96.5917 |
| Cuartil 3 | 220.388 | 13.7 | 4.2 |
| Rango intercuartílico | 209.688 | 96.7672 | 100.792 |
| Rango total | 18487.6 | 8547.19 | 17147.2 |

Prismas con cobertura insuficiente:

| prism_id | observations | first_timestamp | last_timestamp | observed_days | max_gap_hours |
|---|---|---|---|---|---|
| 24-1115 | 10 | 2014-01-04 02:34:07 | 2014-06-06 01:18:39 | 152.948 | 1932.48 |
| 31-1481 | 14 | 2014-01-01 15:15:38 | 2014-01-21 08:40:44 | 19.7258 | 233.602 |
| 31-1608 | 1 | 2014-01-02 18:49:51 | 2014-01-02 18:49:51 | 0 | desconocido / no definido |
| 31-1871 | 7 | 2014-01-10 00:03:09 | 2014-01-24 23:40:33 | 14.9843 | 203.126 |

Se observan componentes con valores positivos y negativos, rangos desiguales y series con saltos o huecos. No se atribuye su origen. El prisma con una sola observación no tiene desviación estándar muestral ni intervalo definibles; su rango observado cero no implica estabilidad. Los tres componentes y valores inicial/final por cada prisma están en [perfiles South West](south_west_prism_profiles.csv).

## Meteorología

Se concatenaron copias analíticas de 2013 y 2014 de la estación **029167**, ordenadas por timestamp, sin unirlas a prismas. Se conservaron año de origen (`source_year`), identificador, fecha original y todas las columnas `original__*`. Se renombran solo en esta copia `product_code` → `weather_product_code`, `quality_code` → `rainfall_quality_code`; se preservan `rainfall_period_days` y `rainfall_mm`.

Calendario: 730 días; 723 medidos (99.041096 %); 7 mediciones desconocidas; 0 fechas sin fila. Se observó lluvia >0 en 93 días y exactamente 0 medido en 630; los desconocidos no forman parte de ninguno de esos grupos.

Fechas desconocidas: **2013-03-08, 2013-10-07, 2013-12-29, 2014-08-17, 2014-09-17, 2014-10-09, 2014-12-18**.

| Indicador | Lluvia reportada (mm) |
|---|---|
| Mínimo | 0 |
| Máximo | 115 |
| Media de días medidos | 1.22849 |
| Mediana | 0 |
| Cuartil 1 | 0 |
| Cuartil 3 | 0 |

Totales mensuales y cobertura (sumas de días medidos; desconocido si todos son desconocidos). Hay 7 meses incompletos, marcados en amarillo. Un total parcial 0 mm no demuestra ausencia de lluvia en el día desconocido. El código de calidad se conserva, pero su interpretación y el cierre horario diario requieren validación.

| month | measured_days | missing_days | rainy_days_observed | observed_rainfall_total_mm | warning |
|---|---|---|---|---|---|
| 2013-01 | 31 | 0 | 5 | 44.8 | Total de días observados del mes completo |
| 2013-02 | 28 | 0 | 5 | 65.6 | Total de días observados del mes completo |
| 2013-03 | 30 | 1 | 6 | 10 | Total parcial: días desconocidos; no imputados |
| 2013-04 | 30 | 0 | 1 | 0.2 | Total de días observados del mes completo |
| 2013-05 | 31 | 0 | 3 | 1 | Total de días observados del mes completo |
| 2013-06 | 30 | 0 | 0 | 0 | Total de días observados del mes completo |
| 2013-07 | 31 | 0 | 1 | 0.2 | Total de días observados del mes completo |
| 2013-08 | 31 | 0 | 0 | 0 | Total de días observados del mes completo |
| 2013-09 | 30 | 0 | 0 | 0 | Total de días observados del mes completo |
| 2013-10 | 30 | 1 | 0 | 0 | Total parcial: días desconocidos; no imputados |
| 2013-11 | 30 | 0 | 4 | 8.2 | Total de días observados del mes completo |
| 2013-12 | 30 | 1 | 8 | 46.4 | Total parcial: días desconocidos; no imputados |
| 2014-01 | 31 | 0 | 16 | 169.8 | Total de días observados del mes completo |
| 2014-02 | 28 | 0 | 17 | 362.8 | Total de días observados del mes completo |
| 2014-03 | 31 | 0 | 3 | 26.8 | Total de días observados del mes completo |
| 2014-04 | 30 | 0 | 2 | 9.8 | Total de días observados del mes completo |
| 2014-05 | 31 | 0 | 1 | 0.2 | Total de días observados del mes completo |
| 2014-06 | 30 | 0 | 1 | 1 | Total de días observados del mes completo |
| 2014-07 | 31 | 0 | 0 | 0 | Total de días observados del mes completo |
| 2014-08 | 30 | 1 | 0 | 0 | Total parcial: días desconocidos; no imputados |
| 2014-09 | 29 | 1 | 0 | 0 | Total parcial: días desconocidos; no imputados |
| 2014-10 | 30 | 1 | 0 | 0 | Total parcial: días desconocidos; no imputados |
| 2014-11 | 30 | 0 | 9 | 55.4 | Total de días observados del mes completo |
| 2014-12 | 30 | 1 | 11 | 86 | Total parcial: días desconocidos; no imputados |

No se imputaron ceros, distribuyeron acumulados de varios días, interpolaron huecos ni afirmó causalidad con movimientos.

## Catálogo de eventos: resumen separado

1171 registros; 2013-12-25 11:24:21.901587486+00:00 → 2014-03-31 15:11:36.451744080+00:00. Timestamps interpretados desde Unix/UTC; el campo epoch original se conserva en `events_records.csv` para auditar precisión y representación. La conversión de epoch decimal a punto flotante puede reflejar redondeo de subsegundos; no implica resolución física nanométrica del tiempo.

| Campo | Mínimo | Máximo |
|---|---|---|
| local_magnitude | -4.5 | 2.4 |
| potency_m3 | 2.21e-05 | 61 |
| loc_e_m | 45626.5 | 49738.2 |
| loc_n_m | 24694.9 | 28966 |
| loc_u_m | -4025.1 | 1487.3 |

El archivo mezcla eventos y voladuras sin etiqueta de tipo. `Potency [m3]` es la magnitud reportada del encabezado, no potencia en vatios; su definición operacional requiere validación. Las coordenadas en metros reportadas por este catálogo no resuelven CRS/datum ni unidades de prismas. Se conserva el rango completo de coordenadas; una coordenada negativa no se clasifica como imposible sin datum. El gráfico espacial PNG es en planta y el HTML muestra tres componentes. No se identifica la voladura del artículo por magnitud ni por proximidad temporal.

## TXT: cambios de velocidad sísmica

44 observaciones; 2013-12-25 00:25:00 → 2014-03-22 12:15:00; todos los intervalos observados son 48.833333 h (48 h 50 min). Rango de cambios: -0.515822067 % a 0.194551691 %. Banda superior: -0.207052653 a 0.410757265 %; inferior: -0.828260257 a 0.000000000 %.

No tiene ID de prisma. El contexto del artículo identifica cambios de velocidad sísmica; la correspondencia exacta de esta tabla no se autenticó. Las bandas se muestran tal como se reportan, sin reconstruir intervalos de confianza, error del MVP ni etiquetas de falla. No es velocidad de desplazamiento superficial. Se conserva la discrepancia con la frecuencia y cobertura del artículo.

## Gráficos entregados y lectura

55 pares PNG/HTML: West Wall 18, South West 27, meteorología 5, eventos 4, TXT 1. Los prismas de cobertura insuficiente están incluidos en las series seleccionadas, sin duplicar gráficos. Los segmentos de línea unen observaciones para lectura; no se escriben mediciones interpoladas. South West muestra la unidad pendiente; el diagrama West Wall utiliza primeras posiciones observadas por prisma y advierte: “Las coordenadas, CRS y datum requieren validación. El gráfico representa posiciones relativas del conjunto”.

Abra [Exploracion_Fase3.html](Exploracion_Fase3.html) para una síntesis con cinco gráficos integrados. La carpeta `interactive/` incluye una copia local de Plotly JS; todos los gráficos funcionan sin internet tras descomprimir el paquete. PNG muestra todas las observaciones; HTML permite ampliar y consultar valores. El inventario siguiente enlaza todas las figuras:

| Figura | PNG | Interactiva |
|---|---|---|
| West Wall: observaciones por prisma | [PNG](figures/west_observations.png) | [HTML](interactive/west_observations.html) |
| West Wall: distribución del movimiento reportado | [PNG](figures/west_distribution.png) | [HTML](interactive/west_distribution.html) |
| West Wall: distribución por prisma; valores extremos conservados | [PNG](figures/west_boxplot.png) | [HTML](interactive/west_boxplot.html) |
| West Wall: prisma 22-1917 | [PNG](figures/west_series_22_1917.png) | [HTML](interactive/west_series_22_1917.html) |
| West Wall: prisma 30-1994 | [PNG](figures/west_series_30_1994.png) | [HTML](interactive/west_series_30_1994.html) |
| West Wall: prisma 30-1995; cobertura insuficiente (<20) | [PNG](figures/west_series_30_1995.png) | [HTML](interactive/west_series_30_1995.html) |
| West Wall: prisma 31-1930; cobertura insuficiente (<20) | [PNG](figures/west_series_31_1930.png) | [HTML](interactive/west_series_31_1930.html) |
| West Wall: prisma 31-2007 | [PNG](figures/west_series_31_2007.png) | [HTML](interactive/west_series_31_2007.html) |
| West Wall: prisma 31-2010 | [PNG](figures/west_series_31_2010.png) | [HTML](interactive/west_series_31_2010.html) |
| West Wall: prisma 36-1969 | [PNG](figures/west_series_36_1969.png) | [HTML](interactive/west_series_36_1969.html) |
| West Wall: prisma 40-1928 | [PNG](figures/west_series_40_1928.png) | [HTML](interactive/west_series_40_1928.html) |
| West Wall: prisma 40-1933 | [PNG](figures/west_series_40_1933.png) | [HTML](interactive/west_series_40_1933.html) |
| West Wall: prisma 40-1938 | [PNG](figures/west_series_40_1938.png) | [HTML](interactive/west_series_40_1938.html) |
| West Wall: disponibilidad diaria por prisma | [PNG](figures/west_availability.png) | [HTML](interactive/west_availability.html) |
| West Wall: comparación entre primera y última observación | [PNG](figures/west_initial_final.png) | [HTML](interactive/west_initial_final.html) |
| West Wall: rango observado por prisma | [PNG](figures/west_range.png) | [HTML](interactive/west_range.html) |
| West Wall: posiciones relativas de la primera observación por prisma | [PNG](figures/west_spatial.png) | [HTML](interactive/west_spatial.html) |
| West Wall: límite de observaciones y fecha documental de falla | [PNG](figures/west_documentary_dates.png) | [HTML](interactive/west_documentary_dates.html) |
| South West: observaciones por prisma — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_observations.png) | [HTML](interactive/south_observations.html) |
| South West: distribución de easting_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_distribution_easting_diff.png) | [HTML](interactive/south_distribution_easting_diff.html) |
| South West: rango por prisma de easting_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_range_easting_diff.png) | [HTML](interactive/south_range_easting_diff.html) |
| South West: distribución de northing_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_distribution_northing_diff.png) | [HTML](interactive/south_distribution_northing_diff.html) |
| South West: rango por prisma de northing_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_range_northing_diff.png) | [HTML](interactive/south_range_northing_diff.html) |
| South West: distribución de height_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_distribution_height_diff.png) | [HTML](interactive/south_distribution_height_diff.html) |
| South West: rango por prisma de height_diff — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_range_height_diff.png) | [HTML](interactive/south_range_height_diff.html) |
| South West: prisma 24-1115 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_24_1115.png) | [HTML](interactive/south_series_24_1115.html) |
| South West: prisma 31-1464 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1464.png) | [HTML](interactive/south_series_31_1464.html) |
| South West: prisma 31-1478 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1478.png) | [HTML](interactive/south_series_31_1478.html) |
| South West: prisma 31-1481 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1481.png) | [HTML](interactive/south_series_31_1481.html) |
| South West: prisma 31-1499 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1499.png) | [HTML](interactive/south_series_31_1499.html) |
| South West: prisma 31-1500 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1500.png) | [HTML](interactive/south_series_31_1500.html) |
| South West: prisma 31-1502 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1502.png) | [HTML](interactive/south_series_31_1502.html) |
| South West: prisma 31-1504 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1504.png) | [HTML](interactive/south_series_31_1504.html) |
| South West: prisma 31-1530 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1530.png) | [HTML](interactive/south_series_31_1530.html) |
| South West: prisma 31-1608 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1608.png) | [HTML](interactive/south_series_31_1608.html) |
| South West: prisma 31-1633 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1633.png) | [HTML](interactive/south_series_31_1633.html) |
| South West: prisma 31-1867 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1867.png) | [HTML](interactive/south_series_31_1867.html) |
| South West: prisma 31-1868 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1868.png) | [HTML](interactive/south_series_31_1868.html) |
| South West: prisma 31-1871 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1871.png) | [HTML](interactive/south_series_31_1871.html) |
| South West: prisma 31-1910 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1910.png) | [HTML](interactive/south_series_31_1910.html) |
| South West: prisma 31-1911 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1911.png) | [HTML](interactive/south_series_31_1911.html) |
| South West: prisma 31-1913 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1913.png) | [HTML](interactive/south_series_31_1913.html) |
| South West: prisma 31-1957 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_1957.png) | [HTML](interactive/south_series_31_1957.html) |
| South West: prisma 31-2132 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_31_2132.png) | [HTML](interactive/south_series_31_2132.html) |
| South West: prisma 40-1934 — Valores relativos reportados; unidad pendiente de validación | [PNG](figures/south_series_40_1934.png) | [HTML](interactive/south_series_40_1934.html) |
| Meteorología: serie diaria y fechas desconocidas | [PNG](figures/rainfall_daily.png) | [HTML](interactive/rainfall_daily.html) |
| Meteorología: distribución de días medidos | [PNG](figures/rainfall_distribution.png) | [HTML](interactive/rainfall_distribution.html) |
| Meteorología: totales observados por mes | [PNG](figures/rainfall_monthly.png) | [HTML](interactive/rainfall_monthly.html) |
| Meteorología: días lluviosos observados por mes | [PNG](figures/rainfall_rainy_days.png) | [HTML](interactive/rainfall_rainy_days.html) |
| Meteorología: siete fechas con lluvia desconocida | [PNG](figures/rainfall_missing_dates.png) | [HTML](interactive/rainfall_missing_dates.html) |
| Catálogo mixto: distribución de magnitud local | [PNG](figures/events_distribution_local_magnitude.png) | [HTML](interactive/events_distribution_local_magnitude.html) |
| Catálogo mixto: distribución de Potency reportada | [PNG](figures/events_distribution_potency_m3.png) | [HTML](interactive/events_distribution_potency_m3.html) |
| Catálogo mixto: fechas y magnitud, interpretación Unix/UTC | [PNG](figures/events_timeline.png) | [HTML](interactive/events_timeline.html) |
| Catálogo mixto: cobertura espacial; CRS/datum pendientes | [PNG](figures/events_spatial.png) | [HTML](interactive/events_spatial.html) |
| TXT: cambio de velocidad sísmica y bandas reportadas | [PNG](figures/seismic_velocity_series.png) | [HTML](interactive/seismic_velocity_series.html) |

## Pruebas, ejecución e integridad

Resultado de toda la suite: **75 passed in 11.36s**. Se conservan [salida de pytest](pytest-output.txt) y [JUnit XML](pytest-results.xml). Las 14 pruebas nuevas cubren orden de entrada, ejemplos numéricos, puntos únicos, escasa cobertura, intervalos cero, selección y empates, faltantes, lluvia desconocida, totales parciales, unidades pendientes, gráficos y protección de originales/salidas anteriores. Las 61 pruebas previas también pasaron.

Notebook: **10 celdas de código ejecutadas, 0 errores**; [registro](notebook_execution.json). El arranque convencional de un kernel Jupyter fue bloqueado por puertos TCP en este entorno. El ejecutor suministrado usa IPython en un único proceso local y registra salidas reales en el notebook. No presenta el intento fallido como una ejecución exitosa de Jupyter convencional. El notebook importa las funciones de `src/` y no duplica el procesamiento.

Reproducción completa: True para 15 tablas CSV, comparadas SHA-256 antes/después de repetir el pipeline. Integridad: 59 archivos de Fases 1–2, incluidos ocho originales y 32 salidas procesadas, sin cambios. Detalles y validación de las 55 imágenes/HTML en [reproducibility.json](reproducibility.json) y [phase3_metadata.json](phase3_metadata.json).

Punto de control previo: `f64070e`. El commit final se registra en `git_checkpoint.txt`, entregado junto al proyecto. Se revisan diferencias y espacios con `git diff --check` antes de cerrar.

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

Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
