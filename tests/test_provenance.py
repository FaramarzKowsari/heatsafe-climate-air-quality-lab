from __future__ import annotations

import json
from pathlib import Path

from heatsafe.research.provenance import build_experiment_manifest, sha256_file, write_experiment_manifest


def test_manifest_records_input_checksum(tmp_path: Path) -> None:
    data = tmp_path / "input.csv"
    data.write_text("value\n1\n2\n", encoding="utf-8")

    manifest = build_experiment_manifest(
        "experiment-001",
        configuration={"horizon": 24},
        input_paths=[data],
        random_seed=42,
        dependency_names=[],
        repository_root=tmp_path,
    )

    assert manifest.inputs[0].sha256 == sha256_file(data)
    assert manifest.random_seed == 42
    assert manifest.configuration["horizon"] == 24

    output = write_experiment_manifest(manifest, tmp_path / "manifest.json")
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["experiment_id"] == "experiment-001"
    assert parsed["inputs"][0]["size_bytes"] == data.stat().st_size
