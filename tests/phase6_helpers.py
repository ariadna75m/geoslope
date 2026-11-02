"""Explicitly artificial test rows; never appended to project datasets."""
from functools import lru_cache
from pathlib import Path
import json
import pandas as pd
from src.episode_detection import detect_episodes, summarize_episodes
from src.candidate_policies import apply_policies

ROOT=Path(__file__).resolve().parents[1]


def sample(hours=(0,6,12), baseline=(True,False,True), forest=(False,False,True),
           eligible=None, prisms=None):
    n=len(hours);eligible=[True]*n if eligible is None else eligible
    records=[]
    for i,h in enumerate(hours):
        records.append(dict(source_record_id=f'test-{i}',prism_id='A' if prisms is None else prisms[i],
            timestamp=pd.Timestamp('2020-01-01')+pd.Timedelta(hours=h),period='entrenamiento',
            model_eligible=eligible[i],model_ineligibility_reason='' if eligible[i] else 'motivo original de calidad',
            baseline_score=5. if eligible[i] and baseline[i] else (1. if eligible[i] else float('nan')),
            isolation_forest_score=.8 if eligible[i] and forest[i] else (.4 if eligible[i] else float('nan')),
            baseline_marked_q99=baseline[i] if eligible[i] else pd.NA,
            isolation_forest_marked_q99=forest[i] if eligible[i] else pd.NA,
            feature_quality_status='disponible' if eligible[i] else 'desconocido',
            descriptive_explanation='Evidencia artificial de prueba.',feature_deviation_details='[]'))
    data=pd.DataFrame(records)
    for c in ('baseline_marked_q99','isolation_forest_marked_q99'):data[c]=data[c].astype('boolean')
    data['model_eligible']=data.model_eligible.astype(bool)
    return data


def evaluate(data, window=72, minimum=2, policy='hybrid'):
    temporal,closures=detect_episodes(data,window)
    rows=apply_policies(temporal,window,minimum,policy)
    return rows,summarize_episodes(rows,closures,window)


@lru_cache(maxsize=1)
def real_case():
    from scripts.run_phase6 import load_inputs, build_artifacts
    inputs,config=load_inputs()
    return inputs,config,build_artifacts(inputs,config)
