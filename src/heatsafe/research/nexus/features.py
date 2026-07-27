from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from heatsafe.research.nexus.contracts import NexusConfig


@dataclass(frozen=True)
class SupervisedFrame:
    frame: pd.DataFrame
    feature_columns: tuple[str, ...]


def _validate_and_sort(frame: pd.DataFrame, config: NexusConfig) -> pd.DataFrame:
    required = {config.timestamp_column, config.target_column, *config.feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    clean = frame.loc[:, list(required)].copy()
    clean[config.timestamp_column] = pd.to_datetime(clean[config.timestamp_column], utc=True, errors="coerce")
    if clean[config.timestamp_column].isna().any():
        raise ValueError("All timestamps must be parseable")
    if clean[config.timestamp_column].duplicated().any():
        raise ValueError("Duplicate timestamps are not allowed")
    clean = clean.sort_values(config.timestamp_column).reset_index(drop=True)

    deltas = clean[config.timestamp_column].diff().dropna()
    if not deltas.empty:
        expected = pd.Timedelta(config.expected_frequency)
        irregular_ratio = float((deltas != expected).mean())
        if irregular_ratio > 0.05:
            raise ValueError(
                f"Timestamp frequency is too irregular: {irregular_ratio:.1%} of intervals differ from {expected}"
            )
    return clean


def build_supervised_frame(
    frame: pd.DataFrame,
    config: NexusConfig,
    *,
    horizon: int,
) -> SupervisedFrame:
    clean = _validate_and_sort(frame, config)
    target = pd.to_numeric(clean[config.target_column], errors="coerce")
    timestamp = clean[config.timestamp_column]

    output = pd.DataFrame(
        {
            "origin_timestamp": timestamp,
            "origin_target": target,
            "target_timestamp": timestamp.shift(-horizon),
            "future_target": target.shift(-horizon),
        }
    )

    output["hour_sin"] = np.sin(2 * np.pi * timestamp.dt.hour / 24)
    output["hour_cos"] = np.cos(2 * np.pi * timestamp.dt.hour / 24)
    output["dow_sin"] = np.sin(2 * np.pi * timestamp.dt.dayofweek / 7)
    output["dow_cos"] = np.cos(2 * np.pi * timestamp.dt.dayofweek / 7)
    output["doy_sin"] = np.sin(2 * np.pi * timestamp.dt.dayofyear / 365.25)
    output["doy_cos"] = np.cos(2 * np.pi * timestamp.dt.dayofyear / 365.25)

    for lag in config.lags:
        output[f"target_lag_{lag}"] = target.shift(lag)
    for window in config.rolling_windows:
        historical = target.shift(1)
        output[f"target_roll_mean_{window}"] = historical.rolling(window).mean()
        output[f"target_roll_std_{window}"] = historical.rolling(window).std()
        output[f"target_roll_min_{window}"] = historical.rolling(window).min()
        output[f"target_roll_max_{window}"] = historical.rolling(window).max()

    for column in config.feature_columns:
        values = pd.to_numeric(clean[column], errors="coerce")
        output[f"{column}_missing_lag1"] = values.isna().astype(float).shift(1)
        output[f"{column}_lag1"] = values.ffill().shift(1)
        output[f"{column}_lag6"] = values.ffill().shift(6)
        output[f"{column}_roll_mean_24"] = values.ffill().shift(1).rolling(24).mean()

    feature_columns = tuple(
        column
        for column in output.columns
        if column not in {"origin_timestamp", "origin_target", "target_timestamp", "future_target"}
    )
    valid = output.dropna(subset=[*feature_columns, "origin_target", "future_target"]).reset_index(drop=True)
    if len(valid) < config.minimum_valid_rows:
        raise ValueError(
            f"Only {len(valid)} valid supervised rows remain; at least {config.minimum_valid_rows} are required"
        )
    return SupervisedFrame(frame=valid, feature_columns=feature_columns)
