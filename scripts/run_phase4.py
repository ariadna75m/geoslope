"""Construcción y validación independiente de características de West Wall."""
from pathlib import Path
import sys
import json
import time
import importlib.metadata as versions
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import load_feature_config, WINDOWS
from src.exploratory_analysis import read_prepared, DISCLAIMER, WEST_DESCRIPTION
from src.feature_engineering import engineer_features, RATE_DESCRIPTION
from src.feature_validation import (validate_feature_dataset, feature_quality_tables,
                                    export_feature_dataset, check_protected, sha256)

OUT = ROOT/"reports/phase4"
DATA = ROOT/"data/processed/phase4"
PROTECTED = OUT/"protected_before_phase4.json"
SOURCE = ROOT/"data/processed/west_wall"
CONFIG = ROOT/"config/phase4.json"


def build_artifacts(source, config):
    result = engineer_features(source, config)
    validation = validate_feature_dataset(source, result)
    quality, groups, prisms, distributions, status = feature_quality_tables(result)
    tables = {"feature_dictionary.csv": result.dictionary, "feature_quality_summary.csv": quality,
              "feature_group_availability.csv": groups, "prism_feature_summary.csv": prisms,
              "feature_distributions.csv": distributions, "quality_status_counts.csv": status}
    return result, validation, tables


def write_tables(tables, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(directory/name, index=False, float_format="%.17g", na_rep="")


def main():
    began = time.perf_counter()
    check_protected(ROOT, PROTECTED)
    source = read_prepared(SOURCE, "west_wall")
    config = load_feature_config(CONFIG)
    result, validation, tables = build_artifacts(source, config)
    path = export_feature_dataset(result, DATA)
    write_tables(tables, OUT)
    from src.feature_visualizations import feature_plots
    representative = pd.read_csv(ROOT/"reports/phase3/west_wall_representative_prisms.csv", dtype={"prism_id": str})
    figures = feature_plots(result.data, tables["feature_quality_summary.csv"], tables["feature_group_availability.csv"],
                            representative.prism_id.tolist(), config, OUT)
    metadata = {
        "phase": 4, "checkpoint_initial": "fef7d06", "source": "West Wall", "source_path": "data/processed/west_wall/data.csv",
        "source_input_sha256": sha256(SOURCE/"data.csv"), "source_file_sha256": source.source_sha256.iloc[0],
        "config_path": "config/phase4.json", "config_sha256": sha256(CONFIG), "config": config.as_dict(),
        "windows": [{"label": label, "hours": hours, "bounds": "(t−window,t]"} for label, hours in WINDOWS],
        "validation": validation, "feature_dtypes": {c: str(result.data[c].dtype) for c in result.data},
        "feature_dataset": "data/processed/phase4/west_wall_features.csv", "feature_dataset_sha256": sha256(path),
        "table_hashes": {name: sha256(OUT/name) for name in tables},
        "protected_files_intact": check_protected(ROOT, PROTECTED), "protected_manifest": "reports/phase4/protected_before_phase4.json",
        "baseline_current_excluded": True, "feature_future_information": False,
        "no_interpolation": True, "no_imputation": True, "no_sources_joined": True, "no_models_trained": True,
        "no_failure_date_used": True, "rate_description": RATE_DESCRIPTION, "movement_description": WEST_DESCRIPTION,
        "window_changes_policy": "Both endpoints strictly within (t−window,t]; cross-boundary pairs excluded only from window summaries, retained as pair features.",
        "streak_policy": "Zero, missing/invalid pair or prolonged gap resets both streaks; no deletion of records.",
        "coverage_percentage_policy": "No expected sampling frequency assumed; only percentage of rows with mathematically available features reported.",
        "figures": figures, "figure_count": len(figures), "disclaimer": DISCLAIMER,
        "versions": {name: versions.version(name) for name in ["pandas", "numpy", "matplotlib", "plotly", "pytest"]}}
    (OUT/"phase4_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False))
    (OUT/"execution_stats.json").write_text(json.dumps({"processing_seconds": time.perf_counter()-began,
                                                     "timing_excluded_from_deterministic_hashes": True}, indent=2))
    print("Registros:", len(result.data), "Prismas:", result.data.prism_id.nunique(), "Columnas:", len(result.data.columns), flush=True)
    print(tables["feature_group_availability.csv"].to_string(index=False), flush=True)
    print("Protegidos:", metadata["protected_files_intact"], "Figuras:", len(figures), flush=True)
    return result


if __name__ == "__main__":
    main()
