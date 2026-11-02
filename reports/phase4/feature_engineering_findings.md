# Fase 4: ingeniería y validación de características temporales

## 1. Resumen ejecutivo

Se generaron características retrospectivas para **7,178 registros de 49 prismas de West Wall**, conservando todas las filas y todos sus campos originales. La salida tiene **315 columnas**: 20 campos preparados de entrada y 295 columnas añadidas. Las añadidas incluyen 134 banderas de disponibilidad matemática, 134 campos numéricos, otras banderas, trazabilidad y un resumen de calidad; no son 295 variables independientes listas para un modelo.

La suite completa aprobó **113 pruebas, con 0 fallos y 0 omisiones**. Las 226 huellas protegidas permanecen intactas. Se reprodujeron byte a byte siete CSV y se verificó que modificar observaciones futuras no cambia ninguna columna pasada. No se entrenaron modelos ni se generaron alertas.

Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.

## 2. Objetivo de la fase

Preparar variables que describan el cambio observado, la tendencia local, su persistencia y la diferencia respecto al historial anterior de cada prisma. También se indica cuándo falta información para calcularlas. La definición vigente del producto es: «Sistema inteligente de alerta temprana que identifica patrones anómalos en el desplazamiento de taludes y genera alertas para apoyar la evaluación del ingeniero geomecánico». Esta fase prepara los datos para ese objetivo; todavía no implementa alertas.

| Elemento | Ejemplo | Interpretación permitida | Conclusión todavía no permitida |
| --- | --- | --- | --- |
| Dato original | `reported_3d_movement_mm`, `original__reported_3d_movement_mm` | Valor numérico preparado y texto original de una medición | Trayectoria siempre creciente |
| Característica | `movement_rate_mm_per_day` | Tasa entre dos valores reportados consecutivos | Velocidad física validada del talud |
| Bandera de calidad | `is_gap_over_72h` | Existen más de 72 horas entre mediciones | Inestabilidad o alerta geotécnica |
| Comparación histórica | `historical_robust_z_score` | Distancia estadística respecto al historial previo | Probabilidad de colapso |
| Tendencia | `local_trend_72h_slope_mm_per_day` | Pendiente estadística dentro de una ventana pasada | Predicción de movimiento futuro |

## 3. Fuentes utilizadas y excluidas

La ingeniería utiliza exclusivamente `data/processed/west_wall/data.csv`, preparado en Fase 2 a partir de `West Wall Prism Movements - 3 months to 20-Feb-14.csv`. Su cobertura es **2013-11-20 12:41:22 a 2014-02-20 09:17:53**. `reported_3d_movement_mm` conserva el movimiento 3D reportado en milímetros respecto a la referencia indicada en el archivo. No se asume que sea una trayectoria acumulativa estrictamente creciente.

South West permanece separado; `easting_diff`, `northing_diff` y `height_diff` siguen con unidades «requiere validación». No se convierten a milímetros ni se calculan tasas físicas para esa fuente. También permanecen separados los años meteorológicos, catálogo de eventos, posibles voladuras y TXT de cambios de velocidad sísmica. El TXT describe otra magnitud y no se reutiliza como desplazamiento de prismas. No se convierten coordenadas a latitud/longitud; sus unidades no documentadas continúan pendientes.

El artículo de de Wit y Snieder documenta una falla el 23-02-2014, posterior al término de West Wall el 20-02-2014. Esa fecha es contexto externo, no una etiqueta de esta tabla. No aparece en el módulo ni en la configuración de características y no interviene en ventanas, criterios o selección de parámetros. Los precursores sísmicos estudiados por los autores no son resultados obtenidos por este MVP. Véanse [contexto del artículo](../documentation/article_context.md) y el PDF preservado en `data/context/`.

Referencia APA 7: de Wit, T., & Snieder, R. (2026). Did they blow it? Time-lapse velocity variations during an open-pit mine slope failure using seismic noise interferometry. *Seismica, 5*(1). https://doi.org/10.26443/seismica.v5i1.1902

## 4. Reglas contra fuga de información

Cada prisma se ordena por `timestamp`. Una fila usa su observación actual y exclusivamente sus propias observaciones anteriores. Las ventanas tienen límite inferior **abierto** y superior **cerrado**: **(t−W, t]**, con W=24, 72 o 168 horas. No hay ventanas centradas, relleno futuro, escalado global ni parámetros elegidos a partir de la fecha de falla.

La línea base expansiva utiliza **[inicio, t)**: excluye la observación actual. Los conteos previos no incorporan otras series. La disponibilidad también se calcula en ese instante; no se completa usando datos posteriores. Los resúmenes de cambios/tasas dentro de una ventana exigen que **ambos timestamps del par estén dentro de ella**. Un par que cruza el límite inferior queda fuera del resumen móvil, pero su cambio y tasa individuales se conservan en la fila.

Esta implementación procesa prefijos retrospectivos en memoria y reproduce la llegada de observaciones una a una. No implementa todavía un servicio de ingesta ni un almacenamiento incremental de estados.

## 5. Tratamiento de frecuencias irregulares

Se utilizan diferencias reales de tiempo en horas/días. No se remuestrea, interpola, imputa, alisa ni altera el movimiento original. Primera fila sin antecedente: intervalo, cambio y tasa desconocidos. Un timestamp duplicado por prisma bloquea la ingeniería con un mensaje de revisión; no elimina ni fusiona filas. West Wall activo tiene cero duplicados e intervalos cero.

Hay **845 intervalos >24 h, 109 >72 h y 15 >7 días**. Estos conteos se superponen. Una tasa tras un hueco largo permanece calculable si los dos valores son conocidos: representa el promedio entre extremos y no permite conocer lo ocurrido durante el hueco. Se marca `is_prolonged_gap` y se reinician las rachas. Intervalos positivos inferiores a un minuto se marcan para revisión numérica; no son una frecuencia instrumental validada.

Medias, dispersiones y OLS ponderan igualmente cada observación, no el tiempo representado. Las frecuencias heterogéneas pueden afectar estas estadísticas. No se inventa una frecuencia esperada ni porcentaje de completitud temporal. Los porcentajes siguientes indican **filas con cálculo disponible**, no porcentaje de mediciones esperadas ni confianza geomecánica.

## 6. Características construidas

El [diccionario de características](feature_dictionary.csv) enumera **cada una de las 315 columnas**, con descripción, fórmula, unidad, fuente, ventana, mínimo de observaciones, uso del presente/pasado, política de faltantes, límites e interpretaciones. Las columnas originales quedan incluidas para que la salida pueda auditarse completa.

| Familia | Campos y estadísticas |
| --- | --- |
| Trazabilidad | Todos los campos originales y `original__*`; `row_id`, `source_line`, `source_sha256`, `source_record_id`, `source_file_reference` |
| Intervalo | `previous_timestamp`, `elapsed_hours`, `elapsed_days`; inicio, intervalo no positivo, huecos >24/72/168 h, corto/prolongado |
| Cambio | `movement_delta_mm`, `absolute_movement_delta_mm`; incremento/disminución/sin cambio |
| Tasa | `movement_rate_mm_per_day`, `absolute_movement_rate_mm_per_day` y disponibilidad |
| Movimiento por ventana | `movement_{24h,72h,7d}_{mean,median,min,max,range,std,mad,first,last,net_change}_mm` |
| Cambios/tasas por ventana | `delta_{ventana}_*`, `rate_{ventana}_*`: media, mediana, std, mínimo, máximo, suma, suma absoluta, proporciones positivas/negativas y conteos conocidos; `increase_proportion_{ventana}` para los cambios |
| Cobertura por ventana | `window_{ventana}_*`: conteos totales/válidos, duración total/válida, máximo hueco, hueco largo; `has_sufficient_{ventana}_history` |
| Tendencia | `local_trend_{72h,7d}_{points,duration_hours,slope_mm_per_day,r_squared}` |
| Persistencia | `increase_streak_count`, `decrease_streak_count`, duraciones en horas, `streak_evaluable` |
| Historial previo | Conteos, duración, media/mediana/std/MAD, diferencias a media/mediana, z-score convencional/robusto y banderas de dispersión cero/insuficiente |
| Disponibilidad y calidad | Sufijo `_available` para campos numéricos/fecha derivados; `movement_observation_available`, `has_numeric_overflow`, `feature_quality_status` |

Conteo de columnas por grupo del diccionario:

| group | columnas |
| --- | --- |
| availability | 134 |
| change | 2 |
| delta_24h | 10 |
| delta_72h | 10 |
| delta_7d | 10 |
| historical | 15 |
| interval | 3 |
| movement_24h | 10 |
| movement_72h | 10 |
| movement_7d | 10 |
| quality | 13 |
| rate | 2 |
| rate_24h | 10 |
| rate_72h | 10 |
| rate_7d | 10 |
| source | 22 |
| streak | 5 |
| trend_72h | 4 |
| trend_7d | 4 |
| window_24h | 7 |
| window_72h | 7 |
| window_7d | 7 |

Una bandera de signo `False` puede indicar que el cambio es desconocido; siempre debe consultarse `movement_delta_mm_available`. Un conteo de cero es conocido y no se confunde con una estadística no calculable. Se conservan tanto conteos como banderas aunque algunos resulten constantes en este dataset; no se ha seleccionado todavía un conjunto para modelado.

## 7. Fórmulas y unidades

Sea x_t el movimiento reportado en mm y Δd el intervalo real en días:

- Cambio: **Δx_t=x_t−x_anterior**, en mm; cambio absoluto: |Δx_t|.
- **Tasa observada de cambio entre mediciones consecutivas**: **r_t=Δx_t/Δd**, en mm/día, solo con Δd>0 y ambos valores conocidos. No constituye velocidad física validada del macizo rocoso.
- Media: suma(x)/n; rango: máximo−mínimo; desviación estándar muestral: **sqrt(suma((x−media)²)/(n−1))**; MAD sin escalar: **mediana(|x−mediana(x)|)**. Movimiento/cambio usan mm; tasas usan mm/día.
- Cambio entre extremos de ventana: x_último−x_primero. Si uno de esos registros es desconocido, el resultado queda NaN; no se sustituye por otro extremo. Una ventana de un solo registro conocido tiene cambio entre extremos igual a cero, sin evidencia de persistencia.
- Proporción de incrementos/disminuciones: número de pares con Δx>0/Δx<0 dividido entre pares evaluables; cambios cero están incluidos en el denominador. Sin pares, NaN. La suma de tasas tiene unidad mm/día y es una suma matemática, **no** desplazamiento neto integrado.
- Pendiente OLS: **suma((d−media_d)(x−media_x))/suma((d−media_d)²)**, donde d son días transcurridos desde el primer timestamp válido de la ventana. Pendiente en mm/día; **R²=1−SSE/SST**, adimensional. Para serie constante SST=0, R² queda NaN aunque la pendiente sea cero. No se extrapola.
- Diferencias históricas: x_t−media(x_<t) y x_t−mediana(x_<t), en mm. **z=(x_t−media_previa)/std_previa** y **z_robusto=(x_t−mediana_previa)/(1.4826×MAD_previa)**, adimensionales. Dispersión cero o insuficiente deja el score NaN con su bandera; nunca se divide por cero.
- Racha: número de cambios consecutivos evaluables del mismo signo; duración desde el timestamp anterior al primer cambio de la racha hasta t. Cero reinicia ambas rachas con conteos/duraciones cero. Dato desconocido, intervalo inválido o hueco >72 h reinicia y deja la racha de esa fila NaN.

NaN significa «no calculable con los datos y criterios de ese instante». No significa cero movimiento, estabilidad o ausencia de riesgo. Las operaciones que exceden el rango numérico generan NaN y `has_numeric_overflow`; en los datos reales no ocurrió desbordamiento.

## 8. Criterios de historia suficiente

Los criterios se explicaron antes de implementar y se conservan en [config/phase4.json](../../config/phase4.json). Son decisiones técnicas provisionales de disponibilidad, no umbrales geomecánicos; no dependen de la fecha de falla.

| Cálculo | Criterio configurado | Justificación |
| --- | --- | --- |
| Desviación estándar | ≥2 valores conocidos; ddof=1 | Con un dato la dispersión muestral no está definida |
| Resúmenes simples | ≥1 valor conocido; extremos según sus registros | Permite describir datos escasos, con bandera separada de suficiencia |
| Historia suficiente por ventana | ≥3 valores conocidos, duración ≥25% de W y sin hueco interno observado >72 h | Evita confundir pocos puntos concentrados con cobertura reciente suficiente |
| Duración mínima 24/72/168 h | 6/18/42 h | Se aplica la misma fracción técnica de la longitud de ventana |
| Pendiente local | ≥3 timestamps válidos diferentes, duración ≥18/42 h y sin hueco entre puntos válidos >72 h | OLS necesita dispersión temporal y más de un par |
| Línea base previa | ≥20 valores previos conocidos que cubran ≥24 h | Evita referencia basada en pocas observaciones o un instante concentrado |
| Dispersión histórica | Mayor que 0; MAD escalada por 1.4826 | Evita divisiones nulas; constante robusta configurable |
| Intervalo corto/prolongado | 0<Δh<0.01666667 h; Δh>72 h | Banderas de revisión del cálculo; no diagnósticos instrumentales |

La fracción de duración **no es porcentaje de mediciones esperadas**. No garantiza precisión ni independencia de observaciones. `has_sufficient_history` describe la línea base; `_available` describe que existe un resultado matemático. Una ventana puede tener media disponible y aún no cumplir `has_sufficient_24h_history`. La pendiente puede fallar además si los valores desconocidos dejan un hueco demasiado largo entre puntos válidos.

`feature_quality_status` aplica prioridad: sin historia, intervalo inválido, datos/desbordamiento parciales, hueco prolongado, intervalo corto, historia previa insuficiente, cobertura/score/pendiente parcial, características disponibles. No es nivel de atención ni riesgo.

## 9. Resultados de calidad

| Comprobación | Entrada → salida |
| --- | --- |
| Filas | 7178 → 7178; excluidas 0, interpoladas 0, imputadas 0 |
| Prismas | 49 → 49 |
| Campos originales e IDs | Todos conservados y comparados exactamente con la entrada ordenada |
| Claves temporales repetidas/intervalos cero | 0 / 0 |
| Orden | Ascendente por prisma y timestamp |
| Infinitos/desbordamientos en salida | 0 / 0 |
| Movimiento original mínimo/máximo | 0.0 / 3243.655339 mm; ambos conservados |
| Cambios negativos | 3370; todos conservados |
| Columnas completamente NaN | 0 |
| Columnas constantes entre conocidos | 61; documentadas, no eliminadas |

Distribuciones calculadas únicamente para resultados conocidos, sin retirar extremos:

| feature_name | known_rows | missing_rows | min | median | max |
| --- | --- | --- | --- | --- | --- |
| elapsed_hours | 7129 | 49 | 0.0733 | 8.1253 | 357.1681 |
| movement_delta_mm | 7129 | 49 | -209.6786 | 0.3629 | 902.2093 |
| movement_rate_mm_per_day | 7129 | 49 | -5518.8653 | 0.721 | 572.2215 |
| local_trend_72h_slope_mm_per_day | 6638 | 540 | -71.1336 | 0.3619 | 540.8758 |
| local_trend_7d_slope_mm_per_day | 6661 | 517 | -28.8108 | 0.2839 | 446.0482 |

El extremo negativo de la tasa conserva el cambio y el intervalo que lo originaron; no se corrige por su magnitud. Requiere revisión de referencia, adquisición y significado físico antes de cualquier uso geomecánico. No se infiere causalidad.

Estados de calidad:

| quality_status | rows | rows_pct |
| --- | --- | --- |
| características disponibles | 4166 | 58.0385 |
| características parciales | 2001 | 27.8768 |
| historia insuficiente | 853 | 11.8835 |
| hueco prolongado | 109 | 1.5185 |
| sin historia previa | 49 | 0.6826 |

El [resumen de calidad](feature_quality_summary.csv) incluye tipo, conteos y porcentaje NaN, disponibilidad, campos vacíos/constantes para **cada columna**. Las banderas booleanas tienen cero NaN porque expresan condiciones conocidas; su porcentaje de celdas no vacías no equivale al porcentaje de banderas verdaderas. Este último está en la tabla por grupos y por prisma.

Columnas constantes entre sus valores conocidos (sin eliminarlas):

- `source_name`
- `source_sha256`
- `source_file_reference`
- `movement_observation_available`
- `is_nonpositive_interval`
- `is_unusually_short_interval`
- `prior_valid_observations_available`
- `historical_std_zero`
- `historical_mad_zero`
- `window_24h_observation_count_available`
- `window_24h_valid_movement_count_available`
- `window_24h_duration_hours_available`
- `window_24h_valid_duration_hours_available`
- `window_24h_has_long_gap`
- `movement_24h_mean_mm_available`
- `movement_24h_median_mm_available`
- `movement_24h_min_mm_available`
- `movement_24h_max_mm_available`
- `movement_24h_range_mm_available`
- `movement_24h_mad_mm_available`
- `movement_24h_first_mm_available`
- `movement_24h_last_mm_available`
- `movement_24h_net_change_mm_available`
- `delta_24h_valid_count_available`
- `rate_24h_valid_count_available`
- `window_72h_observation_count_available`
- `window_72h_valid_movement_count_available`
- `window_72h_duration_hours_available`
- `window_72h_valid_duration_hours_available`
- `window_72h_has_long_gap`
- `movement_72h_mean_mm_available`
- `movement_72h_median_mm_available`
- `movement_72h_min_mm_available`
- `movement_72h_max_mm_available`
- `movement_72h_range_mm_available`
- `movement_72h_mad_mm_available`
- `movement_72h_first_mm_available`
- `movement_72h_last_mm_available`
- `movement_72h_net_change_mm_available`
- `delta_72h_valid_count_available`
- `rate_72h_valid_count_available`
- `local_trend_72h_points_available`
- `local_trend_72h_duration_hours_available`
- `window_7d_observation_count_available`
- `window_7d_valid_movement_count_available`
- `window_7d_duration_hours_available`
- `window_7d_valid_duration_hours_available`
- `movement_7d_mean_mm_available`
- `movement_7d_median_mm_available`
- `movement_7d_min_mm_available`
- `movement_7d_max_mm_available`
- `movement_7d_range_mm_available`
- `movement_7d_mad_mm_available`
- `movement_7d_first_mm_available`
- `movement_7d_last_mm_available`
- `movement_7d_net_change_mm_available`
- `delta_7d_valid_count_available`
- `rate_7d_valid_count_available`
- `local_trend_7d_points_available`
- `local_trend_7d_duration_hours_available`
- `has_numeric_overflow`

## 10. Características con mayor porcentaje de disponibilidad

Disponibilidad matemática/suficiencia por grupo; denominador común 7178 filas:

| Grupo | Descripción | Filas disponibles | Total de filas | % disponible |
| --- | --- | --- | --- | --- |
| consecutive_change | Cambio entre mediciones | 7129 | 7178 | 99.3174 |
| observed_rate | Tasa observada | 7129 | 7178 | 99.3174 |
| prior_baseline | Línea base previa | 6217 | 7178 | 86.6119 |
| conventional_z | Z-score convencional | 6217 | 7178 | 86.6119 |
| robust_z | Z-score robusto | 6217 | 7178 | 86.6119 |
| streak | Rachas evaluables | 7020 | 7178 | 97.7988 |
| movement_descriptive_24h | Media del movimiento, 24h | 7178 | 7178 | 100 |
| movement_dispersion_24h | Std del movimiento, 24h | 6284 | 7178 | 87.5453 |
| internal_changes_24h | Media de cambios internos, 24h | 6284 | 7178 | 87.5453 |
| sufficient_window_24h | Historia suficiente, 24h | 4510 | 7178 | 62.8309 |
| movement_descriptive_72h | Media del movimiento, 72h | 7178 | 7178 | 100 |
| movement_dispersion_72h | Std del movimiento, 72h | 7020 | 7178 | 97.7988 |
| internal_changes_72h | Media de cambios internos, 72h | 7020 | 7178 | 97.7988 |
| sufficient_window_72h | Historia suficiente, 72h | 6638 | 7178 | 92.477 |
| movement_descriptive_7d | Media del movimiento, 7d | 7178 | 7178 | 100 |
| movement_dispersion_7d | Std del movimiento, 7d | 7114 | 7178 | 99.1084 |
| internal_changes_7d | Media de cambios internos, 7d | 7114 | 7178 | 99.1084 |
| sufficient_window_7d | Historia suficiente, 7d | 6661 | 7178 | 92.7974 |
| local_trend_72h | Pendiente local, 72h | 6638 | 7178 | 92.477 |
| local_trend_7d | Pendiente local, 7d | 6661 | 7178 | 92.7974 |

Medias descriptivas del movimiento alcanzan 100% porque West Wall contiene movimiento conocido en cada fila y la ventana incluye el presente. Sin embargo, solo 62.83% cumple el criterio de historia suficiente de 24 horas. No se presenta ese 100% como cobertura completa.

## 11. Características con disponibilidad limitada

Campos calculados con mayor porcentaje NaN (se excluyen del listado las banderas y copias originales):

| feature_name | available_count | nan_count | available_pct | nan_pct |
| --- | --- | --- | --- | --- |
| delta_24h_std | 4517 | 2661 | 62.9284 | 37.0716 |
| rate_24h_std | 4517 | 2661 | 62.9284 | 37.0716 |
| difference_from_prior_mean_mm | 6217 | 961 | 86.6119 | 13.3881 |
| difference_from_prior_median_mm | 6217 | 961 | 86.6119 | 13.3881 |
| historical_mad_mm | 6217 | 961 | 86.6119 | 13.3881 |
| historical_mean_mm | 6217 | 961 | 86.6119 | 13.3881 |
| historical_median_mm | 6217 | 961 | 86.6119 | 13.3881 |
| historical_robust_z_score | 6217 | 961 | 86.6119 | 13.3881 |
| historical_std_mm | 6217 | 961 | 86.6119 | 13.3881 |
| historical_z_score | 6217 | 961 | 86.6119 | 13.3881 |
| delta_24h_absolute_sum | 6284 | 894 | 87.5453 | 12.4547 |
| delta_24h_decrease_proportion | 6284 | 894 | 87.5453 | 12.4547 |

Las desviaciones estándar de cambios/tasas de 24 horas necesitan dos pares internos, es decir, al menos tres observaciones dentro de la ventana; por eso tienen más NaN que la dispersión del movimiento. La línea base exige veinte observaciones **previas**, por lo que las filas iniciales no tienen comparación histórica. Las pendientes también requieren duración temporal; no basta contar tres filas.

## 12. Prismas con cobertura insuficiente

Prismas que terminan sin alcanzar la línea base previa mínima:

| prism_id | rows | first_timestamp | last_timestamp | prior_baseline_available_pct | local_trend_72h_available_pct | local_trend_7d_available_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 30-1995 | 4 | 2013-11-20 15:49:21 | 2013-11-28 22:32:23 | 0 | 0 | 0 |
| 31-1930 | 17 | 2013-11-20 20:31:19 | 2013-12-08 03:08:37 | 0 | 76.4706 | 64.7059 |

Estos prismas se conservan. Los 47 restantes alcanzan la referencia en algún instante, pero no necesariamente en sus primeras filas ni con igual disponibilidad por ventana. [prism_feature_summary.csv](prism_feature_summary.csv) muestra los 49 prismas, sus fechas, huecos, primera línea base disponible y porcentaje por cada grupo. No se etiqueta «estable» a un prisma por carecer de historia.

## 13. Ejemplos verificables

Son **casos sintéticos de prueba**, separados del dataset real, no mediciones inventadas para el análisis.

| Caso manual | Resultado esperado y comprobado |
| --- | --- |
| x=2,3,6 mm en horas 0,6,24 | Cambios 1 y 3 mm; tasas 4 y 4 mm/día; pendiente 72 h=4 mm/día, R²=1; pendiente 7 d desconocida porque duración 24<42 h |
| x=1,3,5 mm en horas 0,24,25 | En t=25 h, ventana 24 h contiene solo las dos últimas filas; cambio interno total=2 mm, no 4 mm |
| Historial 1,2,3; presente 10 | Con mínimo **solo para este test** de 3 previos y duración mínima 0: media=mediana=2, std=MAD=1, z=8, z robusto=8/1.4826; 10 queda fuera de su referencia |
| Historial 2,2,2; presente 9 | std=MAD=0; ambos scores NaN y banderas de cero activas |
| x=1,1 en un intervalo positivo | Cambio=tasa=0 conocidos; ambas rachas se reinician con cero |
| Intervalo cero o negativo | La función de pares devuelve tasa NaN; la entrada completa con duplicados bloquea ingeniería para revisión |
| Extremo futuro ±10¹² | Todas las columnas de filas previas permanecen idénticas |

Las pruebas cubren también disminuciones, faltantes sin puente/interpolación, signos, rachas, huecos, aislamiento entre prismas, unidades y parámetros configurables. Los criterios reducidos de los casos manuales no se aplicaron al dataset real.

## 14. Pruebas realizadas

Las 75 pruebas anteriores se ejecutaron antes de programar y aprobaron; véase [pytest-before.txt](pytest-before.txt). La ejecución final incluyó **38 pruebas nuevas y 75 anteriores: 113 aprobadas, 0 fallidas, 0 omitidas**, en 13.68 s. Evidencia: [salida Pytest](pytest-output.txt) y [JUnit XML](pytest-results.xml).

Los tres archivos nuevos prueban las fórmulas temporales, entradas inválidas y conservación, y ausencia de fuga: (1) prefijo más futuro extremo, (2) cada prefijo equivalente a llegada incremental, (3) otro prisma independiente. Se verifican los 24 tipos de caso solicitados, incluidos primera fila, intervalos irregulares/cero, desorden, duplicados, huecos 24/72/168 h, dispersión nula, extremos, rachas y conservación. Un test adicional demuestra que modificar mínimos de dispersión y escala MAD queda reflejado tanto en resultados como en el diccionario.

En datos reales, el corte de comprobación fue el punto medio de la cobertura, **2014-01-05 10:59:37.500000**, sin relación con la fecha de falla. Se recalculó un prefijo de **2905 filas de 46 prismas**. Coincidieron exactamente todas las columnas con el cálculo de la serie completa. Después se alteraron las **4273 filas futuras** alternando ±10¹² mm en una copia de prueba y el prefijo volvió a ser idéntico. Esos valores nunca se escribieron en el dataset entregado.

## 15. Integridad y reproducibilidad

Se verificaron **226 archivos protegidos** antes y después: originales, fuentes preparadas, código/pruebas anteriores, artículo, informes, notebook y gráficos históricos. No se reescriben las Fases 1–3. Se crea una carpeta nueva `phase4` para resultados. README y `.gitignore` son las únicas modificaciones de archivos previos autorizadas para documentar esta fase; el resto son incorporaciones.

Se reprodujeron **7 CSV byte a byte**: tabla principal y seis tablas de auditoría. Su lectura/exportación conserva exactamente tipos, números y textos originales. Metadatos contienen configuración, versiones, políticas y huellas; los tiempos de ejecución se guardan aparte porque son variables. El pipeline incluyendo gráficos tomó 35.79 s en esta ejecución; no es una garantía de tiempo en otro equipo.

SHA-256 de la tabla principal: `4fb5d7fc0e456c3e644186c56c5c149d910635e1e742141cb111237cb1c8e452`. Fuente preparada: `bdb56ccf301b5f6489c3773705e31bb324d057a16ac13dfc35be1f7e4732aa2a`. Todas las huellas y las pruebas completas están en [phase4_metadata.json](phase4_metadata.json), [reproducibility.json](reproducibility.json) y [verification-log.txt](verification-log.txt). Se validaron los **17 PNG y sus 17 HTML**; los PNG se revisaron visualmente. Los HTML usan `interactive/plotly.min.js` local y funcionan sin conexión al mantener esa carpeta completa. La identidad byte a byte se exige para las tablas; para las visualizaciones se valida integridad y contenido descriptivo, no identidad binaria entre versiones distintas de bibliotecas.

Comandos desde la raíz del proyecto:

```bash
python -m pip install -r requirements-phase4.txt
python scripts/run_phase4.py
python scripts/verify_phase4.py --reproduce
python -m pytest -q --junitxml=reports/phase4/pytest-results.xml > reports/phase4/pytest-output.txt
python scripts/build_phase4_report.py
```

Checkpoint inicial: `fef7d06`. El identificador final queda en `reports/phase4/git_checkpoint.txt` después del commit, para evitar un archivo que intente incluir el hash de su propio commit. El paquete contiene ese registro; no incluye `.git`.

## 16. Limitaciones

- La falla queda fuera de la cobertura de West Wall; no hay etiquetas suficientes ni observaciones independientes de numerosas fallas. No se calculan métricas de clasificación, falsos positivos o anticipación.
- Movimiento reportado respecto a una referencia no es trayectoria acumulada estricta. Tasa/pendiente son derivados estadísticos, sin validación física o geomecánica. Los signos negativos se preservan.
- Frecuencia irregular, huecos largos y ponderación por observación afectan la lectura; los criterios de suficiencia son provisionales y requieren revisión del especialista.
- Media y MAD pueden calcularse con un solo dato (MAD=0); la bandera de historia suficiente evita confundir ese cálculo con evidencia sólida. R² no está definido para una serie constante.
- La referencia expansiva conserva toda la historia previa y puede adaptarse lentamente a cambios prolongados. Sus scores no son etiquetas ni umbrales de alerta.
- No se unen lluvia, eventos, voladuras o South West hasta validar unidades, zonas horarias, semántica y alineación. Lluvia desconocida permanece desconocida.
- Hay redundancias entre columnas, proporciones de signos y banderas constantes. La tabla contiene trazabilidad y auditoría; alimentar todas sus columnas a un modelo sería inapropiado.
- La reproducción exacta está comprobada con las versiones registradas; cambios de biblioteca pueden modificar detalles numéricos o formato. La implementación de prefijos en memoria es adecuada para este volumen y no es todavía un motor incremental optimizado.
- Errores pendientes de ejecución: ninguno en las comprobaciones realizadas. Persisten decisiones científicas sobre significado físico, fuentes complementarias, frecuencia y futuros criterios de evaluación.

## 17. Recomendaciones para la Fase 5

**Se puede preparar la Fase 5 técnicamente, después de la aprobación formal**, porque se conserva la fuente y las características son causales, trazables y reproducibles. Esto no valida capacidad de predecir fallas.

Antes de entrenar, acordar un subconjunto numérico entendible y evitar IDs, fechas documentales de falla, textos, alias, constantes y duplicaciones como entradas automáticas. Mantener banderas de calidad para contextualizar resultados y tratar valores faltantes explícitamente. Acordar si se excluyen filas de entrenamiento por insuficiencia, documentándolo sin retirar los datos del archivo maestro.

Separar entrenamiento/evaluación por **timestamp**, nunca por fila aleatoria. Cualquier imputador, escalador y ajuste de parámetros debe aprender únicamente del entrenamiento; las características de evaluación pueden usar el historial realmente observado hasta cada instante. Comparar métodos no supervisados con reglas descriptivas transparentes y pruebas de estabilidad temporal. No usar la fecha de falla para ajustar retrospectivamente las ventanas ni presentar accuracy, precisión, recall o F1 sin etiquetas confiables. Revisar extremos y huecos con el ingeniero antes de dar interpretación geomecánica. No se implementó ninguno de esos modelos en esta fase.

## 18. Archivos creados y modificados

| Ruta | Estado y función |
| --- | --- |
| `src/config.py`, `config/phase4.json` | Nuevos; criterios técnicos y validación de parámetros |
| `src/temporal_features.py` | Nuevo; fórmulas, ventanas, línea base, tendencias y rachas |
| `src/feature_engineering.py` | Nuevo; integración por prisma y diccionario |
| `src/feature_validation.py` | Nuevo; conservación, calidad, exportación/lectura exactas |
| `src/feature_visualizations.py` | Nuevo; gráficos de esta fase, reutilizando el exportador anterior sin modificarlo |
| `scripts/run_phase4.py`, `scripts/verify_phase4.py`, `scripts/build_phase4_report.py` | Nuevos; ejecución, auditoría/reproducción e informe |
| `tests/test_feature_engineering.py`, `tests/test_temporal_features.py`, `tests/test_no_temporal_leakage.py`, `tests/__init__.py` | Nuevos; pruebas y paquete de fixtures locales |
| `requirements-phase4.txt` | Nuevo; reutiliza dependencias fijadas de Fase 3 |
| `data/processed/phase4/west_wall_features.csv` | Nuevo; todos los registros y características |
| `reports/phase4/` | Nuevo; informe, diccionario, calidad por campo/grupo/prisma, distribuciones, metadatos, huellas, reproducción, logs y evidencia de pruebas |
| `reports/phase4/figures/`, `reports/phase4/interactive/` | Nuevos; 17 pares PNG/HTML y JavaScript local |
| `README.md` | Modificado; estado del proyecto e instrucciones de Fase 4 |
| `.gitignore` | Modificado; evita versionar gráficos y registro de commit reproducibles; sí se entregan en ZIP |

Árbol de incorporaciones y modificaciones, organizado por carpeta:

- Raíz: `README.md` (modificado), `.gitignore` (modificado), `requirements-phase4.txt` (nuevo).
- `config/`: `phase4.json`.
- `src/`: `config.py`, `temporal_features.py`, `feature_engineering.py`, `feature_validation.py`, `feature_visualizations.py`.
- `scripts/`: `run_phase4.py`, `verify_phase4.py`, `build_phase4_report.py`.
- `tests/`: `__init__.py`, `test_feature_engineering.py`, `test_temporal_features.py`, `test_no_temporal_leakage.py`.
- `data/processed/phase4/`: `west_wall_features.csv`.
- `reports/phase4/`:
  - Informe: `feature_engineering_findings.md`.
  - Tablas: `feature_dictionary.csv`, `feature_quality_summary.csv`, `feature_group_availability.csv`, `prism_feature_summary.csv`, `feature_distributions.csv`, `quality_status_counts.csv`.
  - Auditoría: `phase4_metadata.json`, `protected_before_phase4.json`, `reproducibility.json`, `execution_stats.json`, `git_checkpoint.txt`.
  - Evidencia: `execution_log.txt`, `verification-log.txt`, `pytest-before.txt`, `pytest-development.txt`, `pytest-output.txt`, `pytest-results.xml`.
  - `figures/`: 17 PNG.
  - `interactive/`: 17 HTML y `plotly.min.js` local.

Visualizaciones descriptivas entregadas:

| Visualización | Imagen | Interactiva |
| --- | --- | --- |
| Intervalos temporales observados | [PNG](figures/interval_distribution.png) | [HTML](interactive/interval_distribution.html) |
| Cambios entre mediciones; signos conservados | [PNG](figures/change_distribution.png) | [HTML](interactive/change_distribution.html) |
| Tasa observada de cambio entre mediciones consecutivas | [PNG](figures/rate_distribution.png) | [HTML](interactive/rate_distribution.html) |
| Tendencia estadística local: ventana 72 h | [PNG](figures/trend72_distribution.png) | [HTML](interactive/trend72_distribution.html) |
| Tendencia estadística local: ventana 7 días | [PNG](figures/trend7_distribution.png) | [HTML](interactive/trend7_distribution.html) |
| Disponibilidad matemática por grupo | [PNG](figures/availability_groups.png) | [HTML](interactive/availability_groups.html) |
| Treinta características con mayor porcentaje de NaN | [PNG](figures/missing_features.png) | [HTML](interactive/missing_features.html) |
| Validación temporal: prisma 22-1917 | [PNG](figures/features_prism_22_1917.png) | [HTML](interactive/features_prism_22_1917.html) |
| Validación temporal: prisma 30-1994 | [PNG](figures/features_prism_30_1994.png) | [HTML](interactive/features_prism_30_1994.html) |
| Validación temporal: prisma 30-1995 | [PNG](figures/features_prism_30_1995.png) | [HTML](interactive/features_prism_30_1995.html) |
| Validación temporal: prisma 31-1930 | [PNG](figures/features_prism_31_1930.png) | [HTML](interactive/features_prism_31_1930.html) |
| Validación temporal: prisma 31-2007 | [PNG](figures/features_prism_31_2007.png) | [HTML](interactive/features_prism_31_2007.html) |
| Validación temporal: prisma 31-2010 | [PNG](figures/features_prism_31_2010.png) | [HTML](interactive/features_prism_31_2010.html) |
| Validación temporal: prisma 36-1969 | [PNG](figures/features_prism_36_1969.png) | [HTML](interactive/features_prism_36_1969.html) |
| Validación temporal: prisma 40-1928 | [PNG](figures/features_prism_40_1928.png) | [HTML](interactive/features_prism_40_1928.html) |
| Validación temporal: prisma 40-1933 | [PNG](figures/features_prism_40_1933.png) | [HTML](interactive/features_prism_40_1933.html) |
| Validación temporal: prisma 40-1938 | [PNG](figures/features_prism_40_1938.png) | [HTML](interactive/features_prism_40_1938.html) |

Se detiene aquí el proyecto hasta la revisión y aprobación de la Fase 5.
