from __future__ import annotations

import json
from pathlib import Path

from heatsafe.research.release_review import builder, harmonizer
from heatsafe.research.release_review.contracts import (
    ReviewedReleaseConfig,
)


SOURCE_EXECUTION_ID = "epa-aqs-alameda-pm25-2025-first-real-bulk"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_workspace(root: Path) -> Path:
    workspace = root / "artifacts/local-real-experiments/source"
    experiment = workspace / "experiment"

    _write_json(
        workspace / "real-official-experiment-manifest.json",
        {
            "experiment_id": SOURCE_EXECUTION_ID,
            "bulk_zip_sha256": "6" * 64,
            "selected_station": {"station_id": "06-073-1201"},
        },
    )
    _write_json(
        workspace / "raw-source/bulk-source-report.json",
        {
            "zip_sha256": "6" * 64,
            "requested_geography": {
                "state_code": "06",
                "state_name": "California",
                "county_code": "001",
                "county_name": "Alameda",
            },
            "selected_geography": {
                "state_code": "06",
                "state_name": "California",
                "county_code": "073",
                "county_name": "San Diego",
            },
            "geography_fallback_used": True,
        },
    )
    _write_json(
        workspace / "prepared/station-selection-report.json",
        {
            "selected_station": {"station_id": "06-073-1201"},
            "selected_segment_rows": 3998,
            "selected_segment_start_utc": (
                "2025-07-18T18:00:00+00:00"
            ),
            "selected_segment_end_utc": (
                "2026-01-01T07:00:00+00:00"
            ),
        },
    )
    _write_json(
        experiment / "run-summary.json",
        {
            "experiment_id": SOURCE_EXECUTION_ID,
            "best_by_horizon": {
                "1": "persistence",
                "6": "ridge",
                "24": "random_forest",
            },
        },
    )
    _write_json(
        experiment / "metadata/environment.json",
        {
            "code_revision": "dd82bf8",
            "python_version": "3.13",
        },
    )

    for directory in (
        "report",
        "tables",
        "figures",
        "nexus",
        "metadata",
        "data",
    ):
        (experiment / directory).mkdir(parents=True, exist_ok=True)

    (experiment / "report/report.html").write_text(
        (
            "<html><body><h1>San Diego report</h1>"
            f"<div>Experiment {SOURCE_EXECUTION_ID}</div>"
            "</body></html>"
        ),
        encoding="utf-8",
    )
    (experiment / "report/report.md").write_text(
        f"# Report\n\nExperiment: `{SOURCE_EXECUTION_ID}`\n",
        encoding="utf-8",
    )
    (experiment / "tables/all-model-metrics.csv").write_text(
        "model,mae\npersistence,1\n",
        encoding="utf-8",
    )
    (experiment / "figures/best-mae.svg").write_text(
        "<svg></svg>",
        encoding="utf-8",
    )
    _write_json(experiment / "nexus/report.json", {"status": "ok"})
    (experiment / "metadata/CITATION.cff").write_text(
        "cff-version: 1.2.0\n",
        encoding="utf-8",
    )
    (experiment / "data/input.csv").write_text(
        "timestamp,pm25\n2025-07-18T18:00:00Z,12\n",
        encoding="utf-8",
    )
    _write_json(
        experiment / "data/dataset-descriptor.json",
        {"rows": 3998},
    )
    _write_json(
        experiment / "experiment-spec.json",
        {"experiment_id": SOURCE_EXECUTION_ID},
    )
    _write_json(
        experiment / "experiment-spec.original.json",
        {"experiment_id": SOURCE_EXECUTION_ID},
    )
    return workspace


def _build_source_release(
    tmp_path: Path,
    monkeypatch,
) -> tuple[Path, Path]:
    workspace = _make_workspace(tmp_path)
    monkeypatch.setattr(
        builder,
        "verify_real_official_experiment",
        lambda _: {"valid": True, "failures": []},
    )
    source_release = tmp_path / "artifacts/releases/source-reviewed"
    builder.build_reviewed_release(
        workspace,
        output_directory=source_release,
        config=ReviewedReleaseConfig(),
    )
    return workspace, source_release


def test_harmonize_realistic_san_diego_release(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace, source_release = _build_source_release(
        tmp_path,
        monkeypatch,
    )
    monkeypatch.setattr(
        harmonizer,
        "verify_real_official_experiment",
        lambda _: {"valid": True, "failures": []},
    )

    output = (
        tmp_path
        / "artifacts/releases/"
        "epa-airdata-california-pm25-2025-first-real-reviewed"
    )
    result = harmonizer.harmonize_reviewed_release(
        source_release,
        workspace=workspace,
        output_directory=output,
    )

    summary = json.loads(
        (output / "release-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["release_id"] == (
        harmonizer.DEFAULT_RELEASE_ID
    )
    assert summary["public_experiment_id"] == (
        harmonizer.DEFAULT_PUBLIC_EXPERIMENT_ID
    )
    assert summary["source_execution_id"] == SOURCE_EXECUTION_ID
    assert summary["selected_geography"]["county_name"] == (
        "San Diego"
    )
    assert "San Diego County" in summary["title"]
    assert "Alameda County" not in summary["title"]
    assert summary["selected_station"] == "06-073-1201"
    assert summary["selected_segment_rows"] == 3998
    assert summary["doi_minted"] is False

    time_basis = summary["time_basis"]
    assert time_basis["utc_year_boundary_crossed"] is True
    assert time_basis["segment_end_utc"].startswith(
        "2026-01-01T07:00:00"
    )
    assert time_basis["segment_end_local"].startswith(
        "2025-12-31T23:00:00-08:00"
    )

    citation = (
        output / "metadata/CITATION.cff"
    ).read_text(encoding="utf-8")
    assert "San Diego County" in citation
    assert "Alameda County" not in citation

    zenodo = json.loads(
        (
            output / "metadata/zenodo-github-template.json"
        ).read_text(encoding="utf-8")
    )
    assert "San Diego County" in zenodo["title"]
    assert zenodo["version"] == "0.1.0"

    report = (
        output / "experiment/report/report.html"
    ).read_text(encoding="utf-8")
    assert harmonizer.DEFAULT_PUBLIC_EXPERIMENT_ID in report
    assert SOURCE_EXECUTION_ID in report
    assert "Final metadata harmonization" in report

    crosswalk = json.loads(
        (
            output / "metadata/identifier-crosswalk.json"
        ).read_text(encoding="utf-8")
    )
    assert crosswalk["source_execution_id"] == SOURCE_EXECUTION_ID
    assert crosswalk["public_experiment_id"] == (
        harmonizer.DEFAULT_PUBLIC_EXPERIMENT_ID
    )

    assert result["verification"]["valid"] is True
    assert Path(result["release_archive"]).is_file()
    assert harmonizer.verify_harmonized_release(output)["valid"] is True


def test_harmonized_release_detects_tampering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace, source_release = _build_source_release(
        tmp_path,
        monkeypatch,
    )
    monkeypatch.setattr(
        harmonizer,
        "verify_real_official_experiment",
        lambda _: {"valid": True, "failures": []},
    )

    output = tmp_path / "final-release"
    harmonizer.harmonize_reviewed_release(
        source_release,
        workspace=workspace,
        output_directory=output,
    )
    (output / "README.md").write_text(
        "tampered",
        encoding="utf-8",
    )

    verification = harmonizer.verify_harmonized_release(output)
    assert verification["valid"] is False
    assert any(
        "Checksum mismatch: README.md" in str(item)
        for item in verification["failures"]
    )


def test_pacific_time_fallback_without_tzdata(
    monkeypatch,
) -> None:
    def _missing_zone(_: str):
        raise harmonizer.ZoneInfoNotFoundError("missing tzdata")

    monkeypatch.setattr(harmonizer, "ZoneInfo", _missing_zone)
    basis = harmonizer._time_basis(
        start_utc_text="2025-07-18T18:00:00+00:00",
        end_utc_text="2026-01-01T07:00:00+00:00",
        source_collection_year=2025,
        local_timezone="America/Los_Angeles",
    )

    assert basis["segment_start_local"].startswith(
        "2025-07-18T11:00:00-07:00"
    )
    assert basis["segment_end_local"].startswith(
        "2025-12-31T23:00:00-08:00"
    )
    assert "fallback" in basis["timezone_resolution"]
