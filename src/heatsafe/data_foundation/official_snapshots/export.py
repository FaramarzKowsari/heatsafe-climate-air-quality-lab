from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from heatsafe.core.models import NormalizedObservation


BENCHMARK_COLUMNS: tuple[str, ...] = (
    "timestamp_utc",
    "source_name",
    "source_dataset",
    "source_record_id",
    "station_id",
    "latitude",
    "longitude",
    "country",
    "region",
    "city",
    "variable",
    "value",
    "unit",
    "measurement_type",
    "quality_flag",
    "data_status",
    "retrieved_at",
    "license",
    "source_url",
)


def write_benchmark_table(
    observations: Iterable[NormalizedObservation],
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        observations,
        key=lambda item: (
            item.timestamp_utc,
            item.variable,
            item.station_id or "",
            item.source_record_id or "",
        ),
    )
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=BENCHMARK_COLUMNS)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "timestamp_utc": item.timestamp_utc.isoformat(),
                    "source_name": item.source_name,
                    "source_dataset": item.source_dataset,
                    "source_record_id": item.source_record_id or "",
                    "station_id": item.station_id or "",
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "country": item.country or "",
                    "region": item.region or "",
                    "city": item.city or "",
                    "variable": item.variable,
                    "value": item.value,
                    "unit": item.unit,
                    "measurement_type": str(item.measurement_type),
                    "quality_flag": item.quality_flag,
                    "data_status": item.data_status,
                    "retrieved_at": item.retrieved_at.isoformat(),
                    "license": item.license,
                    "source_url": item.source_url,
                }
            )
    return output
