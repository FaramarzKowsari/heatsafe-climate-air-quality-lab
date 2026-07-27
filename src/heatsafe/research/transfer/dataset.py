from __future__ import annotations

import numpy as np
import pandas as pd


SYNTHETIC_DOMAINS: tuple[tuple[str, str, float, float, float], ...] = (
    ("europe-coastal-01", "Europe", 1.5, 0.5, 0.2),
    ("europe-inland-01", "Europe", 3.0, 1.5, 0.4),
    ("north-america-east-01", "North America", 0.0, 2.5, 0.1),
    ("north-america-west-01", "North America", 2.0, 5.0, 0.8),
    ("canada-central-01", "Canada", -3.0, 1.0, 0.3),
    ("canada-pacific-01", "Canada", -1.0, 3.0, 0.6),
    ("turkiye-coastal-01", "Türkiye", 4.0, 2.0, 0.3),
    ("turkiye-inland-01", "Türkiye", 5.0, 4.0, 0.5),
)


def generate_synthetic_multicity_frame(
    *,
    rows_per_city: int = 720,
    random_state: int = 42,
) -> pd.DataFrame:
    if rows_per_city < 360:
        raise ValueError("At least 360 rows per city are required")

    frames: list[pd.DataFrame] = []
    for index, (city, region, temperature_shift, pollution_shift, smoke_factor) in enumerate(
        SYNTHETIC_DOMAINS
    ):
        rng = np.random.default_rng(random_state + index * 101)
        timestamp = pd.date_range(
            "2025-01-01",
            periods=rows_per_city,
            freq="h",
            tz="UTC",
        )
        hour = np.arange(rows_per_city) % 24
        day = np.arange(rows_per_city) / 24
        seasonal = 5 * np.sin(2 * np.pi * day / 30 + index / 3)
        daily = 6 * np.sin(2 * np.pi * (hour - 7) / 24)

        temperature = (
            21
            + temperature_shift
            + daily
            + seasonal
            + rng.normal(0, 0.9, rows_per_city)
        )
        humidity = np.clip(
            63
            - 16 * np.sin(2 * np.pi * (hour - 7) / 24)
            - 0.7 * temperature_shift
            + rng.normal(0, 4, rows_per_city),
            18,
            98,
        )
        wind = np.clip(
            8
            + 3 * np.sin(2 * np.pi * hour / 24 + index / 2)
            + rng.normal(0, 1.8, rows_per_city),
            0,
            None,
        )

        smoke = np.zeros(rows_per_city)
        episode_start = 180 + index * 13
        episode_end = min(rows_per_city, episode_start + 72)
        if episode_start < rows_per_city:
            smoke[episode_start:episode_end] = np.linspace(
                0.2,
                1.0 + smoke_factor,
                episode_end - episode_start,
            )

        pm25 = (
            7
            + pollution_shift
            + 0.38 * np.maximum(temperature - 25, 0)
            + 0.07 * humidity
            - 0.30 * wind
            + (34 + 16 * smoke_factor) * smoke
            + 3.5 * np.sin(2 * np.pi * hour / 24)
            + rng.normal(0, 2.1, rows_per_city)
        )
        pm25 = np.clip(pm25, 0.5, None)

        frame = pd.DataFrame(
            {
                "timestamp": timestamp,
                "city": city,
                "region": region,
                "temperature_c": temperature,
                "relative_humidity_pct": humidity,
                "wind_speed_kmh": wind,
                "smoke_proxy": smoke,
                "pm25": pm25,
                "data_origin": "synthetic-domain-shift-demo",
            }
        )
        missing = rng.choice(
            rows_per_city,
            size=max(3, rows_per_city // 120),
            replace=False,
        )
        frame.loc[missing, "relative_humidity_pct"] = np.nan
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def validate_multicity_frame(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    city_column: str,
    region_column: str,
    target_column: str,
    feature_columns: tuple[str, ...],
    minimum_rows_per_city: int,
) -> pd.DataFrame:
    required = {
        timestamp_column,
        city_column,
        region_column,
        target_column,
        *feature_columns,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    clean = frame.loc[:, list(required)].copy()
    clean[timestamp_column] = pd.to_datetime(
        clean[timestamp_column],
        utc=True,
        errors="coerce",
    )
    if clean[timestamp_column].isna().any():
        raise ValueError("All timestamps must be parseable")

    clean[city_column] = clean[city_column].astype(str).str.strip()
    clean[region_column] = clean[region_column].astype(str).str.strip()
    if (clean[city_column] == "").any() or (clean[region_column] == "").any():
        raise ValueError("City and region values must be non-empty")

    city_region_counts = clean.groupby(city_column)[region_column].nunique()
    inconsistent = city_region_counts[city_region_counts > 1]
    if not inconsistent.empty:
        raise ValueError(
            f"Each city must map to one region: {inconsistent.index.tolist()}"
        )

    duplicate = clean.duplicated([city_column, timestamp_column])
    if duplicate.any():
        raise ValueError("Duplicate city-timestamp rows are not allowed")

    counts = clean.groupby(city_column).size()
    too_small = counts[counts < minimum_rows_per_city]
    if not too_small.empty:
        raise ValueError(
            "Cities below minimum row count: "
            + ", ".join(f"{city}={count}" for city, count in too_small.items())
        )

    if clean[city_column].nunique() < 3:
        raise ValueError("At least three cities are required")
    if clean[region_column].nunique() < 2:
        raise ValueError("At least two regions are required")

    return clean.sort_values([city_column, timestamp_column]).reset_index(drop=True)
