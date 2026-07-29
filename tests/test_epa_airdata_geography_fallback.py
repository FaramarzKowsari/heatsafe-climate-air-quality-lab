from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from heatsafe.research.official_experiment.bulk_airdata import (
    load_alameda_pm25_observations,
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
    "Sample Duration",
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
    *,
    state_code: object = "6.0",
    parameter_code: object = "88101.0",
    duration: str = "1 HOUR",
) -> list[object]:
    date_value, time_value = timestamp.split()
    return [
        state_code,
        county_code,
        site,
        parameter_code,
        "1.0",
        "37.8",
        "-122.2",
        "PM2.5 - Local Conditions",
        duration,
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


def test_numeric_like_codes_match_alameda(tmp_path: Path) -> None:
    zip_path = tmp_path / "hourly_88101_2025.zip"
    _write_zip(
        zip_path,
        [
            _row("1.0", "Alameda", "7.0", "2025-01-01 00:00"),
            _row("1.0", "Alameda", "7.0", "2025-01-01 01:00"),
            _row(
                "1.0",
                "Alameda",
                "7.0",
                "2025-01-02 00:00",
                duration="24 HOUR",
            ),
        ],
    )

    observations, report = load_alameda_pm25_observations(
        zip_path,
        chunksize=1,
        minimum_zip_size_bytes=0,
    )

    assert len(observations) == 2
    assert observations[0].station_id == "06-001-0007"
    assert report["geography_fallback_used"] is False
    assert report["selected_geography"]["county_code"] == "001"
    assert report["filter"]["sample_duration"] == "1 HOUR"


def test_fallback_chooses_best_hourly_california_county(
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
    assert report["selected_geography"] == {
        "state_code": "06",
        "state_name": "California",
        "county_code": "075",
        "county_name": "San Francisco",
    }
    assert all(
        item.station_id == "06-075-0005"
        for item in observations
    )
