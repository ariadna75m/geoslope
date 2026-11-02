# Monitoreo de taludes — Resultado de Fase 2

Fecha: 3 de octubre de 2026. Alcance: carga, validación y preparación independiente. Fases 3–8 pendientes de aprobación. No se calcularon velocidades ni aceleraciones, no se unieron fuentes y no se entrenaron modelos ni se construyó interfaz.

## Resultado y comparación cuantitativa

**Las cuatro fuentes quedaron preparadas por separado.** Se cargaron correctamente los siete archivos tabulares originales (CSV, DAT y TXT) y se probó compatibilidad Excel real XLSX/XLS con archivos sintéticos utilizados exclusivamente en pruebas. Los ocho originales, incluido el PDF, mantienen su SHA-256 inicial.

| Fuente | Antes | Conservadas | Excluidas | IDs corregidos | Marcadas conservadas | Duplicados antes → después | Intervalos cero antes → después | Celdas faltantes antes → después |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| West Wall | 7178 | 7178 | 0 | 0 | 21 | 0 → 0 | 0 → 0 | 0 → 0 |
| South West | 82401 | 82400 | 1 | 0 | 32 | 1 → 0 | 1 → 0 | 0 → 0 |
| Lluvia 2013 | 365 | 365 | 0 | 0 | 3 | 0 → 0 | 0 → 0 | 9 → 9 |
| Lluvia 2014 | 365 | 365 | 0 | 0 | 4 | 0 → 0 | 0 → 0 | 12 → 12 |

Totales: **90.309 filas de entrada, 90.308 conservadas, 1 copia exacta excluida, 0 identificadores corregidos y 60 filas conservadas con marcas**. Las marcas/correcciones son subconjuntos de conservadas; no se suman nuevamente. El tipado, los nombres normalizados y la construcción de timestamp son cambios de representación, no correcciones geomecánicas. Todas las salidas activas tienen 0 fechas no interpretables, 0 claves contradictorias y 0 errores de validación. Las advertencias sobre unidades, tiempo, huecos y pocos datos permanecen.

La Fase 2 prepara cuatro archivos de entrada. El DAT no se incorpora como observaciones adicionales porque reproduce South West; los eventos y el TXT se prueban en lectura pero todavía no se integran ni se utilizan como variables de desplazamiento.

## Transformaciones aplicadas y su evidencia

1. **Lectura controlada.** Extensiones permitidas CSV, XLSX, XLS, DAT y TXT; máximo por defecto 32 MiB, 250.000 filas y 256 columnas. Búsqueda de encabezado hasta 50 registros, esquema conocido o fila explícita. UTF-8 por defecto; otra codificación solo si se configura. El preámbulo de South West queda en metadatos. DAT: corrección restringida al encabezado de 15 nombres conocido, separando dos componentes de prisma para sus 16 campos. Registros de ancho incorrecto se rechazan. Las líneas físicamente vacías se registran; una fila con campos vacíos completos se conserva para validar/quarantinar.
2. **Nombres normalizados.** Mapeo explícito de cada columna, sin cambiar valores ni unidades. West Wall usa `reported_3d_movement_mm`. Su descripción es: “Movimiento 3D reportado en milímetros respecto a la referencia indicada en el encabezado. No se asume que sea una trayectoria acumulativa estrictamente creciente”.
3. **Originales y trazabilidad.** Cada fila recibe `row_id = SHA256(huella del archivo | hoja Excel o None | línea física inicial)`, `source_line`, `source_name` y `source_sha256`. `original_rows.csv` conserva encabezados y celdas de la lectura original; `original__<columna>` conserva el texto de cada campo junto a su versión tipada. Los valores/códigos de origen nunca se sobreescriben en los originales.
4. **Tipado numérico.** Se convierten únicamente las columnas definidas por esquema. Vacíos pasan a valores tipados desconocidos; no se imputa. Un texto inválido o valor no finito se conserva en la columna original y se marca, con su versión numérica desconocida. En las cuatro fuentes reales no se encontraron conversiones numéricas inválidas.
5. **Identificadores.** Se quitan espacios exteriores y se conservan ceros iniciales. No hubo identificadores reales que necesitaran esta corrección. La estación sigue siendo `029167`.
6. **Timestamp.** Prisma: fecha original + hora original; meteorología: año, mes y día. Meses ingleses se interpretan mediante un mapa explícito sin depender del locale. La regla de año de dos dígitos es 2000–2099, declarada para este conjunto; no es una regla universal para archivos históricos. Horas/minutos/segundos fuera de rango se rechazan, sin normalizar silenciosamente segundo 60. No se asigna zona horaria a prismas/clima.
7. **Duplicados exactos.** Se conserva la primera ocurrencia física de dos filas idénticas; el desempate usa la línea original solo porque los registros son idénticos, no como corte temporal. La copia adicional se conserva en `excluded_rows.csv`, con motivo y vínculo a la fila retenida.
8. **Claves inutilizables o contradictorias.** Las fechas/IDs esenciales inválidos y todas las filas de claves repetidas con valores distintos se conservan fuera de la salida activa para revisión; no se selecciona un valor arbitrario. En las fuentes reales hubo 0 casos.
9. **Ordenamiento.** Se ordena por `prism_id`/`station_id` y `timestamp`; se mantiene `row_id` como desempate técnico. West Wall cambia 6.813 posiciones y South West 82.400; meteorología conserva el orden. `row_dispositions.csv` registra línea original y posición procesada. No se realizaron cortes de entrenamiento.
10. **Marcas de calidad.** Se conservan faltantes, valores no utilizables y prismas con menos de 20 instantes únicos. Este mínimo es configurable y operativo, no geotécnico. West Wall: `30-1995` (4) y `31-1930` (17), 21 filas marcadas. South West: `24-1115` (10), `31-1481` (14), `31-1608` (1) y `31-1871` (7), 32 filas marcadas. Lluvia: 3 y 4 filas marcadas, respectivamente. Los huecos mayores a 24 h se advierten sin interpolación ni creación de observaciones.

Cada evento de `transformations.jsonl` registra operación, número de filas afectadas, estado antes/después (filas, columnas y huella), política y ubicación de evidencia. Los valores antes/después se reconstruyen por `row_id` entre `original_rows.csv`, las columnas `original__*`, los campos tipados y el archivo de exclusiones. El orden antes/después se reconstruye mediante `row_dispositions.csv`. Los originales del DAT y sus encabezados quedan documentados en metadatos de lectura y en la Fase 1.

## Exclusión exacta en South West

| Campo | Valor |
| --- | --- |
| Prisma | 31-1637 |
| Timestamp | 2014-05-22 21:36:56 |
| Línea excluida | 24763 |
| Línea conservada | 24762 |
| Motivo | exact_duplicate |
| row_id excluido | 49f0938c14abbe5e8242b880a53c743adbfdbcf0075b4b6a29ad7f167d58c59a |
| row_id conservado | 69d94effbd29c60fbd2c596b08207af067d7fc0b41f8a7832c7e5e4ad9a75cc6 |

La línea 24.763 es idéntica a la 24.762 en todos los campos fuente. La exclusión se aplica a la salida procesada; ambas líneas siguen intactas en `data/raw/` y en `original_rows.csv`. No se excluyó ningún registro por ser extremo ni por tener poco historial.

## Meteorología y unidades pendientes

Los dos años permanecen en carpetas independientes; no se concatenan ni se unen a prismas. Se conservan año/mes/día originales, estación, producto, código de calidad y período de medición. Los 7 faltantes de lluvia siguen desconocidos, no cero: 2013-03-08, 2013-10-07, 2013-12-29, 2014-08-17, 2014-09-17, 2014-10-09 y 2014-12-18. También permanecen desconocidos sus períodos y códigos de calidad: 21 celdas faltantes antes y después.

Todas las coordenadas y diferencias de South West permanecen con unidad **“requiere validación”** y sin sufijos físicos inferidos. West Wall conserva el mm explícito del movimiento reportado; sus coordenadas requieren validación. Se mantienen pendientes CRS/datum, hora/zona de los prismas, cierre y disponibilidad de lluvia, significado de `N`, metodología de ajustes y referencia/fórmula del movimiento. No se convierten coordenadas ni se impone crecimiento monotónico al movimiento. El TXT no se usa como velocidad de desplazamiento.

## Pruebas y aceptación

**61 pruebas pasaron; 0 fallos, 0 errores y 0 omitidas.** Tiempo de la ejecución final: 8.659 s. Evidencia: `pytest-output.txt` y `pytest-results.xml`.

Casos cubiertos: los siete archivos reales; XLSX y XLS generados solo para pruebas; preámbulo; fila explícita; tipos, tamaño y extensiones inválidos; ancho incorrecto; encabezados vacíos/repetidos; límites; trazabilidad multilínea; fórmulas XLSX conservadas sin evaluación; fechas/horas inválidas; índices externos no únicos; faltantes de lluvia; valores extremos/decrecientes; prismas con una observación; huecos largos; duplicados exactos/contradictorios; colisión tras recortar IDs; conservación de originales; partición completa de filas; exportación protegida contra escritura en raw; estabilidad de IDs y resultados.

**Reproducción completa verificada:** dos ejecuciones sucesivas generaron los mismos 32 archivos preparados, idénticos byte a byte por SHA-256. Los tiempos de ejecución se almacenan aparte porque varían. Se verificó además que cada valor `original__*` coincide con la lectura original y que cada fila pertenece exactamente a conservadas o excluidas.

| Criterio | Resultado |
| --- | --- |
| Carga de todos los tabulares reales | 7/7 correctos; PDF conservado como documentación |
| Columnas/tipos/fechas | Validación estricta y errores identificables |
| Orden por timestamp dentro de prisma | Verificado |
| Intervalos cero después | 0 en las 4 salidas |
| Integridad de originales | 8/8 SHA-256 idénticos |
| Auditoría de cada transformación | Journal + datos originales/transformados + disposición de filas |
| Pruebas unitarias | Todas satisfactorias |
| Comparación cuantitativa | quality_comparison.csv y este informe |
| Unidades pendientes | Persisten en metadata.json y schema_dictionary.csv |

## Archivos creados y modificados

Creados: `src/__init__.py`, `src/schemas.py`, `src/data_loader.py`, `src/data_validation.py`, `src/preprocessing.py`; `tests/conftest.py`, `tests/test_data_loader.py`, `tests/test_data_validation.py`, `tests/test_preprocessing.py`; `pytest.ini`, `requirements.txt`, `requirements-dev.txt`; `scripts/run_phase2.py`, `scripts/build_phase2_report.py`, `scripts/verify_phase2.py`; las salidas bajo `data/processed/` y los informes bajo `reports/phase2/`.

Modificados: `README.md` y `.gitignore`. Los scripts/resultados de la Fase 1 y todos los originales permanecen sin modificaciones. `src/schemas.py` centraliza columnas y unidades para que carga, validación y preparación usen una sola definición; el script de ejecución mantiene esta fase independiente del futuro análisis.

Por fuente, `data/processed/<fuente>/` contiene: `data.csv`, `original_rows.csv`, `excluded_rows.csv` (con encabezados aunque no haya exclusiones), `row_dispositions.csv`, `metadata.json`, `quality_before.json`, `quality_after.json` y `transformations.jsonl`.

## Decisiones y errores pendientes

No quedan errores de ejecución o fallos de pruebas en el flujo entregado. Siguen pendientes las validaciones documentales citadas y la decisión del especialista sobre registros con poco historial. Ninguna advertencia se convierte en diagnóstico de estabilidad. CSV no conserva dtypes: al reabrir, leer IDs, estación y campos `original__*` como texto para mantener ceros y texto vacío. Para Excel se conservan valores almacenados; no se preserva en la tabla procesada el formato visual del libro. XLSX no evalúa fórmulas y las marca como no numéricas cuando corresponda; XLS lee valores almacenados mediante xlrd y no recupera fórmulas, macros ni su formato. Los archivos originales permanecen intactos.

Instalación, reproducción y auditoría: `README.md`. Punto de control antes de la Fase 2: `2130e29`. No se implementó lógica de análisis exploratorio, características físicas, modelos ni interfaz.

**Fase 2 terminada. Se espera aprobación explícita antes de comenzar la Fase 3.**

Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
