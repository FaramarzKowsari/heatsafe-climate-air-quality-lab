from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class UrbanHeatResult:
    record_count: int
    urban_mean_lst_c: float
    peripheral_mean_lst_c: float
    surface_heat_difference_c: float
    hottest_cells: list[dict[str, float]]
    vegetation_correlation: float | None
    provenance: dict[str, str]
    warnings: list[str]


def analyze_urban_heat(frame: pd.DataFrame, *, source: str, acquisition_date: str, product: str) -> UrbanHeatResult:
    required = {"latitude", "longitude", "land_surface_temperature_c", "zone"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing urban-heat columns: {sorted(missing)}")
    valid = frame.dropna(subset=list(required)).copy()
    if valid.empty:
        raise ValueError("No valid urban-heat cells are available")
    valid["zone"] = valid["zone"].str.lower()
    urban = valid[valid["zone"] == "urban"]
    peripheral = valid[valid["zone"].isin({"peripheral", "rural", "reference"})]
    if urban.empty or peripheral.empty:
        raise ValueError("Both urban and peripheral/reference cells are required")
    urban_mean = float(urban["land_surface_temperature_c"].mean())
    peripheral_mean = float(peripheral["land_surface_temperature_c"].mean())
    hottest = valid.nlargest(5, "land_surface_temperature_c")
    correlation = None
    if "ndvi" in valid.columns and valid["ndvi"].notna().sum() >= 3:
        correlation = float(valid["ndvi"].corr(valid["land_surface_temperature_c"]))
    return UrbanHeatResult(
        record_count=len(valid),
        urban_mean_lst_c=round(urban_mean, 3),
        peripheral_mean_lst_c=round(peripheral_mean, 3),
        surface_heat_difference_c=round(urban_mean - peripheral_mean, 3),
        hottest_cells=[
            {
                "latitude": round(float(row.latitude), 5),
                "longitude": round(float(row.longitude), 5),
                "land_surface_temperature_c": round(float(row.land_surface_temperature_c), 3),
            }
            for row in hottest.itertuples()
        ],
        vegetation_correlation=round(correlation, 4) if correlation is not None else None,
        provenance={"source": source, "acquisition_date": acquisition_date, "product": product},
        warnings=[
            "Land-surface temperature is not the same quantity as near-surface air temperature.",
            "Satellite acquisition time, cloud masking, emissivity, and surface materials affect interpretation.",
        ],
    )
