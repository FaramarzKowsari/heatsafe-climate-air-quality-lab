from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .models import ComparatorInput


@dataclass(frozen=True)
class ComparatorResult:
    record_count: int
    start: str
    end: str
    indoor_outdoor_temperature_difference_mean_c: float | None
    estimated_thermal_lag_steps: int | None
    indoor_temperature_rate_c_per_hour: float | None
    window_open_temperature_change_c_per_hour: float | None
    window_open_pm25_change_ug_m3_per_hour: float | None
    nighttime_recovery_c: float | None
    event_counts: dict[str, int]
    observations: list[str]
    limitations: list[str]


def _slope_per_hour(times: pd.Series, values: pd.Series) -> float | None:
    valid = pd.DataFrame({"time": times, "value": values}).dropna()
    if len(valid) < 2:
        return None
    x = (valid["time"] - valid["time"].iloc[0]).dt.total_seconds().to_numpy() / 3600
    if np.ptp(x) == 0:
        return None
    return float(np.polyfit(x, valid["value"].to_numpy(), 1)[0])


def _thermal_lag(indoor: pd.Series, outdoor: pd.Series, max_lag: int = 24) -> int | None:
    frame = pd.DataFrame({"indoor": indoor, "outdoor": outdoor}).dropna()
    if len(frame) < 10:
        return None
    indoor_centered = frame["indoor"] - frame["indoor"].mean()
    outdoor_centered = frame["outdoor"] - frame["outdoor"].mean()
    best_lag: int | None = None
    best_corr = -2.0
    for lag in range(0, min(max_lag, len(frame) // 3) + 1):
        shifted = outdoor_centered.shift(lag)
        corr = indoor_centered.corr(shifted)
        if pd.notna(corr) and corr > best_corr:
            best_corr = float(corr)
            best_lag = lag
    return best_lag


def compare_indoor_outdoor(data: ComparatorInput) -> ComparatorResult:
    rows = [record.model_dump() for record in data.records]
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp")
    frame["event"] = frame["event"].fillna("")

    temperature_difference = None
    pair = frame.dropna(subset=["indoor_temperature_c", "outdoor_temperature_c"])
    if not pair.empty:
        temperature_difference = float((pair["indoor_temperature_c"] - pair["outdoor_temperature_c"]).mean())

    lag = _thermal_lag(frame["indoor_temperature_c"], frame["outdoor_temperature_c"])
    indoor_rate = _slope_per_hour(frame["timestamp"], frame["indoor_temperature_c"])

    window_open = frame[frame["event"].str.lower().isin({"windows opened", "window opened", "windows open"})]
    window_temp_rate = _slope_per_hour(window_open["timestamp"], window_open["indoor_temperature_c"])
    window_pm_rate = _slope_per_hour(window_open["timestamp"], window_open["indoor_pm25_ug_m3"])

    night = frame[(frame["timestamp"].dt.hour >= 20) | (frame["timestamp"].dt.hour <= 6)]
    nighttime_recovery = None
    if night["indoor_temperature_c"].notna().sum() >= 2:
        nighttime_recovery = float(night["indoor_temperature_c"].max() - night["indoor_temperature_c"].min())

    counts = frame.loc[frame["event"] != "", "event"].value_counts().to_dict()
    observations: list[str] = []
    if lag is not None:
        observations.append(f"The strongest simple indoor/outdoor temperature alignment occurred at a lag of {lag} sample steps.")
    if window_temp_rate is not None:
        direction = "fell" if window_temp_rate < 0 else "rose"
        observations.append(f"During rows marked as window-open events, indoor temperature {direction} at an apparent rate of {abs(window_temp_rate):.2f} °C/hour.")
    if window_pm_rate is not None:
        direction = "fell" if window_pm_rate < 0 else "rose"
        observations.append(f"During rows marked as window-open events, indoor PM2.5 {direction} at an apparent rate of {abs(window_pm_rate):.2f} µg/m³/hour.")
    if not observations:
        observations.append("The supplied records are insufficient for stable event-response observations.")

    return ComparatorResult(
        record_count=len(frame),
        start=frame["timestamp"].min().isoformat(),
        end=frame["timestamp"].max().isoformat(),
        indoor_outdoor_temperature_difference_mean_c=round(temperature_difference, 3) if temperature_difference is not None else None,
        estimated_thermal_lag_steps=lag,
        indoor_temperature_rate_c_per_hour=round(indoor_rate, 4) if indoor_rate is not None else None,
        window_open_temperature_change_c_per_hour=round(window_temp_rate, 4) if window_temp_rate is not None else None,
        window_open_pm25_change_ug_m3_per_hour=round(window_pm_rate, 4) if window_pm_rate is not None else None,
        nighttime_recovery_c=round(nighttime_recovery, 3) if nighttime_recovery is not None else None,
        event_counts={str(key): int(value) for key, value in counts.items()},
        observations=observations,
        limitations=[
            "These are observational associations, not controlled causal estimates.",
            "Lag is reported in sample steps; interpretation depends on the sampling interval.",
            "Event annotations should describe time intervals, not only single timestamps, for stronger analysis.",
        ],
    )
