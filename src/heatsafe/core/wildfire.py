from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Iterable



@dataclass(frozen=True)
class FireDetection:
    latitude: float
    longitude: float
    timestamp: str
    confidence: str | float = "unknown"
    frp_mw: float | None = None
    source: str = "unknown"


@dataclass(frozen=True)
class WildfireContextResult:
    nearest_fire_km: float | None
    fire_count_within_radius: int
    pm25_change: float | None
    smoke_transport_plausibility: str
    causal_attribution: str
    evidence_labels: list[str]
    interpretation: list[str]
    limitations: list[str]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def analyze_wildfire_context(
    *,
    target_latitude: float,
    target_longitude: float,
    fires: Iterable[FireDetection],
    pm25_before: float | None = None,
    pm25_during: float | None = None,
    wind_direction_deg: float | None = None,
    wind_speed_kmh: float | None = None,
    radius_km: float = 250.0,
) -> WildfireContextResult:
    distances = [haversine_km(target_latitude, target_longitude, fire.latitude, fire.longitude) for fire in fires]
    nearest = min(distances) if distances else None
    count = sum(distance <= radius_km for distance in distances)
    pm_change = None if pm25_before is None or pm25_during is None else pm25_during - pm25_before

    if count == 0:
        plausibility = "Low based on supplied fire detections"
    elif wind_speed_kmh is None or wind_direction_deg is None:
        plausibility = "Unresolved because transport data are incomplete"
    elif wind_speed_kmh < 3:
        plausibility = "Limited long-range transport support from weak wind"
    else:
        plausibility = "Possible; a trajectory model is required for stronger attribution"

    labels: list[str] = []
    if distances:
        labels.append("Fire detected")
    if wind_direction_deg is not None:
        labels.append("Smoke transport estimated")
    if pm_change is not None:
        labels.append("PM2.5 change measured or supplied")
    labels.append("Causal attribution unconfirmed")

    interpretation: list[str] = []
    if nearest is not None:
        interpretation.append(f"The nearest supplied detection is approximately {nearest:.1f} km from the target.")
    if pm_change is not None:
        interpretation.append(f"PM2.5 changed by {pm_change:+.1f} µg/m³ between the supplied comparison periods.")
    interpretation.append("Distance, wind, aerosol information, and ground-level PM2.5 should be considered together.")

    return WildfireContextResult(
        nearest_fire_km=round(nearest, 2) if nearest is not None else None,
        fire_count_within_radius=count,
        pm25_change=round(pm_change, 2) if pm_change is not None else None,
        smoke_transport_plausibility=plausibility,
        causal_attribution="Unconfirmed; the supplied evidence supports context, not definitive causation.",
        evidence_labels=labels,
        interpretation=interpretation,
        limitations=[
            "Active-fire detections do not prove that smoke reached the selected location.",
            "Aerosol optical depth and trajectory models can improve context but still require cautious interpretation.",
            "This module does not issue official smoke or evacuation warnings.",
        ],
    )
