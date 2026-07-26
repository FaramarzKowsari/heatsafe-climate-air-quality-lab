from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndoorAirClueResult:
    ventilation_clue: str
    humidity_context: str
    condensation_context: str
    reasons: list[str]
    limitations: list[str]


def assess_indoor_air_clues(
    *,
    co2_ppm: float | None,
    indoor_humidity_pct: float | None,
    indoor_temperature_c: float | None,
    cold_surface_temperature_c: float | None = None,
) -> IndoorAirClueResult:
    """Return non-diagnostic CO2, humidity, and condensation clues.

    CO2 is treated as an occupancy/ventilation clue, not a complete measure of
    indoor-air quality. Condensation context uses a simplified dew-point
    approximation and must not be presented as a mold diagnosis.
    """
    reasons: list[str] = []
    if co2_ppm is None:
        ventilation = "Insufficient CO2 data"
        reasons.append("No indoor CO2 value was supplied.")
    elif co2_ppm < 800:
        ventilation = "Lower occupancy-related CO2 accumulation"
        reasons.append(f"The supplied CO2 value is {co2_ppm:.0f} ppm.")
    elif co2_ppm < 1200:
        ventilation = "Moderate occupancy-related CO2 accumulation"
        reasons.append(f"The supplied CO2 value is {co2_ppm:.0f} ppm; interpretation depends on outdoor CO2, occupancy, sensor quality, and timing.")
    else:
        ventilation = "Higher occupancy-related CO2 accumulation"
        reasons.append(f"The supplied CO2 value is {co2_ppm:.0f} ppm; verify the sensor and consult local ventilation guidance.")

    if indoor_humidity_pct is None:
        humidity = "Insufficient humidity data"
    elif indoor_humidity_pct < 30:
        humidity = "Low relative humidity context"
    elif indoor_humidity_pct <= 60:
        humidity = "Moderate relative humidity context"
    else:
        humidity = "Elevated relative humidity context"
        reasons.append(f"Indoor relative humidity is {indoor_humidity_pct:.0f}%; duration and surface temperatures matter.")

    condensation = "Insufficient data for a condensation clue"
    if indoor_temperature_c is not None and indoor_humidity_pct is not None and cold_surface_temperature_c is not None:
        # Magnus approximation, valid for ordinary indoor ranges.
        import math

        a, b = 17.62, 243.12
        gamma = math.log(max(1e-6, indoor_humidity_pct / 100.0)) + (a * indoor_temperature_c) / (b + indoor_temperature_c)
        dew_point = (b * gamma) / (a - gamma)
        margin = cold_surface_temperature_c - dew_point
        condensation = "Surface is above the estimated dew point" if margin > 2 else "Surface is near or below the estimated dew point"
        reasons.append(f"Estimated dew point is {dew_point:.1f} °C and the supplied cold-surface temperature is {cold_surface_temperature_c:.1f} °C.")

    return IndoorAirClueResult(
        ventilation_clue=ventilation,
        humidity_context=humidity,
        condensation_context=condensation,
        reasons=reasons,
        limitations=[
            "CO2 is a ventilation clue, not a complete indoor-air-quality score.",
            "The calculation does not diagnose mold, moisture damage, or a health condition.",
            "Sensor placement, calibration, occupancy, outdoor conditions, and duration affect interpretation.",
        ],
    )
