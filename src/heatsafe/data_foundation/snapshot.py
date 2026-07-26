from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Iterable

from heatsafe import __version__
from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.contracts import (
    DataQualityReport,
    RetrievalMetadata,
    SnapshotManifest,
    SourceDescriptor,
)
from heatsafe.research.provenance import detect_git_revision


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def write_snapshot(
    output_directory: str | Path,
    *,
    snapshot_id: str,
    source: SourceDescriptor,
    observations: Iterable[NormalizedObservation],
    quality: DataQualityReport,
    retrieval: RetrievalMetadata | None = None,
    parameters: dict[str, object] | None = None,
    repository_root: str | Path | None = None,
) -> SnapshotManifest:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    items = list(observations)

    observations_path = directory / "observations.jsonl"
    quality_path = directory / "quality-report.json"
    manifest_path = directory / "manifest.json"

    observation_text = "\n".join(
        item.model_dump_json(exclude_none=False)
        for item in items
    )
    if observation_text:
        observation_text += "\n"
    _atomic_write(observations_path, observation_text)
    _atomic_write(quality_path, quality.model_dump_json(indent=2))

    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        source=source,
        observation_count=len(items),
        observations_file=observations_path.name,
        observations_sha256=sha256_file(observations_path),
        quality_report_file=quality_path.name,
        quality_report_sha256=sha256_file(quality_path),
        retrieval=retrieval,
        software_version=__version__,
        code_revision=detect_git_revision(repository_root),
        parameters=dict(parameters or {}),
    )
    _atomic_write(manifest_path, manifest.model_dump_json(indent=2))
    return manifest


def verify_snapshot(directory: str | Path) -> dict[str, object]:
    root = Path(directory)
    manifest = SnapshotManifest.model_validate_json(
        (root / "manifest.json").read_text(encoding="utf-8")
    )
    observations_path = root / manifest.observations_file
    quality_path = root / manifest.quality_report_file
    observations_ok = (
        observations_path.is_file()
        and sha256_file(observations_path) == manifest.observations_sha256
    )
    quality_ok = (
        quality_path.is_file()
        and sha256_file(quality_path) == manifest.quality_report_sha256
    )
    line_count = 0
    if observations_path.is_file():
        line_count = sum(1 for line in observations_path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "snapshot_id": manifest.snapshot_id,
        "observations_checksum_valid": observations_ok,
        "quality_checksum_valid": quality_ok,
        "manifest_observation_count": manifest.observation_count,
        "jsonl_observation_count": line_count,
        "count_valid": line_count == manifest.observation_count,
        "valid": observations_ok and quality_ok and line_count == manifest.observation_count,
    }


def load_observations(directory: str | Path) -> list[NormalizedObservation]:
    root = Path(directory)
    manifest = SnapshotManifest.model_validate_json(
        (root / "manifest.json").read_text(encoding="utf-8")
    )
    path = root / manifest.observations_file
    return [
        NormalizedObservation.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
