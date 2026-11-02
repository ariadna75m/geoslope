"""Desviaciones descriptivas aproximadas; no atribuciones exactas del bosque."""
import json
import numpy as np


def add_explanations(result, features, dictionary):
    scores = result.scores.copy()
    bundle = result.bundle
    units = dictionary.set_index("feature_name").unit.to_dict()
    eligible = scores.model_eligible
    transformed = bundle.pipeline[:-1].transform(features.loc[eligible]) if eligible.any() else np.empty((0, len(bundle.selected_features)))
    standardized = dict(zip(features.loc[eligible].index, transformed))
    explanations, detail = [], []
    for index, row in scores.iterrows():
        if not row.model_eligible:
            explanations.append("No evaluable para modelado: " + row.model_ineligibility_reason + ". No se interpreta como normal.")
            detail.append("[]"); continue
        high = bool(row.baseline_marked_q95 or row.isolation_forest_marked_q95)
        order = np.argsort(-np.abs(standardized[index]), kind="stable")[:3]
        items = [{"feature": bundle.selected_features[i], "reported_value": None if np.isnan(features.loc[index, bundle.selected_features[i]]) else float(features.loc[index, bundle.selected_features[i]]),
                  "unit": units.get(bundle.selected_features[i], "requiere validación"), "absolute_training_scaled_deviation": float(abs(standardized[index][i]))} for i in order]
        label = "Puntuación experimental elevada" if high else "Puntuación experimental disponible"
        text = label + "; mayores desviaciones descriptivas respecto al entrenamiento: "
        text += "; ".join(item["feature"] + "=" + (f"{item['reported_value']:.4g} {item['unit']}" if item["reported_value"] is not None else "desconocido; mediana de entrenamiento") for item in items)
        text += f". Z robusto previo={features.loc[index, 'historical_robust_z_score']:.3g}; tendencia 72h={features.loc[index, 'local_trend_72h_slope_mm_per_day']:.3g} mm/día; racha={features.loc[index, 'increase_streak_count']:.0f} incrementos."
        text += " Calidad: " + row.feature_quality_status + ". Explicación aproximada; no contribución exacta de Isolation Forest ni diagnóstico geomecánico."
        explanations.append(text); detail.append(json.dumps(items, ensure_ascii=False, allow_nan=False))
    scores["descriptive_explanation"], scores["feature_deviation_details"] = explanations, detail
    return scores
