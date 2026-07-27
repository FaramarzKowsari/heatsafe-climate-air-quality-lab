from __future__ import annotations

import json
from pathlib import Path

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.official_snapshots.contracts import (
    OfficialSnapshotConfig,
)
from heatsafe.data_foundation.official_snapshots.recipes import (
    EEARequest,
    EPARequest,
    ERA5Request,
    FIRMSRequest,
    NOAARequest,
    recipe_for_source,
)


class ExternalAcquisitionRequired(RuntimeError):
    def __init__(self, message: str, request_specification: dict[str, object]) -> None:
        super().__init__(message)
        self.request_specification = request_specification


def acquire_observations(
    config: OfficialSnapshotConfig,
) -> list[NormalizedObservation]:
    recipe = recipe_for_source(config.source_id, config.request_parameters)

    if isinstance(recipe, NOAARequest):
        from heatsafe.connectors.noaa_cdo import NOAACDOConnector

        return NOAACDOConnector().fetch(
            station_id=recipe.station_id,
            latitude=recipe.latitude,
            longitude=recipe.longitude,
            start=recipe.start.isoformat(),
            end=recipe.end.isoformat(),
            datatypes=recipe.datatypes,
            city=recipe.city,
            country=recipe.country,
        )

    if isinstance(recipe, EPARequest):
        from heatsafe.connectors.epa_aqs import EPAAQSConnector

        return EPAAQSConnector().fetch(
            parameter_code=recipe.parameter_code,
            begin_date=recipe.begin_date.isoformat(),
            end_date=recipe.end_date.isoformat(),
            state_code=recipe.state_code,
            county_code=recipe.county_code,
            city=recipe.city,
            country=recipe.country,
        )

    if isinstance(recipe, FIRMSRequest):
        from heatsafe.connectors.nasa_firms import NASAFIRMSAreaConnector

        return NASAFIRMSAreaConnector().fetch(
            west=recipe.west,
            south=recipe.south,
            east=recipe.east,
            north=recipe.north,
            day_range=recipe.day_range,
            source=recipe.source,
            date_value=(
                recipe.date_value.isoformat()
                if recipe.date_value is not None
                else None
            ),
            country=recipe.country,
            city=recipe.city,
        )

    if isinstance(recipe, EEARequest):
        from heatsafe.connectors.eea_parquet import EEAParquetConnector

        return EEAParquetConnector().fetch(
            path=recipe.path,
            column_map=recipe.column_map,
            country=recipe.country,
            city=recipe.city,
        )

    if isinstance(recipe, ERA5Request):
        raise ExternalAcquisitionRequired(
            (
                "ERA5-Land requires an authorized Copernicus download. "
                "Use the emitted request specification, then normalize and "
                "freeze the downloaded official file."
            ),
            recipe.to_cds_request(),
        )

    raise AssertionError("Unreachable acquisition recipe")


def write_external_request_specification(
    config: OfficialSnapshotConfig,
    output_path: str | Path,
) -> Path:
    recipe = recipe_for_source(config.source_id, config.request_parameters)
    if not isinstance(recipe, ERA5Request):
        raise ValueError(
            "External request specifications are currently defined for ERA5-Land"
        )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_id": config.source_id,
        "dataset_id": config.dataset_id,
        "version": config.version,
        "cds_dataset": "reanalysis-era5-land",
        "request": recipe.to_cds_request(),
        "credential_environment_variables": ["CDSAPI_URL", "CDSAPI_KEY"],
        "scientific_boundary": (
            "This file is a request specification, not a downloaded dataset "
            "and not evidence of successful acquisition."
        ),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
