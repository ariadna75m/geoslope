# Validación técnica — Fase 6

**Estado: aprobada con observaciones.** El estado se refiere a las comprobaciones técnicas; la aprobación para uso geotécnico queda pendiente del especialista.

| Comprobación | Resultado |
| --- | --- |
| Suite anterior antes de cambios | 158 aprobadas, 0 fallidas, 0 omitidas |
| Suite completa | 200 aprobadas, 0 fallidas, 0 omitidas |
| Pruebas nuevas | 42 aprobadas |
| Archivos previos intactos | 426 |
| Filas conservadas | 7.178, 49 prismas |
| No evaluables conservados con motivo | 1.280 |
| CSV reproducidos byte a byte | 12 |
| Recarga de todas las columnas y tipos | Exactamente iguales |
| Modelos y scores anteriores | Hashes y predicciones idénticos |
| Entrenamiento de producción | No ejecutado; métodos fit bloqueados durante verificación |
| Ventanas y separación por prisma | Límites inclusivos, más de la ventana y conteos independientes comprobados |
| Plantilla del especialista | Todos sus campos de decisión vacíos |
| Gráficos verificados | 10 pares PNG/HTML offline |

| cutoff_exclusive | rows_checked | all_causal_columns_identical |
| --- | --- | --- |
| 2013-12-05 | 732 | True |
| 2014-01-15 | 3917 | True |
| 2014-02-02 | 5453 | True |
| 2014-02-15 | 6799 | True |

La prueba de prefijos compara **todas las columnas causales**, incluidos IDs, scores, marcas, conteos, estados y explicaciones, con cuatro cortes por timestamp. Resúmenes finales y cierre permanecen solo en la tabla retrospectiva. Las pruebas artificiales separadas añaden futuro y verifican límites de 24, 48 y 72 horas.

**Alcance de causalidad:** invariancia de la agrupación condicionada a marcas congeladas de Fase 5. Las puntuaciones de entrenamiento se obtuvieron con un modelo ajustado al cierre de ese periodo y son retrospectivas; no estaban disponibles en cada fecha histórica de entrenamiento. `model_available_at_observation` es falso en esas filas y verdadero desde la frontera de validación; no reemplaza la elegibilidad de datos. Validación y prueba utilizan un modelo ya aprendido con información anterior. No se afirma una simulación operativa en línea del periodo de entrenamiento.

Los 158 tests anteriores incluyen ajustes de modelos aislados dentro de sus pruebas de regresión; esto no constituye reentrenamiento de producción ni modificación de artefactos. La lógica de Fase 6 y su verificador bloquean `fit` de bosque, imputador, escalador y regla.

Durante desarrollo se corrigió la diferencia de índices de las tablas auxiliares al recargarlas; IDs y valores ya coincidían. Se normalizan índices auxiliares, no las fechas ni los datos originales. Evidencia anterior conservada en `verification-development.txt`. La verificación final pasa sin errores pendientes de ejecución.

También se fijó a `datetime64[ns]` el tipo de la fecha de disponibilidad del modelo, para que recargue con el mismo tipo que en memoria; la fecha no cambió. Evidencia en `verification-date-development.txt`. El informe exige que la prueba de reproducción esté vinculada por hash a los metadatos actuales para impedir reutilizar una prueba obsoleta.

Referencias: `pytest-before.txt/.xml`, `pytest-results.xml`, `pytest-output.txt`, `verification-log.txt`, `reproducibility.json`, `protected_before_phase6.json` y `phase6_metadata.json`. Checkpoint inicial `5da058eff47a10c529f97d2ac67e90e2292cba3d`; el checkpoint final se registra después del commit en `git_checkpoint.txt` para evitar autorreferencia.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
