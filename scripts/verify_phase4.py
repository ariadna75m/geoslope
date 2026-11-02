"""Verifica artefactos, reproducción exacta y ausencia de fuga en los datos reales."""
from pathlib import Path
import sys
import json
import argparse
import tempfile
import pandas as pd
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_phase4 import (build_artifacts, write_tables, OUT, DATA, PROTECTED, SOURCE, CONFIG)
from src.config import load_feature_config
from src.exploratory_analysis import read_prepared
from src.feature_engineering import engineer_features
from src.feature_validation import (check_protected, sha256, export_feature_dataset, read_feature_dataset, validate_feature_dataset)


def main(reproduce=False):
    metadata = json.loads((OUT/"phase4_metadata.json").read_text())
    protected = check_protected(ROOT, PROTECTED)
    assert sha256(CONFIG) == metadata["config_sha256"], "Cambió la configuración; regenerar Fase 4."
    assert sha256(SOURCE/"data.csv") == metadata["source_input_sha256"]
    assert sha256(DATA/"west_wall_features.csv") == metadata["feature_dataset_sha256"]
    for name, expected in metadata["table_hashes"].items():
        assert sha256(OUT/name) == expected, name
    for asset in metadata["figures"]:
        with Image.open(OUT/asset["png"]) as picture: picture.verify()
        text = (OUT/asset["html"]).read_text()
        assert 'src="plotly.min.js"' in text and "Plotly.newPlot" in text
    assert (OUT/"interactive/plotly.min.js").is_file()
    proof = {"protected_files_intact": protected, "input_output_rows": metadata["validation"]["output_rows"],
             "prisms": metadata["validation"]["prisms"], "validated_png_html_pairs": len(metadata["figures"]),
             "current_artifact_hashes_verified": True, "full_reproduction_completed": False}
    if reproduce:
        source = read_prepared(SOURCE, "west_wall")
        config = load_feature_config(CONFIG)
        result, validation, tables = build_artifacts(source, config)
        with tempfile.TemporaryDirectory(prefix="phase4-reproduction-") as directory:
            replica_path = export_feature_dataset(result, directory)
            write_tables(tables, directory)
            assert sha256(replica_path) == metadata["feature_dataset_sha256"], "Características no reproducibles byte a byte."
            for name, expected in metadata["table_hashes"].items():
                assert sha256(Path(directory)/name) == expected, name
        restored = read_feature_dataset(DATA/"west_wall_features.csv", metadata["feature_dtypes"])
        pd.testing.assert_frame_equal(result.data, restored, check_exact=True)
        # Corte de prueba: punto medio de cobertura, no fecha de falla ni parámetro del cálculo.
        cutoff = source.timestamp.min()+(source.timestamp.max()-source.timestamp.min())/2
        prefix_source = source.loc[source.timestamp.le(cutoff)]
        expected = engineer_features(prefix_source, config).data
        actual = result.data.loc[result.data.timestamp.le(cutoff)].reset_index(drop=True)
        pd.testing.assert_frame_equal(expected, actual, check_exact=True)
        altered = source.copy(deep=True)
        future = altered.timestamp.gt(cutoff)
        altered.loc[future, "reported_3d_movement_mm"] = [1e12 if i % 2 else -1e12 for i in range(future.sum())]
        altered_features = engineer_features(altered, config).data
        actual_altered = altered_features.loc[altered_features.timestamp.le(cutoff)].reset_index(drop=True)
        pd.testing.assert_frame_equal(expected, actual_altered, check_exact=True)
        proof.update(full_reproduction_completed=True, csv_tables_byte_identical=len(tables)+1, roundtrip_exact=True,
                     temporal_leakage_test={"cutoff_timestamp": str(cutoff), "prefix_rows": len(expected),
                                          "prefix_prisms": int(expected.prism_id.nunique()), "future_rows_altered": int(future.sum()),
                                          "all_columns_identical": True, "failure_date_not_used": True})
    path = OUT/"reproducibility.json"
    if path.exists() and not reproduce:
        previous = json.loads(path.read_text())
        if previous.get("full_reproduction_completed") and previous.get("feature_dataset_sha256") == metadata["feature_dataset_sha256"]:
            proof.update(previous)
    proof["feature_dataset_sha256"] = metadata["feature_dataset_sha256"]
    proof["protected_files_intact"] = check_protected(ROOT, PROTECTED)
    path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    print(json.dumps(proof, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--reproduce", action="store_true")
    main(parser.parse_args().reproduce)
