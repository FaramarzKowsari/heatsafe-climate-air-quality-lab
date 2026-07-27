from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from heatsafe.research.benchmark_registry.contracts import DatasetCard
from heatsafe.research.benchmark_registry.validation import verify_dataset_snapshot


router = APIRouter(prefix="/api/v1/benchmark-registry", tags=["benchmark-registry"])


class VerifySnapshotRequest(BaseModel):
    card: DatasetCard
    snapshot_root: str


@router.get("/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "paid_ai_api_required": False,
        "live_provider_credentials_required_for_verification": False,
        "supports": [
            "dataset-card-validation",
            "sha256-verification",
            "file-size-verification",
            "csv-row-and-column-verification",
            "registry-index-generation",
            "benchmark-release-bundles",
        ],
        "official_sources_registered_elsewhere": [
            "NOAA NCEI",
            "US EPA AQS",
            "European Environment Agency",
            "NASA FIRMS",
            "Copernicus ERA5-Land",
        ],
    }


@router.post("/verify")
def verify(payload: VerifySnapshotRequest) -> dict[str, object]:
    root = Path(payload.snapshot_root)
    if not root.is_dir():
        raise HTTPException(status_code=422, detail="snapshot_root is not a directory")
    return verify_dataset_snapshot(payload.card, root)
