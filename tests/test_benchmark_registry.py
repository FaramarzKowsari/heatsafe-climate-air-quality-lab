from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from heatsafe.research.benchmark_registry.contracts import (
    BenchmarkProtocol,
    BenchmarkRelease,
    DatasetCard,
    SnapshotArtifact,
    SourceCitation,
    SpatialCoverage,
    TemporalCoverage,
)
from heatsafe.research.benchmark_registry.hashing import sha256_file
from heatsafe.research.benchmark_registry.registry import build_registry_index
from heatsafe.research.benchmark_registry.release import create_release_bundle
from heatsafe.research.benchmark_registry.validation import (
    load_dataset_card,
    verify_dataset_snapshot,
)


def _card(tmp_path: Path) -> DatasetCard:
    data = tmp_path / "snapshot.csv"
    data.write_text("timestamp,pm25\n2025-01-01T00:00:00Z,12.5\n", encoding="utf-8")
    now = datetime.now(UTC)
    return DatasetCard(
        dataset_id="epa-aqs-demo",
        version="1.0.0",
        title="EPA AQS frozen demonstration snapshot",
        description="A deterministic local fixture representing an immutable official-source snapshot.",
        source_id="epa-aqs",
        role="external-test",
        target_variables=("pm25",),
        units={"pm25": "ug/m3"},
        spatial=SpatialCoverage(countries=("United States",), cities=("Demo City",)),
        temporal=TemporalCoverage(
            start_utc=now - timedelta(days=1),
            end_utc=now,
            nominal_resolution="hourly",
        ),
        station_selection_protocol="Select one predetermined monitoring site.",
        quality_control_protocol="Retain valid observations and preserve source flags.",
        missing_data_policy="Do not impute the immutable raw snapshot.",
        known_limitations=("Fixture data are not scientific evidence.",),
        citation=SourceCitation(
            authority="US EPA",
            dataset_name="Air Quality System",
            homepage="https://www.epa.gov/aqs",
            documentation_url="https://aqs.epa.gov/aqsweb/documents/data_api.html",
            citation_text="US EPA Air Quality System.",
            license_summary="United States government data; provider guidance applies.",
            access_date_utc=now,
        ),
        artifacts=(
            SnapshotArtifact(
                relative_path="snapshot.csv",
                kind="raw",
                media_type="text/csv",
                size_bytes=data.stat().st_size,
                sha256=sha256_file(data),
                rows=1,
                columns=2,
            ),
        ),
        created_at_utc=now,
        status="verified",
        tags=("fixture", "epa"),
    )


def test_snapshot_verification(tmp_path: Path) -> None:
    card = _card(tmp_path)
    report = verify_dataset_snapshot(card, tmp_path)
    assert report["valid"] is True
    assert report["artifacts"][0]["actual_rows"] == 1


def test_snapshot_checksum_failure(tmp_path: Path) -> None:
    card = _card(tmp_path)
    (tmp_path / "snapshot.csv").write_text("changed\n", encoding="utf-8")
    report = verify_dataset_snapshot(card, tmp_path)
    assert report["valid"] is False
    assert any("Checksum mismatch" in item for item in report["failures"])


def test_registry_index_and_release_bundle(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    datasets = registry / "datasets"
    releases = registry / "releases"
    datasets.mkdir(parents=True)
    releases.mkdir(parents=True)

    snapshot_root = tmp_path / "snapshot-root"
    snapshot_root.mkdir()
    card = _card(snapshot_root)
    card_path = datasets / "epa-aqs-demo-1.0.0.json"
    card_path.write_text(card.model_dump_json(indent=2), encoding="utf-8")

    result_file = tmp_path / "leaderboard.csv"
    result_file.write_text("model,mae\nridge,4.2\n", encoding="utf-8")
    now = datetime.now(UTC)
    release = BenchmarkRelease(
        release_id="heatsafe-official-demo",
        version="1.0.0",
        title="HeatSafe official benchmark demonstration",
        dataset_cards=("datasets/epa-aqs-demo-1.0.0.json",),
        protocol=BenchmarkProtocol(
            protocol_id="heatsafe-demo-protocol",
            version="1.0.0",
            title="Demonstration protocol",
            target_variable="pm25",
            forecast_horizons_hours=(1,),
            event_threshold=35.0,
            split_strategy="Chronological",
            external_validation_strategy="Leave-one-city-out",
            models=("persistence", "ridge"),
            metrics=("mae",),
            random_seed=42,
            source_code_revision="abcdef1",
            prohibited_claims=("Official warning authority",),
            created_at_utc=now,
        ),
        result_artifacts=(
            SnapshotArtifact(
                relative_path="leaderboard.csv",
                kind="benchmark-result",
                media_type="text/csv",
                size_bytes=result_file.stat().st_size,
                sha256=sha256_file(result_file),
                rows=1,
                columns=2,
            ),
        ),
        release_notes=("Deterministic demonstration release.",),
        created_at_utc=now,
    )
    release_path = releases / "heatsafe-official-demo-1.0.0.json"
    release_path.write_text(release.model_dump_json(indent=2), encoding="utf-8")

    index = build_registry_index(registry)
    assert len(index.datasets) == 1
    assert len(index.releases) == 1
    assert len(index.registry_sha256) == 64

    bundle = create_release_bundle(
        release,
        registry_root=registry,
        output_directory=tmp_path / "bundle",
    )
    assert Path(bundle["manifest"]).is_file()
    loaded = load_dataset_card(card_path)
    assert loaded.dataset_id == "epa-aqs-demo"
