from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from pydantic import TypeAdapter

from .models import NormalizedObservation


OBSERVATION_LIST = TypeAdapter(list[NormalizedObservation])


def validate_observations(payload: object) -> list[NormalizedObservation]:
    return OBSERVATION_LIST.validate_python(payload)


def checksum_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum_manifest(paths: Iterable[str | Path], destination: str | Path) -> None:
    manifest = {str(Path(path)): checksum_file(path) for path in paths}
    Path(destination).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def normalize_observation(**payload: object) -> NormalizedObservation:
    """Validate one observation against the shared provenance contract."""
    from datetime import datetime, timezone
    payload.setdefault("retrieved_at", datetime.now(timezone.utc))
    return NormalizedObservation.model_validate(payload)
