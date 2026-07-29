from __future__ import annotations

import json
from pathlib import Path

from heatsafe.research.release_review import builder
from heatsafe.research.release_review.contracts import ReviewedReleaseConfig


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_workspace(root: Path) -> Path:
    workspace = root / "artifacts/local-real-experiments/test"
    experiment = workspace / "experiment"

    _write_json(
        workspace / "real-official-experiment-manifest.json",
        {
            "bulk_zip_sha256": "a" * 64,
            "selected_station": {"station_id": "06-001-0007"},
        },
    )
    _write_json(
        workspace / "raw-source/bulk-source-report.json",
        {
            "zip_sha256": "a" * 64,
            "requested_geography": {
                "state_code": "06",
                "county_code": "001",
                "county_name": "Alameda",
            },
            "selected_geography": {
                "state_code": "06",
                "state_name": "California",
                "county_code": "001",
                "county_name": "Alameda",
            },
            "geography_fallback_used": False,
        },
    )
    _write_json(
        workspace / "prepared/station-selection-report.json",
        {
            "selected_station": {"station_id": "06-001-0007"},
            "selected_segment_rows": 720,
            "selected_segment_start_utc": "2025-01-01T00:00:00+00:00",
            "selected_segment_end_utc": "2025-01-30T23:00:00+00:00",
        },
    )
    _write_json(
        experiment / "run-summary.json",
        {"best_by_horizon": {"1": "persistence", "24": "ridge"}},
    )
    _write_json(
        experiment / "metadata/environment.json",
        {"code_revision": "abc123", "python_version": "3.13"},
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
        "<html><body>report</body></html>", encoding="utf-8"
    )
    (experiment / "report/report.md").write_text("# Report", encoding="utf-8")
    (experiment / "tables/all-model-metrics.csv").write_text(
        "model,mae\na,1\n", encoding="utf-8"
    )
    (experiment / "figures/best-mae.svg").write_text(
        "<svg></svg>", encoding="utf-8"
    )
    _write_json(experiment / "nexus/report.json", {"status": "ok"})
    (experiment / "metadata/CITATION.cff").write_text(
        "cff-version: 1.2.0\n", encoding="utf-8"
    )
    (experiment / "data/input.csv").write_text(
        "timestamp,pm25\n2025-01-01T00:00:00Z,12\n",
        encoding="utf-8",
    )
    _write_json(experiment / "data/dataset-descriptor.json", {"rows": 720})
    _write_json(experiment / "experiment-spec.json", {"experiment_id": "test"})
    _write_json(
        experiment / "experiment-spec.original.json",
        {"experiment_id": "test"},
    )
    return workspace


def test_build_reviewed_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = _make_workspace(tmp_path)
    monkeypatch.setattr(
        builder,
        "verify_real_official_experiment",
        lambda _: {"valid": True, "failures": []},
    )

    output = tmp_path / "artifacts/releases/reviewed"
    result = builder.build_reviewed_release(
        workspace,
        output_directory=output,
        config=ReviewedReleaseConfig(),
    )

    assert result.verification["valid"] is True
    assert Path(result.release_archive or "").is_file()
    assert (output / "release-summary.html").is_file()
    assert (output / "metadata/zenodo-deposition.json").is_file()
    assert (output / "metadata/CITATION.cff").is_file()
    assert (output / "checksums.sha256").is_file()

    summary = json.loads(
        (output / "release-summary.json").read_text(encoding="utf-8")
    )
    assert summary["selected_station"] == "06-001-0007"
    assert summary["selected_segment_rows"] == 720
    assert summary["doi_minted"] is False


def test_tampered_release_fails_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = _make_workspace(tmp_path)
    monkeypatch.setattr(
        builder,
        "verify_real_official_experiment",
        lambda _: {"valid": True, "failures": []},
    )
    output = tmp_path / "release"
    builder.build_reviewed_release(
        workspace,
        output_directory=output,
    )

    (output / "README.md").write_text("tampered", encoding="utf-8")
    verification = builder.verify_reviewed_release(output)
    assert verification["valid"] is False
    assert any(
        "Checksum mismatch: README.md" in str(item)
        for item in verification["failures"]
    )
