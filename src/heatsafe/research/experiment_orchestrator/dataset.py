from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from heatsafe.data_foundation.snapshot import load_observations
from heatsafe.research.experiment_orchestrator.contracts import ExperimentSpec
from heatsafe.research.nexus.dataset import (
    generate_synthetic_nexus_frame,
    observations_to_hourly_frame,
)
from heatsafe.research.provenance import sha256_file


def _resolve_source_path(spec_path: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = spec_path.parent / candidate
    return candidate.resolve()


def load_experiment_frame(
    spec: ExperimentSpec,
    *,
    spec_path: str | Path,
    canonical_output: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_spec_path = Path(spec_path).resolve()
    output = Path(canonical_output)
    output.parent.mkdir(parents=True, exist_ok=True)

    source_path: Path | None = None
    source_sha256: str | None = None

    if spec.dataset.kind == "synthetic":
        frame = generate_synthetic_nexus_frame(
            rows=spec.dataset.rows,
            random_state=spec.dataset.seed,
        )
    elif spec.dataset.kind == "csv":
        assert spec.dataset.path is not None
        source_path = _resolve_source_path(source_spec_path, spec.dataset.path)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        source_sha256 = sha256_file(source_path)
        frame = pd.read_csv(source_path)
    else:
        assert spec.dataset.path is not None
        source_path = _resolve_source_path(source_spec_path, spec.dataset.path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        observations = load_observations(source_path)
        frame = observations_to_hourly_frame(
            observations,
            variables=spec.dataset.variables,
            station_id=spec.dataset.station_id,
            frequency=spec.dataset.frequency,
        )

    if frame.empty:
        raise ValueError("The experiment dataset is empty")

    frame.to_csv(output, index=False)

    descriptor: dict[str, Any] = {
        "kind": spec.dataset.kind,
        "canonical_path": str(output),
        "canonical_sha256": sha256_file(output),
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "source_path": str(source_path) if source_path is not None else None,
        "source_sha256": source_sha256,
        "synthetic_seed": spec.dataset.seed if spec.dataset.kind == "synthetic" else None,
    }
    return frame, descriptor
