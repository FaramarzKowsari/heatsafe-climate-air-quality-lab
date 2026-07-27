from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from heatsafe.research.transfer.contracts import ExternalValidationConfig
from heatsafe.research.transfer.engine import run_external_validation


router = APIRouter(
    prefix="/api/v1/external-validation",
    tags=["external-validation"],
)


class ExternalValidationRunRequest(BaseModel):
    timestamps: list[str] = Field(min_length=540, max_length=50_000)
    cities: list[str] = Field(min_length=540, max_length=50_000)
    regions: list[str] = Field(min_length=540, max_length=50_000)
    target_values: list[float | None] = Field(
        min_length=540,
        max_length=50_000,
    )
    covariates: dict[str, list[float | None]] = Field(default_factory=dict)
    target_name: str = "pm25"
    horizons: tuple[int, ...] = (1, 6)
    event_threshold: float = 35.0
    bootstrap_repetitions: int = Field(default=50, ge=20, le=500)
    block_length: int = Field(default=24, ge=2, le=168)
    random_state: int = 42
    models: tuple[str, ...] = ("persistence", "ridge")

    @model_validator(mode="after")
    def equal_lengths(self) -> ExternalValidationRunRequest:
        expected = len(self.timestamps)
        named_lengths = {
            "cities": len(self.cities),
            "regions": len(self.regions),
            "target_values": len(self.target_values),
        }
        invalid = {
            name: length
            for name, length in named_lengths.items()
            if length != expected
        }
        invalid.update(
            {
                name: len(values)
                for name, values in self.covariates.items()
                if len(values) != expected
            }
        )
        if invalid:
            raise ValueError(
                f"Every input vector must have length {expected}: {invalid}"
            )
        return self


@router.get("/capabilities")
def external_validation_capabilities() -> dict[str, object]:
    return {
        "study": "HeatSafe Multi-City External Validation",
        "paid_ai_api_required": False,
        "validation_modes": [
            "leave-one-city-out",
            "leave-one-region-out",
        ],
        "inference": [
            "moving-block-bootstrap",
            "diebold-mariano",
            "split-conformal-intervals",
        ],
        "slices": ["season", "event-intensity"],
    }


@router.post("/run")
def external_validation_run(
    payload: ExternalValidationRunRequest,
) -> dict[str, Any]:
    data: dict[str, object] = {
        "timestamp": payload.timestamps,
        "city": payload.cities,
        "region": payload.regions,
        payload.target_name: payload.target_values,
        **payload.covariates,
    }
    frame = pd.DataFrame(data)
    rows_per_city = frame.groupby("city").size()
    minimum_rows = int(rows_per_city.min()) if not rows_per_city.empty else 180
    config = ExternalValidationConfig(
        target_column=payload.target_name,
        feature_columns=tuple(payload.covariates),
        horizons=payload.horizons,
        event_threshold=payload.event_threshold,
        minimum_rows_per_city=max(180, min(minimum_rows, 300)),
        bootstrap_repetitions=payload.bootstrap_repetitions,
        block_length=payload.block_length,
        random_state=payload.random_state,
        models=payload.models,
    )
    try:
        report = run_external_validation(frame, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report.model_dump(mode="json")
