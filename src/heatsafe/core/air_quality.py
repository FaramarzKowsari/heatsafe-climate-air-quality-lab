from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AirQualitySummary:
    pollutant: str
    unit: str
    count: int
    completeness_pct: float
    mean: float
    median: float
    minimum: float
    maximum: float
    p95: float
    event_count: int
    standard: str | None
    latest_aqi: int | None
    warnings: list[str]


PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]
PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500),
]


def _interpolate_aqi(value: float, breakpoints: list[tuple[float, float, int, int]]) -> int:
    value = max(0.0, value)
    for concentration_low, concentration_high, index_low, index_high in breakpoints:
        if concentration_low <= value <= concentration_high:
            index = ((index_high - index_low) / (concentration_high - concentration_low)) * (
                value - concentration_low
            ) + index_low
            return int(round(index))
    return 500


def us_epa_aqi(pollutant: str, concentration: float) -> int:
    pollutant_key = pollutant.lower().replace(".", "").replace("_", "")
    if pollutant_key == "pm25":
        return _interpolate_aqi(np.floor(concentration * 10) / 10, PM25_BREAKPOINTS)
    if pollutant_key == "pm10":
        return _interpolate_aqi(round(concentration), PM10_BREAKPOINTS)
    raise ValueError("Only PM2.5 and PM10 are implemented for the explicitly labeled US EPA AQI example")


def summarize_air_quality(
    timestamps: Iterable[object],
    values: Iterable[float | None],
    *,
    pollutant: str = "PM2.5",
    unit: str = "µg/m³",
    event_threshold: float | None = 35.0,
    aqi_standard: str | None = None,
) -> AirQualitySummary:
    frame = pd.DataFrame({"timestamp": list(timestamps), "value": list(values)})
    if frame.empty:
        raise ValueError("At least one air-quality record is required")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    expected = len(frame)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    valid = frame.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
    if valid.empty:
        raise ValueError("No valid air-quality records remain after validation")
    if (valid["value"] < 0).any():
        raise ValueError("Negative pollutant concentrations are not accepted")
    completeness = 100.0 * len(valid) / expected

    threshold = event_threshold
    event_count = 0
    if threshold is not None:
        above = valid["value"] >= threshold
        event_count = int((above & ~above.shift(fill_value=False)).sum())

    latest_aqi: int | None = None
    warnings = ["Raw concentrations and AQI values are not interchangeable."]
    if aqi_standard == "US EPA AQI":
        latest_aqi = us_epa_aqi(pollutant, float(valid.iloc[-1]["value"]))
        warnings.append("The displayed AQI is explicitly the US EPA AQI and should not be relabeled as a European index.")
    elif aqi_standard:
        warnings.append(f"AQI standard '{aqi_standard}' was requested but no conversion was applied.")

    if completeness < 90:
        warnings.append(f"Completeness is {completeness:.1f}%; summary statistics may be biased by missing periods.")

    return AirQualitySummary(
        pollutant=pollutant,
        unit=unit,
        count=len(valid),
        completeness_pct=round(completeness, 2),
        mean=round(float(valid["value"].mean()), 3),
        median=round(float(valid["value"].median()), 3),
        minimum=round(float(valid["value"].min()), 3),
        maximum=round(float(valid["value"].max()), 3),
        p95=round(float(valid["value"].quantile(0.95)), 3),
        event_count=event_count,
        standard=aqi_standard,
        latest_aqi=latest_aqi,
        warnings=warnings,
    )
