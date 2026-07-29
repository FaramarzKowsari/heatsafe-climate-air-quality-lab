from __future__ import annotations

import os
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx

from heatsafe.connectors.base import BaseConnector, ConnectorError
from heatsafe.core.models import MeasurementType, NormalizedObservation


class EPAAQSConnector(BaseConnector):
    name = "US EPA AQS"
    source_id = "epa-aqs"
    base_url = "https://aqs.epa.gov/data/api/sampleData/byCounty"

    def __init__(
        self,
        email: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        resolved_email = email or os.getenv("EPA_AQS_EMAIL")
        resolved_key = api_key or os.getenv("EPA_AQS_KEY")
        if not resolved_email or not resolved_key:
            raise ValueError("EPA AQS credentials require EPA_AQS_EMAIL and EPA_AQS_KEY")
        super().__init__(requests_per_second=1.0, **kwargs)
        self.email = resolved_email
        self.api_key = resolved_key

    def fetch(
        self,
        *,
        parameter_code: str,
        begin_date: str,
        end_date: str,
        state_code: str,
        county_code: str,
        city: str | None = None,
        country: str = "US",
    ) -> list[NormalizedObservation]:
        start = date.fromisoformat(begin_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("end_date must not precede begin_date")
        if end - start > timedelta(days=366):
            raise ValueError("Split large EPA AQS requests into intervals no longer than one year")

        params = {
            "email": self.email,
            "key": self.api_key,
            "param": parameter_code,
            "bdate": start.strftime("%Y%m%d"),
            "edate": end.strftime("%Y%m%d"),
            "state": state_code.zfill(2),
            "county": county_code.zfill(3),
        }
        try:
            result = self._resilient_client().request(
                "GET",
                self.base_url,
                source_id=self.source_id,
                params=params,
                cache_ttl=self.default_cache_ttl(),
            )
        except (RuntimeError, httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"EPA AQS request failed: {exc}") from exc
        payload = result.payload
        if not isinstance(payload, dict):
            raise ConnectorError("EPA AQS returned a non-object payload")

        header = payload.get("Header", [])
        if isinstance(header, list) and header:
            status = str(header[0].get("status", "")).lower()
            if "failed" in status or "error" in status:
                raise ConnectorError(f"EPA AQS response status: {header[0]}")

        rows = payload.get("Data", [])
        if not isinstance(rows, list):
            raise ConnectorError("EPA AQS Data field is not a list")

        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("sample_measurement") is None:
                continue
            date_gmt = str(row.get("date_gmt") or "")
            time_gmt = str(row.get("time_gmt") or "00:00")
            if not date_gmt:
                continue
            parsed_time = time.fromisoformat(time_gmt[:5])
            timestamp = datetime.combine(date.fromisoformat(date_gmt), parsed_time, tzinfo=UTC)
            latitude = row.get("latitude")
            longitude = row.get("longitude")
            if latitude is None or longitude is None:
                continue
            site_id = (
                f"{str(row.get('state_code', state_code)).zfill(2)}-"
                f"{str(row.get('county_code', county_code)).zfill(3)}-"
                f"{str(row.get('site_number', 'unknown')).zfill(4)}"
            )
            parameter_name = str(row.get("parameter") or f"parameter_{parameter_code}")
            variable = (
                "pm25"
                if parameter_code in {"88101", "88502"} or "PM2.5" in parameter_name.upper()
                else parameter_name.lower().replace(" ", "_")
            )
            qualifiers = row.get("qualifier")
            quality_parts = [
                f"sample_duration={row.get('sample_duration', 'unknown')}",
                f"method_code={row.get('method_code', 'unknown')}",
                f"qualifier={qualifiers or 'none'}",
            ]
            observations.append(
                NormalizedObservation(
                    source_name=self.name,
                    source_dataset="AQS Sample Data by County",
                    source_record_id=f"{site_id}:{parameter_code}:{timestamp.isoformat()}:{row.get('poc', '')}",
                    station_id=site_id,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    country=country,
                    city=city or row.get("local_site_name"),
                    timestamp_utc=timestamp,
                    timestamp_local=None,
                    timezone="UTC",
                    variable=variable,
                    value=float(row["sample_measurement"]),
                    unit=str(row.get("units_of_measure") or "source-unit"),
                    measurement_type=MeasurementType.OBSERVED,
                    quality_flag=";".join(quality_parts),
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license="United States government data; retain EPA AQS method, qualifier, duration, and site metadata",
                    source_url="https://aqs.epa.gov/aqsweb/documents/data_api.html",
                )
            )
        return observations
