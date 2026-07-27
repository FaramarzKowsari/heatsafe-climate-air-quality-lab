from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from heatsafe.core.models import NormalizedObservation


def observations_to_hourly_frame(
    observations: Sequence[NormalizedObservation],
    *,
    variables: Sequence[str],
    station_id: str | None = None,
    frequency: str = "1h",
) -> pd.DataFrame:
    selected = [
        observation
        for observation in observations
        if observation.variable in set(variables)
        and (station_id is None or observation.station_id == station_id)
    ]
    if not selected:
        raise ValueError("No observations match the requested variables and station")

    stations = {observation.station_id for observation in selected if observation.station_id is not None}
    if station_id is None and len(stations) > 1:
        raise ValueError("Multiple stations are present; select station_id explicitly")

    frame = pd.DataFrame(
        {
            "timestamp": [observation.timestamp_utc for observation in selected],
            "variable": [observation.variable for observation in selected],
            "value": [observation.value for observation in selected],
        }
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    pivot = frame.pivot_table(index="timestamp", columns="variable", values="value", aggfunc="mean")
    pivot = pivot.sort_index().resample(frequency).mean()
    pivot.index.name = "timestamp"
    return pivot.reset_index()


def generate_synthetic_nexus_frame(
    *,
    rows: int = 1_500,
    random_state: int = 42,
) -> pd.DataFrame:
    if rows < 240:
        raise ValueError("At least 240 rows are required")
    rng = np.random.default_rng(random_state)
    timestamp = pd.date_range("2025-01-01", periods=rows, freq="h", tz="UTC")
    hour = np.arange(rows) % 24
    day = np.arange(rows) / 24

    temperature = (
        23
        + 6 * np.sin(2 * np.pi * (hour - 7) / 24)
        + 2.5 * np.sin(2 * np.pi * day / 14)
        + rng.normal(0, 0.8, rows)
    )
    humidity = np.clip(
        62 - 18 * np.sin(2 * np.pi * (hour - 7) / 24) + rng.normal(0, 4, rows),
        18,
        98,
    )
    wind = np.clip(9 + 4 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 2, rows), 0, None)
    smoke_episode = np.zeros(rows)
    for start in (300, 720, 1_100):
        if start < rows:
            end = min(rows, start + 60)
            smoke_episode[start:end] = np.linspace(0.2, 1.0, end - start)

    pm25 = (
        8
        + 0.42 * np.maximum(temperature - 25, 0)
        + 0.08 * humidity
        - 0.32 * wind
        + 42 * smoke_episode
        + 4 * np.sin(2 * np.pi * hour / 24)
        + rng.normal(0, 2.2, rows)
    )
    pm25 = np.clip(pm25, 0.5, None)

    frame = pd.DataFrame(
        {
            "timestamp": timestamp,
            "temperature_c": temperature,
            "relative_humidity_pct": humidity,
            "wind_speed_kmh": wind,
            "smoke_proxy": smoke_episode,
            "pm25": pm25,
            "city": "Synthetic City",
        }
    )
    missing_indices = rng.choice(rows, size=max(3, rows // 100), replace=False)
    frame.loc[missing_indices, "relative_humidity_pct"] = np.nan
    return frame
