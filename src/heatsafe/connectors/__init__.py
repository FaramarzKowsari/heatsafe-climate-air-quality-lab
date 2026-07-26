"""Environmental data adapters with explicit provenance and licensing metadata."""

from .nasa_power import NASAPowerDailyConnector
from .open_meteo import OpenMeteoAirQualityConnector, OpenMeteoWeatherConnector
from .openaq import OpenAQConnector

__all__ = [
    "NASAPowerDailyConnector",
    "OpenMeteoAirQualityConnector",
    "OpenMeteoWeatherConnector",
    "OpenAQConnector",
]
