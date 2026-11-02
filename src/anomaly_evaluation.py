"""Estabilidad, acuerdo y carga de revisión; sin métricas supervisadas reales."""
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from .temporal_split import PERIODS
from .anomaly_models import fit_isolation, fit_with_frozen_preprocessing, train_percentile, tree_feature_metadata
from .model_preprocessing import preprocessing_metadata
from copy import deepcopy
import hashlib


def top_ids(scores, identifiers, fraction):
    scores, identifiers = np.asarray(scores), np.asarray(identifiers)
    if not len(scores): return set()
    order = np.lexsort((identifiers.astype(str), -scores))
    count = max(1, math.ceil(fraction*len(scores)))
    return set(identifiers[order[:count]])


def jaccard(a, b):
    return len(a & b)/len(a | b) if a | b else 1.


def rank_correlation(a, b):
    if len(a) < 2 or np.unique(a).size < 2 or np.unique(b).size < 2: return np.nan
    return pd.Series(np.asarray(a)).corr(pd.Series(np.asarray(b)), method="spearman")


def evaluation_tables(result, features):
    scores, bundle = result.scores, result.bundle
    threshold_rows, comparison, workloads, profiles, agreement = [], [], [], [], []
    for model in ("baseline", "isolation_forest"):
        score_col = model+"_score"
        train = scores.loc[scores.period.eq(PERIODS[0]) & scores.model_eligible, score_col]
        for period in PERIODS:
            g = scores.loc[scores.period.eq(period)]
            e = g.loc[g.model_eligible]
            marked = e[model+"_marked_q99"].astype(bool)
            comparison.append({"model": model, "period": period, "rows": len(g), "eligible_rows": len(e),
                               "mean_score": e[score_col].mean(), "median_score": e[score_col].median(),
                               "score_q95": e[score_col].quantile(.95), "max_score": e[score_col].max(),
                               "marked_q99_rows": int(marked.sum()), "marked_q99_pct": 100*marked.mean() if len(e) else np.nan,
                               "marked_prisms": e.loc[marked, "prism_id"].nunique(),
                               "ks_distance_vs_training": ks_2samp(train, e[score_col]).statistic if len(e) else np.nan,
                               "reference_threshold_scope": "training only; no independent labels"})
            for label, threshold in bundle.thresholds[model].items():
                flags = e[model+"_marked_"+label].astype(bool)
                concentration = e.loc[flags, "prism_id"].value_counts()
                threshold_rows.append({"model": model, "threshold_label": label, "threshold": threshold, "period": period,
                                       "eligible_rows": len(e), "marked_rows": int(flags.sum()), "marked_pct": 100*flags.mean() if len(e) else np.nan,
                                       "prisms_affected": len(concentration),
                                       "top_prism_share_of_marked_pct": 100*concentration.iloc[0]/flags.sum() if flags.any() else 0.,
                                       "top_three_prisms_share_of_marked_pct": 100*concentration.head(3).sum()/flags.sum() if flags.any() else 0.})
            for day, block in g.groupby(g.timestamp.dt.normalize(), sort=True):
                eligible = block.model_eligible
                flags = block.loc[eligible, model+"_marked_q99"].astype(bool)
                workloads.append({"model": model, "period": period, "group_type": "day", "group_key": str(day.date()),
                                  "rows": len(block), "eligible_rows": int(eligible.sum()), "marked_rows": int(flags.sum()),
                                  "marked_pct_of_eligible": 100*flags.mean() if len(flags) else np.nan,
                                  "days_with_no_eligible_measurements": not bool(eligible.any())})
            for prism, block in g.groupby("prism_id", sort=True):
                eligible = block.model_eligible
                flags = block.loc[eligible, model+"_marked_q99"].astype(bool)
                workloads.append({"model": model, "period": period, "group_type": "prism", "group_key": prism,
                                  "rows": len(block), "eligible_rows": int(eligible.sum()), "marked_rows": int(flags.sum()),
                                  "marked_pct_of_eligible": 100*flags.mean() if len(flags) else np.nan,
                                  "days_with_no_eligible_measurements": False})
                context = features.loc[block.index]
                profiles.append({"model": model, "period": period, "prism_id": prism, "rows": len(block), "eligible_rows": int(eligible.sum()),
                                 "marked_q99_rows": int(flags.sum()), "marked_pct_of_eligible": 100*flags.mean() if len(flags) else np.nan,
                                 "median_score": block.loc[eligible, score_col].median(), "max_score": block.loc[eligible, score_col].max(),
                                 "median_reported_movement_mm": context.reported_3d_movement_mm.median(),
                                 "median_elapsed_hours": context.elapsed_hours.median(), "training_eligible_rows": int(result.training.prism_id.eq(prism).sum()),
                                 "seen_in_training": bool(result.training.prism_id.eq(prism).any())})
    for period in PERIODS:
        g = scores.loc[scores.period.eq(period) & scores.model_eligible]
        for fraction in bundle.config["top_fractions"]:
            a = top_ids(g.baseline_score, g.source_record_id, fraction)
            b = top_ids(g.isolation_forest_score, g.source_record_id, fraction)
            overlap = g[g.source_record_id.isin(a & b)]
            agreement.append({"period": period, "top_fraction": fraction, "eligible_rows": len(g),
                              "ranking_spearman": rank_correlation(g.baseline_score, g.isolation_forest_score),
                              "jaccard_top": jaccard(a, b), "common_top_rows": len(a & b), "common_prisms": overlap.prism_id.nunique(),
                              "baseline_only_top_rows": len(a-b), "forest_only_top_rows": len(b-a)})
    differing = scores.loc[scores.model_eligible & scores.baseline_marked_q99.ne(scores.isolation_forest_marked_q99).fillna(False)].copy()
    differing["experimental_disagreement"] = np.where(differing.baseline_marked_q99.astype(bool), "solo regla estadística", "solo Isolation Forest")
    return {"model_comparison.csv": pd.DataFrame(comparison), "threshold_sensitivity.csv": pd.DataFrame(threshold_rows),
            "model_agreement.csv": pd.DataFrame(agreement), "review_workload.csv": pd.DataFrame(workloads),
            "prism_score_profiles.csv": pd.DataFrame(profiles), "method_only_observations.csv": differing}


def seed_stability(result, data):
    bundle = result.bundle
    e = result.scores.model_eligible
    g = data.loc[e]
    reference = result.scores.loc[e, "isolation_forest_score"].to_numpy()
    values, records = [], []
    for seed in bundle.config["seeds"]:
        parameters = {**bundle.config["primary_model"], "random_state": seed}
        model = bundle.pipeline if seed == bundle.config["primary_model"]["random_state"] else fit_isolation(result.training, bundle.selected_features, parameters)
        score = -model.score_samples(g)
        train_score = -model.score_samples(result.training)
        threshold = np.quantile(train_score, .99)
        values.append(score)
        for period in PERIODS:
            mask = result.periods.loc[e].eq(period).to_numpy()
            a, b = reference[mask], score[mask]
            ids = g.source_record_id.to_numpy()[mask]
            for fraction in bundle.config["top_fractions"]:
                records.append({"seed": seed, "period": period, "top_fraction": fraction,
                                "ranking_spearman_vs_primary": rank_correlation(a, b),
                                "jaccard_top_vs_primary": jaccard(top_ids(a, ids, fraction), top_ids(b, ids, fraction)),
                                "score_mean": b.mean() if len(b) else np.nan,
                                "mean_absolute_score_change": np.abs(a-b).mean() if len(b) else np.nan,
                                "marked_q99_pct": 100*np.mean(b > threshold) if len(b) else np.nan,
                                "training_q99_threshold": threshold})
    values = np.asarray(values)
    variability = result.scores.loc[e, ["source_record_id", "prism_id", "timestamp", "period"]].copy()
    variability["score_mean_across_seeds"] = values.mean(axis=0)
    variability["score_std_across_seeds"] = values.std(axis=0, ddof=1)
    variability["score_min_across_seeds"] = values.min(axis=0)
    variability["score_max_across_seeds"] = values.max(axis=0)
    # Ranks compare observations only within their own chronological period.
    ranks_by_seed = []
    for seed_score in values:
        ranked = pd.Series(seed_score, index=g.index).groupby(result.periods.loc[e]).rank(method="average", ascending=False)
        ranks_by_seed.append(ranked.to_numpy())
    rank_values = np.asarray(ranks_by_seed)
    variability["rank_min_across_seeds"] = rank_values.min(axis=0)
    variability["rank_max_across_seeds"] = rank_values.max(axis=0)
    variability["rank_range_across_seeds"] = rank_values.max(axis=0)-rank_values.min(axis=0)
    variability["rank_std_across_seeds"] = rank_values.std(axis=0, ddof=1)
    return pd.DataFrame(records), variability


def max_features_sensitivity(result, data):
    """Tres presupuestos de variables, misma selección y preprocesamiento congelado.

    El entero 1 es un conteo; float 0.5 y 1.0 son fracciones. Las etiquetas
    mantienen el tipo incluso cuando un CSV o un formateador redondea números.
    """
    bundle = result.bundle
    eligible = result.scores.model_eligible
    transformed = data.loc[eligible]
    reference = result.scores.loc[eligible, "isolation_forest_score"].to_numpy()
    summary, daily, prism_rows, tree_rows, score_rows, variants = [], [], [], [], [], {}
    train_digest = hashlib.sha256(pd.util.hash_pandas_object(result.training[bundle.selected_features], index=False).values.tobytes()
                                  + "|".join(result.training.source_record_id).encode()).hexdigest()
    preprocessor = preprocessing_metadata(bundle.pipeline[:-1])
    preprocessor_hash = hashlib.sha256(json.dumps(preprocessor, sort_keys=True).encode()).hexdigest()
    for budget in bundle.config["max_features_comparison"]:
        literal, kind = repr(budget), type(budget).__name__
        label = literal + " (" + kind + ")"
        parameters = {**bundle.config["primary_model"], "max_features": budget}
        pipeline = bundle.pipeline if type(budget) is float and budget == 1.0 else fit_with_frozen_preprocessing(result.training, bundle.pipeline, parameters)
        assert preprocessing_metadata(pipeline[:-1]) == preprocessor
        learned = -pipeline.score_samples(result.training)
        threshold = float(np.quantile(learned, .99))
        score = -pipeline.score_samples(transformed)
        flags = score > threshold
        effective = tree_feature_metadata(pipeline)
        variant = deepcopy(result)
        variant.bundle.pipeline = pipeline
        variant.bundle.config["primary_model"] = parameters
        variant.bundle.thresholds["isolation_forest"] = {
            f"q{round(q*100)}": float(np.quantile(learned, q)) for q in bundle.config["threshold_quantiles"]}
        variant.bundle.thresholds["isolation_forest"]["internal"] = -float(pipeline.named_steps["model"].offset_)
        variant.bundle.training_score_references["isolation_forest"] = learned
        variant.scores = variant.bundle.score_new(data)
        variant.scores.insert(3, "period", result.periods)
        variants[label] = variant
        all_scores = result.scores[["source_record_id", "prism_id", "timestamp", "period", "model_eligible"]].copy()
        all_scores["isolation_forest_score"] = np.nan
        all_scores.loc[eligible, "isolation_forest_score"] = score
        all_scores["training_percentile"] = train_percentile(learned, all_scores.isolation_forest_score)
        all_scores["marked_q99"] = pd.Series(pd.NA, index=all_scores.index, dtype="boolean")
        all_scores.loc[eligible, "marked_q99"] = flags
        all_scores["variant"], all_scores["max_features_literal"], all_scores["max_features_type"] = label, literal, kind
        score_rows.append(all_scores)
        forest = pipeline.named_steps["model"]
        names = bundle.selected_features
        for index, (tree, indices) in enumerate(zip(forest.estimators_, forest.estimators_features_)):
            used = sorted(set(tree.tree_.feature[tree.tree_.feature >= 0]))
            tree_rows.append({"variant": label, "tree_index": index, "max_features_literal": literal,
                              "max_features_type": kind, "available_feature_count": len(indices),
                              "available_feature_names": ";".join(names[i] for i in indices),
                              "used_in_splits_feature_count": len(used),
                              "used_in_splits_feature_names": ";".join(names[indices[i]] for i in used)})
        for period in PERIODS:
            mask = result.periods.loc[eligible].eq(period).to_numpy()
            block = all_scores.loc[all_scores.period.eq(period)]
            valid = block.loc[block.model_eligible]
            a, b = reference[mask], score[mask]
            ids = valid.source_record_id.to_numpy()
            marked = valid.loc[valid.marked_q99.astype(bool)]
            concentration = marked.prism_id.value_counts()
            day_counts = []
            for day, group in block.groupby(block.timestamp.dt.normalize(), sort=True):
                subset = group.loc[group.model_eligible]
                marked_count = int(subset.marked_q99.sum())
                day_counts.append(marked_count)
                daily.append({"variant": label, "period": period, "day": str(day.date()), "eligible_rows": len(subset),
                              "marked_rows": marked_count, "marked_pct": 100*marked_count/len(subset) if len(subset) else np.nan,
                              "no_eligible_measurements": not len(subset)})
            for prism, group in block.groupby("prism_id", sort=True):
                subset = group.loc[group.model_eligible]
                count = int(subset.marked_q99.sum())
                prism_rows.append({"variant": label, "period": period, "prism_id": prism, "rows": len(group),
                                   "eligible_rows": len(subset), "marked_rows": count,
                                   "marked_pct": 100*count/len(subset) if len(subset) else np.nan,
                                   "maximum_score": subset.isolation_forest_score.max(),
                                   "share_of_period_marked_pct": 100*count/len(marked) if len(marked) else 0.})
            for fraction in bundle.config["top_fractions"]:
                summary.append({"variant": label, "max_features_literal": literal, "max_features_type": kind,
                                "selected_feature_count": len(names), "effective_features_per_tree": effective["effective_available_features_per_tree"][0],
                                "period": period, "top_fraction": fraction, "ranking_spearman_vs_primary": rank_correlation(a,b),
                                "jaccard_top_vs_primary": jaccard(top_ids(a,ids,fraction),top_ids(b,ids,fraction)),
                                "mean_score": b.mean() if len(b) else np.nan, "median_score": np.median(b) if len(b) else np.nan,
                                "marked_q99_rows": len(marked), "marked_q99_pct": 100*len(marked)/len(valid) if len(valid) else np.nan,
                                "marked_prisms": len(concentration), "top_prism_share_of_marked_pct": 100*concentration.iloc[0]/len(marked) if len(marked) else 0.,
                                "top_three_prisms_share_of_marked_pct": 100*concentration.head(3).sum()/len(marked) if len(marked) else 0.,
                                "ks_distance_vs_training": ks_2samp(learned,b).statistic if len(b) else np.nan,
                                "maximum_daily_marked_rows": max(day_counts,default=0), "days_without_marks": sum(x==0 for x in day_counts),
                                "training_q99_threshold": threshold, "training_rows": len(result.training),
                                "training_signature": train_digest, "preprocessing_sha256": preprocessor_hash,
                                "parameters": json.dumps({**parameters,"n_jobs":1},sort_keys=True)})
    return {"max_features_sensitivity.csv": pd.DataFrame(summary), "max_features_daily_workload.csv": pd.DataFrame(daily),
            "max_features_prism_profiles.csv": pd.DataFrame(prism_rows), "tree_feature_availability.csv": pd.DataFrame(tree_rows),
            "max_features_scores.csv": pd.concat(score_rows,ignore_index=True)}, variants


def hyperparameter_sensitivity(result, data):
    bundle = result.bundle; base = bundle.config["primary_model"]
    variants = [("contamination", str(x), {**base, "contamination": x}, bundle.selected_features, True) for x in bundle.config["contaminations"]]
    variants += [("n_estimators", str(x), {**base, "n_estimators": x}, bundle.selected_features, True) for x in bundle.config["tree_counts"] if x != base["n_estimators"]]
    variants += [("max_samples", str(x), {**base, "max_samples": x}, bundle.selected_features, True) for x in bundle.config["sample_counts"] if x != base["max_samples"]]
    variants += [("transformation", "training_median_no_scaler", base, bundle.selected_features, False)]
    subset = [name for name in bundle.selected_features if "7d" not in name]
    if len(subset) >= 2: variants += [("feature_set", "without_7d", base, subset, True)]
    e = result.scores.model_eligible
    g = data.loc[e]
    reference = result.scores.loc[e, "isolation_forest_score"].to_numpy()
    records = []
    for family, label, parameters, features, robust in variants:
        pipeline = bundle.pipeline if parameters == base and features == bundle.selected_features and robust else fit_isolation(result.training, features, parameters, robust)
        score = -pipeline.score_samples(g); trained = -pipeline.score_samples(result.training)
        threshold = np.quantile(trained, .99); internal = -pipeline.named_steps["model"].offset_
        for period in PERIODS:
            mask = result.periods.loc[e].eq(period).to_numpy()
            a, b = reference[mask], score[mask]; ids = g.source_record_id.to_numpy()[mask]
            records.append({"family": family, "variant": label, "period": period, "parameters": json.dumps(parameters, sort_keys=True),
                            "selected_feature_count": len(features), "features": ";".join(features), "robust_scaler": robust,
                            "ranking_spearman_vs_primary": rank_correlation(a,b), "jaccard_top_2pct_vs_primary": jaccard(top_ids(a,ids,.02), top_ids(b,ids,.02)),
                            "mean_absolute_score_change": np.abs(a-b).mean() if len(b) else np.nan,
                            "marked_q99_pct": 100*np.mean(b>threshold) if len(b) else np.nan,
                            "marked_internal_pct": 100*np.mean(b>internal) if len(b) else np.nan,
                            "training_q99_threshold": threshold, "training_internal_threshold": internal})
    return pd.DataFrame(records)
