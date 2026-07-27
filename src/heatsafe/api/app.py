from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from heatsafe import __version__
from heatsafe.api.data_foundation import router as data_foundation_router
from heatsafe.api.heataq_nexus import router as heataq_nexus_router
from heatsafe.api.external_validation import router as external_validation_router
from heatsafe.api.benchmark_registry import router as benchmark_registry_router
from heatsafe.api.official_snapshots import router as official_snapshots_router
from heatsafe.ai import capabilities, deterministic_explanation
from heatsafe.core.air_quality import summarize_air_quality
from heatsafe.core.climate import analyze_climate_trend
from heatsafe.core.comparator import compare_indoor_outdoor
from heatsafe.core.cooling import estimate_cooling_cost
from heatsafe.core.heatwaves import detect_heatwaves
from heatsafe.core.home_profile import build_home_profile
from heatsafe.core.indoor_air import assess_indoor_air_clues
from heatsafe.core.models import (
    ClimateRecord,
    ComparatorInput,
    CoolingCostInput,
    HeatwaveConfig,
    HomeProfileInput,
    VentilationInput,
    VentilationPlanInput,
)
from heatsafe.core.regions import REGIONAL_WORKFLOWS
from heatsafe.core.urban_heat import analyze_urban_heat
from heatsafe.core.ventilation import build_hourly_plan, decide_ventilation
from heatsafe.core.wildfire import FireDetection, analyze_wildfire_context
from heatsafe.research.benchmark import run_benchmark
from heatsafe.research.compound_risk import analyze_compound_risk


class TrendRequest(BaseModel):
    records: list[ClimateRecord] = Field(min_length=2)
    base_temperature_c: float = 18.0
    hot_day_threshold_c: float = 35.0
    hot_night_threshold_c: float = 20.0
    baseline_start_year: int | None = None
    baseline_end_year: int | None = None


class HeatwaveRequest(BaseModel):
    records: list[ClimateRecord] = Field(min_length=3)
    config: HeatwaveConfig = Field(default_factory=HeatwaveConfig)


class AirQualityRequest(BaseModel):
    timestamps: list[str] = Field(min_length=1)
    values: list[float | None] = Field(min_length=1)
    pollutant: str = "PM2.5"
    unit: str = "µg/m³"
    event_threshold: float | None = 35.0
    aqi_standard: str | None = None


class IndoorAirClueRequest(BaseModel):
    co2_ppm: float | None = Field(default=None, ge=0, le=100_000)
    indoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    indoor_temperature_c: float | None = Field(default=None, ge=-20, le=60)
    cold_surface_temperature_c: float | None = Field(default=None, ge=-50, le=80)


class UrbanHeatRequest(BaseModel):
    cells: list[dict[str, Any]] = Field(min_length=2)
    source: str = "user-entered"
    acquisition_date: str
    product: str


class WildfireRequest(BaseModel):
    target_latitude: float = Field(ge=-90, le=90)
    target_longitude: float = Field(ge=-180, le=180)
    fires: list[dict[str, Any]]
    pm25_before: float | None = Field(default=None, ge=0)
    pm25_during: float | None = Field(default=None, ge=0)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
    radius_km: float = Field(default=250, gt=0, le=5000)


class BenchmarkRequest(BaseModel):
    values: list[float] = Field(min_length=150, max_length=100_000)
    target: str = "PM2.5"
    horizons: list[int] = Field(default_factory=lambda: [1, 6, 12, 24, 48])
    event_threshold: float = 35.0


class CompoundRiskRequest(BaseModel):
    components: dict[str, float] = Field(min_length=2)
    weights: dict[str, float] | None = None
    interaction_strength: float = Field(default=0.15, ge=0, le=1)
    sensitivity_perturbation: float = Field(default=0.25, gt=0, lt=1)


app = FastAPI(
    title="HeatSafe Climate & Air Quality Intelligence Lab API",
    version=__version__,
    description=(
        "Deterministic environmental decision support, climate and air-quality analytics, "
        "compound-hazard research, reproducible forecasting and optional AI explanation modes. "
        "Not an official warning, medical, emergency-response or building-certification system."
    ),
    license_info={"name": "Apache-2.0"},
)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "mode": "standard-no-llm"}


@app.get("/api/v1/ai/capabilities")
def ai_capabilities() -> dict[str, dict[str, object]]:
    return capabilities()


@app.get("/api/v1/regions")
def regions() -> dict[str, Any]:
    return REGIONAL_WORKFLOWS


@app.post("/api/v1/home/profile")
def home_profile(payload: HomeProfileInput) -> dict[str, Any]:
    return build_home_profile(payload).model_dump()


@app.post("/api/v1/ventilation/decision")
def ventilation_decision(payload: VentilationInput) -> dict[str, Any]:
    result = decide_ventilation(payload)
    response = result.model_dump(mode="json")
    response["standard_explanation"] = asdict(deterministic_explanation(response))
    return response


@app.post("/api/v1/ventilation/plan")
def ventilation_plan(payload: VentilationPlanInput) -> list[dict[str, Any]]:
    return [point.model_dump(mode="json") for point in build_hourly_plan(payload)]


@app.post("/api/v1/cooling/cost")
def cooling_cost(payload: CoolingCostInput) -> dict[str, Any]:
    return estimate_cooling_cost(payload).model_dump()


@app.post("/api/v1/compare/indoor-outdoor")
def comparator(payload: ComparatorInput) -> dict[str, Any]:
    return asdict(compare_indoor_outdoor(payload))


@app.post("/api/v1/climate/trend")
def climate_trend(payload: TrendRequest) -> dict[str, Any]:
    baseline = None
    if payload.baseline_start_year is not None and payload.baseline_end_year is not None:
        baseline = (payload.baseline_start_year, payload.baseline_end_year)
    result = analyze_climate_trend(
        payload.records,
        base_temperature_c=payload.base_temperature_c,
        hot_day_threshold_c=payload.hot_day_threshold_c,
        hot_night_threshold_c=payload.hot_night_threshold_c,
        baseline_years=baseline,
    )
    return asdict(result)


@app.post("/api/v1/climate/heatwaves")
def heatwaves(payload: HeatwaveRequest) -> list[dict[str, Any]]:
    return [asdict(event) for event in detect_heatwaves(payload.records, payload.config)]


@app.post("/api/v1/air-quality/summary")
def air_quality_summary(payload: AirQualityRequest) -> dict[str, Any]:
    if len(payload.timestamps) != len(payload.values):
        raise HTTPException(status_code=422, detail="timestamps and values must have the same length")
    try:
        result = summarize_air_quality(
            payload.timestamps,
            payload.values,
            pollutant=payload.pollutant,
            unit=payload.unit,
            event_threshold=payload.event_threshold,
            aqi_standard=payload.aqi_standard,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(result)


@app.post("/api/v1/indoor-air/clues")
def indoor_air_clues(payload: IndoorAirClueRequest) -> dict[str, Any]:
    return asdict(assess_indoor_air_clues(**payload.model_dump()))


@app.post("/api/v1/urban-heat/summary")
def urban_heat(payload: UrbanHeatRequest) -> dict[str, Any]:
    try:
        result = analyze_urban_heat(
            pd.DataFrame(payload.cells),
            source=payload.source,
            acquisition_date=payload.acquisition_date,
            product=payload.product,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(result)


@app.post("/api/v1/wildfire/context")
def wildfire_context(payload: WildfireRequest) -> dict[str, Any]:
    try:
        fires = [FireDetection(**item) for item in payload.fires]
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid fire detection: {exc}") from exc
    result = analyze_wildfire_context(
        target_latitude=payload.target_latitude,
        target_longitude=payload.target_longitude,
        fires=fires,
        pm25_before=payload.pm25_before,
        pm25_during=payload.pm25_during,
        wind_direction_deg=payload.wind_direction_deg,
        wind_speed_kmh=payload.wind_speed_kmh,
        radius_km=payload.radius_km,
    )
    return asdict(result)


@app.post("/api/v1/research/compound-risk")
def compound_risk(payload: CompoundRiskRequest) -> dict[str, object]:
    try:
        result = analyze_compound_risk(
            payload.components,
            weights=payload.weights,
            interaction_strength=payload.interaction_strength,
            sensitivity_perturbation=payload.sensitivity_perturbation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump()


@app.post("/api/v1/benchmark/run")
def benchmark(payload: BenchmarkRequest) -> dict[str, Any]:
    supported = tuple(sorted(set(payload.horizons)))
    if any(horizon not in {1, 6, 12, 24, 48} for horizon in supported):
        raise HTTPException(status_code=422, detail="Supported horizons are 1, 6, 12, 24, and 48 hours")
    try:
        report = run_benchmark(
            pd.Series(payload.values),
            target=payload.target,
            horizons=supported,
            event_threshold=payload.event_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return report.model_dump()


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "apps" / "web"
STATIC_ROOT = WEB_ROOT / "static"
if STATIC_ROOT.exists():
    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")

# Register the HeatSafe Data Foundation router.
app.include_router(data_foundation_router)

# Register the HeatAQ Nexus research router.
app.include_router(heataq_nexus_router)

# Register the external-validation research router.
app.include_router(external_validation_router)

# Register the official benchmark registry API.
app.include_router(benchmark_registry_router)

# Register the official snapshot pipeline API.
app.include_router(official_snapshots_router)
