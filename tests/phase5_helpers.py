"""Casos artificiales de prueba; nunca se incorporan a los datos reales."""
from functools import lru_cache
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from src.phase5_config import load_model_config
from src.feature_engineering import engineer_features
from src.anomaly_models import train_models
from tests.test_feature_engineering import synthetic

@lru_cache(maxsize=1)
def _case():
    rng=np.random.default_rng(123)
    n=260; t=np.arange(n)
    raw=pd.concat([synthetic(2+.01*t+.2*np.sin(t/3)+rng.normal(0,.04,n),t*6,prism='A'),
                   synthetic(4+.005*t+.15*np.sin(t/4)+rng.normal(0,.03,n),t*6+2,prism='B')],ignore_index=True)
    result=engineer_features(raw)
    cfg=load_model_config(Path(__file__).resolve().parents[1]/'config/phase5.json')
    cfg['primary_model']['n_estimators']=32;cfg['primary_model']['max_samples']=64
    cfg['minimum_training_rows']=20
    return result.data,result.dictionary,raw,cfg

def model_case():return deepcopy(_case())

@lru_cache(maxsize=1)
def _trained():
    data,dictionary,_,cfg=model_case()
    return train_models(data,dictionary,cfg)

def trained_case():return deepcopy(_trained())
