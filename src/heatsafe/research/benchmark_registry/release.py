from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from heatsafe.research.benchmark_registry.contracts import BenchmarkRelease
from heatsafe.research.benchmark_registry.hashing import sha256_file
from heatsafe.research.benchmark_registry.validation import load_dataset_card


def create_release_bundle(
    release: BenchmarkRelease,
    *,
    registry_root: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    registry = Path(registry_root)
    output = Path(output_directory)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    cards_out = output / "dataset-cards"
    cards_out.mkdir()

    copied_cards: list[dict[str, str]] = []
    for card_ref in release.dataset_cards:
        source = registry / card_ref
        card = load_dataset_card(source)
        target = cards_out / source.name
        shutil.copy2(source, target)
        copied_cards.append(
            {
                "dataset_id": card.dataset_id,
                "version": card.version,
                "path": str(target.relative_to(output)),
                "sha256": sha256_file(target),
            }
        )

    release_path = output / "benchmark-release.json"
    release_path.write_text(release.model_dump_json(indent=2), encoding="utf-8")

    manifest = {
        "release_id": release.release_id,
        "version": release.version,
        "release_sha256": sha256_file(release_path),
        "dataset_cards": copied_cards,
        "result_artifacts": [
            artifact.model_dump(mode="json")
            for artifact in release.result_artifacts
        ],
        "publication_boundary": (
            "A release candidate is not a DOI-backed publication until "
            "artifacts are deposited in a preservation repository and the "
            "record is manually reviewed."
        ),
    }
    manifest_path = output / "release-bundle-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "release": str(release_path),
        "manifest": str(manifest_path),
        "dataset_cards": copied_cards,
    }
