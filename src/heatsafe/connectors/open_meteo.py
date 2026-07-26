from __future__ import annotations

from datetime import datetime, timezone

import httpx

from heatsafe.core.models import MeasurementType, NormalizedObservation

from .base import BaseConnector, ConnectorError


class OpenMeteoWeatherConnector(BaseConnector):
    name = "Open-Meteo Weather Forecast"
    base_url = "https://api.open-meteo.com/v1/forecast"

    def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        city: str | None = None,
        country: str | None = None,
        forecast_days: int = 3,
    ) -> list[NormalizedObservation]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
            "timezone": "UTC",
            "forecast_days": min(max(forecast_days, 1), 16),
        }
        try:
            with self._client() as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"Open-Meteo weather request failed: {exc}") from exc
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        variables = {
            "temperature_2m": ("temperature_c", "°C"),
            "relative_humidity_2m": ("relative_humidity_pct", "%"),
            "wind_speed_10m": ("wind_speed_kmh", "km/h"),
            "wind_direction_10m": ("wind_direction_deg", "degree"),
        }
        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for index, time_value in enumerate(times):
            timestamp = datetime.fromisoformat(time_value).replace(tzinfo=timezone.utc)
            for source_key, (variable, unit) in variables.items():
                values = hourly.get(source_key, [])
                if index >= len(values) or values[index] is None:
                    continue
                observations.append(
                    NormalizedObservation(
                        source_name=self.name,
                        source_dataset="Forecast API",
                        source_record_id=f"{latitude}:{longitude}:{time_value}:{source_key}",
                        latitude=latitude,
                        longitude=longitude,
                        country=country,
                        city=city,
                        timestamp_utc=timestamp,
                        timestamp_local=timestamp,
                        timezone="UTC",
                        variable=variable,
                        value=float(values[index]),
                        unit=unit,
                        measurement_type=MeasurementType.FORECAST,
                        quality_flag="model_output_not_station_observation",
                        data_status="available",
                        retrieved_at=retrieved_at,
                        license="CC BY 4.0; verify current service terms for deployment tier",
                        source_url="https://open-meteo.com/en/docs",
                    )
                )
        return observations


class OpenMeteoAirQualityConnector(BaseConnector):
    name = "Open-Meteo Air Quality"
    base_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        city: str | None = None,
        country: str | None = None,
        forecast_days: int = 3,
    ) -> list[NormalizedObservation]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "timezone": "UTC",
            "forecast_days": min(max(forecast_days, 1), 7),
        }
        try:
            with self._client() as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ConnectorError(f"Open-Meteo air-quality request failed: {exc}") from exc
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        variables = {
            "pm2_5": ("pm25", "µg/m³"),
            "pm10": ("pm10", "µg/m³"),
            "carbon_monoxide": ("co", "µg/m³"),
            "nitrogen_dioxide": ("no2", "µg/m³"),
            "sulphur_dioxide": ("so2", "µg/m³"),
            "ozone": ("o3", "µg/m³"),
        }
        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for index, time_value in enumerate(times):
            timestamp = datetime.fromisoformat(time_value).replace(tzinfo=timezone.utc)
            for source_key, (variable, unit) in variables.items():
                values = hourly.get(source_key, [])
                if index >= len(values) or values[index] is None:
                    continue
                observations.append(
                    NormalizedObservation(
                        source_name=self.name,
                        source_dataset="CAMS-derived Air Quality Forecast API",
                        source_record_id=f"{latitude}:{longitude}:{time_value}:{source_key}",
                        latitude=latitude,
                        longitude=longitude,
                        country=country,
                        city=city,
                        timestamp_utc=timestamp,
                        timestamp_local=timestamp,
                        timezone="UTC",
                        variable=variable,
                        value=float(values[index]),
                        unit=unit,
                        measurement_type=MeasurementType.FORECAST,
                        quality_flag="modeled_air_quality_not_ground_monitor",
                        data_status="available",
                        retrieved_at=retrieved_at,
                        license="CC BY 4.0; verify current service terms for deployment tier",
                        source_url="https://open-meteo.com/en/docs/air-quality-api",
                    )
                )
        return observations


# Backward-compatible concise alias used by examples and tests.
OpenMeteoConnector = OpenMeteoWeatherConnector
