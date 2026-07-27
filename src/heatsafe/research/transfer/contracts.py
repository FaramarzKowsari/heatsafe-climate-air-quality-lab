from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ValidationMode = Literal["leave-one-city-out", "leave-one-region-out"]


class ExternalValidationConfig(BaseModel):
    timestamp_column: str = "timestamp"
    city_column: str = "city"
    region_column: str = "region"
    target_column: str = "pm25"
    feature_columns: tuple[str, ...] = ()
    horizons: tuple[int, ...] = (1, 6, 24)
    event_threshold: float = 35.0
    alpha: float = Field(default=0.1, gt=0, lt=1)
    source_train_fraction: float = Field(default=0.80, ge=0.6, le=0.9)
    minimum_rows_per_city: int = Field(default=300, ge=180)
    bootstrap_repetitions: int = Field(default=300, ge=20, le=5_000)
    block_length: int = Field(default=24, ge=2, le=336)
    random_state: int = 42
    models: tuple[str, ...] = (
        "persistence",
        "seasonal_naive_24h",
        "ridge",
        "random_forest",
        "gradient_boosting",
    )
    validation_modes: tuple[ValidationMode, ...] = (
        "leave-one-city-out",
        "leave-one-region-out",
    )
    expected_frequency: str = "1h"

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        clean = tuple(sorted(set(values)))
        if not clean or any(value <= 0 for value in clean):
            raise ValueError("horizons must contain unique positive integers")
        return clean

    @field_validator("feature_columns", "models", "validation_modes")
    @classmethod
    def unique_nonempty_strings(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        clean = tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not clean:
            raise ValueError("At least one value is required")
        return clean

    @model_validator(mode="after")
    def validate_models(self) -> ExternalValidationConfig:
        supported = {
            "persistence",
            "seasonal_naive_24h",
            "moving_average_6h",
            "linear_regression",
            "ridge",
            "random_forest",
            "gradient_boosting",
        }
        unknown = sorted(set(self.models) - supported)
        if unknown:
            raise ValueError(f"Unsupported models: {unknown}")
        return self


class ShiftDiagnostic(BaseModel):
    target_mean_shift: float
    target_std_ratio: float
    feature_shift_index: float
    train_event_rate: float
    test_event_rate: float


class FoldMetric(BaseModel):
    validation_mode: ValidationMode
    holdout_domain: str
    holdout_region: str | None = None
    model: str
    horizon_hours: int
    train_domains: int
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
    prediction_interval_coverage: float
    mean_interval_width: float
    conformal_quantile: float
    relative_mae_skill_vs_persistence: float
    bootstrap_skill_ci_lower: float
    bootstrap_skill_ci_upper: float
    dm_statistic: float
    dm_p_value: float
    shift: ShiftDiagnostic


class SliceMetric(BaseModel):
    validation_mode: ValidationMode
    holdout_domain: str
    model: str
    horizon_hours: int
    slice_type: Literal["season", "intensity"]
    slice_value: str
    n: int
    mae: float
    rmse: float
    mean_bias: float
    event_f1: float


class RobustnessRow(BaseModel):
    rank: int
    model: str
    folds: int
    horizons: int
    mean_mae: float
    median_mae: float
    worst_domain_mae: float
    mean_relative_skill: float
    mean_event_f1: float
    mean_interval_coverage: float
    mean_feature_shift_index: float


class ExternalValidationReport(BaseModel):
    study_name: str = "HeatSafe Multi-City External Validation"
    study_version: str = "0.4.0-preview"
    target: str
    horizons: list[int]
    validation_modes: list[ValidationMode]
    cities: list[str]
    regions: list[str]
    fold_metrics: list[FoldMetric]
    slice_metrics: list[SliceMetric]
    robustness_leaderboard: list[RobustnessRow]
    best_model_by_mode_and_horizon: dict[str, str]
    dataset_summary: dict[str, Any]
    protocol: list[str]
    limitations: list[str]
