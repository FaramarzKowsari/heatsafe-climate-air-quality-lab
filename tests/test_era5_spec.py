from __future__ import annotations

from heatsafe.data_foundation.era5_land import ERA5LandRequestSpec


def test_era5_request_is_explicit() -> None:
    spec = ERA5LandRequestSpec(years=(2025, 2026), months=(6, 7), days=(1, 2), hours=(0, 12), area=(42, 26, 36, 45))
    request = spec.to_cds_request()
    assert request["year"] == ["2025", "2026"]
    assert request["time"] == ["00:00", "12:00"]
    assert request["area"] == [42.0, 26.0, 36.0, 45.0]
