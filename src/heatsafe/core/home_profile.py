from __future__ import annotations

from .models import HomeProfileInput, HomeProfileResult


def build_home_profile(data: HomeProfileInput) -> HomeProfileResult:
    pathways: list[tuple[str, int, str]] = []
    rationale: list[str] = []
    investigations: list[str] = []
    gaps: list[str] = []

    solar_score = 0
    if data.window_orientation in {"west", "south", "mixed"}:
        solar_score += 3
        rationale.append(f"{data.window_orientation.title()}-oriented glazing can receive substantial direct solar exposure.")
    if data.window_area == "large":
        solar_score += 2
        rationale.append("Large glazing increases the area available for solar heat gain.")
    if data.external_shading == "none":
        solar_score += 3
        investigations.append("Observe which windows receive direct sun and test temporary external shading where permitted.")
    pathways.append(("Solar gain through glazing", solar_score, "Window orientation, glazing area, and external shade dominate this pathway."))

    roof_score = 0
    if data.floor_level == "top":
        roof_score += 3
        rationale.append("Top-floor rooms are more exposed to stored roof heat.")
    if data.roof_exposure == "direct":
        roof_score += 4
        investigations.append("Compare ceiling temperature and room temperature through the late afternoon and evening.")
    if data.insulation_context == "poor":
        roof_score += 2
    pathways.append(("Roof and envelope heat transfer", roof_score, "Roof exposure and insulation context shape conductive heat gain."))

    storage_score = 0
    if data.thermal_mass_context == "heavy":
        storage_score += 3
        rationale.append("Heavy materials can store daytime heat and release it after sunset.")
        investigations.append("Track whether indoor temperature remains high after outdoor temperature falls.")
    pathways.append(("Thermal storage and delayed release", storage_score, "Thermal mass can shift the indoor heat peak later than the outdoor peak."))

    internal_score = min(len(data.internal_heat_sources), 4) + (2 if data.occupancy >= 4 else 1 if data.occupancy >= 2 else 0)
    if data.internal_heat_sources:
        rationale.append("Internal equipment and activities add heat that must eventually leave the home.")
        investigations.append("Log cooking, computing, laundry, and other high-load activities beside indoor temperature changes.")
    pathways.append(("Internal heat generation", internal_score, "Occupancy and equipment create heat independent of outdoor conditions."))

    pathways.sort(key=lambda item: item[1], reverse=True)
    dominant = pathways[0][0]
    secondary = pathways[1][0] if len(pathways) > 1 else "Not resolved"

    if data.cross_ventilation:
        ventilation_limitation = "No major layout limitation reported; actual performance still depends on wind, opening size, and outdoor conditions."
    elif data.single_sided_ventilation:
        ventilation_limitation = "Single-sided ventilation may exchange air slowly and may not flush stored heat efficiently."
        investigations.append("Use a smoke-free ribbon or lightweight tissue to observe airflow direction without using flames.")
    else:
        ventilation_limitation = "Natural ventilation availability is unclear or limited."
        gaps.append("opening configuration and airflow path")

    if data.outdoor_air_quality_concerns:
        air_constraint = "Outdoor particles or smoke may conflict with heat-removal opportunities; use time-specific air-quality data."
        investigations.append("Compare indoor and outdoor PM2.5 before using prolonged ventilation during smoke or pollution events.")
    else:
        air_constraint = "No persistent air-quality concern was reported, but local conditions should still be checked before ventilation."

    if data.insulation_context == "unknown":
        gaps.append("insulation condition")
    if data.thermal_mass_context == "unknown":
        gaps.append("thermal mass")
    if not data.cooling_equipment:
        gaps.append("mechanical cooling capacity")

    priority = pathways[0][2]

    if not investigations:
        investigations.append("Run a seven-day heat log before making expensive changes.")

    return HomeProfileResult(
        likely_dominant_heat_pathway=dominant,
        secondary_heat_pathway=secondary,
        ventilation_limitation=ventilation_limitation,
        air_quality_constraint=air_constraint,
        priority_observation=priority,
        suggested_low_risk_investigation=investigations,
        data_gaps=sorted(set(gaps)),
        rationale=rationale,
        limitations=[
            "This is a structured observational profile, not a professional building diagnosis or certification.",
            "Construction details, local climate, occupant behavior, and sensor placement can change the apparent pathway.",
        ],
    )
