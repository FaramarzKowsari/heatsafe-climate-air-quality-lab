from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from heatsafe.research.experiment_orchestrator.bundle import verify_checksums
from heatsafe.research.experiment_orchestrator.contracts import (
    DatasetSpec,
    ExperimentSpec,
    ReleaseSpec,
    ReportSpec,
)
from heatsafe.research.experiment_orchestrator.runner import run_experiment
from heatsafe.research.experiment_orchestrator.templates import (
    default_experiment_spec,
)
from heatsafe.research.nexus.contracts import NexusConfig


@pytest.fixture(scope="module")
def experiment_output(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("experiment-orchestrator")
    spec = ExperimentSpec(
        experiment_id="orchestrator-test",
        title="Experiment orchestrator test",
        description=(
            "A deterministic test of paper-ready artifacts, checksums, "
            "reports and the self-contained reproduction bundle."
        ),
        dataset=DatasetSpec(kind="synthetic", rows=300, seed=42),
        nexus=NexusConfig(
            timestamp_column="timestamp",
            target_column="pm25",
            feature_columns=(
                "temperature_c",
                "relative_humidity_pct",
                "wind_speed_kmh",
                "smoke_proxy",
            ),
            horizons=(1,),
            lags=(1, 2, 3, 6, 12, 24),
            rolling_windows=(6, 12, 24),
            minimum_valid_rows=100,
            rolling_origin_step=24,
            rolling_origin_max_origins=2,
            random_state=42,
        ),
        report=ReportSpec(title="Experiment Orchestrator Test Report"),
        release=ReleaseSpec(version="0.1.0", create_zip=True),
    )
    spec_path = root / "source-spec.json"
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    output = root / "output"
    run_experiment(
        spec,
        spec_path=spec_path,
        output_directory=output,
        repository_root=Path.cwd(),
    )
    return output


def test_default_template_is_complete() -> None:
    spec = default_experiment_spec()
    assert spec.experiment_id == "heataq-nexus-synthetic-paper-demo"
    assert spec.dataset.kind == "synthetic"
    assert 24 in spec.nexus.horizons


def test_paper_ready_bundle(experiment_output: Path) -> None:
    expected = [
        "experiment-spec.json",
        "data/input.csv",
        "nexus/report.json",
        "tables/all-model-metrics.csv",
        "tables/best-by-horizon.csv",
        "figures/best-mae-by-horizon.svg",
        "figures/coverage-by-horizon.svg",
        "report/report.md",
        "report/report.html",
        "metadata/CITATION.cff",
        "metadata/zenodo-candidate.json",
        "orchestration-manifest.json",
        "checksums.sha256",
        "release/orchestrator-test-0.1.0-candidate.zip",
    ]
    for relative in expected:
        assert (experiment_output / relative).is_file(), relative

    summary = json.loads(
        (experiment_output / "run-summary.json").read_text(encoding="utf-8")
    )
    assert summary["experiment_id"] == "orchestrator-test"
    assert summary["best_by_horizon"]
    assert verify_checksums(experiment_output)["valid"] is True


def test_checksum_verification_detects_tampering(
    experiment_output: Path,
    tmp_path: Path,
) -> None:
    tampered = tmp_path / "tampered"
    shutil.copytree(experiment_output, tampered)
    (tampered / "tables/best-by-horizon.csv").write_text(
        "tampered\n",
        encoding="utf-8",
    )
    report = verify_checksums(tampered)
    assert report["valid"] is False
    assert any(
        "tables/best-by-horizon.csv" in failure
        for failure in report["failures"]
    )
