from __future__ import annotations

import json
from pathlib import Path

import pytest

from heatsafe.research.release_review import doi_finalizer


DOI = "10.5281/zenodo.21710054"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_harmonized_release(root: Path) -> Path:
    release = root / "harmonized-release"
    (release / "metadata").mkdir(parents=True)
    (release / "experiment/report").mkdir(parents=True)

    _write_json(
        release / "release-summary.json",
        {
            "release_id": (
                "epa-airdata-california-pm25-2025-first-real-reviewed"
            ),
            "release_version": "0.1.0",
            "release_status": (
                "final-metadata-harmonized-reviewed-candidate"
            ),
            "doi_minted": False,
            "public_experiment_id": (
                "epa-airdata-california-pm25-2025-first-real-bulk"
            ),
            "source_execution_id": (
                "epa-aqs-alameda-pm25-2025-first-real-bulk"
            ),
            "selected_geography": {
                "county_name": "San Diego",
                "state_name": "California",
            },
            "selected_station": "06-073-1201",
            "selected_segment_rows": 3998,
            "time_basis": {
                "segment_start_utc": "2025-07-18T18:00:00+00:00",
                "segment_end_utc": "2026-01-01T07:00:00+00:00",
                "segment_start_local": "2025-07-18T11:00:00-07:00",
                "segment_end_local": "2025-12-31T23:00:00-08:00",
                "local_timezone": "America/Los_Angeles",
            },
        },
    )
    (release / "release-summary.html").write_text(
        "<html><body><main><h1>Release</h1></main></body></html>",
        encoding="utf-8",
    )
    for name in (
        "README.md",
        "RELEASE_NOTES.md",
        "REVIEW_CHECKLIST.md",
        "PUBLICATION_LIMITATIONS.md",
    ):
        (release / name).write_text(f"# {name}\n", encoding="utf-8")

    (release / "metadata/CITATION.cff").write_text(
        'cff-version: 1.2.0\nversion: "0.1.0"\ntype: dataset\n',
        encoding="utf-8",
    )
    _write_json(
        release / "metadata/final-publication-metadata.json",
        {"title": "San Diego benchmark", "doi": None},
    )
    _write_json(
        release / "metadata/identifier-crosswalk.json",
        {
            "public_experiment_id": (
                "epa-airdata-california-pm25-2025-first-real-bulk"
            )
        },
    )
    _write_json(
        release / "metadata/time-basis.json",
        {
            "segment_start_utc": "2025-07-18T18:00:00+00:00",
            "segment_end_utc": "2026-01-01T07:00:00+00:00",
            "segment_start_local": "2025-07-18T11:00:00-07:00",
            "segment_end_local": "2025-12-31T23:00:00-08:00",
            "local_timezone": "America/Los_Angeles",
        },
    )
    _write_json(
        release / "metadata/zenodo-deposition.json",
        {"metadata": {"notes": "Reviewed candidate."}},
    )
    _write_json(
        release / "metadata/zenodo-github-template.json",
        {"notes": "Reviewed candidate."},
    )
    _write_json(
        release / "metadata/datacite-metadata.json",
        {
            "data": {
                "type": "dois",
                "attributes": {"event": "publish"},
            }
        },
    )
    _write_json(
        release / "metadata/release-manifest.json",
        {
            "release_id": (
                "epa-airdata-california-pm25-2025-first-real-reviewed"
            ),
            "publication_gate": {
                "automatic_publish": False,
            },
        },
    )
    (release / "experiment/report/report.html").write_text(
        "<html><body><h1>Report</h1></body></html>",
        encoding="utf-8",
    )
    (release / "experiment/report/report.md").write_text(
        "# Report\n",
        encoding="utf-8",
    )
    return release


def _make_publication_handoff(root: Path) -> Path:
    handoff = root / "publication-handoff"
    assets = handoff / "assets"
    assets.mkdir(parents=True)
    for name in (
        "old-release.zip",
        "SHA256SUMS.txt",
        "CITATION.cff",
        "final-publication-metadata.json",
        "identifier-crosswalk.json",
        "time-basis.json",
        "zenodo-deposition.json",
        "release-summary.json",
    ):
        (assets / name).write_text("old\n", encoding="utf-8")

    (handoff / "GITHUB_RELEASE_NOTES.md").write_text(
        "# Release\n\n"
        "**DOI:** Pending Zenodo draft review and publication\n\n"
        "- `epa-airdata-california-pm25-2025-first-real-reviewed-v0.1.0.zip`\n\n"
        "Archive SHA-256:\n\n```text\n"
        + "0" * 64
        + "\n```\n",
        encoding="utf-8",
    )
    for name in (
        "PUBLICATION_READINESS.html",
        "PUBLICATION_HANDOFF.json",
        "PUBLICATION_SEQUENCE.md",
        "ZENODO_DRAFT_FORM_GUIDE.md",
        "CREATE_GITHUB_DRAFT_RELEASE_09.cmd",
        "OPEN_GITHUB_RELEASE_PAGE_09.cmd",
        "OPEN_ZENODO_DRAFT_09.cmd",
        "RESERVED_DOI.txt",
    ):
        (handoff / name).write_text("draft\n", encoding="utf-8")
    return handoff


def test_normalize_reserved_doi() -> None:
    assert doi_finalizer.normalize_reserved_doi(DOI) == DOI
    assert doi_finalizer.normalize_reserved_doi(
        f"https://doi.org/{DOI}"
    ) == DOI
    with pytest.raises(ValueError):
        doi_finalizer.normalize_reserved_doi(
            "10.1234/example"
        )


def test_finalize_release_and_handoff(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_release = _make_harmonized_release(tmp_path)
    source_handoff = _make_publication_handoff(tmp_path)

    monkeypatch.setattr(
        doi_finalizer,
        "verify_harmonized_release",
        lambda _: {"valid": True, "failures": []},
    )
    monkeypatch.setattr(
        doi_finalizer,
        "verify_publication_handoff",
        lambda _: {"valid": True, "failures": []},
    )

    release_output = tmp_path / "doi-final-release"
    release_result = (
        doi_finalizer.finalize_reserved_doi_release(
            source_release,
            output_directory=release_output,
            reserved_doi=DOI,
        )
    )

    assert release_result["verification"]["valid"] is True
    assert Path(release_result["release_archive"]).is_file()
    summary = json.loads(
        (release_output / "release-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["doi"] == DOI
    assert summary["doi_reserved"] is True
    assert summary["doi_registered"] is False
    assert f'doi: "{DOI}"' in (
        release_output / "metadata/CITATION.cff"
    ).read_text(encoding="utf-8")
    assert DOI in (
        release_output / "experiment/report/report.html"
    ).read_text(encoding="utf-8")

    handoff_output = tmp_path / "doi-final-handoff"
    handoff_result = (
        doi_finalizer.finalize_reserved_doi_handoff(
            source_handoff,
            doi_final_release=release_output,
            output_directory=handoff_output,
            reserved_doi=DOI,
        )
    )

    assert handoff_result["verification"]["valid"] is True
    assert DOI in (
        handoff_output / "GITHUB_RELEASE_NOTES.md"
    ).read_text(encoding="utf-8")
    assert (
        handoff_output
        / "assets/"
        "epa-airdata-california-pm25-2025-first-real-reviewed-"
        "v0.1.0-doi-final.zip"
    ).is_file()
    handoff = json.loads(
        (
            handoff_output / "DOI_FINALIZATION_HANDOFF.json"
        ).read_text(encoding="utf-8")
    )
    assert handoff["reserved_doi"] == DOI
    assert handoff["doi_registered"] is False


def test_doi_final_release_detects_tampering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_release = _make_harmonized_release(tmp_path)
    monkeypatch.setattr(
        doi_finalizer,
        "verify_harmonized_release",
        lambda _: {"valid": True, "failures": []},
    )

    output = tmp_path / "doi-final-release"
    doi_finalizer.finalize_reserved_doi_release(
        source_release,
        output_directory=output,
        reserved_doi=DOI,
    )
    (output / "README.md").write_text(
        "tampered",
        encoding="utf-8",
    )

    verification = doi_finalizer.verify_doi_final_release(
        output,
        reserved_doi=DOI,
    )
    assert verification["valid"] is False
    assert any(
        "Checksum mismatch: README.md" in str(item)
        for item in verification["failures"]
    )
