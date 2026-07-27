from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


DatasetRole = Literal[
    "training",
    "calibration",
    "validation",
    "external-test",
    "reference",
]
SnapshotStatus = Literal["draft", "verified", "released", "deprecated"]
ArtifactKind = Literal[
    "raw",
    "normalized",
    "quality-report",
    "metadata",
    "benchmark-result",
]


class SourceCitation(BaseModel):
    authority: str = Field(min_length=2)
    dataset_name: str = Field(min_length=2)
    homepage: HttpUrl
    documentation_url: HttpUrl | None = None
    citation_text: str = Field(min_length=5)
    license_summary: str = Field(min_length=5)
    access_date_utc: datetime


class SnapshotArtifact(BaseModel):
    relative_path: str = Field(min_length=1)
    kind: ArtifactKind
    media_type: str = Field(min_length=3)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: int | None = Field(default=None, ge=0)
    columns: int | None = Field(default=None, ge=0)

    @field_validator("relative_path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip("/")
        if not normalized or normalized.startswith("../") or "/../" in normalized:
            raise ValueError("relative_path must stay inside the snapshot directory")
        return normalized


class SpatialCoverage(BaseModel):
    countries: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    cities: tuple[str, ...] = ()
    stations: tuple[str, ...] = ()
    bounding_box: tuple[float, float, float, float] | None = None

    @field_validator("countries", "regions", "cities", "stations")
    @classmethod
    def unique_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))


class TemporalCoverage(BaseModel):
    start_utc: datetime
    end_utc: datetime
    nominal_resolution: str = Field(min_length=2)
    timezone_policy: str = "UTC"

    @model_validator(mode="after")
    def chronological(self) -> TemporalCoverage:
        if self.end_utc <= self.start_utc:
            raise ValueError("end_utc must be later than start_utc")
        return self


class DatasetCard(BaseModel):
    dataset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,80}$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
    title: str = Field(min_length=5)
    description: str = Field(min_length=20)
    source_id: str = Field(min_length=3)
    role: DatasetRole
    target_variables: tuple[str, ...]
    feature_variables: tuple[str, ...] = ()
    units: dict[str, str]
    spatial: SpatialCoverage
    temporal: TemporalCoverage
    station_selection_protocol: str = Field(min_length=10)
    quality_control_protocol: str = Field(min_length=10)
    missing_data_policy: str = Field(min_length=10)
    known_limitations: tuple[str, ...]
    citation: SourceCitation
    artifacts: tuple[SnapshotArtifact, ...]
    created_at_utc: datetime
    created_by: str = "Faramarz Kowsari"
    status: SnapshotStatus = "draft"
    supersedes: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_variables", "known_limitations", "tags")
    @classmethod
    def require_unique_nonempty(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        clean = tuple(dict.fromkeys(item.strip() for item in values if item.strip()))
        if not clean:
            raise ValueError("At least one non-empty value is required")
        return clean

    @model_validator(mode="after")
    def validate_units_and_artifacts(self) -> DatasetCard:
        variables = set(self.target_variables) | set(self.feature_variables)
        missing_units = sorted(variables - set(self.units))
        if missing_units:
            raise ValueError(f"Missing units for variables: {missing_units}")
        if not self.artifacts:
            raise ValueError("At least one snapshot artifact is required")
        paths = [artifact.relative_path for artifact in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate artifact paths are not allowed")
        return self


class BenchmarkProtocol(BaseModel):
    protocol_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,80}$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    title: str
    target_variable: str
    forecast_horizons_hours: tuple[int, ...]
    event_threshold: float
    split_strategy: str
    external_validation_strategy: str
    models: tuple[str, ...]
    metrics: tuple[str, ...]
    random_seed: int
    source_code_revision: str = Field(min_length=7)
    prohibited_claims: tuple[str, ...]
    created_at_utc: datetime

    @field_validator("forecast_horizons_hours")
    @classmethod
    def positive_horizons(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        clean = tuple(sorted(set(values)))
        if not clean or any(value <= 0 for value in clean):
            raise ValueError("Forecast horizons must be positive")
        return clean


class BenchmarkRelease(BaseModel):
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,100}$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    title: str
    dataset_cards: tuple[str, ...]
    protocol: BenchmarkProtocol
    result_artifacts: tuple[SnapshotArtifact, ...]
    release_notes: tuple[str, ...]
    created_at_utc: datetime
    status: Literal["candidate", "released", "withdrawn"] = "candidate"
    doi: str | None = None

    @model_validator(mode="after")
    def release_has_inputs_and_outputs(self) -> BenchmarkRelease:
        if not self.dataset_cards:
            raise ValueError("At least one dataset card is required")
        if not self.result_artifacts:
            raise ValueError("At least one result artifact is required")
        return self


class RegistryIndexEntry(BaseModel):
    identifier: str
    version: str
    status: str
    card_path: str
    sha256: str
    title: str


class RegistryIndex(BaseModel):
    generated_at_utc: datetime
    datasets: list[RegistryIndexEntry]
    releases: list[RegistryIndexEntry]
    registry_sha256: str
