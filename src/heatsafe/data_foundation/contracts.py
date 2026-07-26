from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from heatsafe.core.models import NormalizedObservation


class AccessMode(StrEnum):
    OPEN = "open"
    TOKEN = "token"
    CREDENTIAL = "credential"
    LOCAL_FILE = "local-file"
    MANUAL = "manual"
    DISCOVERY_REQUIRED = "discovery-required"


class SourceCategory(StrEnum):
    WEATHER = "weather"
    CLIMATE = "climate"
    AIR_QUALITY = "air-quality"
    FIRE = "fire"
    REANALYSIS = "reanalysis"
    SATELLITE = "satellite"
    LOCAL = "local"


class LicenseStatus(StrEnum):
    DOCUMENTED = "documented"
    PROVIDER_SPECIFIC = "provider-specific"
    REVIEW_REQUIRED = "review-required"
    RESTRICTED_REDISTRIBUTION = "restricted-redistribution"


class SourceDescriptor(BaseModel):
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]+$")
    name: str
    category: SourceCategory
    authority: str
    access_mode: AccessMode
    homepage: str
    documentation_url: str
    license_summary: str
    license_status: LicenseStatus
    credential_environment_variables: tuple[str, ...] = ()
    temporal_resolution: str | None = None
    spatial_resolution: str | None = None
    measurement_type: str
    production_status: str
    redistribution_notes: str
    citation_text: str
    tags: tuple[str, ...] = ()


class RetrievalMetadata(BaseModel):
    request_id: str
    source_id: str
    requested_at_utc: datetime
    completed_at_utc: datetime
    request_parameters: dict[str, Any]
    request_url: str | None = None
    http_status: int | None = None
    attempts: int = Field(ge=1)
    from_cache: bool
    response_sha256: str
    etag: str | None = None
    last_modified: str | None = None
    record_count: int = Field(ge=0)


class QualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class QualityIssue(BaseModel):
    severity: QualitySeverity
    code: str
    message: str
    observation_index: int | None = None
    source_record_id: str | None = None


class DataQualityReport(BaseModel):
    assessed_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation_count: int = Field(ge=0)
    unique_observation_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    quality_score: float = Field(ge=0, le=1)
    variable_counts: dict[str, int]
    unit_counts: dict[str, int]
    measurement_type_counts: dict[str, int]
    issues: list[QualityIssue]


class SnapshotManifest(BaseModel):
    snapshot_id: str
    schema_version: str = "1.0"
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: SourceDescriptor
    observation_count: int = Field(ge=0)
    observations_file: str
    observations_sha256: str
    quality_report_file: str
    quality_report_sha256: str
    retrieval: RetrievalMetadata | None = None
    software_version: str
    code_revision: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    observations: list[NormalizedObservation]
    quality: DataQualityReport
    snapshot_directory: str | None = None
    manifest: SnapshotManifest | None = None
