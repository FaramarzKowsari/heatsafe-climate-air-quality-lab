from __future__ import annotations

from dataclasses import dataclass

from .models import (
    HourClassification,
    VentilationDecision,
    VentilationInput,
    VentilationPlanInput,
    VentilationPlanPoint,
    VentilationResult,
)

SAFETY_NOTICE = (
    "Educational decision support only. This is not an official warning service, "
    "medical advice, or a substitute for local public-health and emergency guidance."
)


@dataclass(frozen=True)
class _Thresholds:
    clean_pm25: float = 12.0
    moderate_pm25: float = 35.0
    high_pm25: float = 55.0
    useful_temperature_delta: float = 1.5
    strong_temperature_delta: float = 3.0
    high_humidity: float = 75.0
    minimum_wind: float = 1.0


THRESHOLDS = _Thresholds()


def decide_ventilation(data: VentilationInput) -> VentilationResult:
    missing: list[str] = []
    reasons: list[str] = []
    limitations = [
        "Thresholds are conservative educational defaults and may not match local official guidance.",
        "Indoor sensor placement, outdoor station distance, and forecast uncertainty can change the result.",
    ]

    if data.indoor_temperature_c is None:
        missing.append("indoor_temperature_c")
    if data.outdoor_temperature_c is None:
        missing.append("outdoor_temperature_c")

    if missing:
        return VentilationResult(
            decision=VentilationDecision.INSUFFICIENT,
            reasons=["Indoor and outdoor temperatures are required for a ventilation comparison."],
            confidence="Low",
            missing_inputs=missing,
            input_values=data.model_dump(mode="json"),
            source_timestamps=data.source_timestamps,
            limitations=limitations,
            safety_notice=SAFETY_NOTICE,
        )

    assert data.indoor_temperature_c is not None
    assert data.outdoor_temperature_c is not None
    temperature_delta = data.indoor_temperature_c - data.outdoor_temperature_c

    if temperature_delta >= THRESHOLDS.strong_temperature_delta:
        reasons.append(f"Outdoor air is {temperature_delta:.1f} °C cooler than indoor air.")
    elif temperature_delta >= THRESHOLDS.useful_temperature_delta:
        reasons.append(f"Outdoor air is modestly cooler by {temperature_delta:.1f} °C.")
    elif temperature_delta > 0:
        reasons.append(f"Outdoor air is only {temperature_delta:.1f} °C cooler, so heat removal may be limited.")
    else:
        reasons.append(f"Outdoor air is {-temperature_delta:.1f} °C warmer than indoor air.")

    pm25 = data.pm25_ug_m3
    smoke = data.smoke_context

    if smoke == "likely":
        reasons.append("A likely smoke context makes uncontrolled outdoor-air entry unfavorable.")
        decision = VentilationDecision.KEEP_CLOSED
        confidence = "High" if pm25 is not None else "Moderate"
    elif pm25 is not None and pm25 >= THRESHOLDS.high_pm25:
        reasons.append(f"PM2.5 is elevated at {pm25:.1f} µg/m³.")
        decision = VentilationDecision.KEEP_CLOSED
        confidence = "High"
    elif temperature_delta <= 0:
        decision = VentilationDecision.KEEP_CLOSED
        confidence = "High" if pm25 is not None else "Moderate"
    elif pm25 is None:
        missing.append("pm25_ug_m3")
        reasons.append("No PM2.5 value is available, so outdoor-air quality cannot be assessed.")
        decision = VentilationDecision.CONDITIONAL
        confidence = "Low"
    elif pm25 <= THRESHOLDS.clean_pm25 and temperature_delta >= THRESHOLDS.useful_temperature_delta:
        reasons.append(f"PM2.5 is comparatively low at {pm25:.1f} µg/m³.")
        decision = VentilationDecision.FAVORABLE
        confidence = "High" if smoke == "none" else "Moderate"
    elif pm25 <= THRESHOLDS.moderate_pm25 and temperature_delta >= THRESHOLDS.strong_temperature_delta:
        reasons.append(f"PM2.5 is not low ({pm25:.1f} µg/m³), but the cooling potential is substantial.")
        decision = VentilationDecision.CONDITIONAL
        confidence = "Moderate"
    elif pm25 <= THRESHOLDS.moderate_pm25:
        reasons.append(f"PM2.5 is {pm25:.1f} µg/m³ and the temperature advantage is limited.")
        decision = VentilationDecision.CONDITIONAL
        confidence = "Moderate"
    else:
        reasons.append(f"PM2.5 is high enough ({pm25:.1f} µg/m³) to outweigh modest cooling potential.")
        decision = VentilationDecision.KEEP_CLOSED
        confidence = "High"

    if data.outdoor_humidity_pct is not None and data.outdoor_humidity_pct >= THRESHOLDS.high_humidity:
        reasons.append(f"Outdoor relative humidity is high at {data.outdoor_humidity_pct:.0f}%, reducing comfort benefit.")
        if decision == VentilationDecision.FAVORABLE:
            decision = VentilationDecision.CONDITIONAL
            confidence = "Moderate"

    if data.wind_speed_kmh is not None and data.wind_speed_kmh < THRESHOLDS.minimum_wind:
        reasons.append("Wind is very weak, so natural air exchange may be slow.")
        if decision == VentilationDecision.FAVORABLE and not data.cross_ventilation:
            decision = VentilationDecision.CONDITIONAL
            confidence = "Moderate"

    if data.cross_ventilation:
        reasons.append("Cross-ventilation is available, which can improve air exchange when outdoor conditions are suitable.")
    else:
        reasons.append("Only limited or single-sided ventilation is assumed.")

    if data.air_purifier_available and decision == VentilationDecision.CONDITIONAL:
        reasons.append("An air purifier may help manage indoor particles after a short controlled ventilation period.")

    if data.solar_exposure == "high" and data.hour_local is not None and 11 <= data.hour_local <= 18:
        reasons.append("High daytime solar exposure may continue adding heat even while windows are open.")

    if data.user_constraints:
        reasons.append("User constraints were recorded but should be interpreted with local professional guidance when safety-critical.")

    return VentilationResult(
        decision=decision,
        reasons=reasons,
        confidence=confidence,
        missing_inputs=missing,
        input_values=data.model_dump(mode="json"),
        source_timestamps=data.source_timestamps,
        limitations=limitations,
        safety_notice=SAFETY_NOTICE,
    )


def build_hourly_plan(data: VentilationPlanInput) -> list[VentilationPlanPoint]:
    plan: list[VentilationPlanPoint] = []
    for point in data.forecasts:
        result = decide_ventilation(
            VentilationInput(
                indoor_temperature_c=data.indoor_temperature_c,
                outdoor_temperature_c=point.outdoor_temperature_c,
                indoor_humidity_pct=data.indoor_humidity_pct,
                outdoor_humidity_pct=point.outdoor_humidity_pct,
                pm25_ug_m3=point.pm25_ug_m3,
                pm10_ug_m3=point.pm10_ug_m3,
                wind_speed_kmh=point.wind_speed_kmh,
                wind_direction_deg=point.wind_direction_deg,
                smoke_context=point.smoke_context,
                hour_local=point.timestamp.hour,
                solar_exposure=point.solar_exposure,
                window_orientation=data.window_orientation,
                cross_ventilation=data.cross_ventilation,
                air_purifier_available=data.air_purifier_available,
            )
        )
        classification = {
            VentilationDecision.FAVORABLE: HourClassification.MORE_FAVORABLE,
            VentilationDecision.CONDITIONAL: HourClassification.CONDITIONAL,
            VentilationDecision.KEEP_CLOSED: HourClassification.LESS_FAVORABLE,
            VentilationDecision.INSUFFICIENT: HourClassification.INSUFFICIENT,
        }[result.decision]
        plan.append(
            VentilationPlanPoint(
                timestamp=point.timestamp,
                classification=classification,
                decision=result.decision,
                reasons=result.reasons,
                confidence=result.confidence,
            )
        )
    return plan
