from __future__ import annotations

from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
    validate_multicity_frame,
)


def test_synthetic_multicity_dataset_has_domains() -> None:
    frame = generate_synthetic_multicity_frame(
        rows_per_city=360,
        random_state=8,
    )
    assert frame["city"].nunique() == 8
    assert frame["region"].nunique() == 4
    assert len(frame) == 8 * 360
    assert set(
        [
            "timestamp",
            "city",
            "region",
            "temperature_c",
            "relative_humidity_pct",
            "wind_speed_kmh",
            "smoke_proxy",
            "pm25",
        ]
    ).issubset(frame.columns)


def test_city_region_mapping_must_be_unique() -> None:
    frame = generate_synthetic_multicity_frame(rows_per_city=360)
    first_city = str(frame["city"].iloc[0])
    index = frame.index[frame["city"] == first_city][0]
    frame.loc[index, "region"] = "Different Region"
    try:
        validate_multicity_frame(
            frame,
            timestamp_column="timestamp",
            city_column="city",
            region_column="region",
            target_column="pm25",
            feature_columns=("temperature_c",),
            minimum_rows_per_city=300,
        )
    except ValueError as exc:
        assert "one region" in str(exc)
    else:
        raise AssertionError("Inconsistent city-region mapping should fail")
