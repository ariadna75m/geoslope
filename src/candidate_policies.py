"""Explicit candidate rules and descriptive workload, without real labels."""
import numpy as np
import pandas as pd

POLICIES = ('union', 'consensus', 'persistence', 'hybrid')


def apply_policies(rows, window_hours=72, min_marks=2, primary_policy='hybrid'):
    if window_hours not in (24,48,72) or min_marks not in (2,3) or primary_policy not in POLICIES:
        raise ValueError('Configuración temporal o política inválida.')
    data = rows.copy(deep=True)
    union = data.union_mark.fillna(False)
    agree = data.agreement_same_row.fillna(False)
    persistent = union & data[f'union_marks_last_{window_hours}h'].ge(min_marks)
    selections = dict(union=union, consensus=agree, persistence=persistent, hybrid=agree | persistent)
    for name, selection in selections.items():
        data['candidate_'+name] = selection.astype('boolean').mask(~data.model_eligible)
    selected = selections[primary_policy]
    observing = union & data[f'union_marks_last_{window_hours}h'].ge(2)
    data['causal_state'] = np.select([~data.model_eligible, ~union, selected, observing],
                                    ['no_evaluable','sin_marca','candidato_revision','episodio_en_observacion'],
                                    default='marca_aislada')
    data['candidate_policy'] = np.where(selected, primary_policy, '')
    data['review_pending'] = selected
    return data


def daily_workload(rows):
    if rows.empty:
        return pd.DataFrame(columns=['date','policy','candidate_rows','eligible_rows','ineligible_rows','observed_rows'])
    days = pd.date_range(rows.timestamp.min().normalize(), rows.timestamp.max().normalize(), freq='D')
    observed = rows.timestamp.dt.normalize()
    output = []
    for policy in POLICIES:
        for day in days:
            group = rows.loc[observed.eq(day)]
            output.append({'date': day, 'policy': policy, 'candidate_rows': int(group['candidate_'+policy].sum()),
                           'eligible_rows': int(group.model_eligible.sum()),
                           'ineligible_rows': int((~group.model_eligible).sum()), 'observed_rows': len(group)})
    return pd.DataFrame(output)


def compare_policies(rows, episodes, window_hours, min_marks, include_periods=True):
    scopes = [('total', rows)]
    if include_periods:
        scopes.extend((p, rows.loc[rows.period.eq(p)]) for p in ('entrenamiento','validación','prueba'))
    output = []
    for period, group in scopes:
        union_count = int(group.union_mark.sum())
        union_episodes = group.loc[group.union_mark.fillna(False), 'episode_id'].nunique()
        days = daily_workload(group)
        for policy in POLICIES:
            candidates = group.loc[group['candidate_'+policy].fillna(False)]
            selected_ids = candidates.episode_id.unique()
            summaries = episodes.loc[episodes.episode_id.isin(selected_ids)]
            counts = days.loc[days.policy.eq(policy), 'candidate_rows']
            output.append({
                'period': period, 'policy': policy, 'window_hours': window_hours, 'min_marks': min_marks,
                'candidate_rows': len(candidates), 'candidate_episodes': len(summaries),
                'candidate_prisms': candidates.prism_id.nunique(), 'calendar_days': len(counts),
                'mean_candidates_per_day': counts.mean() if len(counts) else 0.,
                'maximum_daily_candidates': int(counts.max()) if len(counts) else 0,
                'days_with_candidates': int(counts.gt(0).sum()),
                'days_without_evaluable_records': int(days.loc[days.policy.eq(policy), 'eligible_rows'].eq(0).sum()),
                'union_reference_rows': union_count,
                'row_reduction_vs_union_pct': 100*(1-len(candidates)/union_count) if union_count else np.nan,
                'episode_reduction_vs_union_pct': 100*(1-len(summaries)/union_episodes) if union_episodes else np.nan,
                'median_episode_duration_hours': summaries.duration_hours.median(),
                'median_marks_per_episode': summaries.union_mark_count.median(),
                'episodes_with_agreement': int(summaries.agreement_count.gt(0).sum()),
                'episodes_with_quality_interruption': int(summaries.quality_interruption_flag.sum()),
                'ineligible_records_in_selected_episodes': int(summaries.ineligible_record_count.sum()),
            })
    return pd.DataFrame(output)
