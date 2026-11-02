"""Selección y elegibilidad independientes de los valores futuros."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .phase5_config import CANDIDATES


def eligibility(data, selected, config):
    required = ["has_sufficient_history", "has_sufficient_72h_history", "has_sufficient_7d_history",
                "is_first_observation", "is_nonpositive_interval", "is_prolonged_gap"]
    if not set(required + config["mandatory_features"] + list(selected)).issubset(data):
        raise ValueError("Faltan características o banderas necesarias para elegibilidad.")
    reasons = pd.Series("", index=data.index, dtype=object)

    def flag(mask, label):
        mask = pd.Series(mask, index=data.index).fillna(True)
        reasons.loc[mask] = reasons.loc[mask].map(lambda x: (x + "; " if x else "") + label)

    flag(data.is_first_observation, "sin historia previa")
    flag(~data.has_sufficient_history, "historia previa insuficiente")
    flag(data.is_nonpositive_interval, "intervalo inválido")
    if config["exclude_prolonged_gaps"]: flag(data.is_prolonged_gap, "hueco prolongado")
    if config["require_72h_history"]: flag(~data.has_sufficient_72h_history, "cobertura 72h insuficiente")
    if config["require_7d_history"]: flag(~data.has_sufficient_7d_history, "cobertura 7d insuficiente")
    mandatory = data[config["mandatory_features"]].apply(pd.to_numeric, errors="raise")
    flag(mandatory.isna().any(axis=1), "característica indispensable faltante")
    values = data[list(selected)].apply(pd.to_numeric, errors="raise") if selected else mandatory
    flag(np.isinf(values.to_numpy()).any(axis=1) | np.isinf(mandatory.to_numpy()).any(axis=1), "valor infinito")
    if selected:
        flag(values.isna().mean(axis=1).gt(config["max_row_missing_fraction"]), "demasiadas características faltantes")
    return reasons.eq(""), reasons


@dataclass
class SelectionResult:
    selected: list
    candidates: pd.DataFrame
    excluded: pd.DataFrame
    spearman: pd.DataFrame
    pearson: pd.DataFrame
    pairs: pd.DataFrame


def select_features(training, dictionary, config):
    priority = config["candidate_priority"]
    if not set(priority).issubset(CANDIDATES) or not set(priority).issubset(training):
        raise ValueError("Candidatos no permitidos o inexistentes.")
    if len(training) < config["minimum_training_rows"]:
        raise ValueError("Entrenamiento elegible insuficiente para seleccionar variables.")
    numeric = training[priority].apply(pd.to_numeric, errors="raise")
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError("Infinito en candidatos de entrenamiento.")
    spearman, pearson = numeric.corr(method="spearman"), numeric.corr(method="pearson")
    units = dictionary.set_index("feature_name").unit.to_dict()
    selected, records, pairs = [], [], []
    for feature in priority:
        x = numeric[feature]; missing = x.isna().mean(); variance = x.var(ddof=1)
        reason, correlated, correlation = "incluida", "", np.nan
        if x.notna().sum() == 0: reason = "completamente vacía en entrenamiento"
        elif x.dropna().nunique() <= 1: reason = "constante en entrenamiento"
        elif missing > config["max_training_missing_fraction"]: reason = "faltantes de entrenamiento exceden criterio"
        elif feature.startswith("absolute_") and feature.removeprefix("absolute_") in selected:
            correlated = feature.removeprefix("absolute_")
            correlation = spearman.loc[feature, correlated]
            reason = "transformación absoluta determinista del predictor con signo; se evita doble ponderación"
        else:
            for retained in selected:
                rho = spearman.loc[feature, retained]
                if pd.notna(rho) and abs(rho) > config["spearman_limit"]:
                    correlated, correlation = retained, rho
                    reason = "redundante según Spearman; se conserva prioridad interpretativa declarada"
                    break
            if reason == "incluida": selected.append(feature)
        records.append({"feature_name": feature, "included": reason == "incluida", "reason": reason,
                        "unit": units.get(feature, "requiere validación"), "training_missing_pct": 100*missing,
                        "training_variance": variance, "training_unique_known": x.nunique(),
                        "correlated_with": correlated, "spearman_with_retained": correlation,
                        "pearson_with_retained": pearson.loc[feature, correlated] if correlated else np.nan,
                        "transformation": "mediana entrenamiento si opcional faltante; RobustScaler; extremos conservados",
                        "permitted_interpretation": "Descripción estadística del movimiento reportado; sin probabilidad de falla."})
    if len(selected) < 2:
        raise ValueError("Menos de dos candidatos variables disponibles; revisar entrenamiento.")
    for i, feature in enumerate(priority):
        for other in priority[:i]:
            known = numeric[[feature, other]].dropna()
            pairs.append({"feature_a": other, "feature_b": feature, "known_pairs": len(known),
                          "spearman": spearman.loc[feature, other], "pearson": pearson.loc[feature, other],
                          "near_duplicate": bool(abs(spearman.loc[feature, other]) > config["spearman_limit"]),
                          "absolute_vs_signed": feature == "absolute_" + other or other == "absolute_" + feature,
                          "exact_duplicate_on_training": bool(len(known) and known[feature].equals(known[other]))})
    table = pd.DataFrame(records)
    excluded = table.loc[~table.included].to_dict("records")
    for feature in training.columns:
        if feature in priority: continue
        reason = "fuera del conjunto candidato compacto; no se incorpora automáticamente"
        if feature.startswith("original__") or feature in {"prism_id", "timestamp", "row_id", "source_record_id", "source_line", "source_name", "source_sha256", "source_file_reference", "date_original", "time_original"}:
            reason = "identificador, texto, fecha o trazabilidad; predictor prohibido"
        elif feature in {"total_prior_observations", "prior_valid_observations", "prior_history_duration_hours", "previous_timestamp"}:
            reason = "posición/historia temporal o fecha; se conserva solo como contexto"
        elif training[feature].dtype == bool or feature == "feature_quality_status":
            reason = "bandera/calidad separada del modelo; contexto o elegibilidad"
        excluded.append({"feature_name": feature, "included": False, "reason": reason, "unit": units.get(feature, "no aplica")})
    return SelectionResult(selected, table, pd.DataFrame(excluded), spearman, pearson, pd.DataFrame(pairs))
