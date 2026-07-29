from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from heatsafe.data_foundation.official_snapshots.acquisition import (
    acquire_observations,
)
from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
    OfficialSnapshotConfig,
)
from heatsafe.data_foundation.official_snapshots.pipeline import (
    freeze_official_snapshot,
)
from heatsafe.data_foundation.official_snapshots.planning import (
    build_acquisition_plan,
)
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import (
    load_observations,
    verify_snapshot,
)
from heatsafe.research.experiment_orchestrator.contracts import (
    DatasetSpec,
    ExperimentSpec,
    ReleaseSpec,
    ReportSpec,
)
from heatsafe.research.experiment_orchestrator.runner import (
    run_experiment,
    verify_experiment_directory,
)
from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.official_experiment.contracts import (
    RealOfficialExperimentConfig,
)
from heatsafe.research.official_experiment.preparation import (
    prepare_hourly_station_frame,
)
from heatsafe.research.provenance import sha256_file


def _load_real_config(path: str | Path) -> RealOfficialExperimentConfig:
    return RealOfficialExperimentConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _resolve_relative(base_file: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base_file.parent / candidate
    return candidate.resolve()


def _load_snapshot_config(
    real_config: RealOfficialExperimentConfig,
    *,
    real_config_path: Path,
) -> tuple[OfficialSnapshotConfig, Path]:
    snapshot_path = _resolve_relative(
        real_config_path,
        real_config.snapshot_config_path,
    )
    snapshot_config = OfficialSnapshotConfig.model_validate_json(
        snapshot_path.read_text(encoding="utf-8")
    )
    return snapshot_config, snapshot_path


def write_real_experiment_plan(
    config_path: str | Path,
    output_path: str | Path,
) -> Path:
    real_path = Path(config_path).resolve()
    real_config = _load_real_config(real_path)
    snapshot_config, snapshot_path = _load_snapshot_config(
        real_config,
        real_config_path=real_path,
    )
    source = DEFAULT_REGISTRY.get(snapshot_config.source_id)
    acquisition_plan = build_acquisition_plan(snapshot_config, source)

    payload = {
        "experiment_id": real_config.experiment_id,
        "title": real_config.title,
        "description": real_config.description,
        "real_experiment_config": str(real_path),
        "snapshot_config": str(snapshot_path),
        "source_id": snapshot_config.source_id,
        "dataset_id": snapshot_config.dataset_id,
        "dataset_version": snapshot_config.version,
        "credential_environment_variables": list(
            acquisition_plan.credential_environment_variables
        ),
        "credential_values_present": {
            name: bool(os.getenv(name))
            for name in acquisition_plan.credential_environment_variables
        },
        "sanitized_request_parameters": (
            acquisition_plan.sanitized_request_parameters
        ),
        "request_sha256": acquisition_plan.request_sha256,
        "station_selection_policy": (
            real_config.station_policy.model_dump(mode="json")
        ),
        "forecast_horizons_hours": list(real_config.horizons),
        "event_threshold": real_config.event_threshold,
        "scientific_boundary": (
            "This is a secret-free execution plan. It is not evidence that "
            "official data were acquired or that an experiment succeeded."
        ),
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output


def _prepare_workspace(path: Path, *, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"Workspace is not empty: {path}. Use --overwrite to replace it."
            )
        resolved = path.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe workspace: {resolved}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _write_open_report_scripts(workspace: Path) -> None:
    report = workspace / "experiment/report/report.html"
    command = workspace / "OPEN_REPORT.cmd"
    command.write_text(
        "@echo off\r\n"
        "start \"\" \"%~dp0experiment\\report\\report.html\"\r\n",
        encoding="utf-8",
    )
    shell = workspace / "open-report.sh"
    shell.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "python -m webbrowser "
        f'"file://{report.resolve().as_posix()}"\n',
        encoding="utf-8",
    )


def run_real_official_experiment(
    config_path: str | Path,
    *,
    workspace: str | Path,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    real_path = Path(config_path).resolve()
    real_config = _load_real_config(real_path)
    snapshot_config, snapshot_config_path = _load_snapshot_config(
        real_config,
        real_config_path=real_path,
    )

    output_root = Path(workspace)
    _prepare_workspace(output_root, overwrite=overwrite)

    plan_path = write_real_experiment_plan(
        real_path,
        output_root / "execution-plan.json",
    )

    observations = acquire_observations(snapshot_config)
    snapshot_release = freeze_official_snapshot(
        observations,
        config=snapshot_config,
        output_root=output_root / "official-snapshots",
        registry_root=output_root / "registry",
        repository_root=repository_root,
        acquisition_mode=AcquisitionMode.LIVE_CONNECTOR,
        overwrite=overwrite,
    )
    if not snapshot_release.quality_gate.passed:
        raise RuntimeError(
            "The official snapshot quality gate did not pass: "
            + "; ".join(snapshot_release.quality_gate.reasons)
        )

    snapshot_directory = Path(snapshot_release.snapshot_directory)
    frozen_observations = load_observations(snapshot_directory)
    frame, selection_report = prepare_hourly_station_frame(
        frozen_observations,
        real_config.station_policy,
    )

    prepared_root = output_root / "prepared"
    prepared_root.mkdir(parents=True, exist_ok=True)
    prepared_csv = prepared_root / "selected-station-hourly.csv"
    frame.to_csv(prepared_csv, index=False)
    selection_path = prepared_root / "station-selection-report.json"
    selection_path.write_text(
        json.dumps(selection_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    selected_station = str(
        selection_report["selected_station"]["station_id"]
    )
    source_spec = ExperimentSpec(
        experiment_id=real_config.experiment_id,
        title=real_config.title,
        description=real_config.description,
        dataset=DatasetSpec(
            kind="csv",
            path="prepared/selected-station-hourly.csv",
            seed=real_config.random_state,
            variables=(real_config.station_policy.target_variable,),
            frequency="1h",
        ),
        nexus=NexusConfig(
            timestamp_column="timestamp",
            target_column=real_config.station_policy.target_variable,
            feature_columns=(),
            horizons=real_config.horizons,
            event_threshold=real_config.event_threshold,
            alpha=real_config.alpha,
            random_state=real_config.random_state,
            minimum_valid_rows=real_config.minimum_valid_rows,
            rolling_origin_step=real_config.rolling_origin_step,
            rolling_origin_max_origins=(
                real_config.rolling_origin_max_origins
            ),
            expected_frequency="1h",
        ),
        report=ReportSpec(
            title=real_config.title,
            subtitle=(
                "First real official-source HeatAQ Nexus forecasting "
                "experiment"
            ),
            author=real_config.created_by,
            organization="HeatSafe Research Lab",
            abstract=(
                "This report evaluates an hourly PM2.5 forecasting benchmark "
                "from an immutable US EPA Air Quality System snapshot. A "
                "monitoring station is selected deterministically by temporal "
                "continuity, and all baselines, fitted models, uncertainty "
                "metrics, checksums and reproduction commands are retained."
            ),
            keywords=(
                "US EPA AQS",
                "PM2.5",
                "official environmental data",
                "forecasting",
                "reproducibility",
            ),
        ),
        release=ReleaseSpec(
            version=real_config.release_version,
            status="candidate",
            create_zip=True,
            license="CC-BY-4.0",
        ),
        notes=(
            "Official source: US EPA Air Quality System.",
            f"Selected monitoring station: {selected_station}.",
            "No paid AI API is used.",
            "No missing target values are imputed inside the selected segment.",
        ),
        limitations=real_config.limitations,
        created_by=real_config.created_by,
    )
    experiment_spec_path = output_root / "real-experiment-spec.json"
    experiment_spec_path.write_text(
        source_spec.model_dump_json(indent=2),
        encoding="utf-8",
    )

    experiment_result = run_experiment(
        source_spec,
        spec_path=experiment_spec_path,
        output_directory=output_root / "experiment",
        repository_root=repository_root,
        overwrite=overwrite,
    )

    snapshot_manifest = snapshot_directory / "manifest.json"
    master = {
        "experiment_id": real_config.experiment_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "created_by": real_config.created_by,
        "source_id": snapshot_config.source_id,
        "dataset_id": snapshot_config.dataset_id,
        "dataset_version": snapshot_config.version,
        "snapshot_config_path": str(snapshot_config_path),
        "execution_plan_path": str(plan_path),
        "execution_plan_sha256": sha256_file(plan_path),
        "snapshot_directory": str(snapshot_directory),
        "snapshot_manifest_sha256": sha256_file(snapshot_manifest),
        "snapshot_quality_gate": (
            snapshot_release.quality_gate.model_dump(mode="json")
        ),
        "snapshot_integrity": snapshot_release.snapshot_integrity,
        "registry_integrity": snapshot_release.registry_integrity,
        "selected_station": selection_report["selected_station"],
        "prepared_csv": str(prepared_csv),
        "prepared_csv_sha256": sha256_file(prepared_csv),
        "selection_report": str(selection_path),
        "selection_report_sha256": sha256_file(selection_path),
        "experiment_output": experiment_result.model_dump(mode="json"),
        "scientific_boundary": (
            "The result is a reproducible station-level forecasting "
            "benchmark. It does not represent personal exposure, countywide "
            "conditions, causal effects, medical risk or official warning "
            "authority."
        ),
    }
    manifest_path = output_root / "real-official-experiment-manifest.json"
    manifest_path.write_text(
        json.dumps(master, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_open_report_scripts(output_root)

    verification = verify_real_official_experiment(output_root)
    if not verification["valid"]:
        raise RuntimeError(
            "The generated real official experiment failed verification: "
            + "; ".join(verification["failures"])
        )

    return {
        "workspace": str(output_root),
        "manifest": str(manifest_path),
        "selected_station": selected_station,
        "selected_segment_rows": selection_report[
            "selected_segment_rows"
        ],
        "report_html": experiment_result.report_html,
        "candidate_release": experiment_result.release_archive,
        "verification": verification,
    }



# HEATSAFE_MANIFEST_PATH_RESOLUTION_V1
def _resolve_manifest_artifact(
    workspace_root: Path,
    value: object,
) -> Path:
    # Resolve old and new manifest path formats without double-prefixing.
    candidate = Path(str(value))

    if candidate.is_absolute():
        return candidate

    if candidate.exists():
        return candidate

    root_parts = workspace_root.parts
    candidate_parts = candidate.parts
    if (
        root_parts
        and len(candidate_parts) >= len(root_parts)
        and candidate_parts[: len(root_parts)] == root_parts
    ):
        return candidate

    return workspace_root / candidate

def verify_real_official_experiment(
    workspace: str | Path,
) -> dict[str, Any]:
    root = Path(workspace)
    failures: list[str] = []

    manifest_path = root / "real-official-experiment-manifest.json"
    if not manifest_path.is_file():
        return {
            "valid": False,
            "failures": [
                "Missing real-official-experiment-manifest.json"
            ],
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot_directory = _resolve_manifest_artifact(
        root,
        manifest["snapshot_directory"],
    )

    snapshot_report = verify_snapshot(snapshot_directory)
    if not bool(snapshot_report.get("valid")):
        failures.append("Official snapshot integrity verification failed")

    experiment_report = verify_experiment_directory(root / "experiment")
    if not bool(experiment_report.get("valid")):
        failures.extend(
            str(item)
            for item in experiment_report.get("failures", [])
        )

    prepared_csv = _resolve_manifest_artifact(
        root,
        manifest["prepared_csv"],
    )
    if not prepared_csv.is_file():
        failures.append("Prepared station CSV is missing")
    elif sha256_file(prepared_csv) != manifest["prepared_csv_sha256"]:
        failures.append("Prepared station CSV checksum mismatch")

    return {
        "valid": not failures,
        "failures": failures,
        "snapshot": snapshot_report,
        "experiment": experiment_report,
        "selected_station": manifest.get("selected_station"),
    }
