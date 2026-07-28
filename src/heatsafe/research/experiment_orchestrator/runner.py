from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from heatsafe.research.experiment_orchestrator.bundle import (
    create_deterministic_archive,
    iter_bundle_files,
    verify_checksums,
    write_artifact_index,
    write_checksums,
)
from heatsafe.research.experiment_orchestrator.contracts import (
    ExperimentRunResult,
    ExperimentSpec,
)
from heatsafe.research.experiment_orchestrator.dataset import load_experiment_frame
from heatsafe.research.experiment_orchestrator.reporting import (
    write_paper_figures,
    write_paper_reports,
    write_paper_tables,
)
from heatsafe.research.nexus.artifacts import write_nexus_artifacts
from heatsafe.research.nexus.evaluation import run_nexus_benchmark
from heatsafe.research.provenance import (
    build_experiment_manifest,
    dependency_versions,
    detect_git_revision,
    write_experiment_manifest,
)


def load_experiment_spec(path: str | Path) -> ExperimentSpec:
    return ExperimentSpec.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"Output directory is not empty: {path}. Use --overwrite to replace it."
            )
        resolved = path.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe output path: {resolved}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _self_contained_spec(spec: ExperimentSpec) -> dict[str, Any]:
    payload = spec.model_dump(mode="json")
    dataset = dict(payload["dataset"])
    dataset["kind"] = "csv"
    dataset["path"] = "data/input.csv"
    payload["dataset"] = dataset
    return payload


def _write_environment(
    *,
    output: Path,
    repository_root: str | Path | None,
    created_at: str,
) -> Path:
    payload = {
        "created_at_utc": created_at,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "code_revision": detect_git_revision(repository_root),
        "dependency_versions": dependency_versions(
            ("numpy", "pandas", "scikit-learn", "scipy", "pydantic")
        ),
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output


def _write_candidate_metadata(
    *,
    spec: ExperimentSpec,
    output_directory: Path,
    created_at: str,
) -> dict[str, str]:
    metadata_root = output_directory / "metadata"
    metadata_root.mkdir(parents=True, exist_ok=True)
    release_date = created_at[:10]

    citation_path = metadata_root / "CITATION.cff"
    citation = f"""cff-version: 1.2.0
message: "If you use this experiment bundle, cite the software repository and the reviewed release."
title: "{spec.title.replace('"', "'")}"
type: dataset
version: "{spec.release.version}"
date-released: "{release_date}"
authors:
  - family-names: "Kowsari"
    given-names: "Faramarz"
    orcid: "https://orcid.org/0000-0003-1692-0453"
repository-code: "https://github.com/FaramarzKowsari/heatsafe-climate-air-quality-lab"
license: "{spec.release.license}"
"""
    citation_path.write_text(citation, encoding="utf-8")

    zenodo_path = metadata_root / "zenodo-candidate.json"
    zenodo = {
        "title": spec.title,
        "description": spec.description,
        "creators": [
            {
                "name": "Kowsari, Faramarz",
                "orcid": "0000-0003-1692-0453",
            }
        ],
        "version": spec.release.version,
        "publication_date": release_date,
        "upload_type": "dataset",
        "license": spec.release.license,
        "keywords": list(spec.report.keywords),
        "related_identifiers": [
            {
                "identifier": (
                    "https://github.com/FaramarzKowsari/"
                    "heatsafe-climate-air-quality-lab"
                ),
                "relation": "isSupplementTo",
                "resource_type": "software",
            }
        ],
        "notes": (
            "Candidate metadata only. Review the artifacts and create a tagged "
            "scientific release before minting a DOI."
        ),
    }
    zenodo_path.write_text(
        json.dumps(zenodo, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "citation": str(citation_path),
        "zenodo_candidate": str(zenodo_path),
    }


def _write_reproduction_files(output_directory: Path) -> dict[str, str]:
    shell_path = output_directory / "reproduce.sh"
    shell_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'heatsafe-experiment run --spec experiment-spec.json '
        '--output reproduced-run --repository-root . --overwrite\n'
        "heatsafe-experiment verify reproduced-run\n",
        encoding="utf-8",
    )

    command_path = output_directory / "reproduce.cmd"
    command_path.write_text(
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "heatsafe-experiment run --spec experiment-spec.json "
        "--output reproduced-run --repository-root . --overwrite\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "heatsafe-experiment verify reproduced-run\r\n",
        encoding="utf-8",
    )

    readme_path = output_directory / "README.md"
    readme_path.write_text(
        "# Reproducible Experiment Bundle\n\n"
        "This directory is self-contained. It includes a canonical CSV input, "
        "the normalized experiment specification, complete model metrics, "
        "paper-ready reports, SVG figures, provenance records and SHA-256 checksums.\n\n"
        "## Reproduce\n\n"
        "```bash\n"
        "bash reproduce.sh\n"
        "```\n\n"
        "On Windows, run `reproduce.cmd`.\n\n"
        "## Verify\n\n"
        "```bash\n"
        "heatsafe-experiment verify .\n"
        "```\n\n"
        "The archive is a candidate research artifact. It does not automatically "
        "mint or claim a DOI.\n",
        encoding="utf-8",
    )

    return {
        "shell": str(shell_path),
        "windows": str(command_path),
        "readme": str(readme_path),
    }


def verify_experiment_directory(path: str | Path) -> dict[str, Any]:
    return verify_checksums(path)


def run_experiment(
    spec: ExperimentSpec,
    *,
    spec_path: str | Path,
    output_directory: str | Path,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
) -> ExperimentRunResult:
    output_root = Path(output_directory)
    _prepare_output(output_root, overwrite=overwrite)
    created_at = datetime.now(UTC).isoformat()

    original_spec = output_root / "experiment-spec.original.json"
    original_spec.write_text(spec.model_dump_json(indent=2), encoding="utf-8")

    reproduction_spec = output_root / "experiment-spec.json"
    reproduction_spec.write_text(
        json.dumps(_self_contained_spec(spec), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    canonical_input = output_root / "data/input.csv"
    frame, dataset_descriptor = load_experiment_frame(
        spec,
        spec_path=spec_path,
        canonical_output=canonical_input,
    )
    descriptor_path = output_root / "data/dataset-descriptor.json"
    descriptor_path.write_text(
        json.dumps(dataset_descriptor, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = run_nexus_benchmark(frame, spec.nexus)
    nexus_paths = write_nexus_artifacts(
        report,
        output_directory=output_root / "nexus",
        config=spec.nexus,
        input_paths=(reproduction_spec, canonical_input),
        repository_root=repository_root,
    )
    table_paths = write_paper_tables(report, output_root / "tables")
    figure_paths = write_paper_figures(report, output_root / "figures")
    report_paths = write_paper_reports(
        spec=spec,
        report=report,
        dataset_descriptor=dataset_descriptor,
        output_directory=output_root / "report",
    )

    environment_path = _write_environment(
        output=output_root / "metadata/environment.json",
        repository_root=repository_root,
        created_at=created_at,
    )
    candidate_paths = _write_candidate_metadata(
        spec=spec,
        output_directory=output_root,
        created_at=created_at,
    )
    reproduction_paths = _write_reproduction_files(output_root)

    summary_path = output_root / "run-summary.json"
    summary = {
        "experiment_id": spec.experiment_id,
        "title": spec.title,
        "created_at_utc": created_at,
        "created_by": spec.created_by,
        "release_version": spec.release.version,
        "release_status": spec.release.status,
        "dataset": dataset_descriptor,
        "target": report.target,
        "horizons": report.horizons,
        "best_by_horizon": report.best_by_horizon,
        "paper_report": report_paths,
        "tables": table_paths,
        "figures": figure_paths,
        "nexus": nexus_paths,
        "candidate_metadata": candidate_paths,
        "reproduction": reproduction_paths,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_outputs = [
        summary_path,
        Path(report_paths["html"]),
        Path(report_paths["markdown"]),
        Path(table_paths["all_model_metrics"]),
        Path(table_paths["best_by_horizon"]),
        Path(figure_paths["best_mae"]),
        Path(figure_paths["coverage"]),
        Path(figure_paths["event_f1"]),
        Path(nexus_paths["report"]),
        Path(nexus_paths["leaderboard"]),
        environment_path,
        Path(candidate_paths["citation"]),
        Path(candidate_paths["zenodo_candidate"]),
    ]
    manifest = build_experiment_manifest(
        f"orchestrator-{spec.experiment_id}",
        configuration=_self_contained_spec(spec),
        input_paths=(reproduction_spec, canonical_input),
        output_paths=manifest_outputs,
        random_seed=spec.nexus.random_state,
        notes=(
            "Paper-ready orchestrated experiment.",
            "All model results are retained.",
            "No paid AI API is used.",
            *spec.notes,
        ),
        repository_root=repository_root,
    )
    orchestration_manifest = write_experiment_manifest(
        manifest,
        output_root / "orchestration-manifest.json",
    )

    categories = {
        "specification": [
            "experiment-spec.json",
            "experiment-spec.original.json",
        ],
        "data": [
            "data/input.csv",
            "data/dataset-descriptor.json",
        ],
        "nexus": [
            Path(value).relative_to(output_root).as_posix()
            for value in nexus_paths.values()
        ],
        "tables": [
            Path(value).relative_to(output_root).as_posix()
            for value in table_paths.values()
        ],
        "figures": [
            Path(value).relative_to(output_root).as_posix()
            for value in figure_paths.values()
        ],
        "reports": [
            Path(value).relative_to(output_root).as_posix()
            for value in report_paths.values()
        ],
        "metadata": [
            environment_path.relative_to(output_root).as_posix(),
            Path(candidate_paths["citation"]).relative_to(output_root).as_posix(),
            Path(candidate_paths["zenodo_candidate"]).relative_to(output_root).as_posix(),
            orchestration_manifest.relative_to(output_root).as_posix(),
        ],
        "reproduction": [
            Path(value).relative_to(output_root).as_posix()
            for value in reproduction_paths.values()
        ],
    }
    write_artifact_index(
        output_root,
        experiment_id=spec.experiment_id,
        categories=categories,
    )

    expected_files = len(list(iter_bundle_files(output_root))) + 1
    verification_path = output_root / "verification.json"
    verification_path.write_text(
        json.dumps(
            {
                "policy": "SHA-256 for every non-release artifact",
                "expected_files": expected_files,
                "verification_command": "heatsafe-experiment verify .",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    checksum_path = write_checksums(output_root)
    verification = verify_checksums(output_root)
    if not verification["valid"]:
        raise RuntimeError(
            "Generated experiment failed checksum verification: "
            + "; ".join(str(item) for item in verification["failures"])
        )

    release_archive: Path | None = None
    if spec.release.create_zip:
        release_archive = create_deterministic_archive(
            output_root,
            archive_name=(
                f"{spec.experiment_id}-{spec.release.version}-candidate.zip"
            ),
        )

    return ExperimentRunResult(
        experiment_id=spec.experiment_id,
        output_directory=str(output_root),
        report_html=report_paths["html"],
        report_markdown=report_paths["markdown"],
        checksums=str(checksum_path),
        verification=str(verification_path),
        release_archive=str(release_archive) if release_archive else None,
        best_by_horizon=report.best_by_horizon,
    )
