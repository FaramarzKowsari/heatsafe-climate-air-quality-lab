from __future__ import annotations

import os
from calendar import monthrange
from datetime import UTC, date, datetime, time
from typing import Any, Iterable

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
        *,
        timeout_seconds: float = 120.0,
        requests_per_second: float | None = 0.15,
        **kwargs: Any,
    ) -> None:
        resolved_email = email or os.getenv("EPA_AQS_EMAIL")
        resolved_key = api_key or os.getenv("EPA_AQS_KEY")
        if not resolved_email or not resolved_key:
            raise ValueError(
                "EPA AQS credentials require EPA_AQS_EMAIL and EPA_AQS_KEY"
            )
        super().__init__(
            timeout_seconds=timeout_seconds,
            requests_per_second=requests_per_second,
            **kwargs,
        )
        self.email = resolved_email
        self.api_key = resolved_key

    @staticmethod
    def _monthly_windows(
        start: date,
        end: date,
    ) -> Iterable[tuple[date, date]]:
        current = start
        while current <= end:
            final_day = monthrange(current.year, current.month)[1]
            month_end = date(current.year, current.month, final_day)
            window_end = min(month_end, end)
            yield current, window_end
            current = date.fromordinal(window_end.toordinal() + 1)

    @staticmethod
    def _is_timeout_error(error: Exception) -> bool:
        message = str(error).lower()
        return "timed out" in message or "timeout" in message

    def _request_window(
        self,
        *,
        parameter_code: str,
        start: date,
        end: date,
        state_code: str,
        county_code: str,
    ) -> list[dict[str, Any]]:
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
            raise ConnectorError(
                "EPA AQS request failed for "
                f"{start.isoformat()} through {end.isoformat()}: {exc}"
            ) from exc

        payload = result.payload
        if not isinstance(payload, dict):
            raise ConnectorError("EPA AQS returned a non-object payload")

        header = payload.get("Header", [])
        if isinstance(header, list) and header:
            status = str(header[0].get("status", "")).lower()
            if "failed" in status or "error" in status:
                raise ConnectorError(
                    "EPA AQS response status for "
                    f"{start.isoformat()} through {end.isoformat()}: "
                    f"{header[0]}"
                )

        rows = payload.get("Data", [])
        if not isinstance(rows, list):
            raise ConnectorError("EPA AQS Data field is not a list")
        return [row for row in rows if isinstance(row, dict)]

    def _request_window_adaptive(
        self,
        *,
        parameter_code: str,
        start: date,
        end: date,
        state_code: str,
        county_code: str,
    ) -> list[dict[str, Any]]:
        try:
            return self._request_window(
                parameter_code=parameter_code,
                start=start,
                end=end,
                state_code=state_code,
                county_code=county_code,
            )
        except ConnectorError as exc:
            if not self._is_timeout_error(exc) or start >= end:
                raise

            span_days = (end - start).days
            midpoint = date.fromordinal(
                start.toordinal() + span_days // 2
            )
            next_day = date.fromordinal(midpoint.toordinal() + 1)

            left = self._request_window_adaptive(
                parameter_code=parameter_code,
                start=start,
                end=midpoint,
                state_code=state_code,
                county_code=county_code,
            )
            right = self._request_window_adaptive(
                parameter_code=parameter_code,
                start=next_day,
                end=end,
                state_code=state_code,
                county_code=county_code,
            )
            return [*left, *right]

    @staticmethod
    def _parse_row(
        row: dict[str, Any],
        *,
        parameter_code: str,
        state_code: str,
        county_code: str,
        city: str | None,
        country: str,
        retrieved_at: datetime,
    ) -> NormalizedObservation | None:
        if row.get("sample_measurement") is None:
            return None

        date_gmt = str(row.get("date_gmt") or "")
        time_gmt = str(row.get("time_gmt") or "00:00")
        if not date_gmt:
            return None

        parsed_time = time.fromisoformat(time_gmt[:5])
        timestamp = datetime.combine(
            date.fromisoformat(date_gmt),
            parsed_time,
            tzinfo=UTC,
        )
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        if latitude is None or longitude is None:
            return None

        site_id = (
            f"{str(row.get('state_code', state_code)).zfill(2)}-"
            f"{str(row.get('county_code', county_code)).zfill(3)}-"
            f"{str(row.get('site_number', 'unknown')).zfill(4)}"
        )
        parameter_name = str(
            row.get("parameter") or f"parameter_{parameter_code}"
        )
        variable = (
            "pm25"
            if parameter_code in {"88101", "88502"}
            or "PM2.5" in parameter_name.upper()
            else parameter_name.lower().replace(" ", "_")
        )
        qualifiers = row.get("qualifier")
        quality_parts = [
            f"sample_duration={row.get('sample_duration', 'unknown')}",
            f"method_code={row.get('method_code', 'unknown')}",
            f"qualifier={qualifiers or 'none'}",
        ]

        return NormalizedObservation(
            source_name=EPAAQSConnector.name,
            source_dataset="AQS Sample Data by County",
            source_record_id=(
                f"{site_id}:{parameter_code}:"
                f"{timestamp.isoformat()}:{row.get('poc', '')}"
            ),
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
            license=(
                "United States government data; retain EPA AQS method, "
                "qualifier, duration, and site metadata"
            ),
            source_url=(
                "https://aqs.epa.gov/aqsweb/documents/data_api.html"
            ),
        )

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
        if start.year != end.year:
            raise ValueError(
                "EPA AQS begin_date and end_date must be in the same year"
            )

        rows: list[dict[str, Any]] = []
        for window_start, window_end in self._monthly_windows(start, end):
            rows.extend(
                self._request_window_adaptive(
                    parameter_code=parameter_code,
                    start=window_start,
                    end=window_end,
                    state_code=state_code,
                    county_code=county_code,
                )
            )

        retrieved_at = self.retrieved_now()
        deduplicated: dict[str, NormalizedObservation] = {}
        for row in rows:
            observation = self._parse_row(
                row,
                parameter_code=parameter_code,
                state_code=state_code,
                county_code=county_code,
                city=city,
                country=country,
                retrieved_at=retrieved_at,
            )
            if observation is None:
                continue
            key = observation.source_record_id or (
                f"{observation.station_id}:"
                f"{observation.timestamp_utc.isoformat()}:"
                f"{observation.value}"
            )
            deduplicated[key] = observation

        return sorted(
            deduplicated.values(),
            key=lambda item: (
                item.timestamp_utc,
                item.station_id or "",
                item.source_record_id or "",
            ),
        )
