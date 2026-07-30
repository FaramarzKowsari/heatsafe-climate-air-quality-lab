from __future__ import annotations

import hashlib
import json
from pathlib import Path

from heatsafe.research.release_review import publication


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_harmonized_release(tmp_path: Path) -> Path:
    release = (
        tmp_path
        / "artifacts/releases/"
        "epa-airdata-california-pm25-2025-first-real-reviewed"
    )
    metadata = release / "metadata"
    metadata.mkdir(parents=True)

    summary = {
        "release_id": (
            "epa-airdata-california-pm25-2025-first-real-reviewed"
        ),
        "release_version": "0.1.0",
        "public_experiment_id": (
            "epa-airdata-california-pm25-2025-first-real-bulk"
        ),
        "source_execution_id": (
            "epa-aqs-alameda-pm25-2025-first-real-bulk"
        ),
        "selected_geography": {
            "state_code": "06",
            "state_name": "California",
            "county_code": "073",
            "county_name": "San Diego",
        },
        "selected_station": "06-073-1201",
        "selected_segment_rows": 3998,
        "time_basis": {
            "local_timezone": "America/Los_Angeles",
            "segment_start_utc": "2025-07-18T18:00:00+00:00",
            "segment_end_utc": "2026-01-01T07:00:00+00:00",
            "segment_start_local": "2025-07-18T11:00:00-07:00",
            "segment_end_local": "2025-12-31T23:00:00-08:00",
        },
        "best_by_horizon": {
            "1": "persistence",
            "6": "ridge",
            "24": "random_forest",
        },
        "keywords": [
            "US EPA AirData",
            "PM2.5",
            "San Diego County",
            "California",
        ],
    }
    _write_json(release / "release-summary.json", summary)
    _write_json(
        metadata / "final-publication-metadata.json",
        {
            "title": "San Diego PM2.5 benchmark",
            "description": "Verified station-level benchmark.",
            "doi": None,
            "doi_minted": False,
        },
    )
    _write_json(
        metadata / "identifier-crosswalk.json",
        {
            "public_release_id": summary["release_id"],
            "public_experiment_id": summary["public_experiment_id"],
            "source_execution_id": summary["source_execution_id"],
        },
    )
    _write_json(metadata / "time-basis.json", summary["time_basis"])
    _write_json(
        metadata / "zenodo-deposition.json",
        {
            "metadata": {
                "title": "San Diego PM2.5 benchmark",
                "upload_type": "dataset",
                "description": "Verified station-level benchmark.",
            }
        },
    )
    (metadata / "CITATION.cff").write_text(
        "cff-version: 1.2.0\ntitle: San Diego benchmark\n",
        encoding="utf-8",
    )

    archive = release.with_name(
        "epa-airdata-california-pm25-2025-first-real-reviewed-v0.1.0.zip"
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"deterministic-scientific-archive")
    return release


def test_prepare_draft_only_publication_handoff(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release = _make_harmonized_release(tmp_path)
    monkeypatch.setattr(
        publication,
        "verify_harmonized_release",
        lambda _: {"valid": True, "failures": []},
    )

    output = tmp_path / "publication-handoff"
    result = publication.prepare_publication_handoff(
        release,
        output_directory=output,
    )

    handoff = json.loads(
        (output / "PUBLICATION_HANDOFF.json").read_text(
            encoding="utf-8"
        )
    )
    assert handoff["github_release_mode"] == "draft-only"
    assert handoff["zenodo_mode"] == "draft-only"
    assert handoff["publishing_enabled"] is False
    assert handoff["doi_minted"] is False
    assert handoff["tag"] == "epa-pm25-2025-v0.1.0"
    assert handoff["selected_station"] == "06-073-1201"

    archive_path = Path(handoff["archive"]["path"])
    assert archive_path.is_file()
    assert handoff["archive"]["sha256"] == hashlib.sha256(
        archive_path.read_bytes()
    ).hexdigest()

    script = (
        output / "CREATE_GITHUB_DRAFT_RELEASE_09.cmd"
    ).read_text(encoding="ascii")
    assert "--draft" in script
    assert "--draft=false" not in script
    assert "CREATE-DRAFT" in script
    assert "actions/publish" not in script.lower()

    sequence = (output / "PUBLICATION_SEQUENCE.md").read_text(
        encoding="utf-8"
    )
    assert "Do not publish either draft" in sequence
    assert "DOI-injection" in sequence

    assert result["verification"]["valid"] is True
    assert publication.verify_publication_handoff(output)["valid"] is True


def test_handoff_detects_tampering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release = _make_harmonized_release(tmp_path)
    monkeypatch.setattr(
        publication,
        "verify_harmonized_release",
        lambda _: {"valid": True, "failures": []},
    )
    output = tmp_path / "publication-handoff"
    publication.prepare_publication_handoff(
        release,
        output_directory=output,
    )

    (output / "GITHUB_RELEASE_NOTES.md").write_text(
        "tampered",
        encoding="utf-8",
    )
    verification = publication.verify_publication_handoff(output)
    assert verification["valid"] is False
    assert any(
        "Checksum mismatch: GITHUB_RELEASE_NOTES.md" in str(item)
        for item in verification["failures"]
    )


def test_handoff_rejects_non_draft_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release = _make_harmonized_release(tmp_path)
    monkeypatch.setattr(
        publication,
        "verify_harmonized_release",
        lambda _: {"valid": True, "failures": []},
    )
    output = tmp_path / "publication-handoff"
    publication.prepare_publication_handoff(
        release,
        output_directory=output,
    )

    handoff_path = output / "PUBLICATION_HANDOFF.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["publishing_enabled"] = True
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")

    verification = publication.verify_publication_handoff(output)
    assert verification["valid"] is False
    assert "Publishing must remain disabled" in verification["failures"]
