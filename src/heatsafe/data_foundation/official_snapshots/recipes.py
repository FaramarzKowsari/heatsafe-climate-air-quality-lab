from __future__ import annotations

from datetime import date
from typing import Any, TypeAlias

from pydantic import BaseModel, Field, field_validator, model_validator

from heatsafe.data_foundation.era5_land import ERA5LandRequestSpec


class NOAARequest(BaseModel):
    station_id: str = Field(min_length=3)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start: date
    end: date
    datatypes: tuple[str, ...] = ("TAVG", "TMAX", "TMIN", "PRCP", "AWND")
    city: str | None = None
    country: str | None = "US"

    @model_validator(mode="after")
    def chronological(self) -> NOAARequest:
        if self.end < self.start:
            raise ValueError("end must not precede start")
        return self


class EPARequest(BaseModel):
    parameter_code: str = Field(min_length=3)
    begin_date: date
    end_date: date
    state_code: str = Field(min_length=1, max_length=2)
    county_code: str = Field(min_length=1, max_length=3)
    city: str | None = None
    country: str = "US"

    @model_validator(mode="after")
    def chronological(self) -> EPARequest:
        if self.end_date < self.begin_date:
            raise ValueError("end_date must not precede begin_date")
        return self


class FIRMSRequest(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    day_range: int = Field(default=1, ge=1, le=10)
    source: str = "VIIRS_SNPP_NRT"
    date_value: date | None = None
    country: str | None = None
    city: str | None = None

    @model_validator(mode="after")
    def valid_bounds(self) -> FIRMSRequest:
        if self.west >= self.east:
            raise ValueError("west must be less than east")
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        return self


class EEARequest(BaseModel):
    path: str = Field(min_length=1)
    column_map: dict[str, str] = Field(default_factory=dict)
    country: str | None = None
    city: str | None = None


class ERA5Request(BaseModel):
    variables: tuple[str, ...] = (
        "2m_temperature",
        "2m_dewpoint_temperature",
        "surface_solar_radiation_downwards",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
    )
    years: tuple[int, ...]
    months: tuple[int, ...] = tuple(range(1, 13))
    days: tuple[int, ...] = tuple(range(1, 32))
    hours: tuple[int, ...] = tuple(range(24))
    area: tuple[float, float, float, float] | None = None

    @field_validator("years")
    @classmethod
    def years_are_present(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if not values:
            raise ValueError("At least one year is required")
        return values

    def to_cds_request(self) -> dict[str, object]:
        return ERA5LandRequestSpec(
            variables=self.variables,
            years=self.years,
            months=self.months,
            days=self.days,
            hours=self.hours,
            area=self.area,
        ).to_cds_request()


RequestRecipe: TypeAlias = (
    NOAARequest
    | EPARequest
    | FIRMSRequest
    | EEARequest
    | ERA5Request
)


REDACTED = "[REDACTED]"
SENSITIVE_FRAGMENTS = (
    "token",
    "key",
    "password",
    "secret",
    "authorization",
    "email",
)


def recipe_for_source(
    source_id: str,
    parameters: dict[str, Any],
) -> RequestRecipe:
    if source_id == "noaa-cdo-ghcnd":
        return NOAARequest.model_validate(parameters)
    if source_id == "epa-aqs":
        return EPARequest.model_validate(parameters)
    if source_id == "nasa-firms-area":
        return FIRMSRequest.model_validate(parameters)
    if source_id == "eea-air-quality-parquet":
        return EEARequest.model_validate(parameters)
    if source_id == "era5-land":
        return ERA5Request.model_validate(parameters)
    raise ValueError(f"Pack 06 has no acquisition recipe for source_id={source_id!r}")


def sanitize_parameters(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS):
                result[str(key)] = REDACTED
            else:
                result[str(key)] = sanitize_parameters(item)
        return result
    if isinstance(value, list):
        return [sanitize_parameters(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_parameters(item) for item in value]
    return value
