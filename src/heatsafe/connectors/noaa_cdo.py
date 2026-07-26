from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from heatsafe.connectors.base import BaseConnector, ConnectorError
from heatsafe.core.models import MeasurementType, NormalizedObservation


class NOAACDOConnector(BaseConnector):
    name = "NOAA NCEI CDO"
    source_id = "noaa-cdo-ghcnd"
    base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"

    VARIABLE_MAP: dict[str, tuple[str, str]] = {
        "TAVG": ("temperature_c", "°C"),
        "TMAX": ("maximum_temperature_c", "°C"),
        "TMIN": ("minimum_temperature_c", "°C"),
        "PRCP": ("precipitation_mm", "mm"),
        "AWND": ("wind_speed_m_s", "m/s"),
    }

    def __init__(self, token: str | None = None, **kwargs: Any) -> None:
        resolved = token or os.getenv("NOAA_CDO_TOKEN")
        if not resolved:
            raise ValueError("NOAA CDO token is required via argument or NOAA_CDO_TOKEN")
        super().__init__(requests_per_second=4.5, **kwargs)
        self.token = resolved

    def fetch(
        self,
        *,
        station_id: str,
        latitude: float,
        longitude: float,
        start: str,
        end: str,
        datatypes: tuple[str, ...] = ("TAVG", "TMAX", "TMIN", "PRCP", "AWND"),
        city: str | None = None,
        country: str | None = "US",
    ) -> list[NormalizedObservation]:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        if end_date < start_date:
            raise ValueError("end must not precede start")
        if end_date - start_date > timedelta(days=366):
            raise ValueError("NOAA CDO daily requests are limited to approximately one year per call")

        params: dict[str, Any] = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "startdate": start_date.isoformat(),
            "enddate": end_date.isoformat(),
            "units": "metric",
            "limit": 1000,
            "offset": 1,
            "includemetadata": "true",
        }
        params["datatypeid"] = ",".join(datatypes)
        headers = {"token": self.token}
        client = self._resilient_client()
        rows: list[dict[str, Any]] = []
        expected_count: int | None = None

        while True:
            try:
                result = client.request(
                    "GET",
                    self.base_url,
                    source_id=self.source_id,
                    params=params,
                    headers=headers,
                    cache_ttl=self.default_cache_ttl(),
                )
            except (RuntimeError, httpx.HTTPError, ValueError) as exc:
                raise ConnectorError(f"NOAA CDO request failed: {exc}") from exc
            payload = result.payload
            if not isinstance(payload, dict):
                raise ConnectorError("NOAA CDO returned a non-object payload")
            page_rows = payload.get("results", [])
            if not isinstance(page_rows, list):
                raise ConnectorError("NOAA CDO results field is not a list")
            rows.extend(item for item in page_rows if isinstance(item, dict))
            metadata = payload.get("metadata", {})
            if isinstance(metadata, dict):
                resultset = metadata.get("resultset", {})
                if isinstance(resultset, dict) and resultset.get("count") is not None:
                    expected_count = int(resultset["count"])
            if not page_rows or expected_count is None or len(rows) >= expected_count:
                break
            params["offset"] = int(params["offset"]) + int(params["limit"])

        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for row in rows:
            datatype = str(row.get("datatype", ""))
            if datatype not in self.VARIABLE_MAP or row.get("value") is None or not row.get("date"):
                continue
            variable, unit = self.VARIABLE_MAP[datatype]
            timestamp = datetime.fromisoformat(str(row["date"]).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            attributes = str(row.get("attributes") or "").strip()
            observations.append(
                NormalizedObservation(
                    source_name=self.name,
                    source_dataset="GHCN Daily via Climate Data Online v2",
                    source_record_id=f"{station_id}:{datatype}:{timestamp.isoformat()}",
                    station_id=station_id,
                    latitude=latitude,
                    longitude=longitude,
                    country=country,
                    city=city,
                    timestamp_utc=timestamp.astimezone(UTC),
                    timestamp_local=None,
                    timezone="UTC",
                    variable=variable,
                    value=float(row["value"]),
                    unit=unit,
                    measurement_type=MeasurementType.OBSERVED,
                    quality_flag=f"noaa_attributes:{attributes or 'none-reported'}",
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license="United States government data; retain NOAA/NCEI attribution and dataset metadata",
                    source_url="https://www.ncei.noaa.gov/cdo-web/webservices/v2",
                )
            )
        return observations
