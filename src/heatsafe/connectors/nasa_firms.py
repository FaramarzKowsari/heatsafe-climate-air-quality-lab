from __future__ import annotations

import csv
import io
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from heatsafe.connectors.base import BaseConnector, ConnectorError
from heatsafe.core.models import MeasurementType, NormalizedObservation


class NASAFIRMSAreaConnector(BaseConnector):
    name = "NASA FIRMS"
    source_id = "nasa-firms-area"
    base_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def __init__(self, map_key: str | None = None, **kwargs: Any) -> None:
        resolved = map_key or os.getenv("NASA_FIRMS_MAP_KEY")
        if not resolved:
            raise ValueError("NASA FIRMS map key is required via argument or NASA_FIRMS_MAP_KEY")
        super().__init__(requests_per_second=1.0, **kwargs)
        self.map_key = resolved

    def fetch(
        self,
        *,
        west: float,
        south: float,
        east: float,
        north: float,
        day_range: int = 1,
        source: str = "VIIRS_SNPP_NRT",
        date_value: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> list[NormalizedObservation]:
        if not -180 <= west < east <= 180:
            raise ValueError("Longitude bounds must satisfy -180 <= west < east <= 180")
        if not -90 <= south < north <= 90:
            raise ValueError("Latitude bounds must satisfy -90 <= south < north <= 90")
        if not 1 <= day_range <= 10:
            raise ValueError("day_range must be between 1 and 10")

        area = f"{west},{south},{east},{north}"
        url = f"{self.base_url}/{self.map_key}/{source}/{area}/{day_range}"
        if date_value:
            datetime.strptime(date_value, "%Y-%m-%d")
            url = f"{url}/{date_value}"
        try:
            result = self._resilient_client().request(
                "GET",
                url,
                source_id=self.source_id,
                response_kind="text",
                cache_ttl=self.default_cache_ttl(),
            )
        except (RuntimeError, httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"NASA FIRMS request failed: {exc}") from exc
        if not isinstance(result.payload, str):
            raise ConnectorError("NASA FIRMS returned a non-text payload")

        reader = csv.DictReader(io.StringIO(result.payload))
        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for index, row in enumerate(reader):
            if not row.get("latitude") or not row.get("longitude") or not row.get("acq_date"):
                continue
            frp = row.get("frp")
            if frp in {None, ""}:
                continue
            acquisition_time = str(row.get("acq_time") or "0000").zfill(4)
            timestamp = datetime.strptime(
                f"{row['acq_date']} {acquisition_time}",
                "%Y-%m-%d %H%M",
            ).replace(tzinfo=UTC)
            source_record_id = (
                f"{source}:{row.get('satellite', 'unknown')}:{row['latitude']}:"
                f"{row['longitude']}:{timestamp.isoformat()}:{index}"
            )
            observations.append(
                NormalizedObservation(
                    source_name=self.name,
                    source_dataset=f"FIRMS Area API {source}",
                    source_record_id=source_record_id,
                    station_id=None,
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    country=country,
                    city=city,
                    timestamp_utc=timestamp,
                    timestamp_local=None,
                    timezone="UTC",
                    variable="fire_radiative_power_mw",
                    value=float(frp),
                    unit="MW",
                    measurement_type=MeasurementType.SATELLITE_DERIVED,
                    quality_flag=(
                        f"confidence={row.get('confidence', 'unknown')};"
                        f"daynight={row.get('daynight', 'unknown')};"
                        f"version={row.get('version', 'unknown')}"
                    ),
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license="NASA Earth observation data; retain FIRMS source and satellite-product attribution",
                    source_url="https://firms.modaps.eosdis.nasa.gov/api/area/",
                )
            )
        return observations
