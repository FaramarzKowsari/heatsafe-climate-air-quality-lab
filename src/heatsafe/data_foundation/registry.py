from __future__ import annotations

from heatsafe.data_foundation.contracts import (
    AccessMode,
    LicenseStatus,
    SourceCategory,
    SourceDescriptor,
)


BUILTIN_SOURCES: tuple[SourceDescriptor, ...] = (
    SourceDescriptor(
        source_id="noaa-cdo-ghcnd",
        name="NOAA NCEI Climate Data Online — GHCN Daily",
        category=SourceCategory.CLIMATE,
        authority="NOAA National Centers for Environmental Information",
        access_mode=AccessMode.TOKEN,
        homepage="https://www.ncei.noaa.gov/cdo-web/",
        documentation_url="https://www.ncei.noaa.gov/cdo-web/webservices/v2",
        license_summary="United States government data; dataset-specific attribution and use guidance apply.",
        license_status=LicenseStatus.PROVIDER_SPECIFIC,
        credential_environment_variables=("NOAA_CDO_TOKEN",),
        temporal_resolution="daily",
        spatial_resolution="station",
        measurement_type="observed",
        production_status="implemented-foundation",
        redistribution_notes="Preserve station, datatype, attributes and retrieval metadata.",
        citation_text="NOAA National Centers for Environmental Information, Climate Data Online.",
        tags=("temperature", "precipitation", "stations", "ghcnd"),
    ),
    SourceDescriptor(
        source_id="epa-aqs",
        name="US EPA Air Quality System Data API",
        category=SourceCategory.AIR_QUALITY,
        authority="United States Environmental Protection Agency",
        access_mode=AccessMode.CREDENTIAL,
        homepage="https://www.epa.gov/aqs",
        documentation_url="https://aqs.epa.gov/aqsweb/documents/data_api.html",
        license_summary="United States government air-quality data; originating agency and method metadata remain important.",
        license_status=LicenseStatus.PROVIDER_SPECIFIC,
        credential_environment_variables=("EPA_AQS_EMAIL", "EPA_AQS_KEY"),
        temporal_resolution="sample-level",
        spatial_resolution="monitoring site",
        measurement_type="observed",
        production_status="implemented-foundation",
        redistribution_notes="Retain qualifiers, methods, duration, site identifiers and GMT timestamps.",
        citation_text="US EPA Air Quality System Data API.",
        tags=("pm25", "ozone", "no2", "monitoring", "usa"),
    ),
    SourceDescriptor(
        source_id="eea-air-quality-parquet",
        name="European Environment Agency Air Quality Download Service",
        category=SourceCategory.AIR_QUALITY,
        authority="European Environment Agency",
        access_mode=AccessMode.LOCAL_FILE,
        homepage="https://aqportal.discomap.eea.europa.eu/download-data/",
        documentation_url="https://www.eea.europa.eu/en/datahub/datahubitem-view/778ef9f5-6293-4846-badd-56a29c70880d",
        license_summary="EEA and reporting-country conditions apply; verify dataset metadata for each download.",
        license_status=LicenseStatus.REVIEW_REQUIRED,
        temporal_resolution="hourly or source-reported",
        spatial_resolution="monitoring station",
        measurement_type="observed",
        production_status="local-parquet-normalizer",
        redistribution_notes="Snapshots should preserve the original archive checksum and reporting status.",
        citation_text="European Environment Agency Air Quality Download Service.",
        tags=("europe", "pm25", "parquet", "stations"),
    ),
    SourceDescriptor(
        source_id="nasa-firms-area",
        name="NASA FIRMS Area API",
        category=SourceCategory.FIRE,
        authority="NASA Fire Information for Resource Management System",
        access_mode=AccessMode.TOKEN,
        homepage="https://firms.modaps.eosdis.nasa.gov/",
        documentation_url="https://firms.modaps.eosdis.nasa.gov/api/area/",
        license_summary="NASA Earth observation data with source-specific attribution requirements.",
        license_status=LicenseStatus.PROVIDER_SPECIFIC,
        credential_environment_variables=("NASA_FIRMS_MAP_KEY",),
        temporal_resolution="near-real-time detections",
        spatial_resolution="satellite detection",
        measurement_type="satellite-derived",
        production_status="implemented-foundation",
        redistribution_notes="Do not describe detections as confirmed smoke impact at a target location.",
        citation_text="NASA FIRMS active fire data.",
        tags=("wildfire", "viirs", "modis", "frp"),
    ),
    SourceDescriptor(
        source_id="era5-land",
        name="Copernicus ERA5-Land",
        category=SourceCategory.REANALYSIS,
        authority="Copernicus Climate Change Service",
        access_mode=AccessMode.CREDENTIAL,
        homepage="https://cds.climate.copernicus.eu/",
        documentation_url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
        license_summary="Copernicus terms and required acknowledgement apply.",
        license_status=LicenseStatus.PROVIDER_SPECIFIC,
        credential_environment_variables=("CDSAPI_URL", "CDSAPI_KEY"),
        temporal_resolution="hourly",
        spatial_resolution="gridded reanalysis",
        measurement_type="reanalysis",
        production_status="request-specification-only",
        redistribution_notes="Large downloads and derived products require explicit versioning and provenance.",
        citation_text="Copernicus Climate Change Service ERA5-Land.",
        tags=("reanalysis", "temperature", "humidity", "europe", "global"),
    ),
    SourceDescriptor(
        source_id="turkiye-mgm",
        name="Türkiye State Meteorological Service",
        category=SourceCategory.WEATHER,
        authority="Meteoroloji Genel Müdürlüğü",
        access_mode=AccessMode.DISCOVERY_REQUIRED,
        homepage="https://www.mgm.gov.tr/",
        documentation_url="https://www.mgm.gov.tr/",
        license_summary="Machine access and redistribution conditions must be verified before automation.",
        license_status=LicenseStatus.REVIEW_REQUIRED,
        temporal_resolution="source-dependent",
        spatial_resolution="source-dependent",
        measurement_type="observed-or-forecast",
        production_status="registry-only",
        redistribution_notes="No undocumented endpoint is embedded in HeatSafe.",
        citation_text="Meteoroloji Genel Müdürlüğü.",
        tags=("turkiye", "weather", "stations"),
    ),
    SourceDescriptor(
        source_id="turkiye-air-quality",
        name="Türkiye National Air Quality Monitoring Network",
        category=SourceCategory.AIR_QUALITY,
        authority="Türkiye environmental authorities",
        access_mode=AccessMode.DISCOVERY_REQUIRED,
        homepage="https://sim.csb.gov.tr/",
        documentation_url="https://sim.csb.gov.tr/",
        license_summary="Machine access, station metadata and redistribution conditions require verification.",
        license_status=LicenseStatus.REVIEW_REQUIRED,
        temporal_resolution="source-dependent",
        spatial_resolution="monitoring station",
        measurement_type="observed",
        production_status="registry-only",
        redistribution_notes="No undocumented endpoint is embedded in HeatSafe.",
        citation_text="Türkiye National Air Quality Monitoring Network.",
        tags=("turkiye", "pm25", "air-quality"),
    ),
)


class SourceRegistry:
    def __init__(self, sources: tuple[SourceDescriptor, ...] = BUILTIN_SOURCES) -> None:
        self._sources = {source.source_id: source for source in sources}
        if len(self._sources) != len(sources):
            raise ValueError("Duplicate source_id values are not allowed")

    def list(self) -> list[SourceDescriptor]:
        return sorted(self._sources.values(), key=lambda source: source.source_id)

    def get(self, source_id: str) -> SourceDescriptor:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KeyError(f"Unknown source_id: {source_id}") from exc

    def filter(
        self,
        *,
        category: SourceCategory | None = None,
        access_mode: AccessMode | None = None,
    ) -> list[SourceDescriptor]:
        return [
            source
            for source in self.list()
            if (category is None or source.category == category)
            and (access_mode is None or source.access_mode == access_mode)
        ]


DEFAULT_REGISTRY = SourceRegistry()
