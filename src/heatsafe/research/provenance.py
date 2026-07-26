from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    created_at_utc: str
    code_revision: str | None
    python_version: str
    platform: str
    random_seed: int | None
    configuration: dict[str, Any]
    inputs: tuple[ArtifactRecord, ...]
    outputs: tuple[ArtifactRecord, ...]
    dependency_versions: dict[str, str]
    notes: tuple[str, ...]

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: str | Path) -> ArtifactRecord:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    return ArtifactRecord(
        path=str(file_path),
        sha256=sha256_file(file_path),
        size_bytes=file_path.stat().st_size,
    )


def detect_git_revision(cwd: str | Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    revision = completed.stdout.strip()
    return revision or None


def dependency_versions(names: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in sorted(set(names)):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def build_experiment_manifest(
    experiment_id: str,
    *,
    configuration: Mapping[str, Any] | None = None,
    input_paths: Iterable[str | Path] = (),
    output_paths: Iterable[str | Path] = (),
    random_seed: int | None = None,
    dependency_names: Iterable[str] = ("numpy", "pandas", "scikit-learn", "scipy"),
    notes: Iterable[str] = (),
    repository_root: str | Path | None = None,
) -> ExperimentManifest:
    identifier = experiment_id.strip()
    if not identifier:
        raise ValueError("experiment_id must be non-empty")

    return ExperimentManifest(
        experiment_id=identifier,
        created_at_utc=datetime.now(UTC).isoformat(),
        code_revision=detect_git_revision(repository_root),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        random_seed=random_seed,
        configuration=dict(configuration or {}),
        inputs=tuple(artifact_record(path) for path in input_paths),
        outputs=tuple(artifact_record(path) for path in output_paths),
        dependency_versions=dependency_versions(dependency_names),
        notes=tuple(str(note) for note in notes),
    )


def write_experiment_manifest(manifest: ExperimentManifest, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest.model_dump(), indent=2, sort_keys=True), encoding="utf-8")
    return output
