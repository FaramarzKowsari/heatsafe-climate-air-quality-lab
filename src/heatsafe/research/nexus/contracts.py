from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class NexusConfig(BaseModel):
    timestamp_column: str = "timestamp"
    target_column: str = "pm25"
    feature_columns: tuple[str, ...] = ()
    horizons: tuple[int, ...] = (1, 6, 12, 24, 48)
    event_threshold: float = 35.0
    alpha: float = Field(default=0.1, gt=0, lt=1)
    train_fraction: float = Field(default=0.70, gt=0, lt=1)
    calibration_fraction: float = Field(default=0.15, gt=0, lt=1)
    lags: tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)
    rolling_windows: tuple[int, ...] = (6, 12, 24, 48)
    random_state: int = 42
    minimum_valid_rows: int = Field(default=180, ge=100)
    rolling_origin_step: int = Field(default=24, ge=1)
    rolling_origin_max_origins: int = Field(default=20, ge=1, le=200)
    expected_frequency: str = "1h"

    @field_validator("horizons", "lags", "rolling_windows")
    @classmethod
    def positive_unique_integers(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        clean = tuple(sorted(set(values)))
        if not clean or any(value <= 0 for value in clean):
            raise ValueError("Values must be unique positive integers")
        return clean

    @model_validator(mode="after")
    def validate_split_fractions(self) -> NexusConfig:
        if self.train_fraction + self.calibration_fraction >= 0.95:
            raise ValueError("train_fraction + calibration_fraction must leave at least 5% for testing")
        return self


class ForecastMetric(BaseModel):
    model: str
    horizon_hours: int
    n_train: int
    n_calibration: int
    n_test: int
    mae: float
    rmse: float
    mean_bias: float
    r2: float
    smape_pct: float
    event_precision: float
    event_recall: float
    event_f1: float
    event_brier: float
    prediction_interval_coverage: float
    mean_interval_width: float
    interval_score: float
    conformal_quantile: float


class RollingOriginMetric(BaseModel):
    model: str
    horizon_hours: int
    origins: int
    mae: float
    rmse: float
    mean_bias: float


class ModelCard(BaseModel):
    model: str
    model_family: str
    intended_use: str
    training_protocol: str
    input_features: list[str]
    uncertainty_method: str
    strengths: list[str]
    limitations: list[str]
    prohibited_claims: list[str]


class NexusReport(BaseModel):
    benchmark_name: str = "HeatAQ Nexus"
    benchmark_version: str = "0.3.0-preview"
    target: str
    timestamp_column: str
    feature_columns: list[str]
    horizons: list[int]
    event_threshold: float
    metrics: list[ForecastMetric]
    rolling_origin_metrics: list[RollingOriginMetric]
    best_by_horizon: dict[int, str]
    leaderboard: list[dict[str, Any]]
    model_cards: list[ModelCard]
    dataset_summary: dict[str, Any]
    split_description: str
    leakage_controls: list[str]
    limitations: list[str]
