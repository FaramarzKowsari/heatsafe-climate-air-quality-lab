from __future__ import annotations

from pydantic import BaseModel, field_validator


class ERA5LandRequestSpec(BaseModel):
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
    data_format: str = "netcdf"
    download_format: str = "unarchived"

    @field_validator("years")
    @classmethod
    def validate_years(cls, years: tuple[int, ...]) -> tuple[int, ...]:
        if not years:
            raise ValueError("At least one year is required")
        if any(year < 1950 or year > 2100 for year in years):
            raise ValueError("ERA5-Land years must be between 1950 and 2100")
        return years

    def to_cds_request(self) -> dict[str, object]:
        request: dict[str, object] = {
            "variable": list(self.variables),
            "year": [f"{year:04d}" for year in self.years],
            "month": [f"{month:02d}" for month in self.months],
            "day": [f"{day:02d}" for day in self.days],
            "time": [f"{hour:02d}:00" for hour in self.hours],
            "data_format": self.data_format,
            "download_format": self.download_format,
        }
        if self.area is not None:
            north, west, south, east = self.area
            request["area"] = [north, west, south, east]
        return request
