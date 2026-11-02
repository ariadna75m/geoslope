# Sensibilidad — ventanas y persistencia

Se cruzan 3 ventanas × 2 mínimos × 4 políticas: **24 combinaciones**, y cuatro ámbitos (total, entrenamiento, validación, prueba), produciendo 96 filas. Al cambiar la ventana cambia tanto el máximo intervalo entre marcas del episodio como la ventana inclusiva de persistencia. Los modelos, scores, q99 y la partición no cambian.

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

| window_hours | episodes | marked_rows | episodes_with_quality_interruption | censored_episodes |
| --- | --- | --- | --- | --- |
| 24 | 58 | 136 | 1 | 11 |
| 48 | 51 | 136 | 2 | 16 |
| 72 | 48 | 136 | 4 | 18 |

Unión y consenso conservan respectivamente 136 y 66 filas en todas las combinaciones; el número de episodios cambia al modificar la agrupación. El mínimo de persistencia no cambia la construcción de episodios. La menor cantidad de filas en esta comparación es 53, con persistencia de 3 marcas en 24 h (reducción 61,029412%); ello no demuestra que sea la alternativa más útil para el especialista. Híbrida varía de 88 a 102 filas. La propuesta principal de 72 h y mínimo 2 está especificada antes del análisis, mantiene explicaciones simples y no se escoge buscando un evento físico. No se utiliza el contexto documental posterior para seleccionar ventanas o políticas.

Las medianas corresponden a los **episodios seleccionados** por cada política; la duración incluye observaciones sin marca dentro de la ventana, hasta el final observado. `mark_span_hours` conserva aparte el tiempo entre primera y última marca. Sin episodios seleccionados, las medianas son desconocidas, no cero.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
