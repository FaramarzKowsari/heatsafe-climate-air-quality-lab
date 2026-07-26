"""Environmental data adapters with explicit provenance and licensing metadata."""

from .eea_parquet import EEAParquetConnector
from .epa_aqs import EPAAQSConnector
from .nasa_firms import NASAFIRMSAreaConnector
from .nasa_power import NASAPowerDailyConnector
from .noaa_cdo import NOAACDOConnector
from .open_meteo import OpenMeteoAirQualityConnector, OpenMeteoWeatherConnector
from .openaq import OpenAQConnector

__all__ = [
    "EEAParquetConnector",
    "EPAAQSConnector",
    "NASAFIRMSAreaConnector",
    "NASAPowerDailyConnector",
    "NOAACDOConnector",
    "OpenAQConnector",
    "OpenMeteoAirQualityConnector",
    "OpenMeteoWeatherConnector",
]
