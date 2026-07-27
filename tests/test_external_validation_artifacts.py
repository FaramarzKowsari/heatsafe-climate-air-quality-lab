from __future__ import annotations

import json
from pathlib import Path

from heatsafe.research.transfer.artifacts import (
    write_external_validation_artifacts,
)
from heatsafe.research.transfer.contracts import ExternalValidationConfig
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
)
from heatsafe.research.transfer.engine import run_external_validation


def test_external_validation_artifact_bundle(tmp_path: Path) -> None:
    frame = generate_synthetic_multicity_frame(rows_per_city=380)
    input_path = tmp_path / "multicity.csv"
    frame.to_csv(input_path, index=False)
    config = ExternalValidationConfig(
        feature_columns=("temperature_c", "wind_speed_kmh"),
        horizons=(1,),
        minimum_rows_per_city=340,
        bootstrap_repetitions=20,
        block_length=12,
        models=("persistence", "ridge"),
        validation_modes=("leave-one-city-out",),
    )
    report = run_external_validation(frame, config)
    artifacts = write_external_validation_artifacts(
        report,
        output_directory=tmp_path / "artifacts",
        config=config,
        input_paths=(input_path,),
        repository_root=tmp_path,
    )
    for path in artifacts.values():
        assert Path(path).is_file()

    manifest = json.loads(
        Path(artifacts["experiment_manifest"]).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["experiment_id"] == "external-validation-pm25"
    assert manifest["inputs"][0]["sha256"]
