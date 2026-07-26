from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class MeasurementType(StrEnum):
    OBSERVED = "observed"
    SATELLITE_DERIVED = "satellite-derived"
    REANALYSIS = "reanalysis"
    MODELED = "modeled"
    FORECAST = "forecast"
    USER_ENTERED = "user-entered"
    ESTIMATED = "estimated"
    SYNTHETIC = "synthetic"


class VentilationDecision(StrEnum):
    FAVORABLE = "Favorable Ventilation"
    CONDITIONAL = "Conditional Ventilation"
    KEEP_CLOSED = "Keep Closed"
    INSUFFICIENT = "Insufficient Data"


class HourClassification(StrEnum):
    MORE_FAVORABLE = "More Favorable"
    CONDITIONAL = "Conditional"
    LESS_FAVORABLE = "Less Favorable"
    INSUFFICIENT = "Insufficient Data"


class NormalizedObservation(BaseModel):
    source_name: str
    source_dataset: str
    source_record_id: str | None = None
    station_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    country: str | None = None
    region: str | None = None
    city: str | None = None
    timestamp_utc: datetime
    timestamp_local: datetime | None = None
    timezone: str = "UTC"
    variable: str
    value: float
    unit: str
    measurement_type: MeasurementType
    quality_flag: str = "not_assessed"
    data_status: str = "available"
    retrieved_at: datetime
    license: str
    source_url: str


class VentilationInput(BaseModel):
    indoor_temperature_c: float | None = Field(default=None, ge=-20, le=60)
    outdoor_temperature_c: float | None = Field(default=None, ge=-50, le=60)
    indoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    outdoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    pm25_ug_m3: float | None = Field(default=None, ge=0, le=2000)
    pm10_ug_m3: float | None = Field(default=None, ge=0, le=3000)
    wind_speed_kmh: float | None = Field(default=None, ge=0, le=400)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    smoke_context: Literal["none", "possible", "likely", "unknown"] = "unknown"
    hour_local: int | None = Field(default=None, ge=0, le=23)
    solar_exposure: Literal["low", "moderate", "high", "unknown"] = "unknown"
    window_orientation: Literal["north", "south", "east", "west", "mixed", "unknown"] = "unknown"
    cross_ventilation: bool = False
    air_purifier_available: bool = False
    user_constraints: list[str] = Field(default_factory=list)
    source_timestamps: dict[str, datetime] = Field(default_factory=dict)


class VentilationResult(BaseModel):
    decision: VentilationDecision
    reasons: list[str]
    confidence: Literal["Low", "Moderate", "High"]
    missing_inputs: list[str]
    input_values: dict[str, Any]
    source_timestamps: dict[str, datetime]
    limitations: list[str]
    safety_notice: str


class HomeProfileInput(BaseModel):
    building_type: Literal["detached", "semi-detached", "apartment", "row-house", "other"]
    floor_level: Literal["basement", "ground", "middle", "top"]
    roof_exposure: Literal["none", "partial", "direct"]
    window_orientation: Literal["north", "south", "east", "west", "mixed"]
    window_area: Literal["small", "medium", "large"]
    external_shading: Literal["none", "partial", "strong"]
    internal_shading: Literal["none", "light", "effective"]
    insulation_context: Literal["unknown", "poor", "moderate", "good"]
    thermal_mass_context: Literal["light", "medium", "heavy", "unknown"]
    cross_ventilation: bool
    single_sided_ventilation: bool
    internal_heat_sources: list[str] = Field(default_factory=list)
    occupancy: int = Field(ge=0, le=30)
    cooling_equipment: list[str] = Field(default_factory=list)
    outdoor_air_quality_concerns: bool = False


class HomeProfileResult(BaseModel):
    likely_dominant_heat_pathway: str
    secondary_heat_pathway: str
    ventilation_limitation: str
    air_quality_constraint: str
    priority_observation: str
    suggested_low_risk_investigation: list[str]
    data_gaps: list[str]
    rationale: list[str]
    limitations: list[str]


class CoolingCostInput(BaseModel):
    device_power_w: float = Field(gt=0, le=100_000)
    estimated_duty_cycle: float = Field(gt=0, le=1)
    daily_runtime_hours: float = Field(gt=0, le=24)
    number_of_days: int = Field(gt=0, le=3660)
    electricity_price_per_kwh: float = Field(ge=0, le=100)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    number_of_rooms: int = Field(default=1, ge=1, le=100)
    cooling_strategy: Literal["whole-home", "zone", "single-room"] = "single-room"
    fan_power_w: float = Field(default=0, ge=0, le=5000)
    fan_runtime_hours: float = Field(default=0, ge=0, le=24)
    fan_assisted_duty_cycle_reduction: float = Field(default=0.0, ge=0, le=0.5)


class CoolingEstimate(BaseModel):
    energy_kwh: float
    estimated_cost: float


class CoolingCostResult(BaseModel):
    low: CoolingEstimate
    central: CoolingEstimate
    high: CoolingEstimate
    fan_energy_kwh: float
    fan_cost: float
    zone_cooling_comparison: dict[str, float]
    assumptions: list[str]
    sensitivity: dict[str, float]
    currency: str
    limitations: list[str]


class ClimateRecord(BaseModel):
    timestamp: datetime
    temperature_c: float = Field(ge=-90, le=70)
    minimum_temperature_c: float | None = Field(default=None, ge=-90, le=70)
    maximum_temperature_c: float | None = Field(default=None, ge=-90, le=70)
    relative_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    city: str | None = None
    region: str | None = None
    source: str = "user-entered"
    measurement_type: MeasurementType = MeasurementType.USER_ENTERED


class HeatwaveConfig(BaseModel):
    definition: Literal["absolute", "percentile", "compound"] = "absolute"
    absolute_threshold_c: float = Field(default=35, ge=-20, le=60)
    percentile: float = Field(default=90, ge=50, le=99.9)
    minimum_duration_days: int = Field(default=3, ge=1, le=30)
    hot_night_threshold_c: float | None = Field(default=20, ge=-20, le=50)
    humidity_threshold_pct: float | None = Field(default=60, ge=0, le=100)
    reference_start_year: int | None = None
    reference_end_year: int | None = None


class HourlyForecastPoint(BaseModel):
    timestamp: datetime
    outdoor_temperature_c: float | None = Field(default=None, ge=-50, le=60)
    outdoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    pm25_ug_m3: float | None = Field(default=None, ge=0, le=2000)
    pm10_ug_m3: float | None = Field(default=None, ge=0, le=3000)
    wind_speed_kmh: float | None = Field(default=None, ge=0, le=400)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    smoke_context: Literal["none", "possible", "likely", "unknown"] = "unknown"
    solar_exposure: Literal["low", "moderate", "high", "unknown"] = "unknown"


class VentilationPlanInput(BaseModel):
    indoor_temperature_c: float = Field(ge=-20, le=60)
    indoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    cross_ventilation: bool = False
    air_purifier_available: bool = False
    window_orientation: Literal["north", "south", "east", "west", "mixed", "unknown"] = "unknown"
    forecasts: list[HourlyForecastPoint] = Field(min_length=1, max_length=72)


class VentilationPlanPoint(BaseModel):
    timestamp: datetime
    classification: HourClassification
    decision: VentilationDecision
    reasons: list[str]
    confidence: str


class ComparatorRecord(BaseModel):
    timestamp: datetime
    indoor_temperature_c: float | None = Field(default=None, ge=-20, le=60)
    outdoor_temperature_c: float | None = Field(default=None, ge=-50, le=60)
    indoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    outdoor_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    indoor_pm25_ug_m3: float | None = Field(default=None, ge=0, le=2000)
    outdoor_pm25_ug_m3: float | None = Field(default=None, ge=0, le=2000)
    event: str | None = None


class ComparatorInput(BaseModel):
    records: list[ComparatorRecord] = Field(min_length=3, max_length=100_000)

    @field_validator("records")
    @classmethod
    def timestamps_are_unique(cls, records: list[ComparatorRecord]) -> list[ComparatorRecord]:
        timestamps = [record.timestamp for record in records]
        if len(set(timestamps)) != len(timestamps):
            raise ValueError("Duplicate timestamps are not allowed")
        return records
