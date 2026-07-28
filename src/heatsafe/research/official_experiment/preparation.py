from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd

from heatsafe.core.models import NormalizedObservation
from heatsafe.research.official_experiment.contracts import (
    StationSelectionPolicy,
)


@dataclass(frozen=True)
class ContiguousRun:
    start: pd.Timestamp
    end: pd.Timestamp
    hours: int


def _duration_match(
    observation: NormalizedObservation,
    tokens: tuple[str, ...],
) -> bool:
    flag = observation.quality_flag.upper()
    return any(token in flag for token in tokens)


def _longest_hourly_run(index: pd.DatetimeIndex) -> ContiguousRun:
    if index.empty:
        raise ValueError("Cannot identify a contiguous run from an empty index")

    ordered = pd.DatetimeIndex(sorted(index.unique()))
    best_start = ordered[0]
    best_end = ordered[0]
    current_start = ordered[0]
    previous = ordered[0]

    for timestamp in ordered[1:]:
        if timestamp - previous != pd.Timedelta(hours=1):
            if previous - current_start > best_end - best_start:
                best_start = current_start
                best_end = previous
            current_start = timestamp
        previous = timestamp

    if previous - current_start > best_end - best_start:
        best_start = current_start
        best_end = previous

    hours = int((best_end - best_start) / pd.Timedelta(hours=1)) + 1
    return ContiguousRun(start=best_start, end=best_end, hours=hours)


def prepare_hourly_station_frame(
    observations: Sequence[NormalizedObservation],
    policy: StationSelectionPolicy,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    target = [
        item
        for item in observations
        if item.variable == policy.target_variable
        and item.station_id
        and np.isfinite(item.value)
    ]
    if not target:
        raise ValueError(
            f"No observations were found for target variable "
            f"{policy.target_variable!r} with station identifiers"
        )

    duration_filtered = [
        item
        for item in target
        if _duration_match(item, policy.allowed_duration_tokens)
    ]
    used_duration_fallback = not duration_filtered
    eligible = duration_filtered if duration_filtered else target

    negative_count = sum(item.value < policy.minimum_value for item in eligible)
    eligible = [
        item for item in eligible if item.value >= policy.minimum_value
    ]
    if not eligible:
        raise ValueError(
            "All eligible target observations were below the minimum value"
        )

    raw_frame = pd.DataFrame(
        {
            "station_id": [str(item.station_id) for item in eligible],
            "timestamp": [
                pd.Timestamp(item.timestamp_utc).tz_convert("UTC").floor("h")
                for item in eligible
            ],
            "value": [float(item.value) for item in eligible],
            "unit": [item.unit for item in eligible],
            "latitude": [item.latitude for item in eligible],
            "longitude": [item.longitude for item in eligible],
            "city": [item.city for item in eligible],
            "quality_flag": [item.quality_flag for item in eligible],
        }
    )

    collapsed = (
        raw_frame.groupby(["station_id", "timestamp"], as_index=False)
        .agg(
            value=("value", "mean"),
            unit=("unit", lambda values: " | ".join(sorted(set(values)))),
            latitude=("latitude", "median"),
            longitude=("longitude", "median"),
            city=("city", lambda values: next(
                (str(value) for value in values if value),
                None,
            )),
            source_records=("quality_flag", "size"),
        )
        .sort_values(["station_id", "timestamp"])
    )

    candidates: list[dict[str, Any]] = []
    station_frames: dict[str, pd.DataFrame] = {}
    station_runs: dict[str, ContiguousRun] = {}

    for station_id, group in collapsed.groupby("station_id", sort=True):
        station_frame = group.sort_values("timestamp").reset_index(drop=True)
        run = _longest_hourly_run(
            pd.DatetimeIndex(station_frame["timestamp"])
        )
        station_frames[str(station_id)] = station_frame
        station_runs[str(station_id)] = run
        candidates.append(
            {
                "station_id": str(station_id),
                "total_hourly_points": int(len(station_frame)),
                "longest_contiguous_hours": run.hours,
                "contiguous_start_utc": run.start.isoformat(),
                "contiguous_end_utc": run.end.isoformat(),
                "latitude": float(station_frame["latitude"].median()),
                "longitude": float(station_frame["longitude"].median()),
                "city": next(
                    (
                        str(value)
                        for value in station_frame["city"]
                        if value is not None and str(value).strip()
                    ),
                    None,
                ),
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item["longest_contiguous_hours"]),
            -int(item["total_hourly_points"]),
            str(item["station_id"]),
        )
    )
    selected = candidates[0]
    selected_station = str(selected["station_id"])
    selected_frame = station_frames[selected_station]
    selected_run = station_runs[selected_station]

    if int(selected["total_hourly_points"]) < policy.minimum_total_hours:
        raise ValueError(
            f"Best station {selected_station} has only "
            f"{selected['total_hourly_points']} hourly points; "
            f"{policy.minimum_total_hours} are required"
        )
    if selected_run.hours < policy.minimum_contiguous_hours:
        raise ValueError(
            f"Best station {selected_station} has a longest contiguous run of "
            f"{selected_run.hours} hours; "
            f"{policy.minimum_contiguous_hours} are required"
        )

    segment = selected_frame.loc[
        (selected_frame["timestamp"] >= selected_run.start)
        & (selected_frame["timestamp"] <= selected_run.end),
        ["timestamp", "value"],
    ].copy()
    segment = segment.rename(
        columns={
            "timestamp": "timestamp",
            "value": policy.target_variable,
        }
    )
    segment = segment.reset_index(drop=True)

    expected = pd.date_range(
        selected_run.start,
        selected_run.end,
        freq="h",
        tz="UTC",
    )
    actual = pd.DatetimeIndex(segment["timestamp"])
    if not actual.equals(expected):
        raise RuntimeError(
            "Internal station selection error: selected segment is not "
            "strictly contiguous at one-hour frequency"
        )

    report: dict[str, Any] = {
        "target_variable": policy.target_variable,
        "allowed_duration_tokens": list(policy.allowed_duration_tokens),
        "duration_filter_fallback_used": used_duration_fallback,
        "source_target_observations": len(target),
        "eligible_observations": len(eligible),
        "negative_or_below_minimum_removed": negative_count,
        "duplicate_source_records_collapsed": int(
            len(raw_frame) - len(collapsed)
        ),
        "selected_station": selected,
        "selected_segment_rows": int(len(segment)),
        "selected_segment_start_utc": selected_run.start.isoformat(),
        "selected_segment_end_utc": selected_run.end.isoformat(),
        "selection_rule": (
            "Maximize longest contiguous one-hour run, then total hourly "
            "points, then choose the lexicographically smallest station ID."
        ),
        "candidate_ranking": candidates,
        "scientific_boundary": (
            "Station selection optimizes temporal continuity for a "
            "forecasting benchmark. It does not establish population "
            "representativeness or causal validity."
        ),
    }
    return segment, report
