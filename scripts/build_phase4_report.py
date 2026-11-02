"""Informe de Fase 4 a partir de salidas verificadas y evidencia de pruebas."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.feature_validation import read_feature_dataset, check_protected
from src.exploratory_analysis import DISCLAIMER

OUT = ROOT / "reports/phase4"


def md_table(frame):
    def cell(value):
        if pd.isna(value):
            return "No disponible"
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value).replace("|", "/").replace("\n", " ")
    rows = ["| " + " | ".join(map(str, frame.columns)) + " |",
            "| " + " | ".join("---" for _ in frame.columns) + " |"]
    rows.extend("| " + " | ".join(cell(value) for value in row) + " |"
                for row in frame.itertuples(index=False, name=None))
    return "\n".join(rows)


def main():
    metadata = json.loads((OUT / "phase4_metadata.json").read_text())
    proof = json.loads((OUT / "reproducibility.json").read_text())
    assert proof["full_reproduction_completed"] and proof["roundtrip_exact"]
    assert proof["temporal_leakage_test"]["all_columns_identical"]
    protected = check_protected(ROOT, OUT / "protected_before_phase4.json")
    suites = ET.parse(OUT / "pytest-results.xml").getroot().findall("testsuite")
    tests = sum(int(s.get("tests", 0)) for s in suites)
    failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    assert failed == 0 and skipped == 0
    test_seconds = sum(float(s.get("time", 0)) for s in suites)
    tables = {name: pd.read_csv(OUT / (name + ".csv")) for name in
              ("feature_dictionary", "feature_quality_summary", "feature_group_availability",
               "prism_feature_summary", "feature_distributions", "quality_status_counts")}
    data = read_feature_dataset(ROOT / metadata["feature_dataset"], metadata["feature_dtypes"])
    validation = metadata["validation"]
    cfg = metadata["config"]
    dictionary = tables["feature_dictionary"]
    quality = tables["feature_quality_summary"]
    prisms = tables["prism_feature_summary"]
    leakage = proof["temporal_leakage_test"]
    original_columns = validation["total_columns"] - validation["derived_columns"]
    availability_count = int(dictionary.group.eq("availability").sum())
    numeric_added = sum(kind in {"int64", "float64"} and name not in data.columns[:original_columns]
                        for name, kind in metadata["feature_dtypes"].items())
    gaps = prisms[["gap_over_24h_rows", "gap_over_72h_rows", "gap_over_7d_rows"]].sum()
    insufficient = prisms.loc[prisms.insufficient_for_baseline_at_end,
                               ["prism_id", "rows", "first_timestamp", "last_timestamp",
                                "prior_baseline_available_pct", "local_trend_72h_available_pct", "local_trend_7d_available_pct"]]
    limited = quality.loc[~quality.group.isin(["source", "availability"]) & quality.nan_pct.gt(0)]
    limited = limited.sort_values(["nan_pct", "feature_name"], ascending=[False, True]).head(12)
    counts = dictionary.groupby("group", sort=True).size().reset_index(name="columnas")
    distributions = tables["feature_distributions"][["feature_name", "known_rows", "missing_rows", "min", "median", "max"]]
    graph_rows = pd.DataFrame([{"Visualización": a["title"], "Imagen": f"[PNG]({a['png']})",
                               "Interactiva": f"[HTML]({a['html']})"} for a in metadata["figures"]])
    timing = json.loads((OUT / "execution_stats.json").read_text())["processing_seconds"]
    constant = "\n".join("- `" + name + "`" for name in validation["constant_columns"])
    group_availability = tables["feature_group_availability"][["feature_group", "available_rows", "total_rows", "available_pct"]].copy()
    labels = {"consecutive_change": "Cambio entre mediciones", "observed_rate": "Tasa observada",
              "prior_baseline": "Línea base previa", "conventional_z": "Z-score convencional",
              "robust_z": "Z-score robusto", "streak": "Rachas evaluables"}
    for window in ("24h", "72h", "7d"):
        labels.update({"movement_descriptive_"+window: "Media del movimiento, "+window,
                       "movement_dispersion_"+window: "Std del movimiento, "+window,
                       "internal_changes_"+window: "Media de cambios internos, "+window,
                       "sufficient_window_"+window: "Historia suficiente, "+window,
                       "local_trend_"+window: "Pendiente local, "+window})
    group_availability.insert(1, "Descripción", group_availability.feature_group.map(labels))
    group_availability = group_availability.rename(columns={"feature_group": "Grupo", "available_rows": "Filas disponibles",
                                                            "total_rows": "Total de filas", "available_pct": "% disponible"})
    text = f"""# Fase 4: ingeniería y validación de características temporales

## 1. Resumen ejecutivo

Se generaron características retrospectivas para **{len(data):,} registros de {data.prism_id.nunique()} prismas de West Wall**, conservando todas las filas y todos sus campos originales. La salida tiene **{len(data.columns)} columnas**: {original_columns} campos preparados de entrada y {validation['derived_columns']} columnas añadidas. Las añadidas incluyen {availability_count} banderas de disponibilidad matemática, {numeric_added} campos numéricos, otras banderas, trazabilidad y un resumen de calidad; no son {validation['derived_columns']} variables independientes listas para un modelo.

La suite completa aprobó **{tests} pruebas, con {failed} fallos y {skipped} omisiones**. Las {protected} huellas protegidas permanecen intactas. Se reprodujeron byte a byte siete CSV y se verificó que modificar observaciones futuras no cambia ninguna columna pasada. No se entrenaron modelos ni se generaron alertas.

{DISCLAIMER}

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

La ingeniería utiliza exclusivamente `data/processed/west_wall/data.csv`, preparado en Fase 2 a partir de `West Wall Prism Movements - 3 months to 20-Feb-14.csv`. Su cobertura es **{data.timestamp.min()} a {data.timestamp.max()}**. `reported_3d_movement_mm` conserva el movimiento 3D reportado en milímetros respecto a la referencia indicada en el archivo. No se asume que sea una trayectoria acumulativa estrictamente creciente.

South West permanece separado; `easting_diff`, `northing_diff` y `height_diff` siguen con unidades «requiere validación». No se convierten a milímetros ni se calculan tasas físicas para esa fuente. También permanecen separados los años meteorológicos, catálogo de eventos, posibles voladuras y TXT de cambios de velocidad sísmica. El TXT describe otra magnitud y no se reutiliza como desplazamiento de prismas. No se convierten coordenadas a latitud/longitud; sus unidades no documentadas continúan pendientes.

El artículo de de Wit y Snieder documenta una falla el 23-02-2014, posterior al término de West Wall el 20-02-2014. Esa fecha es contexto externo, no una etiqueta de esta tabla. No aparece en el módulo ni en la configuración de características y no interviene en ventanas, criterios o selección de parámetros. Los precursores sísmicos estudiados por los autores no son resultados obtenidos por este MVP. Véanse [contexto del artículo](../documentation/article_context.md) y el PDF preservado en `data/context/`.

Referencia APA 7: de Wit, T., & Snieder, R. (2026). Did they blow it? Time-lapse velocity variations during an open-pit mine slope failure using seismic noise interferometry. *Seismica, 5*(1). https://doi.org/10.26443/seismica.v5i1.1902

## 4. Reglas contra fuga de información

Cada prisma se ordena por `timestamp`. Una fila usa su observación actual y exclusivamente sus propias observaciones anteriores. Las ventanas tienen límite inferior **abierto** y superior **cerrado**: **(t−W, t]**, con W=24, 72 o 168 horas. No hay ventanas centradas, relleno futuro, escalado global ni parámetros elegidos a partir de la fecha de falla.

La línea base expansiva utiliza **[inicio, t)**: excluye la observación actual. Los conteos previos no incorporan otras series. La disponibilidad también se calcula en ese instante; no se completa usando datos posteriores. Los resúmenes de cambios/tasas dentro de una ventana exigen que **ambos timestamps del par estén dentro de ella**. Un par que cruza el límite inferior queda fuera del resumen móvil, pero su cambio y tasa individuales se conservan en la fila.

Esta implementación procesa prefijos retrospectivos en memoria y reproduce la llegada de observaciones una a una. No implementa todavía un servicio de ingesta ni un almacenamiento incremental de estados.

## 5. Tratamiento de frecuencias irregulares

Se utilizan diferencias reales de tiempo en horas/días. No se remuestrea, interpola, imputa, alisa ni altera el movimiento original. Primera fila sin antecedente: intervalo, cambio y tasa desconocidos. Un timestamp duplicado por prisma bloquea la ingeniería con un mensaje de revisión; no elimina ni fusiona filas. West Wall activo tiene cero duplicados e intervalos cero.

Hay **{int(gaps.gap_over_24h_rows)} intervalos >24 h, {int(gaps.gap_over_72h_rows)} >72 h y {int(gaps.gap_over_7d_rows)} >7 días**. Estos conteos se superponen. Una tasa tras un hueco largo permanece calculable si los dos valores son conocidos: representa el promedio entre extremos y no permite conocer lo ocurrido durante el hueco. Se marca `is_prolonged_gap` y se reinician las rachas. Intervalos positivos inferiores a un minuto se marcan para revisión numérica; no son una frecuencia instrumental validada.

Medias, dispersiones y OLS ponderan igualmente cada observación, no el tiempo representado. Las frecuencias heterogéneas pueden afectar estas estadísticas. No se inventa una frecuencia esperada ni porcentaje de completitud temporal. Los porcentajes siguientes indican **filas con cálculo disponible**, no porcentaje de mediciones esperadas ni confianza geomecánica.

## 6. Características construidas

El [diccionario de características](feature_dictionary.csv) enumera **cada una de las {len(data.columns)} columnas**, con descripción, fórmula, unidad, fuente, ventana, mínimo de observaciones, uso del presente/pasado, política de faltantes, límites e interpretaciones. Las columnas originales quedan incluidas para que la salida pueda auditarse completa.

| Familia | Campos y estadísticas |
| --- | --- |
| Trazabilidad | Todos los campos originales y `original__*`; `row_id`, `source_line`, `source_sha256`, `source_record_id`, `source_file_reference` |
| Intervalo | `previous_timestamp`, `elapsed_hours`, `elapsed_days`; inicio, intervalo no positivo, huecos >24/72/168 h, corto/prolongado |
| Cambio | `movement_delta_mm`, `absolute_movement_delta_mm`; incremento/disminución/sin cambio |
| Tasa | `movement_rate_mm_per_day`, `absolute_movement_rate_mm_per_day` y disponibilidad |
| Movimiento por ventana | `movement_{{24h,72h,7d}}_{{mean,median,min,max,range,std,mad,first,last,net_change}}_mm` |
| Cambios/tasas por ventana | `delta_{{ventana}}_*`, `rate_{{ventana}}_*`: media, mediana, std, mínimo, máximo, suma, suma absoluta, proporciones positivas/negativas y conteos conocidos; `increase_proportion_{{ventana}}` para los cambios |
| Cobertura por ventana | `window_{{ventana}}_*`: conteos totales/válidos, duración total/válida, máximo hueco, hueco largo; `has_sufficient_{{ventana}}_history` |
| Tendencia | `local_trend_{{72h,7d}}_{{points,duration_hours,slope_mm_per_day,r_squared}}` |
| Persistencia | `increase_streak_count`, `decrease_streak_count`, duraciones en horas, `streak_evaluable` |
| Historial previo | Conteos, duración, media/mediana/std/MAD, diferencias a media/mediana, z-score convencional/robusto y banderas de dispersión cero/insuficiente |
| Disponibilidad y calidad | Sufijo `_available` para campos numéricos/fecha derivados; `movement_observation_available`, `has_numeric_overflow`, `feature_quality_status` |

Conteo de columnas por grupo del diccionario:

{md_table(counts)}

Una bandera de signo `False` puede indicar que el cambio es desconocido; siempre debe consultarse `movement_delta_mm_available`. Un conteo de cero es conocido y no se confunde con una estadística no calculable. Se conservan tanto conteos como banderas aunque algunos resulten constantes en este dataset; no se ha seleccionado todavía un conjunto para modelado.

## 7. Fórmulas y unidades

Sea x_t el movimiento reportado en mm y Δd el intervalo real en días:

- Cambio: **Δx_t=x_t−x_anterior**, en mm; cambio absoluto: |Δx_t|.
- **Tasa observada de cambio entre mediciones consecutivas**: **r_t=Δx_t/Δd**, en mm/día, solo con Δd>0 y ambos valores conocidos. No constituye velocidad física validada del macizo rocoso.
- Media: suma(x)/n; rango: máximo−mínimo; desviación estándar muestral: **sqrt(suma((x−media)²)/(n−1))**; MAD sin escalar: **mediana(|x−mediana(x)|)**. Movimiento/cambio usan mm; tasas usan mm/día.
- Cambio entre extremos de ventana: x_último−x_primero. Si uno de esos registros es desconocido, el resultado queda NaN; no se sustituye por otro extremo. Una ventana de un solo registro conocido tiene cambio entre extremos igual a cero, sin evidencia de persistencia.
- Proporción de incrementos/disminuciones: número de pares con Δx>0/Δx<0 dividido entre pares evaluables; cambios cero están incluidos en el denominador. Sin pares, NaN. La suma de tasas tiene unidad mm/día y es una suma matemática, **no** desplazamiento neto integrado.
- Pendiente OLS: **suma((d−media_d)(x−media_x))/suma((d−media_d)²)**, donde d son días transcurridos desde el primer timestamp válido de la ventana. Pendiente en mm/día; **R²=1−SSE/SST**, adimensional. Para serie constante SST=0, R² queda NaN aunque la pendiente sea cero. No se extrapola.
- Diferencias históricas: x_t−media(x_<t) y x_t−mediana(x_<t), en mm. **z=(x_t−media_previa)/std_previa** y **z_robusto=(x_t−mediana_previa)/({cfg['robust_mad_scale']}×MAD_previa)**, adimensionales. Dispersión cero o insuficiente deja el score NaN con su bandera; nunca se divide por cero.
- Racha: número de cambios consecutivos evaluables del mismo signo; duración desde el timestamp anterior al primer cambio de la racha hasta t. Cero reinicia ambas rachas con conteos/duraciones cero. Dato desconocido, intervalo inválido o hueco >{cfg['prolonged_gap_hours']:g} h reinicia y deja la racha de esa fila NaN.

NaN significa «no calculable con los datos y criterios de ese instante». No significa cero movimiento, estabilidad o ausencia de riesgo. Las operaciones que exceden el rango numérico generan NaN y `has_numeric_overflow`; en los datos reales no ocurrió desbordamiento.

## 8. Criterios de historia suficiente

Los criterios se explicaron antes de implementar y se conservan en [config/phase4.json](../../config/phase4.json). Son decisiones técnicas provisionales de disponibilidad, no umbrales geomecánicos; no dependen de la fecha de falla.

| Cálculo | Criterio configurado | Justificación |
| --- | --- | --- |
| Desviación estándar | ≥{cfg['min_dispersion_observations']} valores conocidos; ddof=1 | Con un dato la dispersión muestral no está definida |
| Resúmenes simples | ≥1 valor conocido; extremos según sus registros | Permite describir datos escasos, con bandera separada de suficiencia |
| Historia suficiente por ventana | ≥{cfg['min_window_observations']} valores conocidos, duración ≥{100*cfg['min_window_span_fraction']:g}% de W y sin hueco interno observado >{cfg['prolonged_gap_hours']:g} h | Evita confundir pocos puntos concentrados con cobertura reciente suficiente |
| Duración mínima 24/72/168 h | 6/18/42 h | Se aplica la misma fracción técnica de la longitud de ventana |
| Pendiente local | ≥{cfg['min_slope_observations']} timestamps válidos diferentes, duración ≥18/42 h y sin hueco entre puntos válidos >{cfg['prolonged_gap_hours']:g} h | OLS necesita dispersión temporal y más de un par |
| Línea base previa | ≥{cfg['min_baseline_observations']} valores previos conocidos que cubran ≥{cfg['min_baseline_span_hours']:g} h | Evita referencia basada en pocas observaciones o un instante concentrado |
| Dispersión histórica | Mayor que {cfg['dispersion_epsilon']:g}; MAD escalada por {cfg['robust_mad_scale']} | Evita divisiones nulas; constante robusta configurable |
| Intervalo corto/prolongado | 0<Δh<{cfg['short_interval_hours']:.8f} h; Δh>{cfg['prolonged_gap_hours']:g} h | Banderas de revisión del cálculo; no diagnósticos instrumentales |

La fracción de duración **no es porcentaje de mediciones esperadas**. No garantiza precisión ni independencia de observaciones. `has_sufficient_history` describe la línea base; `_available` describe que existe un resultado matemático. Una ventana puede tener media disponible y aún no cumplir `has_sufficient_24h_history`. La pendiente puede fallar además si los valores desconocidos dejan un hueco demasiado largo entre puntos válidos.

`feature_quality_status` aplica prioridad: sin historia, intervalo inválido, datos/desbordamiento parciales, hueco prolongado, intervalo corto, historia previa insuficiente, cobertura/score/pendiente parcial, características disponibles. No es nivel de atención ni riesgo.

## 9. Resultados de calidad

| Comprobación | Entrada → salida |
| --- | --- |
| Filas | {validation['input_rows']} → {validation['output_rows']}; excluidas 0, interpoladas 0, imputadas 0 |
| Prismas | {validation['prisms']} → {validation['prisms']} |
| Campos originales e IDs | Todos conservados y comparados exactamente con la entrada ordenada |
| Claves temporales repetidas/intervalos cero | 0 / 0 |
| Orden | Ascendente por prisma y timestamp |
| Infinitos/desbordamientos en salida | {validation['infinite_values']} / {int(data.has_numeric_overflow.sum())} |
| Movimiento original mínimo/máximo | {validation['original_min']} / {validation['original_max']} mm; ambos conservados |
| Cambios negativos | {validation['negative_changes_preserved']}; todos conservados |
| Columnas completamente NaN | {len(validation['fully_empty_columns'])} |
| Columnas constantes entre conocidos | {len(validation['constant_columns'])}; documentadas, no eliminadas |

Distribuciones calculadas únicamente para resultados conocidos, sin retirar extremos:

{md_table(distributions)}

El extremo negativo de la tasa conserva el cambio y el intervalo que lo originaron; no se corrige por su magnitud. Requiere revisión de referencia, adquisición y significado físico antes de cualquier uso geomecánico. No se infiere causalidad.

Estados de calidad:

{md_table(tables['quality_status_counts'])}

El [resumen de calidad](feature_quality_summary.csv) incluye tipo, conteos y porcentaje NaN, disponibilidad, campos vacíos/constantes para **cada columna**. Las banderas booleanas tienen cero NaN porque expresan condiciones conocidas; su porcentaje de celdas no vacías no equivale al porcentaje de banderas verdaderas. Este último está en la tabla por grupos y por prisma.

Columnas constantes entre sus valores conocidos (sin eliminarlas):

{constant}

## 10. Características con mayor porcentaje de disponibilidad

Disponibilidad matemática/suficiencia por grupo; denominador común {len(data)} filas:

{md_table(group_availability)}

Medias descriptivas del movimiento alcanzan 100% porque West Wall contiene movimiento conocido en cada fila y la ventana incluye el presente. Sin embargo, solo {float(tables['feature_group_availability'].set_index('feature_group').loc['sufficient_window_24h','available_pct']):.2f}% cumple el criterio de historia suficiente de 24 horas. No se presenta ese 100% como cobertura completa.

## 11. Características con disponibilidad limitada

Campos calculados con mayor porcentaje NaN (se excluyen del listado las banderas y copias originales):

{md_table(limited[['feature_name','available_count','nan_count','available_pct','nan_pct']])}

Las desviaciones estándar de cambios/tasas de 24 horas necesitan dos pares internos, es decir, al menos tres observaciones dentro de la ventana; por eso tienen más NaN que la dispersión del movimiento. La línea base exige veinte observaciones **previas**, por lo que las filas iniciales no tienen comparación histórica. Las pendientes también requieren duración temporal; no basta contar tres filas.

## 12. Prismas con cobertura insuficiente

Prismas que terminan sin alcanzar la línea base previa mínima:

{md_table(insufficient)}

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

Las 75 pruebas anteriores se ejecutaron antes de programar y aprobaron; véase [pytest-before.txt](pytest-before.txt). La ejecución final incluyó **{tests-75} pruebas nuevas y 75 anteriores: {tests} aprobadas, {failed} fallidas, {skipped} omitidas**, en {test_seconds:.2f} s. Evidencia: [salida Pytest](pytest-output.txt) y [JUnit XML](pytest-results.xml).

Los tres archivos nuevos prueban las fórmulas temporales, entradas inválidas y conservación, y ausencia de fuga: (1) prefijo más futuro extremo, (2) cada prefijo equivalente a llegada incremental, (3) otro prisma independiente. Se verifican los 24 tipos de caso solicitados, incluidos primera fila, intervalos irregulares/cero, desorden, duplicados, huecos 24/72/168 h, dispersión nula, extremos, rachas y conservación. Un test adicional demuestra que modificar mínimos de dispersión y escala MAD queda reflejado tanto en resultados como en el diccionario.

En datos reales, el corte de comprobación fue el punto medio de la cobertura, **{leakage['cutoff_timestamp']}**, sin relación con la fecha de falla. Se recalculó un prefijo de **{leakage['prefix_rows']} filas de {leakage['prefix_prisms']} prismas**. Coincidieron exactamente todas las columnas con el cálculo de la serie completa. Después se alteraron las **{leakage['future_rows_altered']} filas futuras** alternando ±10¹² mm en una copia de prueba y el prefijo volvió a ser idéntico. Esos valores nunca se escribieron en el dataset entregado.

## 15. Integridad y reproducibilidad

Se verificaron **{protected} archivos protegidos** antes y después: originales, fuentes preparadas, código/pruebas anteriores, artículo, informes, notebook y gráficos históricos. No se reescriben las Fases 1–3. Se crea una carpeta nueva `phase4` para resultados. README y `.gitignore` son las únicas modificaciones de archivos previos autorizadas para documentar esta fase; el resto son incorporaciones.

Se reprodujeron **{proof['csv_tables_byte_identical']} CSV byte a byte**: tabla principal y seis tablas de auditoría. Su lectura/exportación conserva exactamente tipos, números y textos originales. Metadatos contienen configuración, versiones, políticas y huellas; los tiempos de ejecución se guardan aparte porque son variables. El pipeline incluyendo gráficos tomó {timing:.2f} s en esta ejecución; no es una garantía de tiempo en otro equipo.

SHA-256 de la tabla principal: `{metadata['feature_dataset_sha256']}`. Fuente preparada: `{metadata['source_input_sha256']}`. Todas las huellas y las pruebas completas están en [phase4_metadata.json](phase4_metadata.json), [reproducibility.json](reproducibility.json) y [verification-log.txt](verification-log.txt). Se validaron los **{metadata['figure_count']} PNG y sus {metadata['figure_count']} HTML**; los PNG se revisaron visualmente. Los HTML usan `interactive/plotly.min.js` local y funcionan sin conexión al mantener esa carpeta completa. La identidad byte a byte se exige para las tablas; para las visualizaciones se valida integridad y contenido descriptivo, no identidad binaria entre versiones distintas de bibliotecas.

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
| `reports/phase4/figures/`, `reports/phase4/interactive/` | Nuevos; {metadata['figure_count']} pares PNG/HTML y JavaScript local |
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

{md_table(graph_rows)}

Se detiene aquí el proyecto hasta la revisión y aprobación de la Fase 5.
"""
    (OUT / "feature_engineering_findings.md").write_text(text, encoding="utf-8")
    print(f"Informe generado; {tests} pruebas; {protected} archivos protegidos intactos.")


if __name__ == "__main__":
    main()
