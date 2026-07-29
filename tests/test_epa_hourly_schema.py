from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from heatsafe.research.official_experiment.bulk_airdata import (
    load_alameda_pm25_observations,
    validate_airdata_zip,
)


COLUMNS = [
    "State Code",
    "County Code",
    "Site Num",
    "Parameter Code",
    "POC",
    "Latitude",
    "Longitude",
    "Parameter Name",
    "Date GMT",
    "Time GMT",
    "Sample Measurement",
    "Units of Measure",
    "Qualifier",
    "Method Type",
    "Method Code",
    "Method Name",
    "State Name",
    "County Name",
    "Date of Last Change",
]


def _write_zip(path: Path, rows: list[list[object]]) -> None:
    frame = pd.DataFrame(rows, columns=COLUMNS)
    csv_path = path.parent / "hourly_88101_2025.csv"
    frame.to_csv(csv_path, index=False)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(csv_path, csv_path.name)


def _row(
    county_code: object,
    county_name: str,
    site: object,
    timestamp: str,
) -> list[object]:
    date_value, time_value = timestamp.split()
    return [
        "6.0",
        county_code,
        site,
        "88101.0",
        "1.0",
        "37.8",
        "-122.2",
        "PM2.5 - Local Conditions",
        date_value,
        time_value,
        "12.5",
        "Micrograms/cubic meter (LC)",
        "",
        "FEM",
        "100",
        "Test Method",
        "California",
        county_name,
        "2026-01-01",
    ]


def test_official_hourly_schema_does_not_require_duration(
    tmp_path: Path,
) -> None:
    zip_path = tmp_path / "hourly_88101_2025.zip"
    _write_zip(
        zip_path,
        [
            _row("1.0", "Alameda", "7.0", "2025-01-01 00:00"),
            _row("1.0", "Alameda", "7.0", "2025-01-01 01:00"),
        ],
    )

    metadata = validate_airdata_zip(
        zip_path,
        minimum_size_bytes=0,
    )
    observations, report = load_alameda_pm25_observations(
        zip_path,
        chunksize=1,
        minimum_zip_size_bytes=0,
    )

    assert metadata["airdata_product_type"] == (
        "official EPA hourly data file"
    )
    assert len(observations) == 2
    assert report["geography_fallback_used"] is False
    assert report["selected_geography"]["county_code"] == "001"
    assert report["filter"]["sample_duration"] == "1 HOUR"
    assert report["filter"]["sample_duration_source"] == (
        "official EPA hourly-file identity"
    )
    assert all(
        "sample_duration=1 HOUR" in item.quality_flag
        and (
            "sample_duration_source="
            "inferred_from_official_epa_hourly_file_identity"
        ) in item.quality_flag
        for item in observations
    )


def test_hourly_schema_fallback_remains_transparent(
    tmp_path: Path,
) -> None:
    zip_path = tmp_path / "hourly_88101_2025.zip"
    _write_zip(
        zip_path,
        [
            _row("13", "Contra Costa", "2", "2025-01-01 00:00"),
            _row("13", "Contra Costa", "2", "2025-01-01 01:00"),
            _row("75", "San Francisco", "5", "2025-01-01 00:00"),
            _row("75", "San Francisco", "5", "2025-01-01 01:00"),
            _row("75", "San Francisco", "5", "2025-01-01 02:00"),
        ],
    )

    observations, report = load_alameda_pm25_observations(
        zip_path,
        chunksize=2,
        minimum_zip_size_bytes=0,
    )

    assert len(observations) == 3
    assert report["geography_fallback_used"] is True
    assert report["selected_geography"]["county_code"] == "075"
