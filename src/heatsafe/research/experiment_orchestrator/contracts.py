from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from heatsafe.research.nexus.contracts import NexusConfig


DatasetKind = Literal["synthetic", "csv", "snapshot"]
ReleaseStatus = Literal["candidate", "reviewed"]


class DatasetSpec(BaseModel):
    kind: DatasetKind = "synthetic"
    path: str | None = None
    rows: int = Field(default=720, ge=240)
    seed: int = 42
    variables: tuple[str, ...] = (
        "pm25",
        "temperature_c",
        "relative_humidity_pct",
        "wind_speed_kmh",
        "smoke_proxy",
    )
    station_id: str | None = None
    frequency: str = "1h"

    @field_validator("variables")
    @classmethod
    def unique_variables(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
    def validate_path(self) -> DatasetSpec:
        if self.kind in {"csv", "snapshot"} and not self.path:
            raise ValueError("path is required for csv and snapshot datasets")
        if self.kind == "snapshot" and not self.variables:
            raise ValueError("variables are required for snapshot datasets")
        return self


class ReportSpec(BaseModel):
    title: str = Field(min_length=5)
    subtitle: str = "Paper-ready reproducible environmental forecasting results"
    author: str = "Faramarz Kowsari"
    organization: str = "HeatSafe Research Lab"
    abstract: str = Field(
        default=(
            "This report records a reproducible HeatAQ Nexus forecasting experiment "
            "with chronological evaluation, explicit baselines, uncertainty metrics, "
            "checksums and exact reproduction commands."
        ),
        min_length=20,
    )
    keywords: tuple[str, ...] = (
        "environmental intelligence",
        "air quality",
        "heat",
        "forecasting",
        "reproducibility",
    )

    @field_validator("keywords")
    @classmethod
    def unique_keywords(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        clean = tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not clean:
            raise ValueError("At least one keyword is required")
        return clean


class ReleaseSpec(BaseModel):
    version: str = Field(default="0.1.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    status: ReleaseStatus = "candidate"
    create_zip: bool = True
    license: str = "CC-BY-4.0"


class ExperimentSpec(BaseModel):
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,100}$")
    title: str = Field(min_length=5)
    description: str = Field(min_length=20)
    dataset: DatasetSpec = Field(default_factory=DatasetSpec)
    nexus: NexusConfig
    report: ReportSpec
    release: ReleaseSpec = Field(default_factory=ReleaseSpec)
    notes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Results apply only to the evaluated data identity and split protocol.",
        "Synthetic demonstration data are a software-validation fixture, not evidence about a real city.",
        "The system is not an official warning service or medical decision tool.",
    )
    created_by: str = "Faramarz Kowsari"

    @field_validator("notes", "limitations")
    @classmethod
    def unique_text(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


class ExperimentRunResult(BaseModel):
    experiment_id: str
    output_directory: str
    report_html: str
    report_markdown: str
    checksums: str
    verification: str
    release_archive: str | None
    best_by_horizon: dict[int, str]
