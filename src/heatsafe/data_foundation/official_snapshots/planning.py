from __future__ import annotations

from datetime import UTC, datetime

from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
    AcquisitionPlan,
    OfficialSnapshotConfig,
)
from heatsafe.data_foundation.official_snapshots.recipes import (
    ERA5Request,
    recipe_for_source,
    sanitize_parameters,
)
from heatsafe.data_foundation.registry import SourceDescriptor
from heatsafe.research.benchmark_registry.hashing import sha256_json


def acquisition_mode(source_id: str) -> AcquisitionMode:
    if source_id in {"noaa-cdo-ghcnd", "epa-aqs", "nasa-firms-area"}:
        return AcquisitionMode.LIVE_CONNECTOR
    if source_id == "eea-air-quality-parquet":
        return AcquisitionMode.LOCAL_FILE
    if source_id == "era5-land":
        return AcquisitionMode.REQUEST_SPEC
    raise ValueError(f"Unsupported official source: {source_id}")


def build_acquisition_plan(
    config: OfficialSnapshotConfig,
    source: SourceDescriptor,
) -> AcquisitionPlan:
    recipe = recipe_for_source(config.source_id, config.request_parameters)
    normalized = recipe.model_dump(mode="json")
    if isinstance(recipe, ERA5Request):
        normalized["cds_request"] = recipe.to_cds_request()

    sanitized = sanitize_parameters(normalized)
    mode = acquisition_mode(config.source_id)
    executable = mode in {
        AcquisitionMode.LIVE_CONNECTOR,
        AcquisitionMode.LOCAL_FILE,
    }
    notes: list[str] = [
        "Credentials are referenced by environment-variable name only.",
        "The plan contains no secret values.",
        "CI validates plans and fixtures without live provider downloads.",
    ]
    if mode == AcquisitionMode.REQUEST_SPEC:
        notes.append(
            "ERA5-Land is emitted as an explicit CDS request specification; "
            "the resulting official file must be downloaded through an "
            "authorized Copernicus workflow before freezing."
        )

    payload = {
        "source_id": config.source_id,
        "dataset_id": config.dataset_id,
        "version": config.version,
        "request": sanitized,
    }
    return AcquisitionPlan(
        source_id=source.source_id,
        source_name=source.name,
        authority=source.authority,
        acquisition_mode=mode,
        credential_environment_variables=source.credential_environment_variables,
        sanitized_request_parameters=sanitized,
        generated_at_utc=datetime.now(UTC),
        request_sha256=sha256_json(payload),
        executable_by_heatsafe=executable,
        notes=tuple(notes),
    )
