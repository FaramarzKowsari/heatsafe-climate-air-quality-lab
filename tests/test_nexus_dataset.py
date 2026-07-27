from __future__ import annotations

from datetime import UTC, datetime

from heatsafe.core.models import MeasurementType, NormalizedObservation
from heatsafe.research.nexus.dataset import observations_to_hourly_frame


def make_observation(hour: int, variable: str, value: float, station: str = "A") -> NormalizedObservation:
    return NormalizedObservation(
        source_name="Test",
        source_dataset="Synthetic",
        source_record_id=f"{station}-{hour}-{variable}",
        station_id=station,
        latitude=41.0,
        longitude=29.0,
        timestamp_utc=datetime(2026, 1, 1, hour, tzinfo=UTC),
        timezone="UTC",
        variable=variable,
        value=value,
        unit="test-unit",
        measurement_type=MeasurementType.SYNTHETIC,
        quality_flag="synthetic",
        retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
        license="CC0-1.0",
        source_url="https://example.org",
    )


def test_observations_are_pivoted_by_variable() -> None:
    observations = [
        make_observation(0, "pm25", 10),
        make_observation(0, "temperature_c", 20),
        make_observation(1, "pm25", 11),
        make_observation(1, "temperature_c", 21),
    ]
    frame = observations_to_hourly_frame(
        observations,
        variables=("pm25", "temperature_c"),
        station_id="A",
    )
    assert list(frame.columns) == ["timestamp", "pm25", "temperature_c"]
    assert len(frame) == 2


def test_multiple_stations_require_selection() -> None:
    observations = [
        make_observation(0, "pm25", 10, station="A"),
        make_observation(0, "pm25", 20, station="B"),
    ]
    try:
        observations_to_hourly_frame(observations, variables=("pm25",))
    except ValueError as exc:
        assert "Multiple stations" in str(exc)
    else:
        raise AssertionError("Multiple stations should require explicit selection")
