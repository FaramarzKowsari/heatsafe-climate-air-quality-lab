from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewedReleaseConfig(BaseModel):
    release_id: str = Field(
        default="epa-pm25-2025-first-real-reviewed",
        pattern=r"^[a-z0-9][a-z0-9._-]{2,120}$",
    )
    version: str = Field(
        default="0.1.0",
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )
    title: str = (
        "US EPA AirData PM2.5 Forecasting Benchmark — "
        "First Reviewed Official-Source Release"
    )
    creator_name: str = "Kowsari, Faramarz"
    creator_orcid: str = "0000-0003-1692-0453"
    repository_url: str = (
        "https://github.com/FaramarzKowsari/"
        "heatsafe-climate-air-quality-lab"
    )
    project_url: str = (
        "https://faramarzkowsari.github.io/"
        "heatsafe-climate-air-quality-lab/"
    )
    license_spdx: str = "CC-BY-4.0"
    zenodo_license: str = "cc-by-4.0"
    access_right: str = "open"
    keywords: tuple[str, ...] = (
        "US EPA AirData",
        "PM2.5",
        "air quality",
        "forecasting",
        "environmental data",
        "reproducibility",
        "uncertainty",
        "Alameda County",
        "California",
    )
    include_canonical_input: bool = True
    include_figures: bool = True
    include_tables: bool = True
    include_nexus_artifacts: bool = True
    create_zip: bool = True


class ReleaseBuildResult(BaseModel):
    release_directory: str
    release_archive: str | None
    release_manifest: str
    release_summary_html: str
    release_summary_json: str
    zenodo_metadata: str
    citation_cff: str
    checksums: str
    verification: dict[str, object]
