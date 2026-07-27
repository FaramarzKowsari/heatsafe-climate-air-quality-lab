from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from heatsafe.research.benchmark_registry.contracts import DatasetRole


class AcquisitionMode(StrEnum):
    LIVE_CONNECTOR = "live-connector"
    LOCAL_FILE = "local-file"
    REQUEST_SPEC = "request-spec"
    NORMALIZED_JSONL = "normalized-jsonl"


class QualityGateConfig(BaseModel):
    minimum_observations: int = Field(default=24, ge=1)
    minimum_unique_fraction: float = Field(default=0.98, ge=0, le=1)
    minimum_quality_score: float = Field(default=0.90, ge=0, le=1)
    maximum_errors: int = Field(default=0, ge=0)
    minimum_records_per_target: int = Field(default=1, ge=1)


class OfficialSnapshotConfig(BaseModel):
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]+$")
    dataset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,80}$")
    version: str = Field(
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$"
    )
    title: str = Field(min_length=5)
    description: str = Field(min_length=20)
    role: DatasetRole = "external-test"
    target_variables: tuple[str, ...]
    feature_variables: tuple[str, ...] = ()
    station_selection_protocol: str = Field(min_length=10)
    quality_control_protocol: str = Field(min_length=10)
    missing_data_policy: str = Field(min_length=10)
    known_limitations: tuple[str, ...]
    tags: tuple[str, ...] = ()
    country: str | None = None
    region: str | None = None
    city: str | None = None
    request_parameters: dict[str, Any] = Field(default_factory=dict)
    quality_gate: QualityGateConfig = Field(default_factory=QualityGateConfig)
    created_by: str = "Faramarz Kowsari"

    @field_validator(
        "target_variables",
        "known_limitations",
    )
    @classmethod
    def require_nonempty_unique(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        clean = tuple(dict.fromkeys(item.strip() for item in values if item.strip()))
        if not clean:
            raise ValueError("At least one non-empty value is required")
        return clean

    @field_validator("feature_variables", "tags")
    @classmethod
    def unique_optional_values(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))

    @model_validator(mode="after")
    def targets_and_features_do_not_overlap(self) -> OfficialSnapshotConfig:
        overlap = sorted(set(self.target_variables) & set(self.feature_variables))
        if overlap:
            raise ValueError(
                f"Variables cannot be both targets and features: {overlap}"
            )
        return self


class AcquisitionPlan(BaseModel):
    source_id: str
    source_name: str
    authority: str
    acquisition_mode: AcquisitionMode
    credential_environment_variables: tuple[str, ...]
    sanitized_request_parameters: dict[str, Any]
    generated_at_utc: datetime
    request_sha256: str
    executable_by_heatsafe: bool
    notes: tuple[str, ...]


class QualityGateResult(BaseModel):
    passed: bool
    reasons: tuple[str, ...]
    observation_count: int
    unique_fraction: float
    quality_score: float
    error_count: int
    target_record_counts: dict[str, int]


class OfficialSnapshotRelease(BaseModel):
    dataset_id: str
    version: str
    source_id: str
    created_at_utc: datetime
    acquisition_mode: AcquisitionMode
    snapshot_directory: str
    snapshot_manifest_path: str
    dataset_card_path: str
    registry_index_path: str
    acquisition_plan_path: str
    benchmark_table_path: str
    quality_gate: QualityGateResult
    snapshot_integrity: dict[str, object]
    registry_integrity: dict[str, object]
    artifact_sha256: dict[str, str]
    scientific_boundary: str
