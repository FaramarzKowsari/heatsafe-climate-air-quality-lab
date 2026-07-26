from __future__ import annotations

from datetime import datetime, timezone

import httpx

from heatsafe.core.models import MeasurementType, NormalizedObservation

from .base import BaseConnector, ConnectorError


class NASAPowerDailyConnector(BaseConnector):
    name = "NASA POWER"
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        start: str,
        end: str,
        city: str | None = None,
        country: str | None = None,
        parameters: tuple[str, ...] = ("T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"),
    ) -> list[NormalizedObservation]:
        params = {
            "parameters": ",".join(parameters),
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start.replace("-", ""),
            "end": end.replace("-", ""),
            "format": "JSON",
            "time-standard": "UTC",
        }
        try:
            with self._client() as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"NASA POWER request failed: {exc}") from exc
        parameter_data = payload.get("properties", {}).get("parameter", {})
        metadata = {
            "T2M": ("temperature_c", "°C"),
            "T2M_MAX": ("maximum_temperature_c", "°C"),
            "T2M_MIN": ("minimum_temperature_c", "°C"),
            "RH2M": ("relative_humidity_pct", "%"),
            "WS10M": ("wind_speed_m_s", "m/s"),
        }
        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for source_parameter, series in parameter_data.items():
            variable, unit = metadata.get(source_parameter, (source_parameter.lower(), "source-unit"))
            for date_key, value in series.items():
                if value in {-999, -999.0, None}:
                    continue
                timestamp = datetime.strptime(date_key, "%Y%m%d").replace(tzinfo=timezone.utc)
                observations.append(
                    NormalizedObservation(
                        source_name=self.name,
                        source_dataset="Daily Point API",
                        source_record_id=f"{latitude}:{longitude}:{date_key}:{source_parameter}",
                        latitude=latitude,
                        longitude=longitude,
                        country=country,
                        city=city,
                        timestamp_utc=timestamp,
                        timestamp_local=timestamp,
                        timezone="UTC",
                        variable=variable,
                        value=float(value),
                        unit=unit,
                        measurement_type=MeasurementType.MODELED,
                        quality_flag="analysis_ready_modeled_product",
                        data_status="available",
                        retrieved_at=retrieved_at,
                        license="NASA data; review POWER terms and attribution guidance",
                        source_url="https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
                    )
                )
        return observations


NasaPowerConnector = NASAPowerDailyConnector
