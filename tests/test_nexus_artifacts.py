from __future__ import annotations

import json
from pathlib import Path

from heatsafe.research.nexus.artifacts import write_nexus_artifacts
from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame
from heatsafe.research.nexus.evaluation import run_nexus_benchmark


def test_artifact_bundle_contains_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    frame = generate_synthetic_nexus_frame(rows=500)
    frame.to_csv(input_path, index=False)
    config = NexusConfig(
        feature_columns=("temperature_c", "relative_humidity_pct"),
        horizons=(1,),
        minimum_valid_rows=180,
        rolling_origin_max_origins=2,
    )
    report = run_nexus_benchmark(frame, config)
    artifacts = write_nexus_artifacts(
        report,
        output_directory=tmp_path / "artifacts",
        config=config,
        input_paths=(input_path,),
        repository_root=tmp_path,
    )
    for path in artifacts.values():
        assert Path(path).is_file()
    manifest = json.loads(Path(artifacts["experiment_manifest"]).read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "heataq-nexus-pm25"
    assert manifest["inputs"][0]["sha256"]
