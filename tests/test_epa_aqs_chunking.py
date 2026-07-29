from __future__ import annotations

from urllib.parse import parse_qs

import httpx

from heatsafe.connectors.epa_aqs import EPAAQSConnector
from heatsafe.data_foundation.http import RetryPolicy


def _row(date_gmt: str, value: float = 12.5) -> dict[str, object]:
    return {
        "state_code": "06",
        "county_code": "001",
        "site_number": "0001",
        "parameter": "PM2.5 - Local Conditions",
        "sample_measurement": value,
        "date_gmt": date_gmt,
        "time_gmt": "00:00",
        "latitude": 37.8,
        "longitude": -122.2,
        "poc": 1,
        "sample_duration": "1 HOUR",
        "method_code": "100",
        "qualifier": None,
        "units_of_measure": "Micrograms/cubic meter (LC)",
        "local_site_name": "Test Site",
    }


def test_epa_connector_splits_requests_by_calendar_month() -> None:
    requested: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = parse_qs(request.url.query.decode())
        requested.append((query["bdate"][0], query["edate"][0]))
        return httpx.Response(
            200,
            json={
                "Header": [{"status": "Success"}],
                "Data": [_row(query["bdate"][0])],
            },
        )

    connector = EPAAQSConnector(
        email="test@example.com",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        requests_per_second=None,
        timeout_seconds=1,
    )
    observations = connector.fetch(
        parameter_code="88101",
        begin_date="2025-01-15",
        end_date="2025-03-02",
        state_code="06",
        county_code="001",
    )

    assert requested == [
        ("20250115", "20250131"),
        ("20250201", "20250228"),
        ("20250301", "20250302"),
    ]
    assert len(observations) == 3


def test_epa_connector_bisects_a_window_after_timeout() -> None:
    requested: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = parse_qs(request.url.query.decode())
        begin = query["bdate"][0]
        end = query["edate"][0]
        requested.append((begin, end))

        if begin == "20250101" and end == "20250131":
            raise httpx.ReadTimeout(
                "simulated timeout",
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "Header": [{"status": "Success"}],
                "Data": [_row(begin)],
            },
        )

    connector = EPAAQSConnector(
        email="test@example.com",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        requests_per_second=None,
        timeout_seconds=1,
        retry_policy=RetryPolicy(maximum_attempts=1),
    )
    observations = connector.fetch(
        parameter_code="88101",
        begin_date="2025-01-01",
        end_date="2025-01-31",
        state_code="06",
        county_code="001",
    )

    assert requested == [
        ("20250101", "20250131"),
        ("20250101", "20250116"),
        ("20250117", "20250131"),
    ]
    assert len(observations) == 2
