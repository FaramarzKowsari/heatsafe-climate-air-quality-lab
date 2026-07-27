from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from heatsafe.core.models import MeasurementType, NormalizedObservation
from heatsafe.data_foundation.official_snapshots.contracts import (
    OfficialSnapshotConfig,
    QualityGateConfig,
)
from heatsafe.data_foundation.official_snapshots.pipeline import (
    evaluate_quality_gate,
    freeze_official_snapshot,
)
from heatsafe.research.benchmark_registry.contracts import DatasetCard
from heatsafe.research.benchmark_registry.registry import read_registry_index


def _observations() -> list[NormalizedObservation]:
    start = datetime(2025, 7, 1, tzinfo=UTC)
    return [
        NormalizedObservation(
            source_name="US EPA AQS",
            source_dataset="AQS Sample Data by County",
            source_record_id=f"06-001-0001:88101:{index}",
            station_id="06-001-0001",
            latitude=37.8,
            longitude=-122.3,
            country="US",
            region="California",
            city="Oakland",
            timestamp_utc=start + timedelta(hours=index),
            timestamp_local=None,
            timezone="UTC",
            variable="pm25",
            value=10.0 + index,
            unit="ug/m3",
            measurement_type=MeasurementType.OBSERVED,
            quality_flag="sample_duration=1 HOUR;qualifier=none",
            data_status="available",
            retrieved_at=start + timedelta(days=1),
            license="United States government data; retain EPA AQS metadata",
            source_url="https://aqs.epa.gov/aqsweb/documents/data_api.html",
        )
        for index in range(4)
    ]


def _config() -> OfficialSnapshotConfig:
    return OfficialSnapshotConfig(
        source_id="epa-aqs",
        dataset_id="epa-aqs-oakland-pm25-demo",
        version="1.0.0",
        title="EPA AQS Oakland PM2.5 demonstration snapshot",
        description=(
            "A deterministic normalized fixture that exercises immutable "
            "snapshot registration without performing a live network request."
        ),
        target_variables=("pm25",),
        station_selection_protocol="Use the predetermined AQS site 06-001-0001.",
        quality_control_protocol="Preserve AQS flags and run deterministic range checks.",
        missing_data_policy="No imputation is performed in the frozen fixture.",
        known_limitations=(
            "The fixture validates software behavior and is not a scientific result.",
        ),
        tags=("epa", "pm25", "software-fixture"),
        country="US",
        region="California",
        city="Oakland",
        request_parameters={
            "parameter_code": "88101",
            "begin_date": "2025-07-01",
            "end_date": "2025-07-01",
            "state_code": "06",
            "county_code": "001",
            "city": "Oakland",
            "country": "US",
        },
        quality_gate=QualityGateConfig(
            minimum_observations=4,
            minimum_unique_fraction=1.0,
            minimum_quality_score=1.0,
            maximum_errors=0,
            minimum_records_per_target=4,
        ),
    )


def test_freeze_creates_snapshot_card_index_and_release(tmp_path: Path) -> None:
    output_root = tmp_path / "snapshots"
    registry_root = tmp_path / "registry"

    release = freeze_official_snapshot(
        _observations(),
        config=_config(),
        output_root=output_root,
        registry_root=registry_root,
    )

    assert release.quality_gate.passed is True
    assert release.snapshot_integrity["valid"] is True
    assert release.registry_integrity["valid"] is True
    assert Path(release.benchmark_table_path).is_file()
    assert Path(release.dataset_card_path).is_file()
    assert Path(release.registry_index_path).is_file()

    card = DatasetCard.model_validate_json(
        Path(release.dataset_card_path).read_text(encoding="utf-8")
    )
    assert card.status == "verified"
    assert card.target_variables == ("pm25",)
    assert card.spatial.cities == ("Oakland",)
    assert len(card.artifacts) == 5

    index = read_registry_index(release.registry_index_path)
    assert len(index.datasets) == 1
    assert index.datasets[0].identifier == card.dataset_id

    release_files = list((registry_root / "snapshot-releases").glob("*.json"))
    assert len(release_files) == 1
    payload = json.loads(release_files[0].read_text(encoding="utf-8"))
    assert payload["scientific_boundary"]


def test_quality_gate_failure_is_explicit() -> None:
    config = _config().model_copy(
        update={
            "quality_gate": QualityGateConfig(
                minimum_observations=10,
                minimum_records_per_target=10,
            )
        }
    )
    result = evaluate_quality_gate(_observations(), config)
    assert result.passed is False
    assert any("minimum_observations" in reason for reason in result.reasons)
    assert any("target 'pm25'" in reason for reason in result.reasons)
