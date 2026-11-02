"""Per-prism chronological state; summaries are explicitly retrospective."""
from collections import deque
import hashlib
import json
import numpy as np
import pandas as pd
from src.phase6_validation import validate_scores

EPISODE_COLUMNS = ['episode_id', 'prism_id', 'start_timestamp', 'last_observed_timestamp',
                   'last_mark_timestamp', 'duration_hours', 'mark_span_hours', 'closure_status',
                   'closure_observed_at', 'expiry_timestamp', 'record_count', 'eligible_record_count',
                   'ineligible_record_count', 'baseline_mark_count', 'iforest_mark_count',
                   'union_mark_count', 'agreement_count', 'maximum_baseline_score',
                   'maximum_iforest_score', 'periods_observed', 'candidate_policies',
                   'quality_interruption_flag', 'predominant_baseline_component',
                   'episode_explanation', 'review_status']


def episode_identifier(prism, first_id, window_hours):
    payload = json.dumps(['phase6-v1', str(prism), str(first_id), int(window_hours)], separators=(',', ':'))
    return 'ep_' + hashlib.sha256(payload.encode()).hexdigest()[:24]


def detect_episodes(scores, window_hours=72):
    if window_hours not in (24, 48, 72):
        raise ValueError('Ventana debe ser 24, 48 o 72 horas.')
    data = validate_scores(scores)
    data['baseline_mark_q99'] = data.baseline_marked_q99.astype('boolean')
    data['iforest_mark_q99'] = data.isolation_forest_marked_q99.astype('boolean')
    data['union_mark'] = data.baseline_mark_q99 | data.iforest_mark_q99
    data['agreement_same_row'] = data.baseline_mark_q99 & data.iforest_mark_q99
    outputs, closures = {}, {}
    width = pd.Timedelta(hours=window_hours)
    for prism, group in data.groupby('prism_id', sort=False):
        histories = {key: deque() for key in ('baseline', 'iforest', 'union', 'eligible', 'ineligible')}
        previous_observation = previous_mark = None
        active_id = None
        episode_start = None
        episode_marks = episode_quality = 0
        for index, row in group.iterrows():
            now = row.timestamp
            eligible = bool(row.model_eligible)
            b = eligible and bool(row.baseline_mark_q99)
            f = eligible and bool(row.iforest_mark_q99)
            marked = b or f
            before_mark_hours = np.nan if previous_mark is None else (now-previous_mark).total_seconds()/3600
            if active_id is not None and now-previous_mark > width:
                closures[active_id] = ('cerrado_por_ventana', now)
                active_id = None
                episode_start = None
                episode_marks = episode_quality = 0
            if marked:
                if active_id is None:
                    active_id = episode_identifier(prism, row.source_record_id, window_hours)
                    episode_start = now
                    episode_marks = episode_quality = 0
                previous_mark = now
                episode_marks += 1
            if active_id is not None and not eligible:
                episode_quality += 1
            for key, yes in [('baseline', b), ('iforest', f), ('union', marked), ('eligible', eligible), ('ineligible', not eligible)]:
                if yes:
                    histories[key].append(now)
                while histories[key] and histories[key][0] < now-pd.Timedelta(hours=72):
                    histories[key].popleft()
            values = {}
            for label in ('baseline', 'iforest', 'union'):
                for hours in (24, 48, 72):
                    values[f'{label}_marks_last_{hours}h'] = sum(t >= now-pd.Timedelta(hours=hours) for t in histories[label])
            values.update(
                hours_since_previous_observation=np.nan if previous_observation is None else (now-previous_observation).total_seconds()/3600,
                hours_since_previous_mark=before_mark_hours,
                eligible_observations_last_72h=len(histories['eligible']),
                ineligible_observations_last_72h=len(histories['ineligible']),
                quality_interruption_flag=not eligible or episode_quality > 0,
                episode_id=active_id or '', episode_start_timestamp=episode_start or pd.NaT,
                episode_union_marks_to_date=episode_marks if active_id else 0,
                episode_ineligible_records_to_date=episode_quality if active_id else 0,
                episode_status=('sin_episodio' if active_id is None else ('marca_aislada' if episode_marks == 1 else 'episodio_en_observacion')),
            )
            outputs[index] = values
            previous_observation = now
        if active_id is not None:
            closures[active_id] = ('censurado_fin_del_prisma', pd.NaT)
    extras = pd.DataFrame.from_dict(outputs, orient='index')
    if data.empty:
        numeric = [f'{label}_marks_last_{hours}h' for label in ('baseline', 'iforest', 'union') for hours in (24,48,72)]
        numeric += ['hours_since_previous_observation','hours_since_previous_mark','eligible_observations_last_72h','ineligible_observations_last_72h','episode_union_marks_to_date','episode_ineligible_records_to_date']
        for name in numeric:
            extras[name] = pd.Series(dtype=float)
        for name in ('episode_id','episode_status'):
            extras[name] = pd.Series(dtype=str)
        extras['episode_start_timestamp'] = pd.Series(dtype='datetime64[ns]')
        extras['quality_interruption_flag'] = pd.Series(dtype=bool)
    return pd.concat([data, extras], axis=1), closures


def summarize_episodes(rows, closures, window_hours):
    summaries = []
    for episode_id, group in rows.loc[rows.episode_id.ne('')].groupby('episode_id', sort=False):
        first = group.iloc[0]
        marked = group.union_mark.fillna(False)
        last_mark = group.loc[marked, 'timestamp'].max()
        status, closed_at = closures[episode_id]
        policies = [p for p in ('union','consensus','persistence','hybrid') if group['candidate_'+p].fillna(False).any()]
        component_names = [c for c in group if c.startswith('baseline_component_')]
        predominant = group.loc[marked, component_names].sum().idxmax().replace('baseline_component_', '') if component_names and group.loc[marked, component_names].notna().any().any() else 'desconocido'
        summaries.append({
            'episode_id': episode_id, 'prism_id': first.prism_id, 'start_timestamp': first.timestamp,
            'last_observed_timestamp': group.timestamp.max(), 'last_mark_timestamp': last_mark,
            'duration_hours': (group.timestamp.max()-first.timestamp).total_seconds()/3600,
            'mark_span_hours': (last_mark-first.timestamp).total_seconds()/3600,
            'closure_status': status, 'closure_observed_at': closed_at,
            'expiry_timestamp': last_mark+pd.Timedelta(hours=window_hours),
            'record_count': len(group), 'eligible_record_count': int(group.model_eligible.sum()),
            'ineligible_record_count': int((~group.model_eligible).sum()),
            'baseline_mark_count': int(group.baseline_mark_q99.sum()),
            'iforest_mark_count': int(group.iforest_mark_q99.sum()),
            'union_mark_count': int(group.union_mark.sum()), 'agreement_count': int(group.agreement_same_row.sum()),
            'maximum_baseline_score': group.baseline_score.max(), 'maximum_iforest_score': group.isolation_forest_score.max(),
            'periods_observed': ';'.join(group.period.drop_duplicates()), 'candidate_policies': ';'.join(policies),
            'quality_interruption_flag': bool((~group.model_eligible).any()),
            'predominant_baseline_component': predominant, 'episode_explanation': '', 'review_status': '',
        })
    return pd.DataFrame(summaries, columns=EPISODE_COLUMNS)
