from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from pydantic import HttpUrl

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
    OfficialSnapshotConfig,
    OfficialSnapshotRelease,
    QualityGateResult,
)
from heatsafe.data_foundation.official_snapshots.export import (
    BENCHMARK_COLUMNS,
    write_benchmark_table,
)
from heatsafe.data_foundation.official_snapshots.planning import (
    build_acquisition_plan,
)
from heatsafe.data_foundation.quality import assess_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import (
    sha256_file,
    verify_snapshot,
    write_snapshot,
)
from heatsafe.research.benchmark_registry.contracts import (
    ArtifactKind,
    DatasetCard,
    SnapshotArtifact,
    SnapshotStatus,
    SourceCitation,
    SpatialCoverage,
    TemporalCoverage,
)
from heatsafe.research.benchmark_registry.registry import write_registry_index
from heatsafe.research.benchmark_registry.validation import (
    verify_dataset_snapshot,
)


def evaluate_quality_gate(
    observations: list[NormalizedObservation],
    config: OfficialSnapshotConfig,
) -> QualityGateResult:
    quality = assess_observations(observations)
    gate = config.quality_gate
    reasons: list[str] = []

    observation_count = len(observations)
    unique_fraction = (
        quality.unique_observation_count / observation_count
        if observation_count
        else 0.0
    )
    target_counts = Counter(
        item.variable
        for item in observations
        if item.variable in config.target_variables
    )

    if observation_count < gate.minimum_observations:
        reasons.append(
            f"observation_count={observation_count} is below "
            f"minimum_observations={gate.minimum_observations}"
        )
    if unique_fraction < gate.minimum_unique_fraction:
        reasons.append(
            f"unique_fraction={unique_fraction:.6f} is below "
            f"minimum_unique_fraction={gate.minimum_unique_fraction:.6f}"
        )
    if quality.quality_score < gate.minimum_quality_score:
        reasons.append(
            f"quality_score={quality.quality_score:.6f} is below "
            f"minimum_quality_score={gate.minimum_quality_score:.6f}"
        )
    if quality.error_count > gate.maximum_errors:
        reasons.append(
            f"error_count={quality.error_count} exceeds "
            f"maximum_errors={gate.maximum_errors}"
        )

    for variable in config.target_variables:
        count = target_counts.get(variable, 0)
        if count < gate.minimum_records_per_target:
            reasons.append(
                f"target {variable!r} has {count} records; "
                f"minimum is {gate.minimum_records_per_target}"
            )

    return QualityGateResult(
        passed=not reasons,
        reasons=tuple(reasons),
        observation_count=observation_count,
        unique_fraction=round(unique_fraction, 6),
        quality_score=quality.quality_score,
        error_count=quality.error_count,
        target_record_counts=dict(target_counts),
    )


def _artifact(
    path: Path,
    *,
    kind: ArtifactKind,
    root: Path,
    rows: int | None = None,
    columns: int | None = None,
) -> SnapshotArtifact:
    return SnapshotArtifact(
        relative_path=path.relative_to(root).as_posix(),
        kind=kind,
        media_type=(
            "text/csv"
            if path.suffix == ".csv"
            else "application/x-ndjson"
            if path.suffix == ".jsonl"
            else "application/json"
        ),
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        rows=rows,
        columns=columns,
    )


def _spatial_coverage(
    observations: list[NormalizedObservation],
    config: OfficialSnapshotConfig,
) -> SpatialCoverage:
    countries = sorted(
        {
            value
            for value in (
                *(item.country for item in observations),
                config.country,
            )
            if value
        }
    )
    regions = sorted(
        {
            value
            for value in (
                *(item.region for item in observations),
                config.region,
            )
            if value
        }
    )
    cities = sorted(
        {
            value
            for value in (
                *(item.city for item in observations),
                config.city,
            )
            if value
        }
    )
    stations = sorted(
        {item.station_id for item in observations if item.station_id}
    )
    latitudes = [item.latitude for item in observations]
    longitudes = [item.longitude for item in observations]
    bounding_box = (
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes),
    )
    return SpatialCoverage(
        countries=tuple(countries),
        regions=tuple(regions),
        cities=tuple(cities),
        stations=tuple(stations),
        bounding_box=bounding_box,
    )


def _temporal_coverage(
    observations: list[NormalizedObservation],
) -> TemporalCoverage:
    timestamps = sorted(item.timestamp_utc for item in observations)
    start = timestamps[0]
    end = timestamps[-1]
    if end <= start:
        end = start + timedelta(seconds=1)
    return TemporalCoverage(
        start_utc=start,
        end_utc=end,
        nominal_resolution="source-reported",
        timezone_policy="UTC",
    )


def _units(
    observations: list[NormalizedObservation],
) -> dict[str, str]:
    by_variable: dict[str, set[str]] = defaultdict(set)
    for item in observations:
        by_variable[item.variable].add(item.unit)
    return {
        variable: " | ".join(sorted(units))
        for variable, units in sorted(by_variable.items())
    }


def freeze_official_snapshot(
    observations: Iterable[NormalizedObservation],
    *,
    config: OfficialSnapshotConfig,
    output_root: str | Path,
    registry_root: str | Path,
    repository_root: str | Path | None = None,
    acquisition_mode: AcquisitionMode = AcquisitionMode.NORMALIZED_JSONL,
    overwrite: bool = False,
) -> OfficialSnapshotRelease:
    items = list(observations)
    if not items:
        raise ValueError("At least one normalized observation is required")

    source = DEFAULT_REGISTRY.get(config.source_id)
    plan = build_acquisition_plan(config, source)
    if acquisition_mode == AcquisitionMode.NORMALIZED_JSONL:
        plan = plan.model_copy(
            update={
                "acquisition_mode": AcquisitionMode.NORMALIZED_JSONL,
                "executable_by_heatsafe": True,
                "notes": (
                    *plan.notes,
                    "This release was frozen from an existing normalized JSONL file.",
                ),
            }
        )
    gate = evaluate_quality_gate(items, config)
    quality = assess_observations(items)

    snapshot_directory = (
        Path(output_root)
        / config.dataset_id
        / config.version
    )
    if snapshot_directory.exists() and any(snapshot_directory.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"Snapshot directory is not empty: {snapshot_directory}"
            )
    snapshot_directory.mkdir(parents=True, exist_ok=True)

    plan_path = snapshot_directory / "acquisition-plan.json"
    plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    snapshot_id = f"{config.dataset_id}-{config.version}"
    manifest = write_snapshot(
        snapshot_directory,
        snapshot_id=snapshot_id,
        source=source,
        observations=items,
        quality=quality,
        parameters={
            "dataset_id": config.dataset_id,
            "version": config.version,
            "role": config.role,
            "target_variables": list(config.target_variables),
            "feature_variables": list(config.feature_variables),
            "request_sha256": plan.request_sha256,
            "quality_gate_passed": gate.passed,
        },
        repository_root=repository_root,
    )

    benchmark_path = write_benchmark_table(
        items,
        snapshot_directory / "benchmark-table.csv",
    )
    manifest_path = snapshot_directory / "manifest.json"
    observations_path = snapshot_directory / manifest.observations_file
    quality_path = snapshot_directory / manifest.quality_report_file

    artifacts = (
        _artifact(
            observations_path,
            kind="normalized",
            root=snapshot_directory,
            rows=len(items),
        ),
        _artifact(
            quality_path,
            kind="quality-report",
            root=snapshot_directory,
        ),
        _artifact(
            manifest_path,
            kind="metadata",
            root=snapshot_directory,
        ),
        _artifact(
            plan_path,
            kind="metadata",
            root=snapshot_directory,
        ),
        _artifact(
            benchmark_path,
            kind="normalized",
            root=snapshot_directory,
            rows=len(items),
            columns=len(BENCHMARK_COLUMNS),
        ),
    )

    registry = Path(registry_root)
    datasets_directory = registry / "datasets"
    releases_directory = registry / "releases"
    snapshot_releases_directory = registry / "snapshot-releases"
    datasets_directory.mkdir(parents=True, exist_ok=True)
    releases_directory.mkdir(parents=True, exist_ok=True)
    snapshot_releases_directory.mkdir(parents=True, exist_ok=True)

    status: SnapshotStatus = "verified" if gate.passed else "draft"
    now = datetime.now(UTC)
    card = DatasetCard(
        dataset_id=config.dataset_id,
        version=config.version,
        title=config.title,
        description=config.description,
        source_id=config.source_id,
        role=config.role,
        target_variables=config.target_variables,
        feature_variables=config.feature_variables,
        units=_units(items),
        spatial=_spatial_coverage(items, config),
        temporal=_temporal_coverage(items),
        station_selection_protocol=config.station_selection_protocol,
        quality_control_protocol=config.quality_control_protocol,
        missing_data_policy=config.missing_data_policy,
        known_limitations=config.known_limitations,
        citation=SourceCitation(
            authority=source.authority,
            dataset_name=source.name,
            homepage=HttpUrl(source.homepage),
            documentation_url=HttpUrl(source.documentation_url),
            citation_text=source.citation_text,
            license_summary=source.license_summary,
            access_date_utc=now,
        ),
        artifacts=artifacts,
        created_at_utc=now,
        created_by=config.created_by,
        status=status,
        tags=tuple(
            dict.fromkeys(
                (
                    *config.tags,
                    "official-source",
                    "immutable-snapshot",
                    config.source_id,
                )
            )
        ),
        metadata={
            "acquisition_mode": acquisition_mode,
            "request_sha256": plan.request_sha256,
            "quality_gate": gate.model_dump(mode="json"),
            "source_license_status": source.license_status,
            "source_redistribution_notes": source.redistribution_notes,
        },
    )

    card_path = (
        datasets_directory
        / f"{config.dataset_id}-{config.version}.json"
    )
    card_path.write_text(card.model_dump_json(indent=2), encoding="utf-8")

    registry_index_path = write_registry_index(registry)
    snapshot_integrity = verify_snapshot(snapshot_directory)
    registry_integrity = verify_dataset_snapshot(card, snapshot_directory)

    checksums = {
        artifact.relative_path: artifact.sha256
        for artifact in artifacts
    }
    checksums[card_path.relative_to(registry).as_posix()] = sha256_file(
        card_path
    )
    checksums[
        registry_index_path.relative_to(registry).as_posix()
    ] = sha256_file(registry_index_path)

    release = OfficialSnapshotRelease(
        dataset_id=config.dataset_id,
        version=config.version,
        source_id=config.source_id,
        created_at_utc=now,
        acquisition_mode=acquisition_mode,
        snapshot_directory=str(snapshot_directory),
        snapshot_manifest_path=str(manifest_path),
        dataset_card_path=str(card_path),
        registry_index_path=str(registry_index_path),
        acquisition_plan_path=str(plan_path),
        benchmark_table_path=str(benchmark_path),
        quality_gate=gate,
        snapshot_integrity=snapshot_integrity,
        registry_integrity=registry_integrity,
        artifact_sha256=checksums,
        scientific_boundary=(
            "A verified snapshot confirms integrity and declared quality gates. "
            "It does not by itself prove representativeness, causal validity, "
            "universal transferability, or official warning authority."
        ),
    )
    release_path = (
        snapshot_releases_directory
        / f"{config.dataset_id}-{config.version}-snapshot-release.json"
    )
    release_path.write_text(
        release.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return release
