from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.evaluation import run_nexus_benchmark


router = APIRouter(prefix="/api/v1/nexus", tags=["heataq-nexus"])


class NexusRunRequest(BaseModel):
    timestamps: list[str] = Field(min_length=240, max_length=20_000)
    target_values: list[float | None] = Field(min_length=240, max_length=20_000)
    covariates: dict[str, list[float | None]] = Field(default_factory=dict)
    target_name: str = "pm25"
    horizons: tuple[int, ...] = (1, 6, 12, 24, 48)
    event_threshold: float = 35.0
    alpha: float = Field(default=0.1, gt=0, lt=1)
    random_state: int = 42

    @model_validator(mode="after")
    def equal_lengths(self) -> NexusRunRequest:
        expected = len(self.timestamps)
        if len(self.target_values) != expected:
            raise ValueError("target_values and timestamps must have equal length")
        invalid = {name: len(values) for name, values in self.covariates.items() if len(values) != expected}
        if invalid:
            raise ValueError(f"Covariate lengths must equal {expected}: {invalid}")
        return self


@router.get("/capabilities")
def nexus_capabilities() -> dict[str, object]:
    return {
        "benchmark": "HeatAQ Nexus",
        "paid_ai_api_required": False,
        "models": [
            "persistence",
            "seasonal_naive_24h",
            "moving_average_6h",
            "linear_regression",
            "ridge",
            "random_forest",
            "gradient_boosting",
        ],
        "uncertainty": "chronological split-conformal intervals",
        "evaluation": ["chronological holdout", "rolling-origin"],
    }


@router.post("/run")
def run_nexus(payload: NexusRunRequest) -> dict[str, Any]:
    data: dict[str, object] = {
        "timestamp": payload.timestamps,
        payload.target_name: payload.target_values,
        **payload.covariates,
    }
    frame = pd.DataFrame(data)
    config = NexusConfig(
        target_column=payload.target_name,
        feature_columns=tuple(payload.covariates),
        horizons=payload.horizons,
        event_threshold=payload.event_threshold,
        alpha=payload.alpha,
        random_state=payload.random_state,
    )
    try:
        report = run_nexus_benchmark(frame, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report.model_dump(mode="json")
