from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from heatsafe.core.models import MeasurementType, NormalizedObservation
from heatsafe.research.official_experiment.contracts import (
    StationSelectionPolicy,
)
from heatsafe.research.official_experiment.preparation import (
    prepare_hourly_station_frame,
)
from heatsafe.research.official_experiment.runner import (
    write_real_experiment_plan,
)


def _observation(
    station_id: str,
    timestamp: datetime,
    value: float,
    *,
    duration: str = "1 HOUR",
    record_suffix: str = "",
) -> NormalizedObservation:
    return NormalizedObservation(
        source_name="US EPA AQS",
        source_dataset="AQS Sample Data by County",
        source_record_id=(
            f"{station_id}:{timestamp.isoformat()}:{record_suffix}"
        ),
        station_id=station_id,
        latitude=37.8,
        longitude=-122.2,
        country="US",
        region="California",
        city=None,
        timestamp_utc=timestamp,
        timestamp_local=None,
        timezone="UTC",
        variable="pm25",
        value=value,
        unit="Micrograms/cubic meter (LC)",
        measurement_type=MeasurementType.OBSERVED,
        quality_flag=(
            f"sample_duration={duration};"
            "method_code=100;qualifier=none"
        ),
        data_status="available",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        license="United States government data",
        source_url=(
            "https://aqs.epa.gov/aqsweb/documents/data_api.html"
        ),
    )


def test_station_selection_prefers_longest_contiguous_run() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    observations: list[NormalizedObservation] = []

    for hour in range(300):
        observations.append(
            _observation(
                "06-001-0001",
                start + timedelta(hours=hour),
                10.0 + hour % 7,
            )
        )

    for hour in range(420):
        if 130 <= hour < 250:
            continue
        observations.append(
            _observation(
                "06-001-0002",
                start + timedelta(hours=hour),
                15.0 + hour % 5,
            )
        )

    observations.append(
        _observation(
            "06-001-0001",
            start + timedelta(hours=10),
            20.0,
            record_suffix="duplicate-poc",
        )
    )
    observations.append(
        _observation(
            "06-001-0001",
            start + timedelta(hours=301),
            -1.0,
        )
    )

    frame, report = prepare_hourly_station_frame(
        observations,
        StationSelectionPolicy(
            minimum_total_hours=100,
            minimum_contiguous_hours=100,
        ),
    )

    assert report["selected_station"]["station_id"] == "06-001-0001"
    assert report["selected_segment_rows"] == 300
    assert report["duplicate_source_records_collapsed"] == 1
    assert report["negative_or_below_minimum_removed"] == 1
    assert len(frame) == 300
    assert frame["timestamp"].is_monotonic_increasing


def test_duration_filter_falls_back_when_duration_is_unknown() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    observations = [
        _observation(
            "06-001-0001",
            start + timedelta(hours=hour),
            12.0,
            duration="UNKNOWN",
        )
        for hour in range(120)
    ]
    _, report = prepare_hourly_station_frame(
        observations,
        StationSelectionPolicy(
            minimum_total_hours=100,
            minimum_contiguous_hours=100,
        ),
    )
    assert report["duration_filter_fallback_used"] is True


def test_secret_free_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("EPA_AQS_EMAIL", raising=False)
    monkeypatch.delenv("EPA_AQS_KEY", raising=False)

    repository = Path(__file__).resolve().parents[1]
    config = (
        repository
        / "examples/real-experiments/"
        "epa-aqs-alameda-pm25-2025.json"
    )
    output = tmp_path / "plan.json"
    write_real_experiment_plan(config, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source_id"] == "epa-aqs"
    assert set(payload["credential_environment_variables"]) == {
        "EPA_AQS_EMAIL",
        "EPA_AQS_KEY",
    }
    assert payload["credential_values_present"] == {
        "EPA_AQS_EMAIL": False,
        "EPA_AQS_KEY": False,
    }
    serialized = output.read_text(encoding="utf-8")
    assert "DO_NOT_PERSIST_CREDENTIAL" not in serialized
