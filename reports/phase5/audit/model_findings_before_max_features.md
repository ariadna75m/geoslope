# Fase 5 — Modelos no supervisados y evaluación temporal

## 1. Resumen ejecutivo

Se implementaron una regla estadística transparente y un Isolation Forest global, con selección de variables y aprendizaje exclusivamente sobre entrenamiento. Se preservan **7,178 filas, 49 prismas y 294 archivos anteriores**. De 20 candidatos, se seleccionaron **17 características**; 5,898 filas (82.17%) son elegibles. Las otras 1,280 permanecen con motivos, puntuaciones desconocidas y clasificaciones experimentales desconocidas.

La suite termina con **147 pruebas aprobadas, 0 fallidas y 0 omitidas**. La reproducción completa genera 24 CSV idénticos byte a byte; los modelos recargados conservan sus parámetros aprendidos y sus puntuaciones. La prueba crítica modifica 3261 filas futuras sin alterar la selección, imputador, escalador, árboles, umbrales ni las puntuaciones de entrenamiento.

La recomendación provisional es conservar **ambas puntuaciones experimentales**: la regla para una referencia interpretable e Isolation Forest para comparación multivariable. No se declara un ganador por precisión real. Se entregan 17 pares PNG/HTML descriptivos; no se implementan alertas operativas ni niveles de riesgo.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.

## 2. Objetivo

Comprobar si un subconjunto compacto y temporalmente válido permite puntuar comportamientos estadísticamente atípicos de forma reproducible, sin información futura ni etiquetas inventadas. La observación actual utiliza el historial realmente disponible hasta su timestamp; el z-score histórico excluye la observación actual de su referencia. Esto permite puntuar al recibir la medición y no implica anticipación validada.

| Término | Interpretación en este proyecto |
| --- | --- |
| Anomalía estadística | Desviación respecto a una referencia aprendida, sin diagnóstico de falla |
| Observación marcada | Score que supera un umbral experimental; candidato para revisión |
| Alerta operativa | Acción definida con el especialista; no generada en esta fase |
| Nivel de atención | Priorización profesional pendiente; no generado |
| Riesgo geomecánico | Requiere evaluación, exposición y consecuencias; no calculado |
| Falla real | Evento físico documentado; no equivalente a una anomalía |

La corrección terminológica se establece en [la adenda de Fase 5](../documentation/phase5_terminology.md): **Características temporalmente válidas, calculadas sin información futura y respetando el orden cronológico.** Se preservan íntegros los documentos históricos y se aclara que esto no demuestra causalidad científica.

## 3. Limitaciones del dataset

La entrada es `data/processed/phase4/west_wall_features.csv`: 7.178 observaciones, 49 prismas y 315 columnas. Procede de West Wall; no se incorpora South West, lluvia, sismicidad ni voladuras. El movimiento 3D reportado está en mm respecto a su referencia documental; no es una trayectoria necesariamente creciente. La tasa y la pendiente son estadísticas del movimiento reportado, no velocidades físicas validadas del macizo.

No hay etiquetas reales suficientes ni miles de fallas independientes. Varias mediciones del mismo prisma y ventanas solapadas están relacionadas. El registro termina el **20-02-2014**. Después de terminar el análisis, se conserva como contexto independiente que el artículo documenta una falla el **23-02-2014**, fuera de esta tabla. Esa fecha no forma parte de la configuración, selección, partición, entrenamiento, umbrales, contaminación o recomendación; no se calcula anticipación predictiva.

Referencia aportada por la usuaria: de Wit, T., & Snieder, R. (2026). Did they blow it? Time-lapse velocity variations during an open-pit mine slope failure using seismic noise interferometry. *Seismica, 5*(1). https://doi.org/10.26443/seismica.v5i1.1902. Véase [contexto del artículo](../documentation/article_context.md). Los cambios de velocidad del TXT corresponden a otro análisis; no se usan como velocidad de prismas.

## 4. Variables candidatas

Se declararon 20 candidatos, prioridad interpretativa y |Spearman| > 0.95 antes del entrenamiento final. Se rechazan candidatos vacíos, constantes o con más de 20% faltantes. Las estadísticas siguientes se calculan sobre las **2909 filas inicialmente elegibles de entrenamiento**, no sobre toda la serie. La varianza conserva las unidades al cuadrado; cero faltantes aquí no significa disponibilidad en las 7.178 filas.

| Candidato | Unidad | Faltante % | Varianza entrenamiento | Incluido |
| --- | --- | --- | --- | --- |
| movement_rate_mm_per_day | mm/día | 0 | 1988.4488 | True |
| local_trend_72h_slope_mm_per_day | mm/día | 0 | 512.9364 | True |
| local_trend_7d_slope_mm_per_day | mm/día | 0 | 389.4718 | True |
| historical_robust_z_score | adimensional | 0 | 4.8968 | True |
| increase_proportion_72h | proporción 0–1 | 0 | 0.0223 | True |
| increase_proportion_7d | proporción 0–1 | 0 | 0.0081 | True |
| movement_72h_mad_mm | mm | 0 | 174.0836 | True |
| movement_7d_mad_mm | mm | 0 | 927.7673 | True |
| delta_72h_absolute_sum | mm | 0 | 4364.124 | True |
| delta_7d_absolute_sum | mm | 0 | 21554.9072 | True |
| movement_delta_mm | mm | 0 | 545.9723 | True |
| increase_streak_duration_hours | horas | 0 | 279.6186 | True |
| increase_streak_count | cambios consecutivos | 0 | 1.2925 | True |
| local_trend_72h_r_squared | adimensional | 0 | 0.0507 | True |
| local_trend_7d_r_squared | adimensional | 0 | 0.0215 | True |
| difference_from_prior_median_mm | mm | 0 | 28756.828 | False |
| movement_72h_range_mm | mm | 0 | 3268.3679 | True |
| movement_7d_range_mm | mm | 0 | 17107.808 | True |
| absolute_movement_delta_mm | mm | 0 | 508.3654 | False |
| absolute_movement_rate_mm_per_day | mm/día | 0 | 1488.7949 | False |

`candidate_features.csv` documenta además valores únicos, interpretación permitida, transformaciones y correlaciones. `spearman_training.csv`, `pearson_training.csv` y `pair_redundancy.csv` conservan las matrices y los 190 pares examinados; Pearson es complementaria, no el criterio de selección.

## 5. Variables seleccionadas y excluidas

| Característica seleccionada | Unidad |
| --- | --- |
| movement_rate_mm_per_day | mm/día |
| local_trend_72h_slope_mm_per_day | mm/día |
| local_trend_7d_slope_mm_per_day | mm/día |
| historical_robust_z_score | adimensional |
| increase_proportion_72h | proporción 0–1 |
| increase_proportion_7d | proporción 0–1 |
| movement_72h_mad_mm | mm |
| movement_7d_mad_mm | mm |
| delta_72h_absolute_sum | mm |
| delta_7d_absolute_sum | mm |
| movement_delta_mm | mm |
| increase_streak_duration_hours | horas |
| increase_streak_count | cambios consecutivos |
| local_trend_72h_r_squared | adimensional |
| local_trend_7d_r_squared | adimensional |
| movement_72h_range_mm | mm |
| movement_7d_range_mm | mm |

Exclusiones dentro del conjunto candidato:

| Excluida | Se conserva | Spearman | Motivo |
| --- | --- | --- | --- |
| difference_from_prior_median_mm | historical_robust_z_score | 0.9729 | redundante según Spearman; se conserva prioridad interpretativa declarada |
| absolute_movement_delta_mm | movement_delta_mm | 0.025 | transformación absoluta determinista del predictor con signo; se evita doble ponderación |
| absolute_movement_rate_mm_per_day | movement_rate_mm_per_day | 0.0199 | transformación absoluta determinista del predictor con signo; se evita doble ponderación |

La diferencia frente a la mediana previa es muy redundante con el z-score robusto. Los valores absolutos son transformaciones deterministas de los predictores con signo: se conservan estos últimos para mantener la dirección y evitar duplicar peso. Una transformación absoluta no tiene necesariamente correlación lineal 1 con su variable original; su dependencia matemática justifica esta exclusión.

Las **298 columnas restantes** están inventariadas en `excluded_features.csv`: incluye las tres candidatas excluidas y 295 columnas fuera del conjunto compacto. IDs, fechas, posiciones temporales, textos originales, archivos, hashes y auditoría solo sirven para trazabilidad. Las banderas de calidad determinan elegibilidad y contexto, sin mezclarse como predictores del bosque. No se incorporan automáticamente otras constantes, alias o ventanas de Fase 4.

## 6. División temporal

Los cuantiles 0,60 y 0,80 se calculan sobre **93 días calendario distintos observados**, con interpolación lineal; cada corte se lleva al comienzo del día siguiente. Se conservan días y timestamps completos en un solo periodo. No se ordena ni corta por número de fila y no hay partición aleatoria. Por eso las proporciones de filas no son exactamente 60/20/20.

| Periodo | Primera medición | Última medición | Días distintos | Filas | Prismas | Elegibles | Elegibles % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| entrenamiento | 2013-11-20 12:41:22 | 2014-01-14 23:21:01 | 56 | 3917 | 46 | 2909 | 74.266 |
| validación | 2014-01-15 02:16:25 | 2014-02-01 23:11:22 | 18 | 1536 | 46 | 1367 | 88.9974 |
| prueba | 2014-02-02 00:03:27 | 2014-02-20 09:17:53 | 19 | 1725 | 46 | 1622 | 94.029 |

Cortes exclusivos: entrenamiento `timestamp < 2014-01-15 00:00:00`; validación hasta `timestamp < 2014-02-02 00:00:00`; prueba desde ese segundo corte. El entrenamiento **elegible** comienza el 2013-11-26 02:42:57 y utiliza 43 prismas; el periodo completo contiene 46.

En validación aparecen `22-2059`, `22-2060` y `22-2061`; dejan de observarse `30-1994`, `30-1995` y `31-1930`. La prueba mantiene los 46 prismas de validación. El campo de nuevos prismas de entrenamiento enumera los iniciales respecto al conjunto previo vacío, no incorporaciones durante validación. `temporal_split_summary.csv` registra disponibilidad de z-score y pendientes por periodo; `prism_score_profiles.csv` identifica los prismas presentes en entrenamiento elegible.

Las características de validación pueden usar mediciones anteriores de entrenamiento, y las de prueba pueden usar el historial observado de validación; el imputador, escala, bosque, regla y umbrales no se reajustan con ellas.

## 7. Elegibilidad

| period | rows | eligible_rows | eligible_pct | no_elegibles |
| --- | --- | --- | --- | --- |
| entrenamiento | 3917 | 2909 | 74.266 | 1008 |
| validación | 1536 | 1367 | 88.9974 | 169 |
| prueba | 1725 | 1622 | 94.029 | 103 |

Se requieren historia previa, cobertura suficiente de 72 h y 7 días, intervalo válido y ausencia de hueco prolongado, según las políticas de Fase 4. Son indispensables la tasa, ambas pendientes, z-score, conteo y duración de racha. Se rechazan infinitos y más de 20% faltantes seleccionados; la transformación aprendida debe producir valores finitos. No se retiran filas del archivo maestro.

| Motivo | Filas afectadas |
| --- | --- |
| característica indispensable faltante | 1280 |
| historia previa insuficiente | 961 |
| cobertura 72h insuficiente | 540 |
| cobertura 7d insuficiente | 517 |
| demasiadas características faltantes | 319 |
| hueco prolongado | 109 |
| sin historia previa | 49 |

Los motivos se solapan y **no deben sumarse** para obtener las 1.280 filas no elegibles. La clasificación usa booleanos anulables: una fila no elegible tiene score, percentil y marcas desconocidos; nunca se representa como normal o como `False`. Hay seis días sin ninguna fila elegible; tampoco constituyen evidencia de estabilidad.

## 8. Preprocesamiento

Pipeline: selector de las 17 columnas → `SimpleImputer(strategy='median')` → `RobustScaler` con mediana e IQR 25–75 → Isolation Forest. Se ajusta una sola vez con entrenamiento elegible. No se eliminan, recortan ni reemplazan extremos para mejorar resultados. No se interpola ni se modifica la tabla de Fase 4.

Los faltantes opcionales pueden usar su mediana fija de entrenamiento; los indispensables impiden puntuar. En este conjunto las filas elegibles tienen todas las variables conocidas: **cero imputaciones efectivamente aplicadas**. No se añaden indicadores de ausencia porque serían constantes en entrenamiento. Las medianas, centros y escalas están en `models/phase5/model_metadata.json` y el preprocesamiento serializado.

Se compara con un bosque sin escalado robusto conservando los mismos extremos; aquí el ranking y las puntuaciones resultan idénticos. Esto es compatible con la invariancia de los cortes de árboles ante transformaciones afines; no demuestra mejor precisión del escalado. No se aplica `log1p` a las entradas del bosque. La regla sí utiliza `log1p` para moderar exclusivamente su componente no negativo de persistencia; los gráficos de la regla lo usan también solo para legibilidad y conservan el score original.

Para aplicar el artefacto a una nueva fila que **ya contiene las características y banderas calculadas con su historial**, desde la raíz del proyecto:

```python
import joblib
bundle = joblib.load('models/phase5/scoring_bundle.joblib')
resultado = bundle.score_new(nueva_fila_con_caracteristicas)
```

No es un pipeline para mediciones crudas aisladas: se necesita el historial de Fase 4. El bosque completo y el preprocesador independiente también se guardan. El módulo `src/` y las versiones indicadas permiten recargar las clases del proyecto.

## 9. Modelo base

La puntuación continua de la regla es:

`0.7 × |z robusto histórico previo| + 0.2 × |(pendiente72h − mediana_train) / escala_train| + 0.1 × log1p(max(0, (duración_racha − mediana_train) / escala_train))`.

La escala es `1.4826 × MAD`; si es cero, se usa IQR y, si ambas son cero, escala unitaria con limitación registrada. Aquí ambas referencias usan MAD: tendencia, centro 0.092245 mm/día y escala 1.804065; persistencia, centro 1.734444 h y escala 2.571487. Pesos y referencias son explícitos; no se ajustan por proximidad a una falla. Calidad actúa como puerta de elegibilidad, no como suma de riesgo.

La marca separada `|z robusto| ≥ 3.5` es una referencia estadística inicial; **no es el umbral del score compuesto ni un límite geomecánico**:

| Periodo | Elegibles | Referencia |z| ≥ 3.5 | Marcación % |
| --- | --- | --- | --- |
| entrenamiento | 2909 | 81 | 2.7845 |
| validación | 1367 | 59 | 4.316 |
| prueba | 1622 | 178 | 10.9741 |

## 10. Isolation Forest

| n_estimators | max_samples | max_features | bootstrap | random_state | contamination |
| --- | --- | --- | --- | --- | --- |
| 200 | 256 | 1 | False | 42 | 0.02 |

Biblioteca: scikit-learn 1.8.0; `n_jobs=1`. Se entrenan 200 árboles sobre un máximo de 256 filas por árbol, con 17 características, sin bootstrap y semilla fija 42. El modelo es global porque hay 2909 filas elegibles distribuidas en 43 prismas y varios prismas son demasiado pequeños para entrenamientos independientes fiables.

Score continuo: **`−score_samples`**, de modo que mayor valor significa mayor atipicidad estadística. No es una probabilidad. El umbral interno es `−offset_`; la contaminación fija 0,02 solo define ese corte. Los percentiles se calculan mediante la distribución empírica de scores de **entrenamiento**, incluyendo empates por la derecha; no se recalculan sobre validación o prueba.

| Modelo | Referencia | Valor |
| --- | --- | --- |
| baseline | q95 | 2.2967 |
| baseline | q98 | 3.3277 |
| baseline | q99 | 4.4398 |
| isolation_forest | q95 | 0.5043 |
| isolation_forest | q98 | 0.5457 |
| isolation_forest | q99 | 0.5873 |
| isolation_forest | internal | 0.5457 |

Todas las marcas usan **score estrictamente mayor que el umbral**. Los empates y el tamaño finito explican pequeñas diferencias respecto al porcentaje nominal. Score, percentil, marca q95/q98/q99 y marca interna son campos separados. q99 se utiliza como referencia común de comparación, no como alerta seleccionada retrospectivamente.

## 11. Modelo opcional

No se implementó LOF: los dos métodos obligatorios ya permiten comparar una regla explícita con una distribución multivariable. Se evita añadir un tercer modelo sin evidencia de que mejore la evaluación. Tampoco se implementan modelos supervisados, redes neuronales o LSTM.

## 12. Evaluación sin etiquetas

| model | period | eligible_rows | mean_score | median_score | max_score | marked_q99_rows | marked_q99_pct | marked_prisms | ks_distance_vs_training |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | entrenamiento | 2909 | 1.1404 | 0.7201 | 80.4633 | 30 | 1.0313 | 11 | 0 |
| baseline | validación | 1367 | 1.1726 | 0.9695 | 9.1225 | 5 | 0.3658 | 5 | 0.1731 |
| baseline | prueba | 1622 | 1.7513 | 1.3262 | 28.0212 | 74 | 4.5623 | 18 | 0.3503 |
| isolation_forest | entrenamiento | 2909 | 0.4028 | 0.387 | 0.857 | 30 | 1.0313 | 4 | 0 |
| isolation_forest | validación | 1367 | 0.4054 | 0.3927 | 0.709 | 3 | 0.2195 | 3 | 0.0854 |
| isolation_forest | prueba | 1622 | 0.4184 | 0.3998 | 0.7232 | 60 | 3.6991 | 15 | 0.1344 |

No se calculan accuracy, precision, recall, F1, AUC, sensibilidad ni especificidad sobre datos reales. Se usan distribución, estabilidad de rankings, coincidencia de conjuntos, marcación experimental, perfiles por prisma y pruebas artificiales. Los scores de métodos diferentes tienen escalas diferentes; no se restan ni se promedian como si fueran comparables.

La distancia KS mide cuánto se separan las distribuciones acumuladas respecto al entrenamiento; no se presenta un p-valor ni se supone independencia de observaciones temporales. Spearman mide asociación de rankings; Jaccard es intersección/unión de los conjuntos superiores, definidos con `ceil(fracción × elegibles)` y desempate determinista por ID.

## 13. Estabilidad temporal

En prueba, la distancia KS de la regla es 0.3503; la de Isolation Forest es 0.1344. Aumentan los scores y las marcas frente a validación; esto describe un cambio de distribución, no su causa ni una probabilidad de falla.

Se conservan perfiles por método, periodo y prisma: número elegible, porcentaje marcado, score, mediana de movimiento, intervalo mediano y representación en entrenamiento. El modelo global puede concentrar marcaciones en prismas de escala distinta. Un ejemplo es `30-1994`, presente solo en entrenamiento:

| model | prism_id | rows | eligible_rows | marked_q99_rows | marked_pct_of_eligible | median_elapsed_hours |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 30-1994 | 35 | 15 | 15 | 100 | 9.9763 |
| isolation_forest | 30-1994 | 35 | 15 | 15 | 100 | 9.9763 |

Que Isolation Forest marque sus 15 observaciones elegibles no convierte sus 35 mediciones originales en un diagnóstico. Debe revisarse la escala, frecuencia, referencia instrumental e historia de ese prisma. Los gráficos incluyen también prismas nuevos de validación para mostrar esta limitación.

## 14. Estabilidad entre semillas

Se utilizaron **42, 7, 2026, 101 y 1729**, manteniendo 42 como referencia previamente fijada. No se escoge la semilla que produzca resultados más convenientes. Resumen de las otras cuatro para los conjuntos superiores del 2%:

| period | rho_mínimo | rho_máximo | Jaccard_mínimo | Jaccard_máximo | marcación_mínima_pct | marcación_máxima_pct |
| --- | --- | --- | --- | --- | --- | --- |
| entrenamiento | 0.9782 | 0.9847 | 0.8438 | 0.873 | 1.0313 | 1.0313 |
| validación | 0.9805 | 0.9844 | 0.6471 | 0.8065 | 0.1463 | 0.2926 |
| prueba | 0.9793 | 0.9847 | 0.8333 | 0.8857 | 2.3428 | 3.9457 |

La correlación mínima es 0.9782 y el Jaccard mínimo 0.6471, superiores a las referencias técnicas previamente declaradas 0.9 y 0.5. `seed_stability.csv` incluye los principales 1%, 2% y 5%; `seed_score_variability.csv` registra media, dispersión y rango del score por observación. Un ranking estable puede coexistir con variación de la marca al cruzar un umbral.

## 15. Sensibilidad a hiperparámetros

Se evalúan 11 variantes, siempre reajustadas **solo sobre entrenamiento** y con la misma máscara de evaluación para una comparación justa. Se comparan contaminación, 100/200/400 árboles, 128/256/512 muestras, ausencia de escalado robusto y retirada de características de 7 días. Resultados en prueba:

| family | variant | selected_feature_count | ranking_spearman_vs_primary | jaccard_top_2pct_vs_primary | marked_q99_pct | marked_internal_pct |
| --- | --- | --- | --- | --- | --- | --- |
| contamination | 0.005 | 17 | 1 | 1 | 3.6991 | 0.3083 |
| contamination | 0.01 | 17 | 1 | 1 | 3.6991 | 3.6991 |
| contamination | 0.02 | 17 | 1 | 1 | 3.6991 | 6.1036 |
| contamination | 0.05 | 17 | 1 | 1 | 3.6991 | 9.4945 |
| contamination | auto | 17 | 1 | 1 | 3.6991 | 9.8644 |
| n_estimators | 100 | 17 | 0.9845 | 0.7838 | 2.9593 | 5.672 |
| n_estimators | 400 | 17 | 0.9959 | 0.8857 | 3.5142 | 6.1036 |
| max_samples | 128 | 17 | 0.987 | 0.8857 | 4.1307 | 5.857 |
| max_samples | 512 | 17 | 0.9862 | 0.8857 | 4.0691 | 6.1652 |
| transformation | training_median_no_scaler | 17 | 1 | 1 | 3.6991 | 6.1036 |
| feature_set | without_7d | 11 | 0.8909 | 0.7838 | 3.1443 | 4.439 |

Cambiar únicamente `contamination` deja los árboles y el ranking intactos con los demás parámetros y semilla fijados; cambia el offset interno y la carga de marcación. Por eso se comparan por separado el q99 aprendido y el corte interno. Retirar las variables de 7 días produce una correlación aproximada de 0,891 en prueba: la elección de características sí importa. No se reajusta el modelo principal después de mirar estos resultados ni se optimiza usando la fecha documental de falla.

## 16. Acuerdo entre modelos

| period | top_fraction | ranking_spearman | jaccard_top | common_top_rows | common_prisms | baseline_only_top_rows | forest_only_top_rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| entrenamiento | 0.01 | 0.4707 | 0.4286 | 18 | 3 | 12 | 12 |
| entrenamiento | 0.02 | 0.4707 | 0.2292 | 22 | 7 | 37 | 37 |
| entrenamiento | 0.05 | 0.4707 | 0.2066 | 50 | 16 | 96 | 96 |
| validación | 0.01 | 0.5515 | 0.2727 | 6 | 5 | 8 | 8 |
| validación | 0.02 | 0.5515 | 0.3333 | 14 | 10 | 14 | 14 |
| validación | 0.05 | 0.5515 | 0.3143 | 33 | 18 | 36 | 36 |
| prueba | 0.01 | 0.6674 | 0.2593 | 7 | 1 | 10 | 10 |
| prueba | 0.02 | 0.6674 | 0.375 | 18 | 6 | 15 | 15 |
| prueba | 0.05 | 0.6674 | 0.5922 | 61 | 14 | 21 | 21 |

En prueba, la asociación de rankings es aproximadamente 0,667 y el acuerdo de los principales 2% es Jaccard 0,375. La regla enfatiza z-score, tendencia y persistencia; el bosque evalúa combinaciones multivariables. El desacuerdo no constituye automáticamente un error. `method_only_observations.csv` conserva 70 casos marcados q99 por un solo método, con trazabilidad y explicación; no se etiquetan como falsos positivos o falsos negativos.

## 17. Resultados sintéticos

Se crean **14 escenarios artificiales** sobre copias de validación del prisma `40-1959`: siete tipos y dos intensidades. Se eligió por disponibilidad estructural de historial y número de observaciones de entrenamiento, sin usar su score ni la fecha documental de falla. Semilla 2026. La amplitud base es diez veces la dispersión robusta de los cambios de entrenamiento: 57.407090 mm; intensidad 3: 172.221270 mm. Son magnitudes de ensayo técnico, no límites geotécnicos.

Se modifica exclusivamente el movimiento reportado en copias y se recalculan sus características con el historial anterior y las mismas políticas de Fase 4. La progresión y la aceleración artificial utilizan tiempo transcurrido real. Los siete tipos son salto positivo, salto negativo, nivel sostenido, incremento progresivo, aceleración artificial, mayor variabilidad y secuencia persistente. Los modelos, imputador, escala y umbrales permanecen congelados. `synthetic_injection_audit.csv` contiene 152 filas modificadas con ID, timestamp, antes/después, delta, escenario y semilla.

| kind | intensity | model | target_rows | eligible_target_rows | marcación_sintética_pct | mean_score_change | mean_training_percentile | fondo_sin_etiqueta_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| positive_jump | 1 | baseline | 1 | 1 | 100 | 12.3358 | 99.5187 | 0.366 |
| positive_jump | 1 | isolation_forest | 1 | 1 | 0 | 0.2282 | 98.7625 | 0.2196 |
| positive_jump | 3 | baseline | 1 | 1 | 100 | 36.8865 | 99.6906 | 0.366 |
| positive_jump | 3 | isolation_forest | 1 | 1 | 100 | 0.3253 | 99.4844 | 1.0249 |
| negative_jump | 1 | baseline | 1 | 1 | 100 | 11.4915 | 99.5187 | 0.366 |
| negative_jump | 1 | isolation_forest | 1 | 1 | 0 | 0.2184 | 98.5906 | 0.2196 |
| negative_jump | 3 | baseline | 1 | 1 | 100 | 36.0422 | 99.6906 | 0.366 |
| negative_jump | 3 | isolation_forest | 1 | 1 | 100 | 0.2944 | 99.4156 | 0.8785 |
| sustained_level | 1 | baseline | 46 | 45 | 100 | 10.2545 | 99.5057 | 0.3782 |
| sustained_level | 1 | isolation_forest | 46 | 45 | 17.7778 | 0.1273 | 91.9392 | 0.2269 |
| sustained_level | 3 | baseline | 46 | 45 | 100 | 31.1033 | 99.6364 | 0.3782 |
| sustained_level | 3 | isolation_forest | 46 | 45 | 51.1111 | 0.1666 | 94.0086 | 0.2269 |
| progressive_increment | 1 | baseline | 7 | 7 | 85.7143 | 6.8116 | 98.1928 | 0.3676 |
| progressive_increment | 1 | isolation_forest | 7 | 7 | 42.8571 | 0.1571 | 86.7407 | 0.2941 |
| progressive_increment | 3 | baseline | 7 | 7 | 100 | 20.1706 | 99.5138 | 0.7353 |
| progressive_increment | 3 | isolation_forest | 7 | 7 | 71.4286 | 0.2459 | 98.0111 | 1.1029 |
| artificial_acceleration | 1 | baseline | 7 | 7 | 42.8571 | 4.4025 | 89.9327 | 0.3676 |
| artificial_acceleration | 1 | isolation_forest | 7 | 7 | 14.2857 | 0.0882 | 69.091 | 0.2941 |
| artificial_acceleration | 3 | baseline | 7 | 7 | 85.7143 | 13.1052 | 94.323 | 0.3676 |
| artificial_acceleration | 3 | isolation_forest | 7 | 7 | 42.8571 | 0.1863 | 83.804 | 0.9559 |
| increased_variability | 1 | baseline | 7 | 7 | 71.4286 | 8.6242 | 98.1044 | 0.3676 |
| increased_variability | 1 | isolation_forest | 7 | 7 | 57.1429 | 0.2364 | 98.954 | 0.3676 |
| increased_variability | 3 | baseline | 7 | 7 | 100 | 27.7976 | 99.6219 | 0.3676 |
| increased_variability | 3 | isolation_forest | 7 | 7 | 100 | 0.2905 | 99.45 | 0.8824 |
| persistent_increases | 1 | baseline | 7 | 7 | 85.7143 | 6.3961 | 98.3205 | 0.3676 |
| persistent_increases | 1 | isolation_forest | 7 | 7 | 42.8571 | 0.1521 | 86.5148 | 0.2941 |
| persistent_increases | 3 | baseline | 7 | 7 | 100 | 19.7551 | 99.5187 | 0.6618 |
| persistent_increases | 3 | isolation_forest | 7 | 7 | 71.4286 | 0.2448 | 98.0258 | 1.1029 |

| Método | Media de marcación sintética por escenario % |
| --- | --- |
| baseline | 90.8163 |
| isolation_forest | 50.839 |

Esta media asigna el mismo peso a cada escenario; **no es precisión real ni recall de fallas**. Son escenarios solapados sobre un solo prisma, no 14 eventos independientes. El cambio sostenido modifica 46 filas por intensidad, de las cuales 45 son elegibles. En total hay 152 posiciones objetivo entre escenarios, 150 elegibles por método; su suma no representa filas reales independientes.

La regla marca más de estas modificaciones con q99; Isolation Forest no marca los saltos de intensidad 1 y solo marca 1/7 de la aceleración artificial de esa intensidad. Su score aumenta aun cuando no cruza q99. La media cercana al 50% del bosque no debe ocultar esas diferencias por tipo. No se ajustaron umbrales para mejorar los casos.

La **tasa de marcación del conjunto de fondo sin etiqueta** se calcula sobre las filas elegibles no modificadas. No es una tasa de falsos positivos: pueden existir comportamientos atípicos desconocidos y algunas ventanas posteriores incorporan la modificación artificial, aunque la fila actual del fondo no se haya editado. Los datos reales nunca se sobrescriben.

## 18. Carga de revisión

Con q99 como referencia experimental, la regla marca 109 observaciones y el bosque 93 en todo el registro; pueden coincidir. Los porcentajes usan únicamente filas elegibles. No se define un flujo operativo de revisión ni una alerta combinada.

| model | máximo_diario | días_sin_marcaciones | días_sin_elegibles |
| --- | --- | --- | --- |
| baseline | 25 | 62 | 6 |
| isolation_forest | 24 | 64 | 6 |

Los seis días sin datos elegibles están incluidos en los días sin marcaciones y deben distinguirse de días efectivamente evaluados sin marca. La carga diaria no equivale a tiempo de trabajo: todavía no se conoce cuánto tarda el especialista en revisar una observación ni cómo agrupar múltiples observaciones de un mismo prisma.

Concentración por periodo y método:

| model | period | marked_rows | marked_pct | prisms_affected | top_prism_share_of_marked_pct | top_three_prisms_share_of_marked_pct |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | entrenamiento | 30 | 1.0313 | 11 | 50 | 70 |
| baseline | validación | 5 | 0.3658 | 5 | 20 | 60 |
| baseline | prueba | 74 | 4.5623 | 18 | 14.8649 | 41.8919 |
| isolation_forest | entrenamiento | 30 | 1.0313 | 4 | 50 | 96.6667 |
| isolation_forest | validación | 3 | 0.2195 | 3 | 33.3333 | 100 |
| isolation_forest | prueba | 60 | 3.6991 | 15 | 16.6667 | 45 |

Los cortes q95 y q98 y el umbral interno están documentados en `threshold_sensitivity.csv` (21 combinaciones método/umbral/periodo). El 5% de filas elegibles es solo una referencia técnica previamente declarada, **no capacidad de revisión validada ni umbral geomecánico**. En prueba ambos q99 individuales quedan por debajo de esa referencia; eso no valida una política de combinar sus marcas.

## 19. Explicabilidad

Cada fila elegible conserva las tres mayores desviaciones absolutas del valor respecto a la mediana e IQR de entrenamiento, con valores y unidades originales. Se añaden z-score histórico, pendiente, racha y calidad. Esta explicación es **aproximada y descriptiva**, no una atribución exacta de los árboles, importancia causal ni diagnóstico. Una desviación grande puede coexistir con otras combinaciones influyentes no capturadas por esa descripción.

Cinco mayores puntuaciones globales del bosque, todas de entrenamiento:

| prism_id | timestamp | period | isolation_forest_score | movement_rate_mm_per_day | historical_robust_z_score | local_trend_72h_slope_mm_per_day |
| --- | --- | --- | --- | --- | --- | --- |
| 30-1994 | 2013-12-13 19:06:49 | entrenamiento | 0.857 | 278.1774 | 35.1208 | 288.5763 |
| 30-1994 | 2013-12-11 10:04:25 | entrenamiento | 0.8513 | 406.1734 | 31.8509 | 450.1665 |
| 30-1994 | 2013-12-11 18:33:03 | entrenamiento | 0.8513 | 384.5958 | 30.5692 | 435.1497 |
| 30-1994 | 2013-12-14 18:08:30 | entrenamiento | 0.8484 | 416.4595 | 28.4484 | 234.5497 |
| 30-1994 | 2013-12-10 18:59:13 | entrenamiento | 0.847 | 411.0213 | 28.7943 | 540.8758 |

Para la primera observación: Puntuación experimental elevada; mayores desviaciones descriptivas respecto al entrenamiento: movement_7d_mad_mm=902.2 mm; local_trend_7d_slope_mm_per_day=446 mm/día; movement_7d_range_mm=2654 mm. Z robusto previo=35.1; tendencia 72h=289 mm/día; racha=10 incrementos. Calidad: características parciales. Explicación aproximada; no contribución exacta de Isolation Forest ni diagnóstico geomecánico.

La concentración en `30-1994` muestra la importancia de revisar escala e historia del prisma antes de atribuir un significado profesional. `top_scored_observations.csv` contiene las 30 mayores observaciones globales; `anomaly_scores.csv` conserva explicaciones para las 7.178 filas, incluidas las razones de no evaluación. `feature_descriptive_deviations.csv` resume desviaciones entre las principales observaciones; no se denomina importancia predictiva de características.

## 20. Modelo recomendado

Se recomienda provisionalmente un **enfoque de comparación con ambas puntuaciones**, manteniendo la regla como referencia interpretable y el bosque como complemento multivariable. No se define una combinación operativa de marcas. No existe evidencia para declarar cuál es más preciso sobre comportamientos geotécnicos reales.

| Criterio previo | Evidencia obtenida | Alcance |
| --- | --- | --- |
| Reproducibilidad | Recarga y reproducción exactas de estado aprendido y scores de ambos métodos | Comprobación técnica |
| Correlación de rankings entre semillas ≥ 0,9 | Mínimo 0.9782 en el bosque | Rankings estables; la regla es determinista |
| Jaccard de top 2% entre semillas ≥ 0,5 | Mínimo 0.6471 | Coincidencia parcial, no etiquetas |
| Marcación sintética media por escenario ≥ 0,5 | Regla 90.82%; bosque 50.84% | El bosque queda apenas por encima y falla en varios tipos/intensidades |
| Referencia de revisión ≤ 5% | q99 de prueba: regla 4,56%; bosque 3,70% | Referencia técnica; capacidad real pendiente |
| Interpretabilidad | Fórmula explícita y desviaciones descriptivas | Más directa en la regla; aproximada en el bosque |
| Ejecución offline e integración | Joblib, JSON, funciones Python, sin servicios externos | Requiere datos con historial y características |
| Inferencia y tamaño | 0.0630 s para 100 observaciones elegibles con ambos scores; bosque 433,200 bytes | Medición local, no garantía de latencia |

El pipeline completo tardó 33.583 s en este entorno, incluida evaluación y sintéticos. El criterio de estabilidad temporal se revisa descriptivamente: existe deriva de scores y concentración por prisma, por lo que no se declara invariancia temporal ni validez fuera del caso. Los criterios son apoyos para comparación, no una puntuación de seguridad. `provisional_recommendation.json` conserva la recomendación y evidencia cuantitativa.

## 21. Limitaciones

- Un solo caso y ausencia de etiquetas reales; no hay evidencia de generalización a otras minas ni capacidad de anticipar fallas.
- Correlación temporal, ventanas solapadas y múltiples mediciones de un mismo prisma; no son eventos de falla independientes.
- El bosque global puede destacar escalas o frecuencias poco representadas, como `30-1994`; los nuevos prismas requieren evaluación específica.
- Un score estable ante semillas no garantiza relevancia geomecánica. Se observan deriva temporal y sensibilidad al conjunto de características.
- Los experimentos sintéticos cubren un prisma y magnitudes definidas; varios cambios de intensidad 1 no superan q99 en el bosque.
- No elegibles permanecen desconocidos; la cobertura aumenta con la historia, pero seis días carecen de observaciones elegibles.
- La imputación opcional está implementada, aunque no fue necesaria en este conjunto elegible; no recupera información geotécnica perdida.
- South West mantiene campos con unidades que requieren validación; lluvia desconocida sigue desconocida. Ninguna fuente se une a West Wall.
- Las explicaciones son desviaciones descriptivas, no contribuciones exactas ni causalidad. No se han definido capacidad de revisión, niveles de atención o reglas operativas.
- La recarga y reproducción exactas se comprobaron con las versiones registradas. Otros entornos o bibliotecas pueden modificar detalles numéricos.

Errores de ejecución pendientes en las comprobaciones realizadas: ninguno. Permanecen decisiones científicas y de producto, detalladas para revisión profesional.

## 22. Pruebas realizadas

Se ejecutaron primero las **113 pruebas anteriores** sin cambios. La suite final contiene **147 pruebas aprobadas**, 0 fallidas y 0 omitidas, en 21.06 s; 34 son nuevas. Evidencia: `pytest-before.txt`, `pytest-development.txt`, `pytest-output.txt`, `pytest-results.xml` y `verification-log.txt`.

| Grupo de aceptación | Evidencia |
| --- | --- |
| Orden cronológico, timestamps iguales, sin mezcla aleatoria | `test_temporal_split.py` y verificación de días completos |
| Selector, constantes, vacíos, redundancia, IDs, auditoría | `test_feature_selection.py`, matrices y tabla de exclusiones |
| Imputador y escalador solo de entrenamiento | `test_model_preprocessing.py`, metadatos y prueba crítica |
| Semilla fija, cambio controlado, score, umbrales, percentiles | `test_anomaly_models.py` y tablas de estabilidad |
| Elegibilidad, NaN y marcas desconocidas | `test_anomaly_models.py` y comprobación sobre las 7.178 filas reales |
| Sintéticos, auditoría, datos reales intactos, saltos/nivel/aceleración | `test_synthetic_anomalies.py` y 14 escenarios evaluados |
| Explicaciones, serialización y recarga exacta | `test_anomaly_models.py` y `verify_phase5.py` |
| Sin fuga, 294 archivos intactos, reproducción completa | `test_phase5_no_leakage.py` y `verify_phase5.py --reproduce` |

Las pruebas unitarias de respuesta a perturbaciones muy fuertes utilizan datos artificiales y amplitud de 5.000 mm; **no sustituyen** los resultados de los 14 ensayos controlados con amplitudes de 57/172 mm sobre copias del caso real. La suite comprueba funcionamiento, no rendimiento geomecánico. Se añadieron también casos de configuración inválida para umbrales y parámetros del bosque.

## 23. Integridad y reproducibilidad

Fuente SHA-256: `4fb5d7fc0e456c3e644186c56c5c149d910635e1e742141cb111237cb1c8e452`. Se verifican los 294 archivos del manifiesto anterior antes/después; se conservan código, pruebas, datos e informes de las Fases 1–4. README y `.gitignore` reciben únicamente documentación de la nueva fase. Checkpoint final de Fase 4: `00b80d9e14f7e49b4d0c338f34d0670299669fb7`. Checkpoint inicial de Fase 5: `11c2a12d3576c739e2e4756f7549ea4e5dacd7b8`. El hash final se registra tras el commit en `reports/phase5/git_checkpoint.txt`, incluido en el paquete.

La verificación incluye las 7.178 filas, 49 prismas, estado desconocido de no elegibles, tipos, scores, percentiles, calendario, 17 pares PNG/HTML y hashes de los artefactos. Al recargar, el preprocesador produce matrices idénticas y los modelos scores idénticos. La reproducción completa comprueba **24 CSV byte a byte**, los JSON de modelos y todos los campos aprendidos de los árboles.

Prueba crítica: se modifican únicamente 20 candidatos en **3261 filas de validación y prueba**, usando valores alternados muy grandes; la selección, imputador, escalador, parámetros, todos los nodos y valores de árboles, regla, umbrales y scores de las **3917 filas de entrenamiento** permanecen exactamente iguales. Esto prueba ausencia de esa vía de fuga; no demuestra causalidad científica.

Los Joblib actuales se verifican por SHA-256 contra metadatos. Al repetir el entrenamiento se compara el **estado aprendido completo**, no los bytes de representación interna del objeto: alias de memoria y relleno de estructuras pueden variar sin cambiar parámetros o predicciones. El fingerprint incluye todos los campos de nodos y valores de cada árbol, escalas, imputación y parámetros. Tiempos de ejecución se almacenan separados y se excluyen de la comparación determinista.

Comandos desde la raíz, una vez instaladas las dependencias:

```bash
python scripts/verify_phase5.py
# Recalcula en una carpeta temporal y prueba la invariancia de entrenamiento:
python scripts/verify_phase5.py --reproduce
python -m pytest -q --junitxml=reports/phase5/pytest-results.xml > reports/phase5/pytest-output.txt
python scripts/build_phase5_report.py
```

Para regenerar las salidas de esta fase: `python scripts/run_phase5.py`; lee y protege los resultados anteriores y solo escribe Fase 5. Las salidas se ejecutaron realmente antes de afirmar su funcionamiento.

## 24. Recomendaciones para la Fase 6

**Puede proponerse avanzar técnicamente, únicamente después de aprobación formal**, porque se cumplen conservación, cronología, aprendizaje en entrenamiento, reproducibilidad y pruebas. La propuesta es integrar puntuaciones experimentales y sus motivos en el alcance que apruebe la usuaria; esto no autoriza automáticamente alertas operativas.

Antes de definirlas, el ingeniero debe revisar la referencia del movimiento, escalas/frecuencias de prismas, tratamiento de no elegibles, elección de umbrales y capacidad real de revisión. También se necesitan casos y etiquetas independientes para evaluar utilidad profesional. Mantener puntuaciones y calidad separadas, documentar el desacuerdo, y distinguir repetidas mediciones de un único episodio. No presentar el 5% experimental como una capacidad de trabajo validada.

No se avanza en este trabajo a dashboard, Streamlit, SQLite, APIs, modelos adicionales, uniones con lluvia/sismicidad/voladuras, detección de cambios ni despliegue. Se detiene la fase para revisión.

## 25. Archivos creados y modificados

Los siete módulos solicitados se crean nuevos. Se añaden cuatro módulos auxiliares por razones concretas: `phase5_config.py` aísla validación de la configuración anterior; `temporal_split.py` hace explícita la partición global; `model_validation.py` verifica estado aprendido y fuga; `phase5_visualizations.py` separa gráficos de entrenamiento. No se modifica código ni pruebas anteriores.

```text
monitoreo-taludes/
├── README.md                         [modificado: instrucciones Fase 5]
├── .gitignore                        [modificado: artefactos reproducibles]
├── requirements-phase5.txt           [nuevo]
├── config/phase5.json
├── src/
│   ├── phase5_config.py
│   ├── temporal_split.py
│   ├── feature_selection.py
│   ├── model_preprocessing.py
│   ├── anomaly_baseline.py
│   ├── anomaly_models.py
│   ├── anomaly_evaluation.py
│   ├── synthetic_anomalies.py
│   ├── model_explanations.py
│   ├── model_validation.py
│   └── phase5_visualizations.py
├── scripts/
│   ├── run_phase5.py
│   ├── verify_phase5.py
│   └── build_phase5_report.py
├── tests/
│   ├── phase5_helpers.py
│   ├── test_feature_selection.py
│   ├── test_temporal_split.py
│   ├── test_model_preprocessing.py
│   ├── test_anomaly_models.py
│   ├── test_synthetic_anomalies.py
│   └── test_phase5_no_leakage.py
├── models/phase5/
│   ├── preprocessing_pipeline.joblib
│   ├── isolation_forest.joblib         [pipeline completo]
│   ├── scoring_bundle.joblib           [ambos scores, elegibilidad y referencias]
│   ├── statistical_baseline.json
│   ├── selected_features.json
│   └── model_metadata.json
├── data/processed/phase5/anomaly_scores.csv
└── reports/
    ├── documentation/phase5_terminology.md
    └── phase5/
        ├── model_findings.md
        ├── candidate_features.csv
        ├── selected_features.csv
        ├── excluded_features.csv
        ├── spearman_training.csv, pearson_training.csv, pair_redundancy.csv
        ├── temporal_split_summary.csv, ineligibility_summary.csv
        ├── model_comparison.csv, threshold_sensitivity.csv
        ├── seed_stability.csv, seed_score_variability.csv
        ├── hyperparameter_sensitivity.csv, contamination_sensitivity.csv
        ├── model_agreement.csv, method_only_observations.csv
        ├── prism_score_profiles.csv, review_workload.csv
        ├── synthetic_anomaly_results.csv, synthetic_injection_audit.csv
        ├── synthetic_target_scores.csv
        ├── top_scored_observations.csv, feature_descriptive_deviations.csv
        ├── phase5_metadata.json, provisional_recommendation.json
        ├── protected_before_phase5.json, reproducibility.json
        ├── execution_stats.json, execution_log.txt, verification-log.txt
        ├── pytest-before.txt, pytest-development.txt, pytest-output.txt
        ├── pytest-results.xml, git_initial.txt, git_checkpoint.txt
        ├── figures/                    [17 PNG]
        └── interactive/                [17 HTML y plotly.min.js local]
```

Los datos derivados, modelos y gráficos se incluyen en el paquete descargable; los archivos voluminosos regenerables se excluyen de Git. El paquete conserva los originales y resultados históricos y no incluye el directorio interno `.git`, entornos o cachés. No hay credenciales. Al descomprimir se mantienen las rutas.

Visualizaciones descriptivas entregadas; los HTML usan `interactive/plotly.min.js` local y funcionan sin internet:

| Visualización | Imagen | Interactiva |
| --- | --- | --- |
| Regla estadística: distribución por periodo | [PNG](figures/baseline_distribution.png) | [HTML](interactive/baseline_distribution.html) |
| Regla estadística: scores reales en el tiempo | [PNG](figures/baseline_time.png) | [HTML](interactive/baseline_time.html) |
| Isolation Forest: distribución por periodo | [PNG](figures/isolation_forest_distribution.png) | [HTML](interactive/isolation_forest_distribution.html) |
| Isolation Forest: scores reales en el tiempo | [PNG](figures/isolation_forest_time.png) | [HTML](interactive/isolation_forest_time.html) |
| Principales observaciones puntuadas por Isolation Forest | [PNG](figures/top_observations.png) | [HTML](interactive/top_observations.html) |
| Marcación experimental diaria: umbral q99 de entrenamiento | [PNG](figures/daily_marking.png) | [HTML](interactive/daily_marking.html) |
| Marcación experimental por prisma; periodos combinados | [PNG](figures/prism_marking.png) | [HTML](interactive/prism_marking.html) |
| Estabilidad entre semillas: ninguna se elige por conveniencia | [PNG](figures/seed_stability.png) | [HTML](interactive/seed_stability.html) |
| Sensibilidad a contaminación; score continuo separado del umbral | [PNG](figures/contamination_sensitivity.png) | [HTML](interactive/contamination_sensitivity.html) |
| Acuerdo de rankings entre regla estadística e Isolation Forest | [PNG](figures/method_agreement.png) | [HTML](interactive/method_agreement.html) |
| Solo pruebas sintéticas: siete alteraciones y dos intensidades | [PNG](figures/synthetic_sensitivity.png) | [HTML](interactive/synthetic_sensitivity.html) |
| Desviaciones aproximadas en las 20 observaciones con mayor score | [PNG](figures/descriptive_feature_deviations.png) | [HTML](interactive/descriptive_feature_deviations.html) |
| Datos reales y scores: prisma 40-1959 | [PNG](figures/model_prism_40_1959.png) | [HTML](interactive/model_prism_40_1959.html) |
| Datos reales y scores: prisma 40-1928 | [PNG](figures/model_prism_40_1928.png) | [HTML](interactive/model_prism_40_1928.html) |
| Datos reales y scores: prisma 40-1933 | [PNG](figures/model_prism_40_1933.png) | [HTML](interactive/model_prism_40_1933.html) |
| Datos reales y scores: prisma 22-2059 | [PNG](figures/model_prism_22_2059.png) | [HTML](interactive/model_prism_22_2059.html) |
| Datos reales y scores: prisma 22-2060 | [PNG](figures/model_prism_22_2060.png) | [HTML](interactive/model_prism_22_2060.html) |

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.

**Fin de Fase 5. Se espera revisión y aprobación formal antes de comenzar la Fase 6.**
