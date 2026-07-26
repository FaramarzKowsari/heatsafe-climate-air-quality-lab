from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.quality import assess_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import verify_snapshot


router = APIRouter(prefix="/api/v1/data", tags=["data-foundation"])


class QualityRequest(BaseModel):
    observations: list[NormalizedObservation] = Field(min_length=1, max_length=100_000)


class SnapshotVerifyRequest(BaseModel):
    directory: str


@router.get("/sources")
def list_sources() -> list[dict[str, object]]:
    return [source.model_dump(mode="json") for source in DEFAULT_REGISTRY.list()]


@router.get("/sources/{source_id}")
def get_source(source_id: str) -> dict[str, object]:
    try:
        source = DEFAULT_REGISTRY.get(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return source.model_dump(mode="json")


@router.post("/quality")
def quality(payload: QualityRequest) -> dict[str, object]:
    return assess_observations(payload.observations).model_dump(mode="json")


@router.post("/snapshot/verify")
def snapshot_verify(payload: SnapshotVerifyRequest) -> dict[str, object]:
    path = Path(payload.directory).expanduser().resolve()
    try:
        return verify_snapshot(path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
