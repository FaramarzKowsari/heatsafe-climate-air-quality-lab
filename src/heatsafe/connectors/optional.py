from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OptionalConnectorSpec:
    name: str
    environment_variables: tuple[str, ...]
    documentation_url: str
    authentication: str
    status: str
    implementation_note: str


OPTIONAL_CONNECTORS = [
    OptionalConnectorSpec(
        name="NOAA Climate Data Online v2",
        environment_variables=("NOAA_CDO_TOKEN",),
        documentation_url="https://www.ncei.noaa.gov/cdo-web/webservices/v2",
        authentication="token header",
        status="adapter contract documented; live credential required",
        implementation_note="Use GHCND station data for observation-focused U.S. climate studies.",
    ),
    OptionalConnectorSpec(
        name="US EPA AQS",
        environment_variables=("EPA_AQS_EMAIL", "EPA_AQS_KEY"),
        documentation_url="https://aqs.epa.gov/aqsweb/documents/ramltohtml.html",
        authentication="email and key",
        status="adapter contract documented; live credential required",
        implementation_note="Prefer AQS for regulatory and historical U.S. ground-monitor data.",
    ),
    OptionalConnectorSpec(
        name="NASA FIRMS",
        environment_variables=("NASA_FIRMS_MAP_KEY",),
        documentation_url="https://firms.modaps.eosdis.nasa.gov/api/area/",
        authentication="free MAP_KEY",
        status="adapter contract documented; live credential required",
        implementation_note="Use active-fire detections as evidence, not proof of smoke exposure.",
    ),
    OptionalConnectorSpec(
        name="Copernicus Climate Data Store ERA5-Land",
        environment_variables=("CDS_API_URL", "CDS_API_KEY"),
        documentation_url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
        authentication="CDS credentials",
        status="workflow documented; large-download connector deferred",
        implementation_note="Use for long-term reanalysis and clearly label data as reanalysis.",
    ),
    OptionalConnectorSpec(
        name="EEA Air Quality Download Service",
        environment_variables=(),
        documentation_url="https://www.eea.europa.eu/en/datahub/datahubitem-view/778ef9f5-6293-4846-badd-56a29c70880d",
        authentication="service dependent",
        status="download workflow documented; bulk parquet ingestion deferred",
        implementation_note="Use verified and up-to-date European measurements with country metadata.",
    ),
    OptionalConnectorSpec(
        name="ECCC MSC GeoMet OGC API",
        environment_variables=(),
        documentation_url="https://api.weather.gc.ca/?f=html",
        authentication="public OGC API",
        status="collection discovery documented; dataset-specific ingestion deferred",
        implementation_note="Select explicit collections and preserve ECCC end-use licence metadata.",
    ),
    OptionalConnectorSpec(
        name="Türkiye Meteoroloji Genel Müdürlüğü",
        environment_variables=(),
        documentation_url="https://www.mgm.gov.tr/",
        authentication="source and service dependent",
        status="official-source workflow documented; public API contract requires verification",
        implementation_note="Use official meteorological products and preserve Turkish attribution and service terms.",
    ),
    OptionalConnectorSpec(
        name="Türkiye National Air Quality Monitoring",
        environment_variables=(),
        documentation_url="https://sim.csb.gov.tr/",
        authentication="source and service dependent",
        status="official-source workflow documented; stable machine API requires verification",
        implementation_note="Use station measurements only with verified access, units, quality flags, and redistribution terms.",
    ),
    OptionalConnectorSpec(
        name="Eurostat Electricity Prices",
        environment_variables=(),
        documentation_url="https://ec.europa.eu/eurostat/web/energy/database",
        authentication="public dataset",
        status="regional-default workflow documented",
        implementation_note="User-entered tariff always overrides a regional average.",
    ),
    OptionalConnectorSpec(
        name="US EIA Open Data",
        environment_variables=("EIA_API_KEY",),
        documentation_url="https://www.eia.gov/opendata/",
        authentication="API key",
        status="regional-default workflow documented; live adapter deferred",
        implementation_note="Use only for labeled regional reference prices, not a household tariff.",
    ),
    OptionalConnectorSpec(
        name="EPİAŞ Transparency Platform",
        environment_variables=(),
        documentation_url="https://seffaflik.epias.com.tr/",
        authentication="endpoint dependent",
        status="Türkiye energy workflow documented; adapter deferred",
        implementation_note="Verify current endpoint and reuse terms before integration.",
    ),
]
