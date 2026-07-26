from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from pydantic import ValidationError

from heatsafe.core.air_quality import summarize_air_quality, us_epa_aqi
from heatsafe.core.climate import analyze_climate_trend
from heatsafe.core.comparator import compare_indoor_outdoor
from heatsafe.core.cooling import estimate_cooling_cost
from heatsafe.core.heatwaves import detect_heatwaves
from heatsafe.core.home_profile import build_home_profile
from heatsafe.core.indoor_air import assess_indoor_air_clues
from heatsafe.core.models import (
    ClimateRecord,
    ComparatorInput,
    ComparatorRecord,
    CoolingCostInput,
    HeatwaveConfig,
    HomeProfileInput,
    VentilationInput,
)
from heatsafe.core.urban_heat import analyze_urban_heat
from heatsafe.core.ventilation import decide_ventilation
from heatsafe.core.wildfire import FireDetection, analyze_wildfire_context

NOW = datetime(2026, 7, 26, tzinfo=timezone.utc)


def test_ventilation_favorable():
    result = decide_ventilation(
        VentilationInput(
            indoor_temperature_c=30,
            outdoor_temperature_c=23,
            pm25_ug_m3=8,
            outdoor_humidity_pct=50,
            wind_speed_kmh=10,
            smoke_context="none",
            cross_ventilation=True,
        )
    )
    assert result.decision.value == "Favorable Ventilation"
    assert result.confidence == "High"


def test_ventilation_keep_closed_for_smoke():
    result = decide_ventilation(
        VentilationInput(
            indoor_temperature_c=30,
            outdoor_temperature_c=22,
            pm25_ug_m3=90,
            smoke_context="likely",
        )
    )
    assert result.decision.value == "Keep Closed"


def test_ventilation_missing():
    result = decide_ventilation(VentilationInput())
    assert result.decision.value == "Insufficient Data"
    assert result.missing_inputs


def test_home_profile_explainable():
    profile = HomeProfileInput(
        building_type="apartment",
        floor_level="top",
        roof_exposure="direct",
        window_orientation="west",
        window_area="large",
        external_shading="none",
        internal_shading="light",
        insulation_context="unknown",
        thermal_mass_context="heavy",
        cross_ventilation=False,
        single_sided_ventilation=True,
        internal_heat_sources=["oven"],
        occupancy=2,
        cooling_equipment=["fan"],
        outdoor_air_quality_concerns=True,
    )
    result = build_home_profile(profile)
    dominant_pathway = result.likely_dominant_heat_pathway.lower()
    assert "roof" in dominant_pathway or "solar" in dominant_pathway
    assert result.data_gaps


def test_cooling_cost_math():
    result = estimate_cooling_cost(
        CoolingCostInput(
            device_power_w=1000,
            estimated_duty_cycle=0.5,
            daily_runtime_hours=10,
            number_of_days=20,
            electricity_price_per_kwh=0.2,
            currency="USD",
        )
    )
    assert result.central.energy_kwh == 100
    assert result.central.estimated_cost == 20
    assert result.low.energy_kwh < result.central.energy_kwh < result.high.energy_kwh


def test_climate_trend_positive(climate_records):
    result = analyze_climate_trend(climate_records)
    assert result.ols_slope_c_per_decade > 0
    assert len(result.annual_means) == 25


def test_heatwave_absolute():
    records = []
    for index, temperature in enumerate([31, 36, 38, 37, 30]):
        records.append(
            ClimateRecord(
                timestamp=NOW + timedelta(days=index),
                temperature_c=temperature,
                minimum_temperature_c=temperature - 10,
                maximum_temperature_c=temperature,
            )
        )
    events = detect_heatwaves(records, HeatwaveConfig(absolute_threshold_c=35, minimum_duration_days=3))
    assert len(events) == 1
    assert events[0].duration_days == 3


def test_air_quality_and_labeled_aqi():
    summary = summarize_air_quality(
        [NOW, NOW + timedelta(hours=1)],
        [8, 12],
        aqi_standard="US EPA AQI",
    )
    assert summary.latest_aqi == us_epa_aqi("PM2.5", 12)
    assert summary.standard == "US EPA AQI"


def test_air_quality_no_valid_data():
    with pytest.raises(ValueError):
        summarize_air_quality(["bad"], [None])


def test_comparator_and_duplicate_guard():
    records = []
    for index in range(8):
        records.append(
            ComparatorRecord(
                timestamp=NOW + timedelta(hours=index),
                indoor_temperature_c=29 - index * 0.2,
                outdoor_temperature_c=25 - index * 0.1,
                indoor_pm25_ug_m3=10,
                outdoor_pm25_ug_m3=12,
                event="Windows Opened" if index == 2 else None,
            )
        )
    result = compare_indoor_outdoor(ComparatorInput(records=records))
    assert result.record_count == 8
    with pytest.raises(ValidationError):
        ComparatorInput(records=[records[0], records[0], records[1]])


def test_urban_heat_labeled_lst():
    frame = pd.DataFrame(
        {
            "latitude": [41, 41.01, 41.1, 41.11],
            "longitude": [29, 29.01, 29.1, 29.11],
            "zone": ["urban", "urban", "peripheral", "peripheral"],
            "land_surface_temperature_c": [39, 38, 31, 32],
            "ndvi": [0.1, 0.2, 0.7, 0.6],
        }
    )
    result = analyze_urban_heat(
        frame,
        source="synthetic",
        acquisition_date="2026-07-20",
        product="demo LST",
    )
    assert result.surface_heat_difference_c > 0
    assert any("not" in warning.lower() and "air" in warning.lower() for warning in result.warnings)


def test_wildfire_does_not_claim_causality():
    fires = [
        FireDetection(
            latitude=41.1,
            longitude=29.1,
            timestamp=NOW.isoformat(),
            confidence=90,
            frp_mw=20,
            source="synthetic",
        )
    ]
    result = analyze_wildfire_context(
        target_latitude=41,
        target_longitude=29,
        fires=fires,
        pm25_before=8,
        pm25_during=45,
        wind_direction_deg=200,
        wind_speed_kmh=15,
    )
    assert result.fire_count_within_radius == 1
    assert "unconfirmed" in result.causal_attribution.lower()


def test_indoor_air_clues_are_non_diagnostic():
    result = assess_indoor_air_clues(
        co2_ppm=1350,
        indoor_humidity_pct=68,
        indoor_temperature_c=26,
        cold_surface_temperature_c=17,
    )
    assert "Higher" in result.ventilation_clue
    assert "Elevated" in result.humidity_context
    assert any("does not diagnose" in item for item in result.limitations)


def test_negative_air_quality_rejected():
    with pytest.raises(ValueError):
        summarize_air_quality([NOW], [-1])
