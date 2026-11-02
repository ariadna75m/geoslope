"""Rule components and row-level evidence; no invented forest attribution."""
import numpy as np
import pandas as pd
from src.exploratory_analysis import DISCLAIMER

EVIDENCE_FEATURES = ['reported_3d_movement_mm','historical_robust_z_score',
                     'local_trend_72h_slope_mm_per_day','increase_streak_duration_hours']


def attach_evidence(scores, features, baseline, thresholds):
    ids = scores.source_record_id.tolist()
    if features.source_record_id.duplicated().any():
        raise ValueError('Características con identificadores duplicados.')
    source = features.set_index('source_record_id')
    if not set(ids).issubset(source.index):
        raise ValueError('Faltan características de registros de Fase 5.')
    evidence = source.loc[ids]
    if not evidence.prism_id.to_numpy().tolist() == scores.prism_id.tolist():
        raise ValueError('Prisma no coincide con el identificador de características.')
    if not np.array_equal(pd.to_datetime(evidence.timestamp).to_numpy(), scores.timestamp.to_numpy()):
        raise ValueError('Timestamp no coincide con el identificador de características.')
    data = scores.copy(deep=True)
    for feature in EVIDENCE_FEATURES:
        data[feature] = evidence[feature].to_numpy()
    data['baseline_threshold_q99'] = thresholds['baseline']
    data['iforest_threshold_q99'] = thresholds['isolation_forest']
    weights = baseline['weights']
    trend = baseline['trend_reference']
    persistence = baseline['persistence_reference']
    data['baseline_component_historical_z'] = weights['historical_z']*data.historical_robust_z_score.abs()
    data['baseline_component_trend'] = weights['trend']*((data.local_trend_72h_slope_mm_per_day-trend['center'])/trend['scale']).abs()
    data['baseline_component_persistence'] = weights['persistence']*np.log1p(((data.increase_streak_duration_hours-persistence['center'])/persistence['scale']).clip(lower=0))
    component_cols = [c for c in data if c.startswith('baseline_component_')]
    data.loc[~data.model_eligible, component_cols] = np.nan
    np.testing.assert_allclose(data.loc[data.model_eligible, component_cols].sum(axis=1),
                               data.loc[data.model_eligible, 'baseline_score'], rtol=1e-14, atol=1e-14)
    return data


def explain_rows(rows, window_hours, min_marks):
    data = rows.copy(deep=True)
    reasons = []
    for _, row in data.iterrows():
        if not row.model_eligible:
            reason = 'Registro no evaluable: ' + row.model_ineligibility_reason + '. Calidad desconocida para puntuar; no cuenta como marca ni como evidencia de estabilidad.'
        elif not bool(row.union_mark):
            reason = 'Registro evaluable sin marca q99 en ninguno de los dos métodos; no constituye una conclusión geotécnica.'
        else:
            facts = []
            if bool(row.agreement_same_row):
                facts.append('Los dos métodos marcaron este registro.')
            if bool(row.baseline_mark_q99):
                facts.append(f'El puntaje del modelo base {row.baseline_score:.6g} supera q99={row.baseline_threshold_q99:.6g}.')
            if bool(row.iforest_mark_q99):
                facts.append(f'Isolation Forest marca un comportamiento inusual respecto al entrenamiento: score={row.isolation_forest_score:.6g}, q99={row.iforest_threshold_q99:.6g}.')
            count = row[f'union_marks_last_{window_hours}h']
            facts.append(f'Se observaron {count} marcas de unión para este prisma en las últimas {window_hours} horas, incluyendo este registro; mínimo de persistencia={min_marks}.')
            facts.append(f'Inicio observado del episodio: {row.episode_start_timestamp}; evidencia hasta este instante: {row.episode_union_marks_to_date} marcas y {row.episode_ineligible_records_to_date} registros no evaluables.')
            if row.episode_ineligible_records_to_date:
                facts.append('El episodio presenta interrupción por calidad; los registros no evaluables no aportan persistencia.')
            components = [(c.replace('baseline_component_',''), row[c]) for c in data if c.startswith('baseline_component_')]
            if components:
                facts.append('Componentes calculados de la regla: ' + ', '.join(f'{n}={v:.5g}' for n,v in components) + '.')
            facts.append('Desviaciones descriptivas guardadas: ' + row.descriptive_explanation)
            facts.append('Estas desviaciones no son contribuciones causales de Isolation Forest.')
            facts.append(f'Partición: {row.period}. Revisión pendiente del especialista.' if row.review_pending else f'Partición: {row.period}. Marca en observación, no seleccionada por la política principal.')
            reason = ' '.join(facts)
        if 'model_available_at_observation' in data and not row.model_available_at_observation:
            reason += ' Estado histórico condicionado a puntuaciones retrospectivas de entrenamiento; el modelo congelado no estaba disponible en la fecha original de esta observación.'
        reasons.append(reason)
    data['candidate_reason'] = reasons
    data['professional_notice'] = DISCLAIMER
    return data


def explain_episodes(episodes):
    data = episodes.copy(deep=True)
    data['episode_explanation'] = [
        f'Resumen retrospectivo: {r.union_mark_count} marcas de unión, {r.agreement_count} coincidencias y {r.ineligible_record_count} interrupciones por calidad de registros; {r.record_count} registros observados. Componente predominante de la regla: {r.predominant_baseline_component}. Cierre: {r.closure_status}. Requiere revisión del especialista. {DISCLAIMER}'
        for r in data.itertuples()]
    return data


def specialist_template(episodes, primary_policy='hybrid'):
    selected = episodes.loc[episodes.candidate_policies.str.split(';').map(lambda x: primary_policy in x)].copy()
    result = selected[['episode_id','prism_id','start_timestamp','last_observed_timestamp']].copy()
    result['selection_reason'] = 'Política principal '+primary_policy+': '+selected.episode_explanation
    for name in ('review_status','specialist_relevant','specialist_comment','data_quality_comment',
                 'recommended_follow_up','reviewer','review_date'):
        result[name] = ''
    return result.reset_index(drop=True)
