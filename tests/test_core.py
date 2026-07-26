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
from heatsafe.core.models import ComparatorInput, ComparatorRecord, CoolingCostInput, HeatwaveConfig, HomeProfileInput, VentilationInput
from heatsafe.core.urban_heat import analyze_urban_heat
from heatsafe.core.ventilation import decide_ventilation
from heatsafe.core.wildfire import FireDetection, analyze_wildfire_context

NOW=datetime(2026,7,26,tzinfo=timezone.utc)

def test_ventilation_favorable():
    r=decide_ventilation(VentilationInput(indoor_temperature_c=30,outdoor_temperature_c=23,pm25_ug_m3=8,outdoor_humidity_pct=50,wind_speed_kmh=10,smoke_context="none",cross_ventilation=True))
    assert r.decision.value=="Favorable Ventilation" and r.confidence=="High"

def test_ventilation_keep_closed_for_smoke():
    r=decide_ventilation(VentilationInput(indoor_temperature_c=30,outdoor_temperature_c=22,pm25_ug_m3=90,smoke_context="likely"))
    assert r.decision.value=="Keep Closed"

def test_ventilation_missing():
    r=decide_ventilation(VentilationInput())
    assert r.decision.value=="Insufficient Data" and r.missing_inputs

def test_home_profile_explainable():
    p=HomeProfileInput(building_type="apartment",floor_level="top",roof_exposure="direct",window_orientation="west",window_area="large",external_shading="none",internal_shading="light",insulation_context="unknown",thermal_mass_context="heavy",cross_ventilation=False,single_sided_ventilation=True,internal_heat_sources=["oven"],occupancy=2,cooling_equipment=["fan"],outdoor_air_quality_concerns=True)
    r=build_home_profile(p)
    assert "roof" in r.likely_dominant_heat_pathway.lower() or "solar" in r.likely_dominant_heat_pathway.lower()
    assert r.data_gaps

def test_cooling_cost_math():
    r=estimate_cooling_cost(CoolingCostInput(device_power_w=1000,estimated_duty_cycle=.5,daily_runtime_hours=10,number_of_days=20,electricity_price_per_kwh=.2,currency="USD"))
    assert r.central.energy_kwh==100 and r.central.estimated_cost==20
    assert r.low.energy_kwh<r.central.energy_kwh<r.high.energy_kwh

def test_climate_trend_positive(climate_records):
    r=analyze_climate_trend(climate_records)
    assert r.ols_slope_c_per_decade>0
    assert len(r.annual_means)==25

def test_heatwave_absolute():
    records=[]
    from heatsafe.core.models import ClimateRecord
    for i,t in enumerate([31,36,38,37,30]):
        records.append(ClimateRecord(timestamp=NOW+timedelta(days=i),temperature_c=t,minimum_temperature_c=t-10,maximum_temperature_c=t))
    events=detect_heatwaves(records,HeatwaveConfig(absolute_threshold_c=35,minimum_duration_days=3))
    assert len(events)==1 and events[0].duration_days==3

def test_air_quality_and_labeled_aqi():
    s=summarize_air_quality([NOW,NOW+timedelta(hours=1)],[8,12],aqi_standard="US EPA AQI")
    assert s.latest_aqi==us_epa_aqi("PM2.5",12)
    assert s.standard=="US EPA AQI"

def test_air_quality_no_valid_data():
    with pytest.raises(ValueError): summarize_air_quality(["bad"],[None])

def test_comparator_and_duplicate_guard():
    records=[]
    for i in range(8):
        records.append(ComparatorRecord(timestamp=NOW+timedelta(hours=i),indoor_temperature_c=29-i*.2,outdoor_temperature_c=25-i*.1,indoor_pm25_ug_m3=10,outdoor_pm25_ug_m3=12,event="Windows Opened" if i==2 else None))
    r=compare_indoor_outdoor(ComparatorInput(records=records))
    assert r.record_count==8
    with pytest.raises(ValidationError): ComparatorInput(records=[records[0],records[0],records[1]])

def test_urban_heat_labeled_lst():
    df=pd.DataFrame({"latitude":[41,41.01,41.1,41.11],"longitude":[29,29.01,29.1,29.11],"zone":["urban","urban","peripheral","peripheral"],"land_surface_temperature_c":[39,38,31,32],"ndvi":[.1,.2,.7,.6]})
    r=analyze_urban_heat(df,source="synthetic",acquisition_date="2026-07-20",product="demo LST")
    assert r.surface_heat_difference_c>0
    assert any("not" in x.lower() and "air" in x.lower() for x in r.warnings)

def test_wildfire_does_not_claim_causality():
    fires=[FireDetection(latitude=41.1,longitude=29.1,timestamp=NOW.isoformat(),confidence=90,frp_mw=20,source="synthetic")]
    r=analyze_wildfire_context(target_latitude=41,target_longitude=29,fires=fires,pm25_before=8,pm25_during=45,wind_direction_deg=200,wind_speed_kmh=15)
    assert r.fire_count_within_radius==1
    assert "unconfirmed" in r.causal_attribution.lower()

def test_indoor_air_clues_are_non_diagnostic():
    from heatsafe.core.indoor_air import assess_indoor_air_clues
    result = assess_indoor_air_clues(co2_ppm=1350, indoor_humidity_pct=68, indoor_temperature_c=26, cold_surface_temperature_c=17)
    assert "Higher" in result.ventilation_clue
    assert "Elevated" in result.humidity_context
    assert any("does not diagnose" in item for item in result.limitations)


def test_negative_air_quality_rejected():
    with pytest.raises(ValueError):
        summarize_air_quality([NOW], [-1])
