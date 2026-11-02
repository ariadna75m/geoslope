"""Entrenamiento temporal, scores y artefactos experimentales de Fase 5."""
from dataclasses import dataclass
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from copy import deepcopy
from .phase5_config import validate_model_config
from .temporal_split import temporal_split, PERIODS, split_summary
from .feature_selection import eligibility, select_features
from .model_preprocessing import make_preprocessor, preprocessing_metadata
from .anomaly_baseline import StatisticalBaseline


def train_percentile(reference, values):
    reference = np.sort(np.asarray(reference, dtype=float))
    if not len(reference) or not np.isfinite(reference).all(): raise ValueError("Referencia de percentil inválida.")
    values = np.asarray(values, dtype=float)
    result = 100*np.searchsorted(reference, values, side="right")/len(reference)
    result[~np.isfinite(values)] = np.nan
    return result


def fit_isolation(training, features, parameters, robust=True):
    preprocess = make_preprocessor(features, robust)
    model = IsolationForest(**parameters, n_jobs=1)
    pipeline = Pipeline([*preprocess.steps, ("model", model)])
    pipeline.fit(training)
    return pipeline


def fit_with_frozen_preprocessing(training, fitted_pipeline, parameters):
    """Comparación controlada: conserva mediana/escala aprendidas, ajusta solo el bosque."""
    preprocess = deepcopy(fitted_pipeline[:-1])
    matrix = preprocess.transform(training)
    model = IsolationForest(**parameters, n_jobs=1).fit(matrix)
    return Pipeline([*preprocess.steps, ("model", model)])


def tree_feature_metadata(pipeline):
    forest = pipeline.named_steps["model"]
    names = list(pipeline.named_steps["select"].columns)
    counts = [len(indices) for indices in forest.estimators_features_]
    return {"configured_max_features": forest.max_features,
            "configured_max_features_type": type(forest.max_features).__name__,
            "selected_feature_count": len(names), "selected_feature_names": names,
            "model_input_feature_count": int(forest.n_features_in_),
            "effective_available_features_per_tree": sorted(set(counts)),
            "tree_count": len(counts),
            "trees_with_all_selected_features": sum(set(indices) == set(range(len(names))) for indices in forest.estimators_features_),
            "scope": "available to each tree; not a claim that every split uses all features"}


@dataclass
class ModelBundle:
    selected_features: list
    pipeline: Pipeline
    baseline: StatisticalBaseline
    config: dict
    thresholds: dict
    training_score_references: dict
    version: str
    training_signature: str

    def score_new(self, data):
        eligible, reasons = eligibility(data, self.selected_features, self.config)
        if eligible.any():
            transformed = self.pipeline[:-1].transform(data.loc[eligible])
            bad = ~np.isfinite(transformed).all(axis=1)
            if bad.any():
                indices = data.loc[eligible].index[bad]
                eligible.loc[indices] = False
                reasons.loc[indices] = "transformación no disponible"
        output = data[["source_record_id", "prism_id", "timestamp", "feature_quality_status"]].copy()
        output["model_eligible"], output["model_ineligibility_reason"] = eligible, reasons
        absent = data[self.selected_features].isna()
        output["imputed_feature_count"] = absent.sum(axis=1).where(eligible, 0)
        output["imputed_feature_names"] = [";".join(absent.columns[row.to_numpy()]) if valid else "" for (_, row), valid in zip(absent.iterrows(), eligible)]
        for name in ("is_prolonged_gap", "has_sufficient_history", "has_sufficient_72h_history", "has_sufficient_7d_history"):
            output[name] = data[name]
        for model in ("baseline", "isolation_forest"):
            output[model+"_score"] = np.nan
        if eligible.any():
            g = data.loc[eligible]
            output.loc[eligible, "baseline_score"] = self.baseline.score(g)
            output.loc[eligible, "isolation_forest_score"] = -self.pipeline.score_samples(g)
        for model in ("baseline", "isolation_forest"):
            score = output[model+"_score"]
            if not np.isfinite(score.loc[eligible]).all(): raise ValueError("Score no finito; revisar entrada o referencias.")
            output[model+"_training_percentile"] = train_percentile(self.training_score_references[model], score)
            for label, threshold in self.thresholds[model].items():
                marked = pd.Series(pd.NA, index=data.index, dtype="boolean")
                marked.loc[eligible] = score.loc[eligible].gt(threshold)
                output[model+"_marked_"+label] = marked
        reference = pd.Series(pd.NA, index=data.index, dtype="boolean")
        reference.loc[eligible] = data.loc[eligible, "historical_robust_z_score"].abs().ge(self.config["robust_z_reference"])
        output["baseline_robust_z_reference_marked"] = reference
        output["model_version"] = self.version
        output["model_config_reference"] = "config/phase5.json"
        output["model_config_sha256"] = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()
        return output


@dataclass
class TrainingResult:
    bundle: ModelBundle
    scores: pd.DataFrame
    selection: object
    periods: pd.Series
    cutoffs: dict
    split_table: pd.DataFrame
    training: pd.DataFrame
    preprocessing: dict


def train_models(data, dictionary, config):
    validate_model_config(config)
    if data.empty or not data.source_record_id.is_unique or data.duplicated(["prism_id", "timestamp"]).any():
        raise ValueError("La fuente necesita registros únicos y fechas válidas.")
    periods, cutoffs = temporal_split(data, config)
    initial_eligible, _ = eligibility(data, [], config)
    selection_input = data.loc[periods.eq(PERIODS[0]) & initial_eligible].sort_values(["timestamp", "prism_id", "source_record_id"])
    selection = select_features(selection_input, dictionary, config)
    eligible, _ = eligibility(data, selection.selected, config)
    training = data.loc[periods.eq(PERIODS[0]) & eligible].sort_values(["timestamp", "prism_id", "source_record_id"])
    if len(training) < config["minimum_training_rows"]: raise ValueError("Filas elegibles insuficientes para entrenamiento.")
    pipeline = fit_isolation(training, selection.selected, config["primary_model"])
    baseline = StatisticalBaseline.fit(training, config)
    references = {"baseline": baseline.score(training), "isolation_forest": -pipeline.score_samples(training)}
    thresholds = {model: {f"q{round(q*100)}": float(np.quantile(score, q)) for q in config["threshold_quantiles"]}
                  for model, score in references.items()}
    thresholds["isolation_forest"]["internal"] = -float(pipeline.named_steps["model"].offset_)
    digest = hashlib.sha256(pd.util.hash_pandas_object(training[selection.selected], index=False).values.tobytes()
                            + "|".join(training.source_record_id).encode()).hexdigest()
    version = "phase5-v1-" + digest[:12]
    bundle = ModelBundle(selection.selected, pipeline, baseline, config, thresholds, references, version, digest)
    scores = bundle.score_new(data)
    scores.insert(3, "period", periods)
    return TrainingResult(bundle, scores, selection, periods, cutoffs,
                          split_summary(data, periods, eligible), training, preprocessing_metadata(pipeline[:-1]))
