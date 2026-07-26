from pathlib import Path

import httpx
import pytest
import yaml

from heatsafe.connectors.nasa_power import NasaPowerConnector
from heatsafe.connectors.open_meteo import OpenMeteoConnector
from heatsafe.connectors.openaq import OpenAQConnector
from heatsafe.core.data_contract import normalize_observation
from heatsafe.core.logs import HeatLog
from heatsafe.core.models import MeasurementType

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_parses_and_has_sources():
    data = yaml.safe_load((ROOT / "data/catalog.yml").read_text())
    assert len(data["sources"]) >= 8


def test_normalized_contract():
    observation = normalize_observation(
        source_name="x",
        source_dataset="y",
        latitude=41,
        longitude=29,
        timestamp_utc="2026-01-01T00:00:00Z",
        variable="temperature",
        value=25,
        unit="°C",
        measurement_type="observed",
        license="test",
        source_url="https://example.org",
    )
    assert observation.measurement_type is MeasurementType.OBSERVED


def test_heat_log_roundtrip(tmp_path):
    log = HeatLog()
    log.add({"timestamp": "2026-01-01T00:00:00Z", "indoor_temperature_c": 25})
    path = tmp_path / "log.json"
    log.to_json(path)
    assert HeatLog.from_json(path).records[0]["indoor_temperature_c"] == 25


def test_open_meteo_mock():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "temperature_2m": [20.0],
                    "relative_humidity_2m": [50],
                    "wind_speed_10m": [7.0],
                    "wind_direction_10m": [180],
                },
                "hourly_units": {
                    "temperature_2m": "°C",
                    "relative_humidity_2m": "%",
                    "wind_speed_10m": "km/h",
                    "wind_direction_10m": "°",
                },
            },
        )

    connector = OpenMeteoConnector(transport=httpx.MockTransport(handler))
    rows = connector.fetch(latitude=41, longitude=29, forecast_days=1)
    assert any(row.variable == "temperature_c" for row in rows)


def test_nasa_power_mock():
    def handler(request):
        return httpx.Response(
            200,
            json={"properties": {"parameter": {"T2M": {"20260101": 17.5}}}, "header": {}},
        )

    connector = NasaPowerConnector(transport=httpx.MockTransport(handler))
    rows = connector.fetch(
        latitude=41,
        longitude=29,
        start="20260101",
        end="20260101",
        parameters=["T2M"],
    )
    assert rows[0].measurement_type.value == "modeled"


def test_openaq_requires_key():
    with pytest.raises(ValueError):
        OpenAQConnector(api_key="")


def test_openaq_v3_sensor_metadata_mapping():
    def handler(request):
        if request.url.path.endswith("/latest"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "datetime": {
                                "utc": "2026-01-01T00:00:00Z",
                                "local": "2026-01-01T03:00:00+03:00",
                            },
                            "value": 11.2,
                            "coordinates": {"latitude": 41.0, "longitude": 29.0},
                            "sensorsId": 77,
                            "locationsId": 10,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 10,
                        "name": "Demo",
                        "locality": "Istanbul",
                        "timezone": "Europe/Istanbul",
                        "country": {"code": "TR"},
                        "coordinates": {"latitude": 41.0, "longitude": 29.0},
                        "licenses": [{"name": "Example License"}],
                        "sensors": [
                            {
                                "id": 77,
                                "name": "PM2.5",
                                "parameter": {"id": 2, "name": "pm25", "units": "µg/m³"},
                            }
                        ],
                    }
                ]
            },
        )

    connector = OpenAQConnector(api_key="test-key", transport=httpx.MockTransport(handler))
    rows = connector.fetch(location_id=10)
    assert rows[0].variable == "pm25"
    assert rows[0].unit == "µg/m³"
    assert rows[0].city == "Istanbul"
