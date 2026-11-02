"""Copias controladas: alteraciones artificiales, nunca eventos geotécnicos reales."""
import numpy as np
import pandas as pd
from .feature_engineering import VALUE, engineer_features
from .temporal_split import PERIODS
from .anomaly_baseline import robust_reference

KINDS = ("positive_jump", "negative_jump", "sustained_level", "progressive_increment", "artificial_acceleration", "increased_variability", "persistent_increases")


def inject_anomaly(prism_source, times, kind, amplitude, seed=2026):
    if kind not in KINDS or not np.isfinite(amplitude) or amplitude <= 0: raise ValueError("Escenario sintético inválido.")
    modified = prism_source.copy(deep=True).sort_values("timestamp").reset_index(drop=True)
    times = pd.DatetimeIndex(times)
    mask = modified.timestamp.isin(times)
    indices = np.flatnonzero(mask)
    if not len(indices) or indices[0] == 0: raise ValueError("Se requiere segmento conocido y antecedente.")
    original = modified.loc[mask, VALUE].to_numpy(dtype=float).copy()
    anchor_time = modified.timestamp.iloc[indices[0]-1]
    tau = (modified.loc[mask, "timestamp"]-anchor_time).dt.total_seconds().to_numpy()
    tau = tau/tau[-1]
    if kind in {"positive_jump", "negative_jump"}:
        indices = indices[:1]; original = original[:1]
        new = original + amplitude*(1 if kind == "positive_jump" else -1)
    elif kind == "sustained_level": new = original + amplitude
    elif kind == "progressive_increment": new = original + amplitude*tau
    elif kind == "artificial_acceleration": new = original + amplitude*tau**2
    elif kind == "increased_variability": new = original + np.random.default_rng(seed).normal(0, amplitude, len(indices))
    else: new = float(modified[VALUE].iloc[indices[0]-1]) + amplitude*tau
    modified.loc[indices, VALUE] = new
    audit = modified.loc[indices, ["row_id", "prism_id", "timestamp"]].copy().rename(columns={"row_id": "source_record_id"})
    audit["kind"], audit["original_movement_mm"], audit["synthetic_movement_mm"] = kind, original, new
    audit["injected_delta_mm"] = new-original
    audit["amplitude_mm"], audit["seed"] = amplitude, seed
    return modified, audit


def synthetic_experiments(result, features, prepared_source, feature_config):
    cfg = result.bundle.config
    count = cfg["synthetic_segment_observations"]
    validation = features.loc[result.periods.eq(PERIODS[1])]
    validation_counts = validation.groupby("prism_id").size()
    ranked = result.training.groupby("prism_id").size().rename("training_rows").reset_index().sort_values(["training_rows", "prism_id"], ascending=[False,True])
    candidate = ranked.prism_id.map(validation_counts).fillna(0).ge(count+4)
    if not candidate.any(): raise ValueError("No existe prisma con segmento de validación suficiente para pruebas sintéticas.")
    prism = ranked.loc[candidate, "prism_id"].iloc[0]
    source = prepared_source.loc[prepared_source.prism_id.eq(prism)].sort_values("timestamp").reset_index(drop=True)
    timeline = validation.loc[validation.prism_id.eq(prism)].sort_values("timestamp").timestamp
    start = max(2, len(timeline)//3)
    segment = timeline.iloc[start:start+count]
    duration_rest = timeline.iloc[start:]
    amplitude_reference = robust_reference(result.training.movement_delta_mm)["scale"]*cfg["synthetic_amplitude_scale"]
    real_scores = result.scores.loc[result.periods.eq(PERIODS[1])].copy().set_index("source_record_id")
    metrics, audits, scored_targets = [], [], []
    for kind in KINDS:
        for intensity in cfg["synthetic_intensities"]:
            scenario = f"{kind}_intensity_{intensity:g}"
            times = duration_rest if kind == "sustained_level" else segment
            copy, audit = inject_anomaly(source, times, kind, amplitude_reference*intensity, cfg["synthetic_seed"])
            engineered = engineer_features(copy, feature_config).data
            copy_validation = engineered.loc[engineered.timestamp.isin(timeline)].reset_index(drop=True)
            synthetic_scores = result.bundle.score_new(copy_validation).set_index("source_record_id")
            target_ids = audit.source_record_id.tolist()
            synthetic = synthetic_scores.loc[target_ids]
            original = real_scores.loc[target_ids]
            eligible = synthetic.model_eligible & original.model_eligible
            background = real_scores.copy()
            common = background.index.intersection(synthetic_scores.index)
            columns = ["model_eligible", "isolation_forest_score", "baseline_score", "isolation_forest_marked_q99", "baseline_marked_q99"]
            background.loc[common, columns] = synthetic_scores.loc[common, columns]
            background = background.loc[~background.index.isin(target_ids) & background.model_eligible]
            for model in ("baseline", "isolation_forest"):
                scored = synthetic.loc[eligible, model+"_score"]
                flags = synthetic.loc[eligible, model+"_marked_q99"].astype(bool)
                metrics.append({"scenario": scenario, "kind": kind, "intensity": intensity, "prism_id": prism,
                                "model": model, "target_rows": len(synthetic), "eligible_target_rows": int(eligible.sum()),
                                "synthetic_marked_fraction": flags.mean() if len(flags) else np.nan,
                                "mean_score_change": (scored-original.loc[eligible, model+"_score"]).mean(),
                                "mean_training_percentile": synthetic.loc[eligible,model+"_training_percentile"].mean(),
                                "maximum_training_percentile": synthetic.loc[eligible,model+"_training_percentile"].max(),
                                "unlabelled_background_marked_fraction": background[model+"_marked_q99"].astype(bool).mean() if len(background) else np.nan,
                                "background_rows": len(background), "amplitude_mm": amplitude_reference*intensity,
                                "synthetic_only": True, "threshold_scope": "original eligible training only"})
            audit["scenario"], audit["intensity"] = scenario, intensity
            audits.append(audit)
            targets = synthetic.reset_index().copy(); targets["scenario"] = scenario
            targets["real_forest_score"] = original.isolation_forest_score.to_numpy()
            targets["real_baseline_score"] = original.baseline_score.to_numpy()
            scored_targets.append(targets)
    return pd.DataFrame(metrics), pd.concat(audits,ignore_index=True), pd.concat(scored_targets,ignore_index=True)
