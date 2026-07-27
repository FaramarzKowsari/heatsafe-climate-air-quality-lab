from __future__ import annotations

from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
    OfficialSnapshotConfig,
    QualityGateConfig,
)
from heatsafe.data_foundation.official_snapshots.planning import (
    build_acquisition_plan,
)
from heatsafe.data_foundation.official_snapshots.recipes import (
    ERA5Request,
    sanitize_parameters,
)
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY


def _config(source_id: str, parameters: dict[str, object]) -> OfficialSnapshotConfig:
    return OfficialSnapshotConfig(
        source_id=source_id,
        dataset_id="official-demo",
        version="1.0.0",
        title="Official environmental demonstration snapshot",
        description=(
            "A deterministic configuration used to validate the official "
            "snapshot software pipeline."
        ),
        target_variables=("pm25",),
        station_selection_protocol="Use the predetermined official monitoring location.",
        quality_control_protocol="Preserve provider flags and run HeatSafe quality checks.",
        missing_data_policy="Do not impute the immutable normalized snapshot.",
        known_limitations=("Software fixtures are not scientific evidence.",),
        request_parameters=parameters,
        quality_gate=QualityGateConfig(minimum_observations=1),
    )


def test_sensitive_parameters_are_redacted_recursively() -> None:
    sanitized = sanitize_parameters(
        {
            "api_key": "secret",
            "nested": {"authorization": "Bearer secret", "station": "A"},
            "items": [{"email": "person@example.org"}, {"value": 3}],
        }
    )
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["station"] == "A"
    assert sanitized["items"][0]["email"] == "[REDACTED]"


def test_era5_plan_is_explicit_and_not_claimed_as_downloaded() -> None:
    config = _config(
        "era5-land",
        {
            "years": [2025],
            "months": [7],
            "days": [1, 2],
            "hours": [0, 12],
            "area": [42, 26, 36, 45],
        },
    )
    plan = build_acquisition_plan(
        config,
        DEFAULT_REGISTRY.get("era5-land"),
    )
    assert plan.acquisition_mode == AcquisitionMode.REQUEST_SPEC
    assert plan.executable_by_heatsafe is False
    cds_request = plan.sanitized_request_parameters["cds_request"]
    assert cds_request["year"] == ["2025"]
    assert cds_request["time"] == ["00:00", "12:00"]


def test_era5_request_model_builds_cds_payload() -> None:
    recipe = ERA5Request(
        years=(2024, 2025),
        months=(6,),
        days=(1,),
        hours=(3, 15),
        area=(50, -10, 35, 30),
    )
    payload = recipe.to_cds_request()
    assert payload["year"] == ["2024", "2025"]
    assert payload["area"] == [50.0, -10.0, 35.0, 30.0]
