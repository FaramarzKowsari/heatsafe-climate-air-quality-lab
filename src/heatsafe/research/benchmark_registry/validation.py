from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from heatsafe.research.benchmark_registry.contracts import (
    BenchmarkRelease,
    DatasetCard,
)
from heatsafe.research.benchmark_registry.hashing import sha256_file


class RegistryValidationError(ValueError):
    pass


def load_dataset_card(path: str | Path) -> DatasetCard:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return DatasetCard.model_validate(payload)


def load_benchmark_release(path: str | Path) -> BenchmarkRelease:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return BenchmarkRelease.model_validate(payload)


def _inspect_csv(path: Path) -> tuple[int, int]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration:
            return 0, 0
        rows = sum(1 for _ in reader)
    return rows, len(header)


def verify_dataset_snapshot(
    card: DatasetCard,
    snapshot_root: str | Path,
) -> dict[str, Any]:
    root = Path(snapshot_root)
    failures: list[str] = []
    artifact_results: list[dict[str, Any]] = []

    for artifact in card.artifacts:
        path = root / artifact.relative_path
        result: dict[str, Any] = {
            "relative_path": artifact.relative_path,
            "exists": path.is_file(),
            "expected_sha256": artifact.sha256,
            "expected_size_bytes": artifact.size_bytes,
        }
        if not path.is_file():
            failures.append(f"Missing artifact: {artifact.relative_path}")
            artifact_results.append(result)
            continue

        actual_sha = sha256_file(path)
        actual_size = path.stat().st_size
        result["actual_sha256"] = actual_sha
        result["actual_size_bytes"] = actual_size
        result["checksum_match"] = actual_sha == artifact.sha256
        result["size_match"] = actual_size == artifact.size_bytes

        if actual_sha != artifact.sha256:
            failures.append(f"Checksum mismatch: {artifact.relative_path}")
        if actual_size != artifact.size_bytes:
            failures.append(f"Size mismatch: {artifact.relative_path}")

        if path.suffix.lower() == ".csv":
            rows, columns = _inspect_csv(path)
            result["actual_rows"] = rows
            result["actual_columns"] = columns
            if artifact.rows is not None and rows != artifact.rows:
                failures.append(f"Row-count mismatch: {artifact.relative_path}")
            if artifact.columns is not None and columns != artifact.columns:
                failures.append(f"Column-count mismatch: {artifact.relative_path}")

        artifact_results.append(result)

    return {
        "dataset_id": card.dataset_id,
        "version": card.version,
        "valid": not failures,
        "failures": failures,
        "artifacts": artifact_results,
    }


def assert_dataset_snapshot(
    card: DatasetCard,
    snapshot_root: str | Path,
) -> dict[str, Any]:
    report = verify_dataset_snapshot(card, snapshot_root)
    if not report["valid"]:
        raise RegistryValidationError("; ".join(report["failures"]))
    return report
