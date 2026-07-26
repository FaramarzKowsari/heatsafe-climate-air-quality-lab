from __future__ import annotations

import httpx
import pandas as pd

from heatsafe.connectors.eea_parquet import EEAParquetConnector
from heatsafe.connectors.epa_aqs import EPAAQSConnector
from heatsafe.connectors.nasa_firms import NASAFIRMSAreaConnector
from heatsafe.connectors.noaa_cdo import NOAACDOConnector


def test_noaa_cdo_normalizes_metric_temperature() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["token"] == "test-token"
        return httpx.Response(
            200,
            json={
                "metadata": {"resultset": {"count": 1}},
                "results": [
                    {
                        "date": "2026-07-01T00:00:00",
                        "datatype": "TMAX",
                        "station": "GHCND:TEST",
                        "attributes": ",,W,",
                        "value": 31.2,
                    }
                ],
            },
            request=request,
        )

    connector = NOAACDOConnector(
        token="test-token",
        transport=httpx.MockTransport(handler),
    )
    observations = connector.fetch(
        station_id="GHCND:TEST",
        latitude=40.0,
        longitude=-75.0,
        start="2026-07-01",
        end="2026-07-01",
    )
    assert observations[0].variable == "maximum_temperature_c"
    assert observations[0].unit == "°C"
    assert observations[0].value == 31.2


def test_epa_aqs_preserves_site_and_method_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Header": [{"status": "Success"}],
                "Data": [
                    {
                        "state_code": "37",
                        "county_code": "183",
                        "site_number": "0014",
                        "parameter_code": "88101",
                        "parameter": "PM2.5 - Local Conditions",
                        "date_gmt": "2026-07-01",
                        "time_gmt": "12:00",
                        "sample_measurement": 10.5,
                        "units_of_measure": "Micrograms/cubic meter (LC)",
                        "latitude": 35.8,
                        "longitude": -78.7,
                        "sample_duration": "1 HOUR",
                        "method_code": "170",
                        "qualifier": None,
                        "poc": 1,
                        "local_site_name": "Test Site",
                    }
                ],
            },
            request=request,
        )

    connector = EPAAQSConnector(
        email="researcher@example.org",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    observations = connector.fetch(
        parameter_code="88101",
        begin_date="2026-07-01",
        end_date="2026-07-01",
        state_code="37",
        county_code="183",
    )
    assert observations[0].variable == "pm25"
    assert observations[0].station_id == "37-183-0014"
    assert "method_code=170" in observations[0].quality_flag


def test_firms_parses_fire_radiative_power() -> None:
    csv_text = (
        "latitude,longitude,acq_date,acq_time,frp,satellite,confidence,daynight,version\n"
        "39.0,28.0,2026-07-01,1345,18.4,N,nominal,D,2.0NRT\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=csv_text, request=request)

    connector = NASAFIRMSAreaConnector(
        map_key="test-map-key",
        transport=httpx.MockTransport(handler),
    )
    observations = connector.fetch(west=27, south=38, east=29, north=40)
    assert observations[0].variable == "fire_radiative_power_mw"
    assert observations[0].value == 18.4


def test_eea_frame_normalization() -> None:
    frame = pd.DataFrame(
        [
            {
                "DatetimeBegin": "2026-07-01T12:00:00+00:00",
                "Concentration": 9.4,
                "UnitOfMeasurement": "µg/m³",
                "SamplingPoint": "TRX001",
                "Latitude": 41.0,
                "Longitude": 29.0,
                "Pollutant": "PM2.5",
                "Validity": 1,
                "Verification": 1,
            }
        ]
    )
    observations = EEAParquetConnector().normalize_frame(frame, country="TR")
    assert observations[0].variable == "pm25"
    assert observations[0].station_id == "TRX001"
