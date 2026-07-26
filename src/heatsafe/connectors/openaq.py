from __future__ import annotations

from datetime import datetime

import httpx

from heatsafe.core.models import MeasurementType, NormalizedObservation

from .base import BaseConnector, ConnectorError


class OpenAQConnector(BaseConnector):
    """OpenAQ v3 latest-measurement adapter with sensor metadata mapping."""

    name = "OpenAQ v3"
    base_url = "https://api.openaq.org/v3"

    def __init__(self, api_key: str, **kwargs: object) -> None:
        if not api_key:
            raise ValueError("OpenAQ API key is required")
        super().__init__(**kwargs)
        self.api_key = api_key

    def fetch(self, *, location_id: int, country: str | None = None, city: str | None = None) -> list[NormalizedObservation]:
        headers = {"X-API-Key": self.api_key}
        try:
            with self._client() as client:
                metadata_response = client.get(f"{self.base_url}/locations/{location_id}", headers=headers)
                metadata_response.raise_for_status()
                latest_response = client.get(f"{self.base_url}/locations/{location_id}/latest", headers=headers)
                latest_response.raise_for_status()
                metadata_payload = metadata_response.json()
                latest_payload = latest_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"OpenAQ request failed: {exc}") from exc

        location_results = metadata_payload.get("results", [])
        location = location_results[0] if location_results else {}
        location_coordinates = location.get("coordinates") or {}
        sensor_map: dict[int, tuple[str, str]] = {}
        for sensor in location.get("sensors", []) or []:
            parameter = sensor.get("parameter") or {}
            sensor_map[int(sensor["id"])] = (
                str(parameter.get("name") or sensor.get("name") or "unknown"),
                str(parameter.get("units") or "source-unit"),
            )
        license_names = [str(item.get("name")) for item in (location.get("licenses") or []) if item.get("name")]
        source_license = ", ".join(license_names) or "OpenAQ terms plus originating-provider terms"
        resolved_country = country or (location.get("country") or {}).get("code")
        resolved_city = city or location.get("locality") or location.get("name")
        timezone_name = str(location.get("timezone") or "UTC")

        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for item in latest_payload.get("results", []):
            coordinates = item.get("coordinates") or location_coordinates
            latitude = coordinates.get("latitude")
            longitude = coordinates.get("longitude")
            datetime_data = item.get("datetime") or {}
            utc_value = datetime_data.get("utc")
            sensor_id = item.get("sensorsId")
            if utc_value is None or latitude is None or longitude is None or sensor_id is None or item.get("value") is None:
                continue
            variable, unit = sensor_map.get(int(sensor_id), (f"sensor_{sensor_id}", "source-unit"))
            observations.append(
                NormalizedObservation(
                    source_name=self.name,
                    source_dataset="Location latest measurements",
                    source_record_id=f"{location_id}:{sensor_id}:{utc_value}",
                    station_id=str(location_id),
                    latitude=float(latitude),
                    longitude=float(longitude),
                    country=resolved_country,
                    city=resolved_city,
                    timestamp_utc=datetime.fromisoformat(str(utc_value).replace("Z", "+00:00")),
                    timestamp_local=datetime.fromisoformat(str(datetime_data.get("local")).replace("Z", "+00:00")) if datetime_data.get("local") else None,
                    timezone=timezone_name,
                    variable=variable,
                    value=float(item["value"]),
                    unit=unit,
                    measurement_type=MeasurementType.OBSERVED,
                    quality_flag="source_quality_metadata_required",
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license=source_license,
                    source_url="https://docs.openaq.org/api/operations/location_latest_get_v3_locations__locations_id__latest_get",
                )
            )
        return observations
