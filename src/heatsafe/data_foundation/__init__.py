"""Production-grade environmental data contracts, quality and snapshots."""

from heatsafe.data_foundation.contracts import (
    AccessMode,
    DataQualityReport,
    IngestionResult,
    LicenseStatus,
    RetrievalMetadata,
    SnapshotManifest,
    SourceCategory,
    SourceDescriptor,
)
from heatsafe.data_foundation.quality import assess_observations, deduplicate_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY, SourceRegistry
from heatsafe.data_foundation.snapshot import verify_snapshot, write_snapshot

__all__ = [
    "AccessMode",
    "DEFAULT_REGISTRY",
    "DataQualityReport",
    "IngestionResult",
    "LicenseStatus",
    "RetrievalMetadata",
    "SnapshotManifest",
    "SourceCategory",
    "SourceDescriptor",
    "SourceRegistry",
    "assess_observations",
    "deduplicate_observations",
    "verify_snapshot",
    "write_snapshot",
]
