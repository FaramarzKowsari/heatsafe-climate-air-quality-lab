from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .climate import records_to_frame
from .models import ClimateRecord, HeatwaveConfig


@dataclass(frozen=True)
class HeatwaveEvent:
    start: str
    end: str
    duration_days: int
    peak_temperature_c: float
    cumulative_intensity_c_days: float
    hot_night_count: int
    nighttime_recovery_c: float | None
    data_completeness_pct: float
    definition: str
    threshold_c: float
    confidence: str
    limitations: list[str]


def _daily_frame(records: list[ClimateRecord]) -> pd.DataFrame:
    frame = records_to_frame(records)
    min_column = "minimum_temperature_c" if frame["minimum_temperature_c"].notna().any() else "temperature_c"
    max_column = "maximum_temperature_c" if frame["maximum_temperature_c"].notna().any() else "temperature_c"
    daily = frame.groupby("date").agg(
        max_temp=(max_column, "max"),
        min_temp=(min_column, "min"),
        mean_temp=("temperature_c", "mean"),
        humidity=("relative_humidity_pct", "mean"),
        samples=("temperature_c", "count"),
    )
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def detect_heatwaves(records: list[ClimateRecord], config: HeatwaveConfig) -> list[HeatwaveEvent]:
    daily = _daily_frame(records)
    if daily.empty:
        return []

    reference = daily
    if config.reference_start_year is not None:
        reference = reference[reference.index.year >= config.reference_start_year]
    if config.reference_end_year is not None:
        reference = reference[reference.index.year <= config.reference_end_year]
    if reference.empty:
        reference = daily

    if config.definition == "percentile":
        threshold = float(np.percentile(reference["max_temp"].dropna(), config.percentile))
        qualifies = daily["max_temp"] >= threshold
        definition_text = f"{config.percentile:g}th local percentile"
    elif config.definition == "compound":
        threshold = config.absolute_threshold_c
        humidity_threshold = config.humidity_threshold_pct or 60.0
        qualifies = (daily["max_temp"] >= threshold) & (daily["humidity"] >= humidity_threshold)
        definition_text = f"temperature ≥ {threshold:g} °C and humidity ≥ {humidity_threshold:g}%"
    else:
        threshold = config.absolute_threshold_c
        qualifies = daily["max_temp"] >= threshold
        definition_text = f"absolute threshold ≥ {threshold:g} °C"

    events: list[HeatwaveEvent] = []
    start_idx: int | None = None
    dates = list(daily.index)
    for idx, qualified in enumerate(qualifies.tolist() + [False]):
        if qualified and start_idx is None:
            start_idx = idx
        if not qualified and start_idx is not None:
            end_idx = idx - 1
            block = daily.iloc[start_idx : end_idx + 1]
            consecutive = all((dates[i] - dates[i - 1]).days == 1 for i in range(start_idx + 1, end_idx + 1))
            if len(block) >= config.minimum_duration_days and consecutive:
                hot_night_threshold = config.hot_night_threshold_c
                hot_nights = int((block["min_temp"] >= hot_night_threshold).sum()) if hot_night_threshold is not None else 0
                nighttime_recovery = None
                if block["max_temp"].notna().all() and block["min_temp"].notna().all():
                    nighttime_recovery = float((block["max_temp"] - block["min_temp"]).mean())
                expected = len(block)
                completeness = 100.0 * len(block.dropna(subset=["max_temp"])) / expected
                confidence = "High" if completeness >= 95 and len(block) >= config.minimum_duration_days + 1 else "Moderate"
                events.append(
                    HeatwaveEvent(
                        start=block.index.min().date().isoformat(),
                        end=block.index.max().date().isoformat(),
                        duration_days=len(block),
                        peak_temperature_c=round(float(block["max_temp"].max()), 2),
                        cumulative_intensity_c_days=round(float((block["max_temp"] - threshold).clip(lower=0).sum()), 2),
                        hot_night_count=hot_nights,
                        nighttime_recovery_c=round(nighttime_recovery, 2) if nighttime_recovery is not None else None,
                        data_completeness_pct=round(completeness, 2),
                        definition=definition_text,
                        threshold_c=round(threshold, 2),
                        confidence=confidence,
                        limitations=[
                            "Heatwave definitions vary by jurisdiction and research purpose.",
                            "This detector identifies events in the supplied data; it is not an official warning product.",
                        ],
                    )
                )
            start_idx = None
    return events
