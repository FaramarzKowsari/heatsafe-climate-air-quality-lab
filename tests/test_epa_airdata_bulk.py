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


def _make_zip(path: Path) -> None:
    rows = [
        [
            "06", "001", "0001", "88101", "1",
            "37.8", "-122.2", "PM2.5", "2025-01-01",
            "00:00", "12.5", "Micrograms/cubic meter (LC)",
            "", "FEM", "100", "Test Method", "California",
            "Alameda", "2025-02-01",
        ],
        [
            "06", "013", "0002", "88101", "1",
            "38.0", "-122.0", "PM2.5", "2025-01-01",
            "00:00", "20.0", "Micrograms/cubic meter (LC)",
            "", "FEM", "100", "Other County", "California",
            "Contra Costa", "2025-02-01",
        ],
    ]
    frame = pd.DataFrame(rows, columns=COLUMNS)
    csv_path = path.parent / "hourly_88101_2025.csv"
    frame.to_csv(csv_path, index=False)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(csv_path, csv_path.name)


def test_bulk_parser_filters_alameda(tmp_path: Path) -> None:
    zip_path = tmp_path / "hourly_88101_2025.zip"
    _make_zip(zip_path)
    metadata = validate_airdata_zip(
        zip_path,
        minimum_size_bytes=0,
    )
    observations, report = load_alameda_pm25_observations(
        zip_path,
        chunksize=1,
        minimum_zip_size_bytes=0,
    )

    assert metadata["csv_member"] == "hourly_88101_2025.csv"
    assert len(observations) == 1
    assert observations[0].station_id == "06-001-0001"
    assert observations[0].variable == "pm25"
    assert report["matched_alameda_rows"] == 1
    assert report["unique_stations"] == 1
