"""Informe reproducible: consume artefactos verificados, sin volver a entrenar."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.feature_validation import check_protected
from src.exploratory_analysis import DISCLAIMER

OUT = ROOT / "reports/phase5"


def md_table(frame):
    def cell(value):
        if pd.isna(value):
            return "—"
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value).replace("|", "/").replace("\n", " ")
    result = ["| " + " | ".join(map(str, frame.columns)) + " |",
              "| " + " | ".join("---" for _ in frame.columns) + " |"]
    result.extend("| " + " | ".join(cell(x) for x in row) + " |"
                  for row in frame.itertuples(index=False, name=None))
    return "\n".join(result)


def view(table, columns, labels=None):
    return md_table(table[columns].rename(columns=labels or {}))


def primary_parameter_display(model):
    """Keep the integer/fraction distinction explicit in the exported table."""
    value = model['parameters']['max_features']
    available = model['tree_feature_availability']
    assert type(value) is float and value == 1.0
    assert available['selected_feature_count'] == available['model_input_feature_count'] == 17
    assert available['effective_available_features_per_tree'] == [17]
    assert available['trees_with_all_selected_features'] == available['tree_count'] == 200
    return {**model['execution_parameters'], 'max_features': repr(value),
            'max_features_type': type(value).__name__,
            'selected_features': available['selected_feature_count'],
            'effective_available_features_per_tree': 17}


def main():
    meta = json.loads((OUT / "phase5_metadata.json").read_text())
    model = json.loads((ROOT / "models/phase5/model_metadata.json").read_text())
    baseline = json.loads((ROOT / "models/phase5/statistical_baseline.json").read_text())
    proof = json.loads((OUT / "reproducibility.json").read_text())
    timing = json.loads((OUT / "execution_stats.json").read_text())
    protected = check_protected(ROOT, OUT / "protected_before_phase5.json")
    assert proof["full_reproduction_completed"] and all(proof["training_invariance"].values())
    suites = ET.parse(OUT / "pytest-results.xml").getroot().findall("testsuite")
    tests = sum(int(s.get("tests", 0)) for s in suites)
    failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    assert failed == skipped == 0
    seconds = sum(float(s.get("time", 0)) for s in suites)
    tables = {name: pd.read_csv(OUT / (name + ".csv"), float_precision="round_trip") for name in
              ("candidate_features", "selected_features", "temporal_split_summary", "model_comparison",
               "threshold_sensitivity", "seed_stability", "hyperparameter_sensitivity", "model_agreement",
               "synthetic_anomaly_results", "review_workload", "top_scored_observations", "ineligibility_summary",
               "prism_score_profiles", "method_only_observations", "synthetic_injection_audit",
               "max_features_sensitivity", "max_features_synthetic_results", "prism_30_1994_max_features",
               "seed_prism_instability", "seed_rank_changes")}
    scores = pd.read_csv(ROOT / "data/processed/phase5/anomaly_scores.csv", float_precision="round_trip")
    cfg = meta["config"]
    candidates, selected = tables["candidate_features"], tables["selected_features"]
    split, comparison = tables["temporal_split_summary"], tables["model_comparison"]
    thresholds, seeds = tables["threshold_sensitivity"], tables["seed_stability"]
    hyper, synthetic = tables["hyperparameter_sensitivity"], tables["synthetic_anomaly_results"]
    top = tables["top_scored_observations"]
    daily = tables["review_workload"].query("group_type == 'day'")
    workload = daily.groupby("model", sort=True).agg(
        máximo_diario=("marked_rows", "max"), días_sin_marcaciones=("marked_rows", lambda x: int(x.eq(0).sum())),
        días_sin_elegibles=("days_with_no_eligible_measurements", "sum"))
    macro = synthetic.groupby("model").synthetic_marked_fraction.mean()
    actual_seeds = seeds.query("seed != 42 and top_fraction == 0.02")
    stability = actual_seeds.groupby("period", sort=False).agg(
        rho_mínimo=("ranking_spearman_vs_primary", "min"), rho_máximo=("ranking_spearman_vs_primary", "max"),
        Jaccard_mínimo=("jaccard_top_vs_primary", "min"), Jaccard_máximo=("jaccard_top_vs_primary", "max"),
        marcación_mínima_pct=("marked_q99_pct", "min"), marcación_máxima_pct=("marked_q99_pct", "max")).reset_index()
    synthetic_display = synthetic.copy()
    synthetic_display["marcación_sintética_pct"] = 100 * synthetic_display.synthetic_marked_fraction
    synthetic_display["fondo_sin_etiqueta_pct"] = 100 * synthetic_display.unlabelled_background_marked_fraction
    reference_counts = []
    for period, group in scores.groupby("period", sort=False):
        eligible = group.loc[group.model_eligible]
        reference_counts.append({"Periodo": period, "Elegibles": len(eligible),
                                 "Referencia |z| ≥ 3.5": int(eligible.baseline_robust_z_reference_marked.sum()),
                                 "Marcación %": 100 * eligible.baseline_robust_z_reference_marked.mean()})
    criteria = cfg["recommendation_criteria"]
    recommendation = {
        "recommendation": "paired_experimental_scores; baseline interpretable reference and Isolation Forest multivariate comparator",
        "operational_combination_rule": None, "winner_by_real_accuracy": None,
        "predeclared_criteria": criteria,
        "synthetic_macro_marked_fraction": macro.to_dict(),
        "forest_minimum_seed_ranking_spearman": float(actual_seeds.ranking_spearman_vs_primary.min()),
        "forest_minimum_seed_top_2pct_jaccard": float(actual_seeds.jaccard_top_vs_primary.min()),
        "test_q99_marked_pct": comparison.query("period == 'prueba'").set_index("model").marked_q99_pct.to_dict(),
        "integrity_verified": protected, "full_reproduction_completed": True,
        "phase6_requires_formal_approval": True, "disclaimer": DISCLAIMER}
    (OUT / "provisional_recommendation.json").write_text(json.dumps(recommendation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    figures = pd.DataFrame([{"Visualización": f["title"], "Imagen": f"[PNG]({f['png']})",
                             "Interactiva": f"[HTML]({f['html']})"} for f in meta["figures"]])
    threshold_values = pd.DataFrame([{"Modelo": name, "Referencia": label, "Valor": value}
                                    for name, values in model["thresholds"].items() for label, value in values.items()])
    eligibility_counts = split[["period", "rows", "eligible_rows", "eligible_pct"]].copy()
    eligibility_counts["no_elegibles"] = eligibility_counts.rows - eligibility_counts.eligible_rows
    train_rare = tables["prism_score_profiles"].query("period == 'entrenamiento' and prism_id == '30-1994'")
    concentration = thresholds.query("threshold_label == 'q99'")
    macro_table = pd.DataFrame({"Método": macro.index, "Media de marcación sintética por escenario %": 100 * macro.values})
    reason_columns = ["feature_name", "correlated_with", "spearman_with_retained", "reason"]
    source_sha = meta["source_sha256"]
    revision = json.loads((OUT / "max_features_revision.json").read_text())
    budget_summary = tables["max_features_sensitivity"]
    budget_synthetic = tables["max_features_synthetic_results"]
    budget_macro = budget_synthetic.groupby("variant").synthetic_marked_fraction.mean().mul(100).reset_index(name="Media sintética por escenario %")
    parameter_display = primary_parameter_display(model)
    closure = json.loads((OUT / 'documentation_closure.json').read_text())
    assert closure['production_artifacts_unchanged'] and closure['serialization_reload_scores_exact']
    rank_change = tables['seed_rank_changes']
    rank_summary = rank_change.groupby('period',sort=False).agg(
        score_std_media=('score_std_across_seeds','mean'),score_std_máxima=('score_std_across_seeds','max'),
        posiciones_rango_medio=('rank_range_across_seeds','mean'),posiciones_rango_máximo=('rank_range_across_seeds','max')).reset_index()
    most_unstable = tables['seed_prism_instability'].groupby('period',sort=False).head(3)
    correction = f"""## Corrección de `max_features`

La revisión distinguió el valor numérico de su **tipo Python**. En scikit-learn, el entero `max_features=1` establece **una característica por árbol**; la fracción `max_features=0.5` permite 8 de las 17 características por árbol, y `max_features=1.0` permite las 17. Las variables disponibles no son necesariamente todas las que efectivamente aparecen en los splits.

**El artefacto anterior de este proyecto ya utilizaba `1.0` de tipo float.** Se confirmó antes de programar en `config/phase5.json`, JSON y Joblib, con 17 variables disponibles en los 200 árboles. La tabla Markdown anterior eliminaba ceros decimales y mostraba `1`, generando una ambigüedad. Se corrige la presentación y se exige el tipo float en el modelo principal. No se afirma falsamente que el artefacto anterior utilizó el entero `1`, ni que hubo un cambio numérico de 1 a 1.0 en él. El entero `1` se entrenó en la revisión anterior como **control comparativo nuevo**, no como copia de un modelo histórico de este proyecto.

En la revisión anterior se volvió a entrenar el principal con todas las variables disponibles, manteniendo los datos y parámetros autorizados. **En este cierre documental no se repite el entrenamiento de producción:** se reutilizan y verifican los Joblib, metadatos, scores y comparaciones existentes. La configuración principal es:

```python
IsolationForest(n_estimators=200, max_samples=256, max_features=1.0,
                bootstrap=False, random_state=42, contamination=0.02, n_jobs=1)
```

Metadatos verificados: 17 características seleccionadas, 17 entradas del bosque, **17 disponibles en cada uno de los 200 árboles**, scikit-learn {model['versions']['scikit-learn']}, semilla 42 y 2.909 filas elegibles de entrenamiento. Los nombres son los de la sección 5. `tree_feature_availability.csv` registra para cada árbol los nombres disponibles y los nombres efectivamente usados en splits, para las tres variantes.

En la revisión anterior los scores se recalcularon desde las características, sin copiar resultados anteriores. Son exactamente iguales al principal anterior, al igual que percentiles, marcas, regla, selección, elegibilidad, divisiones, imputación y escala. Se conservó el estado aprendido: {revision['learned_state_unchanged']}. En este cierre se reproducen las puntuaciones mediante inferencia sobre el modelo guardado, sin ajustar selección, imputación, escala, árboles ni umbrales. Las inyecciones sintéticas permanecen idénticas por SHA-256. Cambian la presentación, las comprobaciones de tipo, metadatos de disponibilidad, tablas comparativas y trazabilidad de configuración. `max_features_revision.json` documenta igualdad por columna, y `audit/` conserva el informe anterior y su hash `{revision['previous_report_sha256']}`.

### Verificación del cierre documental

Verificación realizada el **{closure['verified_at_utc']}**. Joblib y `model_metadata.json` coinciden en `max_features=1.0`, tipo `float`, 17 características seleccionadas y **17 disponibles por árbol, en los 200 árboles**. La tabla del modelo principal separa valor, tipo y número efectivo para impedir que el formato suprima el decimal.

Se serializó el bundle existente en un archivo temporal, se recargó y se reprodujeron exactamente scores y percentiles de las 7.178 filas. Se verificaron los hashes de {closure['production_artifact_count']} artefactos de producción y {closure['figure_file_count']} archivos gráficos dependientes, sin cambios respecto al inicio del cierre. Los gráficos y las tablas sintéticas, de estabilidad, carga de revisión y `30-1994` corresponden a esos artefactos; no requieren regeneración numérica. La suite completa vuelve a comprobar ausencia de fuga, incluida la invariancia del entrenamiento frente a cambios en datos futuros.

La reproducción completa de **34 CSV byte a byte** y la perturbación de 3.261 filas futuras pertenecen a la verificación anterior, conservada en `reproducibility.json` y vinculada a los mismos hashes de fuente, configuración y estado aprendido. Este cierre verifica nuevamente la recarga y la reproducción de inferencia; no ejecuta `verify_phase5.py --reproduce` ni el entrenamiento principal. Evidencia actual: `documentation_closure.json`, `documentation_metadata.json`, `pytest-results.xml` y `verification-log.txt`.

Cada comparación conserva el mismo entrenamiento, características, mediana, RobustScaler, contaminación, árboles, muestras y semilla. El imputador y escalador se mantienen **congelados**, y solo cambia el presupuesto de variables del bosque. Cada variante aprende sus propios q95/q98/q99 y umbral interno exclusivamente con entrenamiento; no se reutiliza el umbral del principal para otra variante. Resumen del top 2% frente al principal:

{view(budget_summary.query('top_fraction == 0.02'), ['variant','period','effective_features_per_tree','ranking_spearman_vs_primary','jaccard_top_vs_primary','mean_score','median_score','marked_q99_rows','marked_q99_pct','marked_prisms','ks_distance_vs_training','maximum_daily_marked_rows'])}

`max_features_sensitivity.csv` incluye top 1%, 2% y 5%, concentración en el primer/tres primeros prismas, umbrales, firmas del entrenamiento y preprocesamiento. `max_features_daily_workload.csv`, `max_features_prism_profiles.csv` y `max_features_scores.csv` conservan el detalle diario, por prisma y por observación. En prueba, las marcaciones son 36, 65 y 60 respectivamente; esa cantidad no mide precisión ni utilidad geomecánica.

La revisión anterior evaluó los 14 escenarios para cada presupuesto, con los mismos datos artificiales, semilla e intensidades. En cada ensayo permanecieron congelados bosque, imputador, escala y umbrales. Este informe reconstruye los resultados desde los CSV verificados. La siguiente tabla muestra objetivos elegibles, fracción marcada, cambio medio del score, percentil medio, marcación del fondo sin etiqueta y diferencia en fracción marcada frente al **control nuevo** entero `1`:

{view(budget_synthetic, ['variant','kind','intensity','eligible_target_rows','synthetic_marked_fraction','mean_score_change','mean_training_percentile','unlabelled_background_marked_fraction','synthetic_marked_fraction_difference_vs_int1'])}

{md_table(budget_macro)}

El principal obtiene 50,84% de media por escenario, frente a 55,76% del entero `1` y 60,88% de `0.5`. El principal responde más al nivel sostenido de intensidad 3 que el entero; el control entero marca el salto positivo de intensidad 1 mientras el principal no lo marca. No hay mejora uniforme. Las diferencias de score entre modelos se describen en su propia escala y con sus percentiles; no son diferencias de probabilidad. El fondo sigue sin etiqueta y no se denomina falso positivo. **La corrección de presentación y la disponibilidad de 17 variables no demuestra mayor precisión real.** Continúan sin existir validación geomecánica ni etiquetas reales suficientes.

Revisión específica de `30-1994`, presente solo en entrenamiento:

{view(tables['prism_30_1994_max_features'].query("period == 'entrenamiento'"), ['variant','eligible_rows','marked_q99_rows','marked_q99_pct','maximum_score','prism_rows_in_top30','top30_prism_share_pct'])}

En los tres presupuestos sus 15 filas elegibles se marcan q99 y ocupan 15 de las 30 principales observaciones **del periodo de entrenamiento**. El score máximo cambia, pero se conserva la concentración. `prism_30_1994_observations.csv` registra las 35 filas reales con elegibilidad, scores y explicaciones; sus principales desviaciones siguen correspondiendo a movimiento/tasa, tendencia y comparación robusta con el historial. No se elimina el prisma ni sus extremos, ni se concluye que representa una falla. El nuevo gráfico muestra su movimiento real y sus scores, incluyendo filas no elegibles.

La recomendación se mantiene: regla transparente más principal **1.0 (float)** como comparación experimental multivariable. Se conserva 1.0 como especificación explícita de disponibilidad completa, no porque gane los ensayos sintéticos, produzca menos revisiones ni tenga resultados cercanos a una fecha documental. No se define una alerta combinada y no se avanza a la Fase 6.
"""
    text = f"""# Fase 5 — Modelos no supervisados y evaluación temporal

## 1. Resumen ejecutivo

Se implementaron una regla estadística transparente y un Isolation Forest global, con selección de variables y aprendizaje exclusivamente sobre entrenamiento. Se preservan **{meta['output_rows']:,} filas, {meta['prisms']} prismas y {protected} archivos anteriores**. De 20 candidatos, se seleccionaron **{len(selected)} características**; {meta['eligible_rows']:,} filas ({meta['eligible_pct']:.2f}%) son elegibles. Las otras {meta['input_rows'] - meta['eligible_rows']:,} permanecen con motivos, puntuaciones desconocidas y clasificaciones experimentales desconocidas.

La suite actual termina con **{tests} pruebas aprobadas, {failed} fallidas y {skipped} omitidas**. En este cierre se reproducen las puntuaciones con los modelos guardados, sin reentrenamiento de producción. La reproducción completa previamente verificada conserva {proof['csv_tables_byte_identical']} CSV idénticos byte a byte y una prueba crítica sobre {proof['future_rows_modified']} filas futuras, vinculadas al mismo estado aprendido. Las pruebas actuales vuelven a comprobar invariancia temporal, serialización y recarga.

La recomendación provisional es conservar **ambas puntuaciones experimentales**: la regla para una referencia interpretable e Isolation Forest para comparación multivariable. No se declara un ganador por precisión real. Se entregan {meta['figure_count']} pares PNG/HTML descriptivos; no se implementan alertas operativas ni niveles de riesgo.

> {DISCLAIMER}

{correction}

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

Se declararon 20 candidatos, prioridad interpretativa y |Spearman| > {cfg['spearman_limit']} antes del entrenamiento final. Se rechazan candidatos vacíos, constantes o con más de {100*cfg['max_training_missing_fraction']:.0f}% faltantes. Las estadísticas siguientes se calculan sobre las **{model['training_rows']} filas inicialmente elegibles de entrenamiento**, no sobre toda la serie. La varianza conserva las unidades al cuadrado; cero faltantes aquí no significa disponibilidad en las 7.178 filas.

{view(candidates, ['feature_name', 'unit', 'training_missing_pct', 'training_variance', 'included'], {'feature_name':'Candidato','unit':'Unidad','training_missing_pct':'Faltante %','training_variance':'Varianza entrenamiento','included':'Incluido'})}

`candidate_features.csv` documenta además valores únicos, interpretación permitida, transformaciones y correlaciones. `spearman_training.csv`, `pearson_training.csv` y `pair_redundancy.csv` conservan las matrices y los 190 pares examinados; Pearson es complementaria, no el criterio de selección.

## 5. Variables seleccionadas y excluidas

{view(selected, ['feature_name', 'unit'], {'feature_name':'Característica seleccionada','unit':'Unidad'})}

Exclusiones dentro del conjunto candidato:

{view(candidates.loc[~candidates.included], reason_columns, {'feature_name':'Excluida','correlated_with':'Se conserva','spearman_with_retained':'Spearman','reason':'Motivo'})}

La diferencia frente a la mediana previa es muy redundante con el z-score robusto. Los valores absolutos son transformaciones deterministas de los predictores con signo: se conservan estos últimos para mantener la dirección y evitar duplicar peso. Una transformación absoluta no tiene necesariamente correlación lineal 1 con su variable original; su dependencia matemática justifica esta exclusión.

Las **298 columnas restantes** están inventariadas en `excluded_features.csv`: incluye las tres candidatas excluidas y 295 columnas fuera del conjunto compacto. IDs, fechas, posiciones temporales, textos originales, archivos, hashes y auditoría solo sirven para trazabilidad. Las banderas de calidad determinan elegibilidad y contexto, sin mezclarse como predictores del bosque. No se incorporan automáticamente otras constantes, alias o ventanas de Fase 4.

## 6. División temporal

Los cuantiles 0,60 y 0,80 se calculan sobre **93 días calendario distintos observados**, con interpolación lineal; cada corte se lleva al comienzo del día siguiente. Se conservan días y timestamps completos en un solo periodo. No se ordena ni corta por número de fila y no hay partición aleatoria. Por eso las proporciones de filas no son exactamente 60/20/20.

{view(split, ['period','first_timestamp','last_timestamp','calendar_days','rows','prisms','eligible_rows','eligible_pct'], {'period':'Periodo','first_timestamp':'Primera medición','last_timestamp':'Última medición','calendar_days':'Días distintos','rows':'Filas','prisms':'Prismas','eligible_rows':'Elegibles','eligible_pct':'Elegibles %'})}

Cortes exclusivos: entrenamiento `timestamp < {meta['cutoffs']['train_end_exclusive']}`; validación hasta `timestamp < {meta['cutoffs']['validation_end_exclusive']}`; prueba desde ese segundo corte. El entrenamiento **elegible** comienza el {model['training_first_timestamp']} y utiliza {model['training_prisms']} prismas; el periodo completo contiene 46.

En validación aparecen `22-2059`, `22-2060` y `22-2061`; dejan de observarse `30-1994`, `30-1995` y `31-1930`. La prueba mantiene los 46 prismas de validación. El campo de nuevos prismas de entrenamiento enumera los iniciales respecto al conjunto previo vacío, no incorporaciones durante validación. `temporal_split_summary.csv` registra disponibilidad de z-score y pendientes por periodo; `prism_score_profiles.csv` identifica los prismas presentes en entrenamiento elegible.

Las características de validación pueden usar mediciones anteriores de entrenamiento, y las de prueba pueden usar el historial observado de validación; el imputador, escala, bosque, regla y umbrales no se reajustan con ellas.

## 7. Elegibilidad

{md_table(eligibility_counts)}

Se requieren historia previa, cobertura suficiente de 72 h y 7 días, intervalo válido y ausencia de hueco prolongado, según las políticas de Fase 4. Son indispensables la tasa, ambas pendientes, z-score, conteo y duración de racha. Se rechazan infinitos y más de {100*cfg['max_row_missing_fraction']:.0f}% faltantes seleccionados; la transformación aprendida debe producir valores finitos. No se retiran filas del archivo maestro.

{view(tables['ineligibility_summary'], ['reason','affected_rows'], {'reason':'Motivo','affected_rows':'Filas afectadas'})}

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

La escala es `1.4826 × MAD`; si es cero, se usa IQR y, si ambas son cero, escala unitaria con limitación registrada. Aquí ambas referencias usan MAD: tendencia, centro {baseline['trend_reference']['center']:.6f} mm/día y escala {baseline['trend_reference']['scale']:.6f}; persistencia, centro {baseline['persistence_reference']['center']:.6f} h y escala {baseline['persistence_reference']['scale']:.6f}. Pesos y referencias son explícitos; no se ajustan por proximidad a una falla. Calidad actúa como puerta de elegibilidad, no como suma de riesgo.

La marca separada `|z robusto| ≥ 3.5` es una referencia estadística inicial; **no es el umbral del score compuesto ni un límite geomecánico**:

{md_table(pd.DataFrame(reference_counts))}

## 10. Isolation Forest

{md_table(pd.DataFrame([parameter_display]))}

Biblioteca: scikit-learn {model['versions']['scikit-learn']}; `n_jobs=1`. Se entrenan 200 árboles sobre un máximo de 256 filas por árbol, con 17 características, sin bootstrap y semilla fija 42. El modelo es global porque hay {model['training_rows']} filas elegibles distribuidas en 43 prismas y varios prismas son demasiado pequeños para entrenamientos independientes fiables.

Score continuo: **`−score_samples`**, de modo que mayor valor significa mayor atipicidad estadística. No es una probabilidad. El umbral interno es `−offset_`; la contaminación fija 0,02 solo define ese corte. Los percentiles se calculan mediante la distribución empírica de scores de **entrenamiento**, incluyendo empates por la derecha; no se recalculan sobre validación o prueba.

{md_table(threshold_values)}

Todas las marcas usan **score estrictamente mayor que el umbral**. Los empates y el tamaño finito explican pequeñas diferencias respecto al porcentaje nominal. Score, percentil, marca q95/q98/q99 y marca interna son campos separados. q99 se utiliza como referencia común de comparación, no como alerta seleccionada retrospectivamente.

## 11. Modelo opcional

No se implementó LOF: los dos métodos obligatorios ya permiten comparar una regla explícita con una distribución multivariable. Se evita añadir un tercer modelo sin evidencia de que mejore la evaluación. Tampoco se implementan modelos supervisados, redes neuronales o LSTM.

## 12. Evaluación sin etiquetas

{view(comparison, ['model','period','eligible_rows','mean_score','median_score','max_score','marked_q99_rows','marked_q99_pct','marked_prisms','ks_distance_vs_training'])}

No se calculan accuracy, precision, recall, F1, AUC, sensibilidad ni especificidad sobre datos reales. Se usan distribución, estabilidad de rankings, coincidencia de conjuntos, marcación experimental, perfiles por prisma y pruebas artificiales. Los scores de métodos diferentes tienen escalas diferentes; no se restan ni se promedian como si fueran comparables.

La distancia KS mide cuánto se separan las distribuciones acumuladas respecto al entrenamiento; no se presenta un p-valor ni se supone independencia de observaciones temporales. Spearman mide asociación de rankings; Jaccard es intersección/unión de los conjuntos superiores, definidos con `ceil(fracción × elegibles)` y desempate determinista por ID.

## 13. Estabilidad temporal

En prueba, la distancia KS de la regla es {comparison.query("model == 'baseline' and period == 'prueba'").ks_distance_vs_training.iloc[0]:.4f}; la de Isolation Forest es {comparison.query("model == 'isolation_forest' and period == 'prueba'").ks_distance_vs_training.iloc[0]:.4f}. Aumentan los scores y las marcas frente a validación; esto describe un cambio de distribución, no su causa ni una probabilidad de falla.

Se conservan perfiles por método, periodo y prisma: número elegible, porcentaje marcado, score, mediana de movimiento, intervalo mediano y representación en entrenamiento. El modelo global puede concentrar marcaciones en prismas de escala distinta. Un ejemplo es `30-1994`, presente solo en entrenamiento:

{view(train_rare, ['model','prism_id','rows','eligible_rows','marked_q99_rows','marked_pct_of_eligible','median_elapsed_hours'])}

Que Isolation Forest marque sus 15 observaciones elegibles no convierte sus 35 mediciones originales en un diagnóstico. Debe revisarse la escala, frecuencia, referencia instrumental e historia de ese prisma. Los gráficos incluyen también prismas nuevos de validación para mostrar esta limitación.

## 14. Estabilidad entre semillas

Se utilizaron **42, 7, 2026, 101 y 1729**, manteniendo 42 como referencia previamente fijada. No se escoge la semilla que produzca resultados más convenientes. Resumen de las otras cuatro para los conjuntos superiores del 2%:

{md_table(stability)}

La correlación mínima es {actual_seeds.ranking_spearman_vs_primary.min():.4f} y el Jaccard mínimo {actual_seeds.jaccard_top_vs_primary.min():.4f}, superiores a las referencias técnicas previamente declaradas {criteria['seed_rank_correlation_min']} y {criteria['seed_top_2pct_jaccard_min']}. `seed_stability.csv` incluye los principales 1%, 2% y 5%; `seed_score_variability.csv` registra media, dispersión y rango del score por observación. Un ranking estable puede coexistir con variación de la marca al cruzar un umbral.

Todas las semillas de esta evaluación utilizan `max_features=1.0` de tipo float. Se añade variabilidad de posición **dentro de cada periodo**, con empates por rango promedio; no se mezclan rankings de fechas distintas:

{md_table(rank_summary)}

Los prismas con mayor rango medio de posición entre semillas por periodo son:

{view(most_unstable, ['period','prism_id','eligible_rows','mean_rank_range','maximum_rank_range','mean_score_std','maximum_score_std'])}

`seed_rank_changes.csv` incluye las observaciones que cambian de posición, ordenadas por amplitud de rango; `seed_prism_instability.csv` incluye todos los prismas elegibles por periodo. El tamaño del periodo y la escala del prisma influyen en estos rangos; no son niveles de atención. La semilla 42 sigue fijada y no se selecciona una alternativa más conveniente.

## 15. Sensibilidad a hiperparámetros

Se evalúan 11 variantes, siempre reajustadas **solo sobre entrenamiento** y con la misma máscara de evaluación para una comparación justa. Se comparan contaminación, 100/200/400 árboles, 128/256/512 muestras, ausencia de escalado robusto y retirada de características de 7 días. Resultados en prueba:

{view(hyper.query("period == 'prueba'"), ['family','variant','selected_feature_count','ranking_spearman_vs_primary','jaccard_top_2pct_vs_primary','marked_q99_pct','marked_internal_pct'])}

Cambiar únicamente `contamination` deja los árboles y el ranking intactos con los demás parámetros y semilla fijados; cambia el offset interno y la carga de marcación. Por eso se comparan por separado el q99 aprendido y el corte interno. Retirar las variables de 7 días produce una correlación aproximada de 0,891 en prueba: la elección de características sí importa. No se reajusta el modelo principal después de mirar estos resultados ni se optimiza usando la fecha documental de falla.

La sensibilidad específica a `max_features` se evalúa separadamente con los tres tipos/presupuestos y preprocesamiento congelado, en la sección de corrección y `max_features_sensitivity.csv`.

## 16. Acuerdo entre modelos

{view(tables['model_agreement'], ['period','top_fraction','ranking_spearman','jaccard_top','common_top_rows','common_prisms','baseline_only_top_rows','forest_only_top_rows'])}

En prueba, la asociación de rankings es aproximadamente 0,667 y el acuerdo de los principales 2% es Jaccard 0,375. La regla enfatiza z-score, tendencia y persistencia; el bosque evalúa combinaciones multivariables. El desacuerdo no constituye automáticamente un error. `method_only_observations.csv` conserva {len(tables['method_only_observations'])} casos marcados q99 por un solo método, con trazabilidad y explicación; no se etiquetan como falsos positivos o falsos negativos.

## 17. Resultados sintéticos

Se crean **14 escenarios artificiales** sobre copias de validación del prisma `40-1959`: siete tipos y dos intensidades. Se eligió por disponibilidad estructural de historial y número de observaciones de entrenamiento, sin usar su score ni la fecha documental de falla. Semilla 2026. La amplitud base es diez veces la dispersión robusta de los cambios de entrenamiento: {synthetic.amplitude_mm.min():.6f} mm; intensidad 3: {synthetic.amplitude_mm.max():.6f} mm. Son magnitudes de ensayo técnico, no límites geotécnicos.

Se modifica exclusivamente el movimiento reportado en copias y se recalculan sus características con el historial anterior y las mismas políticas de Fase 4. La progresión y la aceleración artificial utilizan tiempo transcurrido real. Los siete tipos son salto positivo, salto negativo, nivel sostenido, incremento progresivo, aceleración artificial, mayor variabilidad y secuencia persistente. Los modelos, imputador, escala y umbrales permanecen congelados. `synthetic_injection_audit.csv` contiene {len(tables['synthetic_injection_audit'])} filas modificadas con ID, timestamp, antes/después, delta, escenario y semilla.

{view(synthetic_display, ['kind','intensity','model','target_rows','eligible_target_rows','marcación_sintética_pct','mean_score_change','mean_training_percentile','fondo_sin_etiqueta_pct'])}

{md_table(macro_table)}

Esta media asigna el mismo peso a cada escenario; **no es precisión real ni recall de fallas**. Son escenarios solapados sobre un solo prisma, no 14 eventos independientes. El cambio sostenido modifica 46 filas por intensidad, de las cuales 45 son elegibles. En total hay 152 posiciones objetivo entre escenarios, 150 elegibles por método; su suma no representa filas reales independientes.

La regla marca más de estas modificaciones con q99; Isolation Forest no marca los saltos de intensidad 1 y solo marca 1/7 de la aceleración artificial de esa intensidad. Su score aumenta aun cuando no cruza q99. La media cercana al 50% del bosque no debe ocultar esas diferencias por tipo. No se ajustaron umbrales para mejorar los casos.

La **tasa de marcación del conjunto de fondo sin etiqueta** se calcula sobre las filas elegibles no modificadas. No es una tasa de falsos positivos: pueden existir comportamientos atípicos desconocidos y algunas ventanas posteriores incorporan la modificación artificial, aunque la fila actual del fondo no se haya editado. Los datos reales nunca se sobrescriben.

## 18. Carga de revisión

Con q99 como referencia experimental, la regla marca {int(comparison.query("model == 'baseline'").marked_q99_rows.sum())} observaciones y el bosque {int(comparison.query("model == 'isolation_forest'").marked_q99_rows.sum())} en todo el registro; pueden coincidir. Los porcentajes usan únicamente filas elegibles. No se define un flujo operativo de revisión ni una alerta combinada.

{md_table(workload.reset_index())}

Los seis días sin datos elegibles están incluidos en los días sin marcaciones y deben distinguirse de días efectivamente evaluados sin marca. La carga diaria no equivale a tiempo de trabajo: todavía no se conoce cuánto tarda el especialista en revisar una observación ni cómo agrupar múltiples observaciones de un mismo prisma.

Concentración por periodo y método:

{view(concentration, ['model','period','marked_rows','marked_pct','prisms_affected','top_prism_share_of_marked_pct','top_three_prisms_share_of_marked_pct'])}

Los cortes q95 y q98 y el umbral interno están documentados en `threshold_sensitivity.csv` (21 combinaciones método/umbral/periodo). El 5% de filas elegibles es solo una referencia técnica previamente declarada, **no capacidad de revisión validada ni umbral geomecánico**. En prueba ambos q99 individuales quedan por debajo de esa referencia; eso no valida una política de combinar sus marcas.

## 19. Explicabilidad

Cada fila elegible conserva las tres mayores desviaciones absolutas del valor respecto a la mediana e IQR de entrenamiento, con valores y unidades originales. Se añaden z-score histórico, pendiente, racha y calidad. Esta explicación es **aproximada y descriptiva**, no una atribución exacta de los árboles, importancia causal ni diagnóstico. Una desviación grande puede coexistir con otras combinaciones influyentes no capturadas por esa descripción.

Cinco mayores puntuaciones globales del bosque, todas de entrenamiento:

{view(top.head(5), ['prism_id','timestamp','period','isolation_forest_score','movement_rate_mm_per_day','historical_robust_z_score','local_trend_72h_slope_mm_per_day'])}

Para la primera observación: {top.iloc[0].descriptive_explanation}

La concentración en `30-1994` muestra la importancia de revisar escala e historia del prisma antes de atribuir un significado profesional. `top_scored_observations.csv` contiene las 30 mayores observaciones globales; `anomaly_scores.csv` conserva explicaciones para las 7.178 filas, incluidas las razones de no evaluación. `feature_descriptive_deviations.csv` resume desviaciones entre las principales observaciones; no se denomina importancia predictiva de características.

## 20. Modelo recomendado

Se recomienda provisionalmente un **enfoque de comparación con ambas puntuaciones**, manteniendo la regla como referencia interpretable y el bosque como complemento multivariable. No se define una combinación operativa de marcas. No existe evidencia para declarar cuál es más preciso sobre comportamientos geotécnicos reales.

| Criterio previo | Evidencia obtenida | Alcance |
| --- | --- | --- |
| Reproducibilidad | Recarga y reproducción exactas de estado aprendido y scores de ambos métodos | Comprobación técnica |
| Correlación de rankings entre semillas ≥ 0,9 | Mínimo {actual_seeds.ranking_spearman_vs_primary.min():.4f} en el bosque | Rankings estables; la regla es determinista |
| Jaccard de top 2% entre semillas ≥ 0,5 | Mínimo {actual_seeds.jaccard_top_vs_primary.min():.4f} | Coincidencia parcial, no etiquetas |
| Marcación sintética media por escenario ≥ 0,5 | Regla {100*macro['baseline']:.2f}%; bosque {100*macro['isolation_forest']:.2f}% | El bosque queda apenas por encima y falla en varios tipos/intensidades |
| Referencia de revisión ≤ 5% | q99 de prueba: regla 4,56%; bosque 3,70% | Referencia técnica; capacidad real pendiente |
| Interpretabilidad | Fórmula explícita y desviaciones descriptivas | Más directa en la regla; aproximada en el bosque |
| Ejecución offline e integración | Joblib, JSON, funciones Python, sin servicios externos | Requiere datos con historial y características |
| Inferencia y tamaño | {timing['inference_100_observations_seconds']:.4f} s para 100 observaciones elegibles con ambos scores; bosque {timing['model_artifact_bytes']:,} bytes | Medición local, no garantía de latencia |

El pipeline completo tardó {timing['pipeline_seconds']:.3f} s en este entorno, incluida evaluación y sintéticos. El criterio de estabilidad temporal se revisa descriptivamente: existe deriva de scores y concentración por prisma, por lo que no se declara invariancia temporal ni validez fuera del caso. Los criterios son apoyos para comparación, no una puntuación de seguridad. `provisional_recommendation.json` conserva la recomendación y evidencia cuantitativa.

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

Se ejecutaron primero las **113 pruebas anteriores** sin cambios. La suite final contiene **{tests} pruebas aprobadas**, {failed} fallidas y {skipped} omitidas, en {seconds:.2f} s; {tests-113} son nuevas. Evidencia: `pytest-before.txt`, `pytest-development.txt`, `pytest-output.txt`, `pytest-results.xml` y `verification-log.txt`.

Antes de la revisión de max_features se repitieron las 147 pruebas existentes, todas satisfactorias (`audit/pytest_before_revision.txt`). `test_max_features_revision.py` comprueba tipo float, 17 variables efectivas, tres presupuestos, datos y preprocesamiento idénticos, umbrales de entrenamiento, conservación de filas, recarga exacta, invariancia frente al futuro y ausencia de ambigüedad en el informe. Este cierre añade dos regresiones para conservar el decimal, el tipo y el presupuesto efectivo en la tabla, y rechazar el entero como configuración principal. Los modelos ajustados por pruebas permanecen aislados de los artefactos de producción.

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

Fuente SHA-256: `{source_sha}`. Se verifican los {protected} archivos del manifiesto anterior antes/después; se conservan código, pruebas, datos e informes de las Fases 1–4. README y `.gitignore` reciben únicamente documentación de la nueva fase. Checkpoint final de Fase 4: `00b80d9e14f7e49b4d0c338f34d0670299669fb7`. Checkpoint inicial de Fase 5: `{meta['checkpoint_initial']}`. El hash final se registra tras el commit en `reports/phase5/git_checkpoint.txt`, incluido en el paquete.

Checkpoint previo a esta revisión: `{revision['previous_checkpoint']}`. El informe anterior se conserva íntegro en `audit/model_findings_before_max_features.md`, con SHA-256 `{revision['previous_report_sha256']}`. La comparación confirma que el modelo histórico de este proyecto ya tenía float 1.0; el control entero 1 de esta revisión es nuevo.

La verificación actual incluye las 7.178 filas, 49 prismas, estado desconocido de no elegibles, tipos, scores, percentiles, calendario, {meta['figure_count']} pares PNG/HTML y hashes de los artefactos. Al recargar, el preprocesador produce matrices idénticas y los modelos scores idénticos. La reproducción completa anterior comprobó **{proof['csv_tables_byte_identical']} CSV byte a byte**, los JSON de modelos y todos los campos aprendidos de los árboles; se conserva esa evidencia porque los artefactos permanecen intactos.

Prueba crítica anterior: se modificaron únicamente 20 candidatos en **{proof['future_rows_modified']} filas de validación y prueba**, usando valores alternados muy grandes; la selección, imputador, escalador, parámetros, todos los nodos y valores de árboles, regla, umbrales y scores de las **{proof['training_invariance']['training_rows_checked']} filas de entrenamiento** permanecieron exactamente iguales. La suite actual vuelve a comprobar la invariancia temporal y el cierre perturba las 3.261 filas futuras durante inferencia sin ajustar el modelo. Esto comprueba esas vías de fuga; no demuestra causalidad científica.

Los Joblib actuales se verifican por SHA-256 contra metadatos. Al repetir el entrenamiento se compara el **estado aprendido completo**, no los bytes de representación interna del objeto: alias de memoria y relleno de estructuras pueden variar sin cambiar parámetros o predicciones. El fingerprint incluye todos los campos de nodos y valores de cada árbol, escalas, imputación y parámetros. Tiempos de ejecución se almacenan separados y se excluyen de la comparación determinista.

Comandos desde la raíz, una vez instaladas las dependencias:

```bash
python scripts/verify_phase5.py
python scripts/close_phase5_documentation.py
python -m pytest -q --junitxml=reports/phase5/pytest-results.xml > reports/phase5/pytest-output.txt
python scripts/build_phase5_report.py
python scripts/close_phase5_documentation.py --finalize
```

Para una reproducción completa opcional que vuelve a ajustar modelos en una carpeta temporal: `python scripts/verify_phase5.py --reproduce`. Para regenerar las salidas de producción: `python scripts/run_phase5.py`; lee y protege los resultados anteriores y solo escribe Fase 5. **Ninguno de estos dos comandos se ejecuta en este cierre**, que reutiliza los artefactos corregidos.

## 24. Recomendaciones para la Fase 6

**Puede proponerse avanzar técnicamente, únicamente después de aprobación formal**, porque se cumplen conservación, cronología, aprendizaje en entrenamiento, reproducibilidad y pruebas. La propuesta es integrar puntuaciones experimentales y sus motivos en el alcance que apruebe la usuaria; esto no autoriza automáticamente alertas operativas.

Antes de definirlas, el ingeniero debe revisar la referencia del movimiento, escalas/frecuencias de prismas, tratamiento de no elegibles, elección de umbrales y capacidad real de revisión. También se necesitan casos y etiquetas independientes para evaluar utilidad profesional. Mantener puntuaciones y calidad separadas, documentar el desacuerdo, y distinguir repetidas mediciones de un único episodio. No presentar el 5% experimental como una capacidad de trabajo validada.

No se avanza en este trabajo a dashboard, Streamlit, SQLite, APIs, modelos adicionales, uniones con lluvia/sismicidad/voladuras, detección de cambios ni despliegue. Se detiene la fase para revisión.

## 25. Archivos creados y modificados

Los siete módulos solicitados se crearon en Fase 5. Se añadieron cuatro módulos auxiliares por razones concretas: `phase5_config.py` aísla validación de la configuración anterior; `temporal_split.py` hace explícita la partición global; `model_validation.py` verifica estado aprendido y fuga; `phase5_visualizations.py` separa gráficos de entrenamiento. En esta revisión se actualizan módulos y scripts de Fase 5; no se modifica código ni pruebas de Fases 1–4. Se añade `test_max_features_revision.py` y se conserva el informe anterior en `audit/`.

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
│   ├── test_phase5_no_leakage.py
│   └── test_max_features_revision.py    [nuevo en la revisión]
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
        ├── max_features_sensitivity.csv, max_features_daily_workload.csv
        ├── max_features_prism_profiles.csv, max_features_scores.csv
        ├── tree_feature_availability.csv, max_features_synthetic_results.csv
        ├── max_features_revision.json, prism_30_1994_max_features.csv
        ├── prism_30_1994_observations.csv
        ├── seed_rank_changes.csv, seed_prism_instability.csv
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
        ├── audit/                      [informe, hashes y pruebas previas]
        ├── figures/                    [{meta['figure_count']} PNG]
        └── interactive/                [{meta['figure_count']} HTML y plotly.min.js local]
```

Los datos derivados, modelos y gráficos se incluyen en el paquete descargable; los archivos voluminosos regenerables se excluyen de Git. El paquete conserva los originales y resultados históricos y no incluye el directorio interno `.git`, entornos o cachés. No hay credenciales. Al descomprimir se mantienen las rutas.

Visualizaciones descriptivas entregadas; los HTML usan `interactive/plotly.min.js` local y funcionan sin internet:

{md_table(figures)}

> {DISCLAIMER}

**Fin de Fase 5. Se espera revisión y aprobación formal antes de comenzar la Fase 6.**
"""
    (OUT / "model_findings.md").write_text(text, encoding="utf-8")
    print(f"Informe generado: 25 secciones más corrección max_features, {tests} pruebas, {protected} archivos históricos intactos.")


if __name__ == "__main__":
    main()
