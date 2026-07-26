from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

import pandas as pd

from heatsafe.connectors.base import BaseConnector, ConnectorError
from heatsafe.core.models import MeasurementType, NormalizedObservation


DEFAULT_COLUMNS: dict[str, str] = {
    "timestamp": "DatetimeBegin",
    "value": "Concentration",
    "unit": "UnitOfMeasurement",
    "station_id": "SamplingPoint",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "pollutant": "Pollutant",
    "validity": "Validity",
    "verification": "Verification",
}


class EEAParquetConnector(BaseConnector):
    name = "European Environment Agency Air Quality"
    source_id = "eea-air-quality-parquet"

    def normalize_frame(
        self,
        frame: pd.DataFrame,
        *,
        column_map: Mapping[str, str] | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> list[NormalizedObservation]:
        columns = {**DEFAULT_COLUMNS, **dict(column_map or {})}
        required = ("timestamp", "value", "unit", "station_id", "latitude", "longitude", "pollutant")
        missing = [name for name in required if columns[name] not in frame.columns]
        if missing:
            raise ValueError(f"EEA frame is missing mapped columns: {missing}")

        retrieved_at = self.retrieved_now()
        observations: list[NormalizedObservation] = []
        for index, row in frame.iterrows():
            if pd.isna(row[columns["value"]]) or pd.isna(row[columns["timestamp"]]):
                continue
            timestamp = pd.Timestamp(row[columns["timestamp"]]).to_pydatetime()
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            else:
                timestamp = timestamp.astimezone(UTC)
            pollutant = str(row[columns["pollutant"]]).strip()
            normalized_name = pollutant.lower().replace(".", "").replace(" ", "_")
            if normalized_name in {"pm25", "pm2_5"}:
                variable = "pm25"
            elif normalized_name == "pm10":
                variable = "pm10"
            else:
                variable = normalized_name
            validity = row.get(columns.get("validity", ""), "unknown")
            verification = row.get(columns.get("verification", ""), "unknown")
            station_id = str(row[columns["station_id"]])
            observations.append(
                NormalizedObservation(
                    source_name=self.name,
                    source_dataset="Air Quality Download Service Parquet",
                    source_record_id=f"{station_id}:{variable}:{timestamp.isoformat()}:{index}",
                    station_id=station_id,
                    latitude=float(row[columns["latitude"]]),
                    longitude=float(row[columns["longitude"]]),
                    country=country,
                    city=city,
                    timestamp_utc=timestamp,
                    timestamp_local=None,
                    timezone="UTC",
                    variable=variable,
                    value=float(row[columns["value"]]),
                    unit=str(row[columns["unit"]]),
                    measurement_type=MeasurementType.OBSERVED,
                    quality_flag=f"validity={validity};verification={verification}",
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license="EEA and reporting-country terms apply; preserve archive metadata and reporting status",
                    source_url="https://aqportal.discomap.eea.europa.eu/download-data/",
                )
            )
        return observations

    def fetch(
        self,
        *,
        path: str | Path,
        column_map: Mapping[str, str] | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> list[NormalizedObservation]:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        try:
            frame = pd.read_parquet(file_path)
        except (ImportError, ValueError, OSError) as exc:
            raise ConnectorError(
                "Unable to read EEA Parquet. Install the research extra with pyarrow and verify the archive."
            ) from exc
        return self.normalize_frame(
            frame,
            column_map=column_map,
            country=country,
            city=city,
        )
