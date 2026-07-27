from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from heatsafe.research.benchmark_registry.contracts import (
    BenchmarkRelease,
    DatasetCard,
    RegistryIndex,
    RegistryIndexEntry,
)
from heatsafe.research.benchmark_registry.hashing import sha256_file, sha256_json
from heatsafe.research.benchmark_registry.validation import (
    load_benchmark_release,
    load_dataset_card,
)


def _entry(
    *,
    identifier: str,
    version: str,
    status: str,
    absolute_path: Path,
    registry_path: Path,
    title: str,
) -> RegistryIndexEntry:
    return RegistryIndexEntry(
        identifier=identifier,
        version=version,
        status=status,
        card_path=registry_path.as_posix(),
        sha256=sha256_file(absolute_path),
        title=title,
    )


def build_registry_index(registry_root: str | Path) -> RegistryIndex:
    root = Path(registry_root)
    dataset_entries: list[RegistryIndexEntry] = []
    release_entries: list[RegistryIndexEntry] = []

    for path in sorted((root / "datasets").glob("*.json")):
        card: DatasetCard = load_dataset_card(path)
        dataset_entries.append(
            _entry(
                identifier=card.dataset_id,
                version=card.version,
                status=card.status,
                absolute_path=path,
                registry_path=path.relative_to(root),
                title=card.title,
            )
        )

    for path in sorted((root / "releases").glob("*.json")):
        release: BenchmarkRelease = load_benchmark_release(path)
        release_entries.append(
            _entry(
                identifier=release.release_id,
                version=release.version,
                status=release.status,
                absolute_path=path,
                registry_path=path.relative_to(root),
                title=release.title,
            )
        )

    payload = {
        "datasets": [item.model_dump(mode="json") for item in dataset_entries],
        "releases": [item.model_dump(mode="json") for item in release_entries],
    }
    return RegistryIndex(
        generated_at_utc=datetime.now(UTC),
        datasets=dataset_entries,
        releases=release_entries,
        registry_sha256=sha256_json(payload),
    )


def write_registry_index(
    registry_root: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    root = Path(registry_root)
    output = Path(output_path) if output_path else root / "index.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    index = build_registry_index(root)
    output.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    return output


def read_registry_index(path: str | Path) -> RegistryIndex:
    return RegistryIndex.model_validate_json(Path(path).read_text(encoding="utf-8"))
