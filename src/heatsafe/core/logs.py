from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any
from pathlib import Path

import pandas as pd

REQUIRED_LOG_COLUMNS = {
    "timestamp",
    "indoor_temperature_c",
    "indoor_humidity_pct",
    "outdoor_temperature_c",
    "pm25_ug_m3",
    "window_state",
    "fan_state",
    "cooling_state",
    "shade_state",
    "notes",
}


@dataclass(frozen=True)
class HeatLogValidation:
    valid_rows: int
    invalid_rows: int
    duplicate_timestamps: int
    missing_columns: list[str]
    warnings: list[str]


def validate_heat_log_csv(content: str) -> HeatLogValidation:
    frame = pd.read_csv(io.StringIO(content))
    missing = sorted(REQUIRED_LOG_COLUMNS - set(frame.columns))
    if missing:
        return HeatLogValidation(0, len(frame), 0, missing, ["The log schema is incomplete."])
    parsed = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    numeric_columns = [
        "indoor_temperature_c",
        "indoor_humidity_pct",
        "outdoor_temperature_c",
        "pm25_ug_m3",
    ]
    numeric_valid = pd.Series(True, index=frame.index)
    for column in numeric_columns:
        numeric_valid &= pd.to_numeric(frame[column], errors="coerce").notna()
    valid_mask = parsed.notna() & numeric_valid
    duplicates = int(parsed[parsed.notna()].duplicated().sum())
    warnings: list[str] = []
    if duplicates:
        warnings.append("Duplicate timestamps should be resolved before time-series analysis.")
    if (~valid_mask).sum():
        warnings.append("Rows with invalid timestamps or numeric values were found.")
    return HeatLogValidation(
        valid_rows=int(valid_mask.sum()),
        invalid_rows=int((~valid_mask).sum()),
        duplicate_timestamps=duplicates,
        missing_columns=[],
        warnings=warnings,
    )


def records_to_csv(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def records_to_json(records: list[dict[str, Any]]) -> str:
    return json.dumps(records, indent=2, ensure_ascii=False, default=str)


class HeatLog:
    """Small local-first log container with explicit JSON round-tripping."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = list(records or [])

    def add(self, record: dict[str, Any]) -> None:
        if "timestamp" not in record:
            raise ValueError("timestamp is required")
        parsed = pd.to_datetime(record["timestamp"], utc=True, errors="raise")
        normalized = dict(record)
        normalized["timestamp"] = parsed.isoformat()
        if any(item.get("timestamp") == normalized["timestamp"] for item in self.records):
            raise ValueError("Duplicate timestamps are not allowed")
        self.records.append(normalized)
        self.records.sort(key=lambda item: str(item["timestamp"]))

    def to_json(self, path: str | Path) -> None:
        from pathlib import Path
        Path(path).write_text(records_to_json(self.records), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "HeatLog":
        from pathlib import Path
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Heat log JSON must contain a list")
        return cls(records=[dict(item) for item in payload])
