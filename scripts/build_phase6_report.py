"""Rebuild every Phase 6 report from verified tables, without fitting."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.phase6_validation import read_outputs, check_protected, sha256
from src.exploratory_analysis import DISCLAIMER
OUT=ROOT/'reports/phase6'


def md_table(frame):
    def cell(value):
        if pd.isna(value):return '—'
        if isinstance(value,float):return f'{value:.6f}'.rstrip('0').rstrip('.')
        return str(value).replace('|','/').replace('\n',' ')
    lines=['| '+' | '.join(frame.columns)+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    lines += ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)]
    return '\n'.join(lines)


def test_totals(path):
    suites=ET.parse(path).getroot().findall('testsuite')
    return {k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}


def main():
    meta=json.loads((OUT/'phase6_metadata.json').read_text())
    proof=json.loads((OUT/'reproducibility.json').read_text())
    previous=test_totals(OUT/'pytest-before.xml');tests=test_totals(OUT/'pytest-results.xml')
    assert previous==dict(tests=158,failures=0,errors=0,skipped=0)
    assert tests['failures']==tests['errors']==tests['skipped']==0
    assert proof['training_blocked_during_entire_verification'] and proof['phase5_predictions_identical']
    assert proof['restored_all_columns_and_types_exact'] and proof['reproduced_csv_byte_identical']==12
    assert proof['source_metadata_sha256']==sha256(OUT/'phase6_metadata.json')
    assert check_protected(ROOT,OUT/'protected_before_phase6.json')==meta['protected_files_intact']
    for name,h in meta['files'].items():assert sha256(ROOT/name)==h
    tables=read_outputs(ROOT,meta)
    rows=tables['review_candidates.csv'];episodes=tables['episodes.csv'];policy=tables['policy_comparison.csv']
    total=policy.query("period=='total'").set_index('policy')
    sensitivity=tables['sensitivity_analysis.csv'].query("period=='total'")
    p=tables['prism_30_1994_observations.csv'];pe=episodes.loc[episodes.prism_id.eq('30-1994')]
    hybrid=total.loc['hybrid'];union=total.loc['union'];consensus=total.loc['consensus']
    selected=episodes.loc[episodes.candidate_policies.str.split(';').map(lambda x:'hybrid' in x)]
    withheld=tables['marks_not_selected_primary.csv']
    quality=episodes.loc[episodes.quality_interruption_flag]
    examples=selected.sort_values(['start_timestamp','prism_id']).head(4)
    figures=pd.DataFrame([{'Gráfico':f['title'],'PNG':f"[PNG]({f['png']})",'HTML offline':f"[HTML]({f['html']})"} for f in meta['figures']])
    results=md_table(policy[['period','policy','candidate_rows','candidate_episodes','candidate_prisms','mean_candidates_per_day',
                            'maximum_daily_candidates','row_reduction_vs_union_pct']])
    sensitive=md_table(sensitivity[['window_hours','min_marks','policy','candidate_rows','candidate_episodes','candidate_prisms',
                                   'row_reduction_vs_union_pct','maximum_daily_candidates','median_episode_duration_hours',
                                   'median_marks_per_episode','episodes_with_agreement','episodes_with_quality_interruption']])
    state=md_table(tables['causal_state_counts.csv'])
    quality_table=md_table(quality[['episode_id','prism_id','start_timestamp','ineligible_record_count','union_mark_count','candidate_policies']])
    model_display=pd.DataFrame([{'n_estimators':200,'max_samples':256,'max_features':'1.0','tipo':'float',
                                 'características disponibles por árbol':17,'bootstrap':False,'random_state':42,'contamination':.02,'n_jobs':1}])
    frozen_thresholds=meta['frozen_models']['thresholds']
    frozen_table=md_table(pd.DataFrame([{'Método':k,'q99 exacto':repr(v),'q99 redondeado':f'{v:.4f}'} for k,v in frozen_thresholds.items()]))
    first=json.loads((OUT/'initial_verification.json').read_text())
    singleton_count=int(episodes.union_mark_count.eq(1).sum())
    persistent_count=int(episodes.union_mark_count.ge(2).sum())
    cross_period=int(episodes.periods_observed.str.contains(';').sum())
    membership=int(episodes.record_count.sum())
    candidate_reduction=hybrid.row_reduction_vs_union_pct
    prism_table=md_table(p[['source_record_id','timestamp','model_eligible','model_ineligibility_reason',
                            'baseline_score','isolation_forest_score','baseline_training_percentile',
                            'isolation_forest_training_percentile','baseline_mark_q99','iforest_mark_q99',
                            'episode_id','causal_state','baseline_component_historical_z','baseline_component_trend','baseline_component_persistence']])
    prism_description=f"""# Revisión particular — prisma 30-1994

**Hechos observados:** {len(p)} registros, {int(p.model_eligible.sum())} evaluables y {int((~p.model_eligible).sum())} no evaluables. Aparece únicamente en entrenamiento, desde {p.timestamp.min()} hasta {p.timestamp.max()}. Cada método marca sus 15 observaciones evaluables con q99. Se conserva íntegro, sin reajustar modelos.

Sus scores y estados son retrospectivos y condicionados al modelo ajustado al final de entrenamiento. No estaban disponibles como resultados operativos en esas fechas; todas sus filas tienen `model_available_at_observation=False`.

Se genera {len(pe)} episodio con ventana de 72 h. La cadena de marcas dura {pe.mark_span_hours.iloc[0]:.6f} horas: puede superar 72 horas porque esta ventana limita la separación **entre marcas consecutivas**, no la duración máxima del episodio. Las 15 marcas coinciden entre métodos; las políticas unión, consenso e híbrida seleccionan 15 filas y persistencia selecciona 14. Los 20 registros no evaluables preceden al episodio y mantienen sus motivos; no cuentan como interrupciones internas de ese episodio.

{md_table(pe.drop(columns=['episode_explanation','review_status']))}

## Comparación descriptiva con entrenamiento

{md_table(tables['prism_30_1994_training_comparison.csv'])}

Los componentes de la regla se calculan con referencias y pesos ya congelados. El componente predominante, sumado sobre marcas del episodio, es `{pe.predominant_baseline_component.iloc[0]}`. Las mayores desviaciones guardadas por registro son evidencia descriptiva; **no son una atribución causal del Isolation Forest**. Las columnas de componentes permiten comprobar exactamente el score de la regla con los valores originales de Fase 4.

## Evidencia completa por observación

Los identificadores enlazan con los originales. Vacíos numéricos y marcas desconocidas se muestran como “—”; no se convierten en cero ni en ausencia de marca.

{prism_table}

## Revisión pendiente

Este prisma no puede considerarse evidencia de falla. Puede representar un comportamiento particular del prisma, una diferencia de escala, un problema de datos o una condición que requiere revisión del especialista. Deben verificarse referencia, integridad de mediciones, ubicación, mantenimiento e historia local. No se elimina ni se utiliza para ajustar parámetros. Su episodio está **censurado al final de las observaciones del propio prisma**; ausencia posterior de mediciones no implica finalización física ni estabilidad.

> {DISCLAIMER}
"""
    policy_report=f"""# Comparación de políticas — marcas estadísticas experimentales

Todas las políticas requieren una marca actual evaluable. Unión = base OR IF; consenso = base AND IF en la misma fila; persistencia = marca actual AND al menos 2 marcas de unión en [t−72 h,t]; híbrida = consenso OR persistencia.

{results}

La reducción es `100 × (1 − registros candidatos / registros de unión)`; no mide desempeño geotécnico. Los denominadores son {int(union.candidate_rows)} en total, 42 en entrenamiento, 6 en validación y 88 en prueba. El promedio diario incluye todos los días del calendario de cada periodo; seis días sin evaluables no se interpretan como estabilidad. El máximo diario de la híbrida es {int(hybrid.maximum_daily_candidates)}, frente a {int(union.maximum_daily_candidates)} de unión.

Consenso reduce más filas entre las cuatro políticas principales ({consensus.row_reduction_vs_union_pct:.6f}%), pero excluye persistencia de un método. Híbrida conserva {int(hybrid.candidate_rows-consensus.candidate_rows)} filas adicionales mediante persistencia y reduce {candidate_reduction:.6f}% frente a unión. Las {len(withheld)} marcas no seleccionadas siguen disponibles en `marks_not_selected_primary.csv`.

Los episodios candidatos se cuentan por política y por periodo **cuando contienen una fila seleccionada en ese periodo**. Una misma cadena puede atravesar particiones; las cifras por periodo no son eventos de falla independientes y no deben sumarse para inferir un total de eventos. La duración y el total de marcas de cada episodio son retrospectivos completos, nunca utilizados para reescribir estados causales.

{quality_table}

Los cuatro episodios con interrupciones de calidad solo son seleccionados por unión. Híbrida no permite ocultarlos: siguen presentes en `episodes.csv` y en el listado de marcas no seleccionadas. Se requiere revisión del especialista antes de usar cualquier filtro.

> {DISCLAIMER}
"""
    sensitivity_report=f"""# Sensibilidad — ventanas y persistencia

Se cruzan 3 ventanas × 2 mínimos × 4 políticas: **24 combinaciones**, y cuatro ámbitos (total, entrenamiento, validación, prueba), produciendo 96 filas. Al cambiar la ventana cambia tanto el máximo intervalo entre marcas del episodio como la ventana inclusiva de persistencia. Los modelos, scores, q99 y la partición no cambian.

{sensitive}

{md_table(tables['episode_window_summary.csv'])}

Unión y consenso conservan respectivamente 136 y 66 filas en todas las combinaciones; el número de episodios cambia al modificar la agrupación. El mínimo de persistencia no cambia la construcción de episodios. La menor cantidad de filas en esta comparación es 53, con persistencia de 3 marcas en 24 h (reducción 61,029412%); ello no demuestra que sea la alternativa más útil para el especialista. Híbrida varía de 88 a 102 filas. La propuesta principal de 72 h y mínimo 2 está especificada antes del análisis, mantiene explicaciones simples y no se escoge buscando un evento físico. No se utiliza el contexto documental posterior para seleccionar ventanas o políticas.

Las medianas corresponden a los **episodios seleccionados** por cada política; la duración incluye observaciones sin marca dentro de la ventana, hasta el final observado. `mark_span_hours` conserva aparte el tiempo entre primera y última marca. Sin episodios seleccionados, las medianas son desconocidas, no cero.

> {DISCLAIMER}
"""
    validation_report=f"""# Validación técnica — Fase 6

**Estado: aprobada con observaciones.** El estado se refiere a las comprobaciones técnicas; la aprobación para uso geotécnico queda pendiente del especialista.

| Comprobación | Resultado |
| --- | --- |
| Suite anterior antes de cambios | 158 aprobadas, 0 fallidas, 0 omitidas |
| Suite completa | {tests['tests']} aprobadas, 0 fallidas, 0 omitidas |
| Pruebas nuevas | {tests['tests']-158} aprobadas |
| Archivos previos intactos | {proof['protected_files_intact']} |
| Filas conservadas | 7.178, 49 prismas |
| No evaluables conservados con motivo | 1.280 |
| CSV reproducidos byte a byte | {proof['reproduced_csv_byte_identical']} |
| Recarga de todas las columnas y tipos | Exactamente iguales |
| Modelos y scores anteriores | Hashes y predicciones idénticos |
| Entrenamiento de producción | No ejecutado; métodos fit bloqueados durante verificación |
| Ventanas y separación por prisma | Límites inclusivos, más de la ventana y conteos independientes comprobados |
| Plantilla del especialista | Todos sus campos de decisión vacíos |
| Gráficos verificados | {proof['validated_png_html_pairs']} pares PNG/HTML offline |

{md_table(pd.DataFrame(proof['causal_prefix_checks']))}

La prueba de prefijos compara **todas las columnas causales**, incluidos IDs, scores, marcas, conteos, estados y explicaciones, con cuatro cortes por timestamp. Resúmenes finales y cierre permanecen solo en la tabla retrospectiva. Las pruebas artificiales separadas añaden futuro y verifican límites de 24, 48 y 72 horas.

**Alcance de causalidad:** invariancia de la agrupación condicionada a marcas congeladas de Fase 5. Las puntuaciones de entrenamiento se obtuvieron con un modelo ajustado al cierre de ese periodo y son retrospectivas; no estaban disponibles en cada fecha histórica de entrenamiento. `model_available_at_observation` es falso en esas filas y verdadero desde la frontera de validación; no reemplaza la elegibilidad de datos. Validación y prueba utilizan un modelo ya aprendido con información anterior. No se afirma una simulación operativa en línea del periodo de entrenamiento.

Los 158 tests anteriores incluyen ajustes de modelos aislados dentro de sus pruebas de regresión; esto no constituye reentrenamiento de producción ni modificación de artefactos. La lógica de Fase 6 y su verificador bloquean `fit` de bosque, imputador, escalador y regla.

Durante desarrollo se corrigió la diferencia de índices de las tablas auxiliares al recargarlas; IDs y valores ya coincidían. Se normalizan índices auxiliares, no las fechas ni los datos originales. Evidencia anterior conservada en `verification-development.txt`. La verificación final pasa sin errores pendientes de ejecución.

También se fijó a `datetime64[ns]` el tipo de la fecha de disponibilidad del modelo, para que recargue con el mismo tipo que en memoria; la fecha no cambió. Evidencia en `verification-date-development.txt`. El informe exige que la prueba de reproducción esté vinculada por hash a los metadatos actuales para impedir reutilizar una prueba obsoleta.

Referencias: `pytest-before.txt/.xml`, `pytest-results.xml`, `pytest-output.txt`, `verification-log.txt`, `reproducibility.json`, `protected_before_phase6.json` y `phase6_metadata.json`. Checkpoint inicial `{first['checkpoint_initial']}`; el checkpoint final se registra después del commit en `git_checkpoint.txt` para evitar autorreferencia.

> {DISCLAIMER}
"""
    text=f"""# Fase 6 — Episodios temporales y candidatos para revisión

## 1. Resumen ejecutivo

**Estado técnico: aprobada con observaciones; validación geotécnica pendiente.** Se procesan las **7.178 filas de 49 prismas**, manteniendo **5.898 evaluables y 1.280 no evaluables**. Se conservan modelos, 17 características, scores, umbrales y particiones anteriores.

La ventana provisional de 72 h genera **{len(episodes)} episodios en {episodes.prism_id.nunique()} prismas** a partir de 136 marcas de unión, con 66 coincidencias. La híbrida selecciona **{int(hybrid.candidate_rows)} registros, {int(hybrid.candidate_episodes)} episodios y {int(hybrid.candidate_prisms)} prismas**, una reducción de **{candidate_reduction:.6f}% de filas** frente a unión. Hay cuatro episodios con una interrupción de calidad cada uno; ninguno es seleccionado por híbrida, por lo que siguen disponibles para revisión separada. La suite actual pasa **{tests['tests']} pruebas: 158 anteriores y {tests['tests']-158} nuevas**. La causalidad de la agrupación está condicionada a los scores congelados; los estados de entrenamiento son retrospectivos, no una simulación operativa en su fecha original.

> {DISCLAIMER}

## 2. Objetivo

Organizar marcas estadísticas individuales en cadenas temporales por prisma y candidatos interpretables para revisión humana. No se estima un evento físico ni se habilitan decisiones operativas. Hechos observados, decisiones técnicas y supuestos se distinguen en las secciones siguientes.

## 3. Entradas utilizadas

- `data/processed/phase5/anomaly_scores.csv`: 7.178 filas y sus 30 columnas originales; SHA-256 `{meta['source_sha256']}`.
- `data/processed/phase4/west_wall_features.csv`: evidencia existente enlazada uno a uno mediante `source_record_id`, con comprobación de prisma y timestamp. Se leen solo los campos necesarios para explicaciones y gráficos durante la construcción; no se recalculan características.
- Joblib de scoring, bosque y preprocesamiento, JSON de modelos, regla, configuración y metadatos de Fase 5 para comprobar congelación.
- `config/phase6.json`: decisiones técnicas explícitas; no contiene una fecha de falla ni un parámetro ajustado con ese evento.

Entrenamiento hasta el 14-ene-2014; validación 15-ene a 1-feb; prueba 2-feb a 20-feb. La fuente termina {rows.timestamp.max()}. Se conserva el timestamp reportado, sin atribuirle una zona horaria no documentada. Las fuentes meteorológicas, sísmicas y South West no se incorporan a este análisis.

## 4. Confirmación de modelos congelados

{md_table(model_display)}

{frozen_table}

Se utilizan los valores exactos de JSON; **4,4398 y 0,5873 son representaciones redondeadas**, no nuevos umbrales. Marcas = score estrictamente mayor que q99. Los tres Joblib se mantienen por hash y la recarga del bundle reproduce todas las predicciones de Fase 5. Estado aprendido SHA-256 `{meta['frozen_models']['model_state_sha256']}`. Ningún modelo se ajusta en esta fase.

## 5. Definición de marca, episodio y candidato

**Marca:** observación evaluable que supera q99 en al menos un método. **Episodio:** cadena de marcas del mismo prisma con separación consecutiva ≤ ventana; admite registros intermedios sin marca y no evaluables. **Candidato:** fila con marca actual seleccionada por una política explícita.

La primera marca crea un ID derivado de versión, prisma, `source_record_id` inicial y ventana, sin número de fila ni información futura. El ID permanece estable al añadir futuro. El máximo intervalo entre marcas no es la duración máxima de una cadena. Los últimos episodios se consideran censurados al finalizar las observaciones del propio prisma, evitando inferir cierre por falta de información de ese prisma.

## 6. Lógica causal

Orden estable por prisma, timestamp e identificador; timestamps duplicados dentro del prisma se rechazan. Ventanas **[t−h,t] inclusivas** con h=24/48/72; incluyen únicamente marcas conocidas hasta t, incluida la actual. `hours_since_previous_mark` mide desde la marca estrictamente anterior, y es desconocido si no hay marca anterior.

Jerarquía: no evaluable → sin marca → candidato según política principal → episodio en observación cuando hay al menos dos marcas recientes → marca aislada. Para la híbrida con mínimo 2, todas las marcas persistentes son candidatas; por ello el estado principal `episodio_en_observacion` tiene cero filas. Sigue siendo un estado implementado y comprobado con mínimo 3. Los registros sin marca pueden pertenecer a un episodio, pero conservan el estado `sin_marca`.

{state}

**Separación explícita:** `review_candidates.csv` contiene estados y conteos agregados a partir de registros con fecha ≤ la fila actual, condicionados a las marcas ya guardadas, junto con los scores congelados y su ámbito de disponibilidad; `episodes.csv` contiene máximos, duración final y cierre retrospectivos. Estos últimos no vuelven a modificar estados anteriores. Se permite continuidad entre particiones: {cross_period} episodio atraviesa una frontera, utilizando exclusivamente historia anterior al agregar cada registro.

**Alcance y observación importante:** la agrupación es causal **condicionada a las marcas congeladas**. El modelo de Fase 5 se ajustó con todo entrenamiento; sus scores en ese mismo periodo son retrospectivos y no estaban disponibles en la fecha original de cada medición. `model_available_from_timestamp` conserva la frontera 15-ene-2014 y `model_available_at_observation=False` en entrenamiento; validación/prueba tienen ese indicador verdadero. Se conserva la elegibilidad original, independiente de disponibilidad del modelo. Los estados de entrenamiento describen una organización histórica, no un seguimiento operativo en esas fechas. Las pruebas de prefijos comprueban la agregación, sin afirmar que el ajuste previo ocurrió antes de todas las mediciones históricas.

Este indicador representa disponibilidad conforme al protocolo de evaluación temporal, no una fecha real de instalación del modelo en una mina.

## 7. Tratamiento de registros no evaluables

Las 1.280 filas conservan el motivo exacto, scores y marcas desconocidos. No se rellenan con cero ni False. Los conteos temporales cuentan solo marcas conocidas; un conteo de cero no convierte el estado actual desconocido en ausencia comprobada de marca.

`quality_interruption_flag` se activa en la fila no evaluable y permanece activado en las filas posteriores del mismo episodio una vez observada una interrupción. Hay **{meta['rows_with_quality_flag']} filas con ese indicador**; no deben confundirse con 1.280 filas no evaluables. Solo **4** registros no evaluables caen dentro de episodios activos; los restantes no se asignan retrospectivamente a un episodio futuro.

{quality_table}

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

{results}

Entre las cuatro políticas principales, consenso reduce más filas: {consensus.row_reduction_vs_union_pct:.6f}%. La híbrida conserva {int(hybrid.candidate_rows-consensus.candidate_rows)} filas adicionales seleccionadas por persistencia sin coincidencia actual. El detalle y los efectos sobre calidad están en [policy_comparison.md](policy_comparison.md).

## 10. Análisis de sensibilidad

{sensitive}

La sensibilidad mantiene scores y umbrales, cruza 24 combinaciones y conserva detalles por las tres particiones, además del total: 96 filas. Unión conserva 136 y consenso 66 registros en todas las combinaciones; el agrupamiento de episodios sí cambia. Persistencia de 3 marcas/24 h selecciona 53 filas, la menor carga registrada (61,029412% de reducción), pero no se declara la mejor alternativa geotécnica. Véase [sensitivity_analysis.md](sensitivity_analysis.md).

**Decisión técnica inicial:** 72 h y mínimo 2 se fijaron por el alcance solicitado antes de los resultados; proporcionan una regla simple para revisión de mediciones irregulares. **Supuesto pendiente:** el especialista debe decidir si esa separación temporal representa continuidad útil en su contexto. No se calibra con un evento físico.

## 11. Carga estimada de revisión

Total: híbrida pasa de 136 marcas a 102 filas candidatas, reducción del 25%; selecciona 20 de 48 episodios, reducción del 58,333333% de episodios. Se entrega una plantilla con una fila por esos 20 episodios; cada episodio conserva sus marcas y registros asociados, sin deduplicarlos físicamente ni omitir señales de calidad.

Promedio híbrido **{hybrid.mean_candidates_per_day:.6f} filas/día**, máximo **{int(hybrid.maximum_daily_candidates)}**, con **{int(hybrid.days_with_candidates)} días con candidatos** sobre 93 días de calendario. En prueba: 70 candidatos frente a 88 de unión (20,454545% de reducción), en 13 episodios y 13 prismas. No se estima tiempo humano por fila ni se inventa productividad.

Los 48 episodios incluyen {membership} registros: {int(episodes.eligible_record_count.sum())} evaluables y 4 no evaluables. Los restantes registros siguen íntegros en la tabla por fila. Hay {singleton_count} episodios de una sola marca y {persistent_count} con al menos dos marcas en su cadena; esto es un recuento retrospectivo y no reetiqueta la primera marca como persistente.

## 12. Casos destacados y visualizaciones

Ejemplos seleccionados por orden cronológico, sin escogerlos por cercanía a un evento:

{md_table(examples[['episode_id','prism_id','start_timestamp','last_observed_timestamp','union_mark_count','agreement_count','candidate_policies']])}

{md_table(figures)}

Los 10 pares PNG/HTML son descriptivos, usan paleta neutral y JavaScript local. Los gráficos conectan observaciones; no se imputan ni crean mediciones entre ellas. Los scores del prisma particular se presentan en paneles con escalas propias. La duración observada incluye registros intermedios sin marca; `mark_span_hours` se conserva por separado. Ceros diarios significan “sin candidatos observados”, no una conclusión profesional.

## 13. Análisis del prisma 30-1994

**Hecho observado:** 35 registros, 15 evaluables, 20 no evaluables; únicamente entrenamiento. Cada método marca las 15 filas evaluables. Se genera un episodio y la híbrida selecciona las 15; persistencia selecciona 14 porque la primera marca todavía no tiene historia marcada reciente. El componente de regla predominante es `{pe.predominant_baseline_component.iloc[0]}`. Score IF máximo {p.isolation_forest_score.max():.6f}; base máximo {p.baseline_score.max():.6f}.

{md_table(tables['prism_30_1994_training_comparison.csv'])}

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

{tests['tests']} pruebas pasan, se conservan {meta['protected_files_intact']} archivos anteriores y se reproducen 12 CSV byte a byte. Los hashes y predicciones de modelos son idénticos. Los prefijos temporales conservan todas las columnas causales; la verificación bloquea entrenamiento. [validation_report.md](validation_report.md) detalla pruebas y corrección durante desarrollo.

Antes de la siguiente fase se necesita aprobación explícita del alcance por la usuaria y revisión de las observaciones de política/calidad. La validación profesional y la recolección de etiquetas humanas siguen pendientes. **No se construye interfaz ni se avanza a Fase 7 en esta entrega.**

## 18. Conclusión

La Fase 6 organiza marcas existentes en episodios y una propuesta reproducible de revisión. Conserva estados desconocidos, motivos y trazabilidad, separando evidencia disponible en cada instante de los resúmenes finales. La aceptación técnica no constituye aprobación para uso en seguridad.

**Los candidatos no son predicciones de falla, no representan niveles de riesgo, requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para decisiones operativas o de seguridad.**

> {DISCLAIMER}
"""
    reports={'phase6_findings.md':text,'policy_comparison.md':policy_report,
             'sensitivity_analysis.md':sensitivity_report,'prism_30_1994_review.md':prism_description,
             'validation_report.md':validation_report}
    for name,content in reports.items():(OUT/name).write_text(content,encoding='utf-8')
    hashes={str((OUT/name).relative_to(ROOT)):sha256(OUT/name) for name in reports}
    (OUT/'report_metadata.json').write_text(json.dumps({'files_sha256':hashes,'test_totals':tests,
        'previous_test_totals':previous,'source_metadata_sha256':sha256(OUT/'phase6_metadata.json'),
        'reproducibility_sha256':sha256(OUT/'reproducibility.json')},ensure_ascii=False,indent=2)+'\n')
    print(f'Cinco informes reconstruidos: {tests["tests"]} pruebas; {len(episodes)} episodios; {int(hybrid.candidate_rows)} candidatos híbridos.')


if __name__=='__main__':main()
