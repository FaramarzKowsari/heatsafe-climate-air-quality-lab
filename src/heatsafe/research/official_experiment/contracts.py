from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class StationSelectionPolicy(BaseModel):
    target_variable: str = "pm25"
    allowed_duration_tokens: tuple[str, ...] = (
        "1 HOUR",
        "1-HR",
        "HOURLY",
    )
    minimum_value: float = 0.0
    minimum_total_hours: int = Field(default=500, ge=100)
    minimum_contiguous_hours: int = Field(default=240, ge=100)

    @field_validator("allowed_duration_tokens")
    @classmethod
    def normalize_tokens(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        clean = tuple(
            dict.fromkeys(value.strip().upper() for value in values if value.strip())
        )
        if not clean:
            raise ValueError("At least one duration token is required")
        return clean


class RealOfficialExperimentConfig(BaseModel):
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,100}$")
    title: str = Field(min_length=5)
    description: str = Field(min_length=20)
    snapshot_config_path: str
    station_policy: StationSelectionPolicy = Field(
        default_factory=StationSelectionPolicy
    )
    horizons: tuple[int, ...] = (1, 6, 12, 24, 48)
    event_threshold: float = 35.0
    alpha: float = Field(default=0.1, gt=0, lt=1)
    minimum_valid_rows: int = Field(default=180, ge=100)
    rolling_origin_step: int = Field(default=24, ge=1)
    rolling_origin_max_origins: int = Field(default=20, ge=1, le=200)
    random_state: int = 42
    release_version: str = Field(
        default="0.1.0",
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )
    created_by: str = "Faramarz Kowsari"
    limitations: tuple[str, ...] = (
        "Monitoring-site measurements are not equivalent to population exposure.",
        "The selected station represents one monitoring location, not an entire county.",
        "Instrument, method and sampling-duration changes can affect comparability.",
        "This experiment is research software output, not an official warning or medical product.",
    )

    @field_validator("horizons")
    @classmethod
    def positive_unique_horizons(
        cls,
        values: tuple[int, ...],
    ) -> tuple[int, ...]:
        clean = tuple(sorted(set(values)))
        if not clean or any(value <= 0 for value in clean):
            raise ValueError("horizons must contain positive unique integers")
        return clean
