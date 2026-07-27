from __future__ import annotations

import pandas as pd

from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame
from heatsafe.research.nexus.features import build_supervised_frame


def test_features_use_only_historical_values() -> None:
    frame = generate_synthetic_nexus_frame(rows=400)
    config = NexusConfig(
        horizons=(6,),
        feature_columns=("temperature_c", "relative_humidity_pct"),
        minimum_valid_rows=120,
    )
    supervised = build_supervised_frame(frame, config, horizon=6)
    first = supervised.frame.iloc[0]
    origin_time = pd.Timestamp(first["origin_timestamp"])
    target_time = pd.Timestamp(first["target_timestamp"])
    assert target_time - origin_time == pd.Timedelta(hours=6)
    assert "target_lag_1" in supervised.feature_columns
    assert "temperature_c_lag1" in supervised.feature_columns
    assert "future_target" not in supervised.feature_columns


def test_duplicate_timestamps_are_rejected() -> None:
    frame = generate_synthetic_nexus_frame(rows=300)
    frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]
    config = NexusConfig(horizons=(1,), minimum_valid_rows=100)
    try:
        build_supervised_frame(frame, config, horizon=1)
    except ValueError as exc:
        assert "Duplicate timestamps" in str(exc)
    else:
        raise AssertionError("Duplicate timestamps should be rejected")
