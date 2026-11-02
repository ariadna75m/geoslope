# Fase 6 — Episodios temporales y candidatos para revisión

## 1. Resumen ejecutivo

**Estado técnico: aprobada con observaciones; validación geotécnica pendiente.** Se procesan las **7.178 filas de 49 prismas**, manteniendo **5.898 evaluables y 1.280 no evaluables**. Se conservan modelos, 17 características, scores, umbrales y particiones anteriores.

La ventana provisional de 72 h genera **48 episodios en 33 prismas** a partir de 136 marcas de unión, con 66 coincidencias. La híbrida selecciona **102 registros, 20 episodios y 17 prismas**, una reducción de **25.000000% de filas** frente a unión. Hay cuatro episodios con una interrupción de calidad cada uno; ninguno es seleccionado por híbrida, por lo que siguen disponibles para revisión separada. La suite actual pasa **200 pruebas: 158 anteriores y 42 nuevas**. La causalidad de la agrupación está condicionada a los scores congelados; los estados de entrenamiento son retrospectivos, no una simulación operativa en su fecha original.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.

## 2. Objetivo

Organizar marcas estadísticas individuales en cadenas temporales por prisma y candidatos interpretables para revisión humana. No se estima un evento físico ni se habilitan decisiones operativas. Hechos observados, decisiones técnicas y supuestos se distinguen en las secciones siguientes.

## 3. Entradas utilizadas

- `data/processed/phase5/anomaly_scores.csv`: 7.178 filas y sus 30 columnas originales; SHA-256 `dd36d91c8edf841966bffbbdde05a9c7a46ca8ddee7e40c14a19bd547b90930e`.
- `data/processed/phase4/west_wall_features.csv`: evidencia existente enlazada uno a uno mediante `source_record_id`, con comprobación de prisma y timestamp. Se leen solo los campos necesarios para explicaciones y gráficos durante la construcción; no se recalculan características.
- Joblib de scoring, bosque y preprocesamiento, JSON de modelos, regla, configuración y metadatos de Fase 5 para comprobar congelación.
- `config/phase6.json`: decisiones técnicas explícitas; no contiene una fecha de falla ni un parámetro ajustado con ese evento.

Entrenamiento hasta el 14-ene-2014; validación 15-ene a 1-feb; prueba 2-feb a 20-feb. La fuente termina 2014-02-20 09:17:53. Se conserva el timestamp reportado, sin atribuirle una zona horaria no documentada. Las fuentes meteorológicas, sísmicas y South West no se incorporan a este análisis.

## 4. Confirmación de modelos congelados

| n_estimators | max_samples | max_features | tipo | características disponibles por árbol | bootstrap | random_state | contamination | n_jobs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | 256 | 1.0 | float | 17 | False | 42 | 0.02 | 1 |

| Método | q99 exacto | q99 redondeado |
| --- | --- | --- |
| baseline | 4.439772224885318 | 4.4398 |
| isolation_forest | 0.5872931971929567 | 0.5873 |

Se utilizan los valores exactos de JSON; **4,4398 y 0,5873 son representaciones redondeadas**, no nuevos umbrales. Marcas = score estrictamente mayor que q99. Los tres Joblib se mantienen por hash y la recarga del bundle reproduce todas las predicciones de Fase 5. Estado aprendido SHA-256 `7e0b6cb2cf6ea9d6614813800d48609362407e8dd5bc75416980008677954f07`. Ningún modelo se ajusta en esta fase.

## 5. Definición de marca, episodio y candidato

**Marca:** observación evaluable que supera q99 en al menos un método. **Episodio:** cadena de marcas del mismo prisma con separación consecutiva ≤ ventana; admite registros intermedios sin marca y no evaluables. **Candidato:** fila con marca actual seleccionada por una política explícita.

La primera marca crea un ID derivado de versión, prisma, `source_record_id` inicial y ventana, sin número de fila ni información futura. El ID permanece estable al añadir futuro. El máximo intervalo entre marcas no es la duración máxima de una cadena. Los últimos episodios se consideran censurados al finalizar las observaciones del propio prisma, evitando inferir cierre por falta de información de ese prisma.

## 6. Lógica causal

Orden estable por prisma, timestamp e identificador; timestamps duplicados dentro del prisma se rechazan. Ventanas **[t−h,t] inclusivas** con h=24/48/72; incluyen únicamente marcas conocidas hasta t, incluida la actual. `hours_since_previous_mark` mide desde la marca estrictamente anterior, y es desconocido si no hay marca anterior.

Jerarquía: no evaluable → sin marca → candidato según política principal → episodio en observación cuando hay al menos dos marcas recientes → marca aislada. Para la híbrida con mínimo 2, todas las marcas persistentes son candidatas; por ello el estado principal `episodio_en_observacion` tiene cero filas. Sigue siendo un estado implementado y comprobado con mínimo 3. Los registros sin marca pueden pertenecer a un episodio, pero conservan el estado `sin_marca`.

| causal_state | rows |
| --- | --- |
| no_evaluable | 1280 |
| sin_marca | 5762 |
| marca_aislada | 34 |
| episodio_en_observacion | 0 |
| candidato_revision | 102 |

**Separación explícita:** `review_candidates.csv` contiene estados y conteos agregados a partir de registros con fecha ≤ la fila actual, condicionados a las marcas ya guardadas, junto con los scores congelados y su ámbito de disponibilidad; `episodes.csv` contiene máximos, duración final y cierre retrospectivos. Estos últimos no vuelven a modificar estados anteriores. Se permite continuidad entre particiones: 1 episodio atraviesa una frontera, utilizando exclusivamente historia anterior al agregar cada registro.

**Alcance y observación importante:** la agrupación es causal **condicionada a las marcas congeladas**. El modelo de Fase 5 se ajustó con todo entrenamiento; sus scores en ese mismo periodo son retrospectivos y no estaban disponibles en la fecha original de cada medición. `model_available_from_timestamp` conserva la frontera 15-ene-2014 y `model_available_at_observation=False` en entrenamiento; validación/prueba tienen ese indicador verdadero. Se conserva la elegibilidad original, independiente de disponibilidad del modelo. Los estados de entrenamiento describen una organización histórica, no un seguimiento operativo en esas fechas. Las pruebas de prefijos comprueban la agregación, sin afirmar que el ajuste previo ocurrió antes de todas las mediciones históricas.

Este indicador representa disponibilidad conforme al protocolo de evaluación temporal, no una fecha real de instalación del modelo en una mina.

## 7. Tratamiento de registros no evaluables

Las 1.280 filas conservan el motivo exacto, scores y marcas desconocidos. No se rellenan con cero ni False. Los conteos temporales cuentan solo marcas conocidas; un conteo de cero no convierte el estado actual desconocido en ausencia comprobada de marca.

`quality_interruption_flag` se activa en la fila no evaluable y permanece activado en las filas posteriores del mismo episodio una vez observada una interrupción. Hay **1294 filas con ese indicador**; no deben confundirse con 1.280 filas no evaluables. Solo **4** registros no evaluables caen dentro de episodios activos; los restantes no se asignan retrospectivamente a un episodio futuro.

| episode_id | prism_id | start_timestamp | ineligible_record_count | union_mark_count | candidate_policies |
| --- | --- | --- | --- | --- | --- |
| ep_cedab9c87ff036231911a591 | 22-2061 | 2014-02-16 23:41:11 | 1 | 1 | union |
| ep_85c97737d0536095f7c40d79 | 30-1996 | 2014-01-28 16:59:15 | 1 | 1 | union |
| ep_04c18610c13e7a1a478764db | 31-1977 | 2014-02-08 18:05:13 | 1 | 1 | union |
| ep_1e361ac6962998df4992d010 | 31-1977 | 2014-02-15 18:13:32 | 1 | 1 | union |

Estas interrupciones no cierran por sí mismas el episodio. Si un registro posterior revela una separación > ventana respecto a la última marca, se cierra por la regla temporal, sea o no evaluable. Se conservan las 34 marcas no seleccionadas en una tabla auxiliar.

## 8. Políticas comparadas

| Política | Regla causal exacta |
| --- | --- |
| A — Unión | Marca base OR marca IF en el registro actual |
| B — Consenso | Marca base AND marca IF en el registro actual |
| C — Persistencia | Marca actual AND al menos 2 marcas de unión del prisma en [t−72 h,t] |
| D — Híbrida | Consenso actual OR persistencia anterior |

**Decisión técnica explícita:** exigir marca actual en C/D evita extender candidatos a registros sin marca y hace que las políticas sean subconjuntos de unión. La calidad se conserva como una dimensión independiente. No existe clasificación geotécnica automática.

## 9. Resultados por política

| period | policy | candidate_rows | candidate_episodes | candidate_prisms | mean_candidates_per_day | maximum_daily_candidates | row_reduction_vs_union_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| total | union | 136 | 48 | 33 | 1.462366 | 29 | 0 |
| total | consensus | 66 | 17 | 16 | 0.709677 | 20 | 51.470588 |
| total | persistence | 88 | 13 | 13 | 0.946237 | 24 | 35.294118 |
| total | hybrid | 102 | 20 | 17 | 1.096774 | 27 | 25 |
| entrenamiento | union | 42 | 16 | 12 | 0.75 | 4 | 0 |
| entrenamiento | consensus | 18 | 4 | 3 | 0.321429 | 2 | 57.142857 |
| entrenamiento | persistence | 26 | 3 | 3 | 0.464286 | 4 | 38.095238 |
| entrenamiento | hybrid | 30 | 5 | 4 | 0.535714 | 4 | 28.571429 |
| validación | union | 6 | 6 | 6 | 0.333333 | 3 | 0 |
| validación | consensus | 2 | 2 | 2 | 0.111111 | 1 | 66.666667 |
| validación | persistence | 0 | 0 | 0 | 0 | 0 | 100 |
| validación | hybrid | 2 | 2 | 2 | 0.111111 | 1 | 66.666667 |
| prueba | union | 88 | 26 | 22 | 4.631579 | 29 | 0 |
| prueba | consensus | 46 | 11 | 11 | 2.421053 | 20 | 47.727273 |
| prueba | persistence | 62 | 10 | 10 | 3.263158 | 24 | 29.545455 |
| prueba | hybrid | 70 | 13 | 13 | 3.684211 | 27 | 20.454545 |

Entre las cuatro políticas principales, consenso reduce más filas: 51.470588%. La híbrida conserva 36 filas adicionales seleccionadas por persistencia sin coincidencia actual. El detalle y los efectos sobre calidad están en [policy_comparison.md](policy_comparison.md).

## 10. Análisis de sensibilidad

| window_hours | min_marks | policy | candidate_rows | candidate_episodes | candidate_prisms | row_reduction_vs_union_pct | maximum_daily_candidates | median_episode_duration_hours | median_marks_per_episode | episodes_with_agreement | episodes_with_quality_interruption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | 2 | union | 136 | 58 | 33 | 0 | 29 | 19.452917 | 1 | 22 | 1 |
| 24 | 2 | consensus | 66 | 22 | 16 | 51.470588 | 20 | 23.879306 | 2.5 | 22 | 0 |
| 24 | 2 | persistence | 78 | 19 | 13 | 42.647059 | 21 | 38.739167 | 4 | 14 | 0 |
| 24 | 2 | hybrid | 98 | 27 | 17 | 27.941176 | 26 | 23.894722 | 2 | 22 | 0 |
| 24 | 3 | union | 136 | 58 | 33 | 0 | 29 | 19.452917 | 1 | 22 | 1 |
| 24 | 3 | consensus | 66 | 22 | 16 | 51.470588 | 20 | 23.879306 | 2.5 | 22 | 0 |
| 24 | 3 | persistence | 53 | 11 | 9 | 61.029412 | 15 | 47.405833 | 6 | 10 | 0 |
| 24 | 3 | hybrid | 88 | 23 | 16 | 35.294118 | 22 | 23.894722 | 3 | 22 | 0 |
| 48 | 2 | union | 136 | 51 | 33 | 0 | 29 | 43.912778 | 1 | 18 | 2 |
| 48 | 2 | consensus | 66 | 18 | 16 | 51.470588 | 20 | 52.404583 | 3.5 | 18 | 0 |
| 48 | 2 | persistence | 85 | 15 | 13 | 37.5 | 24 | 70.597778 | 7 | 11 | 0 |
| 48 | 2 | hybrid | 101 | 22 | 17 | 25.735294 | 27 | 53.801528 | 3 | 18 | 0 |
| 48 | 3 | union | 136 | 51 | 33 | 0 | 29 | 43.912778 | 1 | 18 | 2 |
| 48 | 3 | consensus | 66 | 18 | 16 | 51.470588 | 20 | 52.404583 | 3.5 | 18 | 0 |
| 48 | 3 | persistence | 67 | 12 | 10 | 50.735294 | 20 | 79.997083 | 8 | 10 | 0 |
| 48 | 3 | hybrid | 93 | 20 | 16 | 31.617647 | 25 | 59.707639 | 3.5 | 18 | 0 |
| 72 | 2 | union | 136 | 48 | 33 | 0 | 29 | 66.844306 | 1 | 17 | 4 |
| 72 | 2 | consensus | 66 | 17 | 16 | 51.470588 | 20 | 69.845556 | 3 | 17 | 0 |
| 72 | 2 | persistence | 88 | 13 | 13 | 35.294118 | 24 | 70.597778 | 9 | 10 | 0 |
| 72 | 2 | hybrid | 102 | 20 | 17 | 25 | 27 | 69.858194 | 3 | 17 | 0 |
| 72 | 3 | union | 136 | 48 | 33 | 0 | 29 | 66.844306 | 1 | 17 | 4 |
| 72 | 3 | consensus | 66 | 17 | 16 | 51.470588 | 20 | 69.845556 | 3 | 17 | 0 |
| 72 | 3 | persistence | 74 | 12 | 12 | 45.588235 | 20 | 70.547361 | 9.5 | 10 | 0 |
| 72 | 3 | hybrid | 95 | 19 | 17 | 30.147059 | 25 | 69.845556 | 3 | 17 | 0 |

La sensibilidad mantiene scores y umbrales, cruza 24 combinaciones y conserva detalles por las tres particiones, además del total: 96 filas. Unión conserva 136 y consenso 66 registros en todas las combinaciones; el agrupamiento de episodios sí cambia. Persistencia de 3 marcas/24 h selecciona 53 filas, la menor carga registrada (61,029412% de reducción), pero no se declara la mejor alternativa geotécnica. Véase [sensitivity_analysis.md](sensitivity_analysis.md).

**Decisión técnica inicial:** 72 h y mínimo 2 se fijaron por el alcance solicitado antes de los resultados; proporcionan una regla simple para revisión de mediciones irregulares. **Supuesto pendiente:** el especialista debe decidir si esa separación temporal representa continuidad útil en su contexto. No se calibra con un evento físico.

## 11. Carga estimada de revisión

Total: híbrida pasa de 136 marcas a 102 filas candidatas, reducción del 25%; selecciona 20 de 48 episodios, reducción del 58,333333% de episodios. Se entrega una plantilla con una fila por esos 20 episodios; cada episodio conserva sus marcas y registros asociados, sin deduplicarlos físicamente ni omitir señales de calidad.

Promedio híbrido **1.096774 filas/día**, máximo **27**, con **25 días con candidatos** sobre 93 días de calendario. En prueba: 70 candidatos frente a 88 de unión (20,454545% de reducción), en 13 episodios y 13 prismas. No se estima tiempo humano por fila ni se inventa productividad.

Los 48 episodios incluyen 398 registros: 394 evaluables y 4 no evaluables. Los restantes registros siguen íntegros en la tabla por fila. Hay 35 episodios de una sola marca y 13 con al menos dos marcas en su cadena; esto es un recuento retrospectivo y no reetiqueta la primera marca como persistente.

## 12. Casos destacados y visualizaciones

Ejemplos seleccionados por orden cronológico, sin escogerlos por cercanía a un evento:

| episode_id | prism_id | start_timestamp | last_observed_timestamp | union_mark_count | agreement_count | candidate_policies |
| --- | --- | --- | --- | --- | --- | --- |
| ep_378ba9e255f13442c33d4029 | 30-1994 | 2013-12-07 20:50:55 | 2013-12-17 18:35:24 | 15 | 15 | union;consensus;persistence;hybrid |
| ep_b08a56d6eb451c2f8cac90c3 | 31-2002 | 2013-12-20 12:39:33 | 2013-12-23 12:26:35 | 1 | 1 | union;consensus;hybrid |
| ep_f93349e3a3d4d627494f5856 | 36-1969 | 2013-12-20 18:13:25 | 2013-12-26 16:02:48 | 12 | 1 | union;consensus;persistence;hybrid |
| ep_e40204f03af8617270a001b4 | 36-1969 | 2014-01-02 21:38:19 | 2014-01-05 19:30:34 | 1 | 1 | union;consensus;hybrid |

| Gráfico | PNG | HTML offline |
| --- | --- | --- |
| Estados causales por registro | [PNG](figures/01_estados.png) | [HTML](interactive/01_estados.html) |
| Episodios por prisma | [PNG](figures/02_episodios_prisma.png) | [HTML](interactive/02_episodios_prisma.html) |
| Carga de revisión por política (72 h, mínimo 2) | [PNG](figures/03_politicas.png) | [HTML](interactive/03_politicas.html) |
| Candidatos diarios; ceros no implican estabilidad | [PNG](figures/04_candidatos_dia.png) | [HTML](interactive/04_candidatos_dia.html) |
| Duración observada de episodios | [PNG](figures/05_duraciones.png) | [HTML](interactive/05_duraciones.html) |
| Marcas por episodio; totales retrospectivos | [PNG](figures/06_marcas_episodio.png) | [HTML](interactive/06_marcas_episodio.html) |
| Coincidencia entre los métodos | [PNG](figures/07_coincidencias.png) | [HTML](interactive/07_coincidencias.html) |
| Sensibilidad temporal de las políticas | [PNG](figures/08_sensibilidad.png) | [HTML](interactive/08_sensibilidad.html) |
| Prisma 30-1994; solo entrenamiento, sin diagnóstico | [PNG](figures/09_prisma_30_1994.png) | [HTML](interactive/09_prisma_30_1994.html) |
| Primeros cuatro episodios seleccionados cronológicamente | [PNG](figures/10_ejemplos.png) | [HTML](interactive/10_ejemplos.html) |

Los 10 pares PNG/HTML son descriptivos, usan paleta neutral y JavaScript local. Los gráficos conectan observaciones; no se imputan ni crean mediciones entre ellas. Los scores del prisma particular se presentan en paneles con escalas propias. La duración observada incluye registros intermedios sin marca; `mark_span_hours` se conserva por separado. Ceros diarios significan “sin candidatos observados”, no una conclusión profesional.

## 13. Análisis del prisma 30-1994

**Hecho observado:** 35 registros, 15 evaluables, 20 no evaluables; únicamente entrenamiento. Cada método marca las 15 filas evaluables. Se genera un episodio y la híbrida selecciona las 15; persistencia selecciona 14 porque la primera marca todavía no tiene historia marcada reciente. El componente de regla predominante es `trend`. Score IF máximo 0.857048; base máximo 80.463332.

| scope | model | eligible_rows | min_score | median_score | maximum_score | q99_frozen |
| --- | --- | --- | --- | --- | --- | --- |
| entrenamiento_evaluable | baseline | 2909 | 0.007831 | 0.720073 | 80.463332 | 4.439772 |
| entrenamiento_evaluable | isolation_forest | 2909 | 0.342612 | 0.387 | 0.857048 | 0.587293 |
| 30-1994_evaluable | baseline | 15 | 7.605273 | 46.33377 | 80.463332 | 4.439772 |
| 30-1994_evaluable | isolation_forest | 15 | 0.748886 | 0.840964 | 0.857048 | 0.587293 |

No puede considerarse evidencia de falla: puede reflejar un comportamiento particular del prisma, diferencia de escala, problema de datos o condición que requiere revisión especializada. No se elimina ni ajusta nada a partir de él. [prism_30_1994_review.md](prism_30_1994_review.md) incluye fechas, motivos, componentes, percentiles y los 35 identificadores.

## 14. Limitaciones

- No hay etiquetas profesionales suficientes; no se calculan métricas de clasificación sobre eventos reales.
- Agrupar o filtrar no demuestra detección de una condición geotécnica ni prevención de un evento.
- La política híbrida descarta de su selección 34 marcas de unión, incluidas las de cuatro episodios con interrupciones; esas marcas permanecen accesibles y requieren valoración.
- Hay frecuencia irregular, huecos, historiales cortos y terminaciones de series por prisma. Un episodio censurado no es un episodio físicamente resuelto.
- Coincidencia entre métodos no equivale a independencia: comparten datos y algunas variables.
- La agrupación no introduce futuro en sus estados, condicionada a scores de Fase 5; los estados de entrenamiento siguen siendo retrospectivos porque el modelo se ajustó al final de ese periodo. No se simula operación en línea antes de que el modelo estuviera disponible.
- Un solo conjunto histórico no representa todos los taludes ni múltiples fallas independientes.
- El evento documental del 23-feb-2014 es posterior al fin del dataset; no se incorpora al código, configuración, umbrales ni selección de política.
- Duraciones y máximos retrospectivos no son información disponible desde el inicio del episodio. Cambian al observar nuevas filas.
- La carga se mide en filas y episodios; no se conoce todavía el esfuerzo humano necesario ni utilidad geotécnica de una selección.

## 15. Política provisional recomendada

**Híbrida: candidato si hay coincidencia de ambos métodos en el registro actual, o si el registro está marcado y hay al menos dos marcas de unión del mismo prisma en [t−72 h,t].** Ventana = 72 h; mínimo = 2. Se conserva una vista completa de unión y de calidad, además de la lista de 34 marcas no seleccionadas.

La propuesta es causal, reproducible, local/offline y explicable; reduce 25% de filas respecto a unión y conserva persistencia de un solo método. No es la que minimiza filas ni se declara óptima. Es una **propuesta provisional sujeta a validación del especialista**, sin activar actuaciones operativas. Si el especialista considera necesario revisar marcas aisladas o calidad interrumpida, debe poder acceder directamente al listado completo.

## 16. Aspectos que deben validar especialistas

Validez de umbrales estadísticos para revisión; ventana 72 h y mínimo 2; tratamiento de irregularidad y largos huecos; referencia del prisma 30-1994; utilidad de coincidencia y persistencia; criterio de relevancia de marcas excluidas y episodios con interrupciones; utilidad y tiempo de revisión por episodio; trazabilidad a registros de mina. Se entrega `specialist_review_template.csv` con campos humanos vacíos. Valores sugeridos para `review_status`: Pendiente, Revisado, Requiere más información; **no se completan automáticamente**.

## 17. Criterios para avanzar a Fase 7

200 pruebas pasan, se conservan 426 archivos anteriores y se reproducen 12 CSV byte a byte. Los hashes y predicciones de modelos son idénticos. Los prefijos temporales conservan todas las columnas causales; la verificación bloquea entrenamiento. [validation_report.md](validation_report.md) detalla pruebas y corrección durante desarrollo.

Antes de la siguiente fase se necesita aprobación explícita del alcance por la usuaria y revisión de las observaciones de política/calidad. La validación profesional y la recolección de etiquetas humanas siguen pendientes. **No se construye interfaz ni se avanza a Fase 7 en esta entrega.**

## 18. Conclusión

La Fase 6 organiza marcas existentes en episodios y una propuesta reproducible de revisión. Conserva estados desconocidos, motivos y trazabilidad, separando evidencia disponible en cada instante de los resúmenes finales. La aceptación técnica no constituye aprobación para uso en seguridad.

**Los candidatos no son predicciones de falla, no representan niveles de riesgo, requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para decisiones operativas o de seguridad.**

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
