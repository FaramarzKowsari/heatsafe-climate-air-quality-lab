from __future__ import annotations

from fastapi import APIRouter, HTTPException

from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionPlan,
    OfficialSnapshotConfig,
)
from heatsafe.data_foundation.official_snapshots.planning import (
    build_acquisition_plan,
)
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY


router = APIRouter(
    prefix="/api/v1/official-snapshots",
    tags=["official-snapshots"],
)


@router.get("/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "paid_ai_api_required": False,
        "live_downloads_in_ci": False,
        "supports": [
            "secret-free acquisition plans",
            "NOAA CDO live connector",
            "US EPA AQS live connector",
            "NASA FIRMS live connector",
            "EEA local Parquet normalization",
            "ERA5-Land request specifications",
            "immutable snapshots",
            "automated Dataset Cards",
            "quality gates",
            "benchmark-table export",
            "registry indexing",
        ],
        "scientific_boundary": (
            "Snapshot verification establishes integrity and declared quality "
            "gates; it does not establish representativeness or official "
            "warning authority."
        ),
    }


@router.post("/plan", response_model=AcquisitionPlan)
def plan(config: OfficialSnapshotConfig) -> AcquisitionPlan:
    try:
        source = DEFAULT_REGISTRY.get(config.source_id)
        return build_acquisition_plan(config, source)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
