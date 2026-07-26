from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from heatsafe.core.models import MeasurementType, NormalizedObservation
from heatsafe.data_foundation.quality import assess_observations, deduplicate_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import load_observations, verify_snapshot, write_snapshot


def observation(record_id: str = "row-1", value: float = 25.0) -> NormalizedObservation:
    return NormalizedObservation(
        source_name="Test",
        source_dataset="Synthetic test",
        source_record_id=record_id,
        latitude=41.0,
        longitude=29.0,
        timestamp_utc=datetime(2026, 7, 26, tzinfo=UTC),
        timezone="UTC",
        variable="temperature_c",
        value=value,
        unit="°C",
        measurement_type=MeasurementType.SYNTHETIC,
        quality_flag="synthetic_test",
        retrieved_at=datetime(2026, 7, 26, 1, tzinfo=UTC),
        license="CC0-1.0",
        source_url="https://example.org/test",
    )


def test_quality_detects_duplicates() -> None:
    first = observation()
    report = assess_observations([first, first])
    assert report.error_count == 1
    assert report.unique_observation_count == 1
    assert len(deduplicate_observations([first, first])) == 1


def test_snapshot_round_trip(tmp_path: Path) -> None:
    items = [observation()]
    quality = assess_observations(items)
    manifest = write_snapshot(
        tmp_path,
        snapshot_id="test-001",
        source=DEFAULT_REGISTRY.get("noaa-cdo-ghcnd"),
        observations=items,
        quality=quality,
    )
    assert manifest.observation_count == 1
    verification = verify_snapshot(tmp_path)
    assert verification["valid"] is True
    loaded = load_observations(tmp_path)
    assert loaded[0].source_record_id == "row-1"


def test_registry_has_honest_status_levels() -> None:
    assert DEFAULT_REGISTRY.get("noaa-cdo-ghcnd").production_status == "implemented-foundation"
    assert DEFAULT_REGISTRY.get("era5-land").production_status == "request-specification-only"
    assert DEFAULT_REGISTRY.get("turkiye-mgm").production_status == "registry-only"
