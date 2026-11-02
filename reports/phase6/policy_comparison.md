# Comparación de políticas — marcas estadísticas experimentales

Todas las políticas requieren una marca actual evaluable. Unión = base OR IF; consenso = base AND IF en la misma fila; persistencia = marca actual AND al menos 2 marcas de unión en [t−72 h,t]; híbrida = consenso OR persistencia.

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

La reducción es `100 × (1 − registros candidatos / registros de unión)`; no mide desempeño geotécnico. Los denominadores son 136 en total, 42 en entrenamiento, 6 en validación y 88 en prueba. El promedio diario incluye todos los días del calendario de cada periodo; seis días sin evaluables no se interpretan como estabilidad. El máximo diario de la híbrida es 27, frente a 29 de unión.

Consenso reduce más filas entre las cuatro políticas principales (51.470588%), pero excluye persistencia de un método. Híbrida conserva 36 filas adicionales mediante persistencia y reduce 25.000000% frente a unión. Las 34 marcas no seleccionadas siguen disponibles en `marks_not_selected_primary.csv`.

Los episodios candidatos se cuentan por política y por periodo **cuando contienen una fila seleccionada en ese periodo**. Una misma cadena puede atravesar particiones; las cifras por periodo no son eventos de falla independientes y no deben sumarse para inferir un total de eventos. La duración y el total de marcas de cada episodio son retrospectivos completos, nunca utilizados para reescribir estados causales.

| episode_id | prism_id | start_timestamp | ineligible_record_count | union_mark_count | candidate_policies |
| --- | --- | --- | --- | --- | --- |
| ep_cedab9c87ff036231911a591 | 22-2061 | 2014-02-16 23:41:11 | 1 | 1 | union |
| ep_85c97737d0536095f7c40d79 | 30-1996 | 2014-01-28 16:59:15 | 1 | 1 | union |
| ep_04c18610c13e7a1a478764db | 31-1977 | 2014-02-08 18:05:13 | 1 | 1 | union |
| ep_1e361ac6962998df4992d010 | 31-1977 | 2014-02-15 18:13:32 | 1 | 1 | union |

Los cuatro episodios con interrupciones de calidad solo son seleccionados por unión. Híbrida no permite ocultarlos: siguen presentes en `episodes.csv` y en el listado de marcas no seleccionadas. Se requiere revisión del especialista antes de usar cualquier filtro.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
