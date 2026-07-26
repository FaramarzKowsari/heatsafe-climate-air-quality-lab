from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.contracts import IngestionResult, RetrievalMetadata
from heatsafe.data_foundation.quality import assess_observations, deduplicate_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY, SourceRegistry
from heatsafe.data_foundation.snapshot import write_snapshot


class ConnectorProtocol(Protocol):
    def fetch(self, **kwargs: Any) -> list[NormalizedObservation]:
        ...


def ingest_to_snapshot(
    connector: ConnectorProtocol,
    *,
    source_id: str,
    snapshot_id: str,
    output_directory: str | Path,
    fetch_kwargs: dict[str, Any],
    retrieval: RetrievalMetadata | None = None,
    registry: SourceRegistry = DEFAULT_REGISTRY,
    repository_root: str | Path | None = None,
) -> IngestionResult:
    raw = connector.fetch(**fetch_kwargs)
    quality = assess_observations(raw)
    unique = deduplicate_observations(raw)
    manifest = write_snapshot(
        output_directory,
        snapshot_id=snapshot_id,
        source=registry.get(source_id),
        observations=unique,
        quality=quality,
        retrieval=retrieval,
        parameters=fetch_kwargs,
        repository_root=repository_root,
    )
    return IngestionResult(
        observations=unique,
        quality=quality,
        snapshot_directory=str(Path(output_directory)),
        manifest=manifest,
    )
