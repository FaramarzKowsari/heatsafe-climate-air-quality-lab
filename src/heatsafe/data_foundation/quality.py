from __future__ import annotations

from collections import Counter
from typing import Iterable

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.contracts import (
    DataQualityReport,
    QualityIssue,
    QualitySeverity,
)


EXPECTED_UNITS: dict[str, set[str]] = {
    "temperature_c": {"°C", "C", "degC"},
    "maximum_temperature_c": {"°C", "C", "degC"},
    "minimum_temperature_c": {"°C", "C", "degC"},
    "relative_humidity_pct": {"%", "percent"},
    "pm25": {"µg/m³", "ug/m3", "Micrograms/cubic meter (LC)"},
    "pm10": {"µg/m³", "ug/m3", "Micrograms/cubic meter (LC)"},
    "wind_speed_kmh": {"km/h"},
    "wind_speed_m_s": {"m/s"},
    "fire_radiative_power_mw": {"MW"},
}

EXPECTED_RANGES: dict[str, tuple[float, float]] = {
    "temperature_c": (-90, 70),
    "maximum_temperature_c": (-90, 70),
    "minimum_temperature_c": (-90, 70),
    "relative_humidity_pct": (0, 100),
    "pm25": (0, 2000),
    "pm10": (0, 3000),
    "wind_speed_kmh": (0, 400),
    "wind_speed_m_s": (0, 120),
    "wind_direction_deg": (0, 360),
    "fire_radiative_power_mw": (0, 1_000_000),
}


def observation_identity(observation: NormalizedObservation) -> tuple[str, str | None, str, str, float, str]:
    return (
        observation.source_name,
        observation.source_record_id,
        observation.timestamp_utc.isoformat(),
        observation.variable,
        observation.value,
        observation.unit,
    )


def deduplicate_observations(
    observations: Iterable[NormalizedObservation],
) -> list[NormalizedObservation]:
    seen: set[tuple[str, str | None, str, str, float, str]] = set()
    unique: list[NormalizedObservation] = []
    for observation in observations:
        identity = observation_identity(observation)
        if identity not in seen:
            seen.add(identity)
            unique.append(observation)
    return unique


def assess_observations(
    observations: Iterable[NormalizedObservation],
) -> DataQualityReport:
    items = list(observations)
    issues: list[QualityIssue] = []
    seen: dict[tuple[str, str | None, str, str, float, str], int] = {}

    for index, observation in enumerate(items):
        identity = observation_identity(observation)
        if identity in seen:
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.ERROR,
                    code="duplicate-observation",
                    message=f"Duplicate of observation index {seen[identity]}",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )
        else:
            seen[identity] = index

        if observation.timestamp_utc.tzinfo is None or observation.timestamp_utc.utcoffset() is None:
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.ERROR,
                    code="naive-utc-timestamp",
                    message="timestamp_utc must be timezone-aware",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )
        if observation.retrieved_at.tzinfo is None or observation.retrieved_at.utcoffset() is None:
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.ERROR,
                    code="naive-retrieval-timestamp",
                    message="retrieved_at must be timezone-aware",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )
        expected_range = EXPECTED_RANGES.get(observation.variable)
        if expected_range and not expected_range[0] <= observation.value <= expected_range[1]:
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.ERROR,
                    code="value-out-of-range",
                    message=(
                        f"{observation.variable}={observation.value} is outside "
                        f"{expected_range[0]}–{expected_range[1]}"
                    ),
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )

        expected_units = EXPECTED_UNITS.get(observation.variable)
        if expected_units and observation.unit not in expected_units:
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.WARNING,
                    code="unexpected-unit",
                    message=(
                        f"{observation.variable} uses {observation.unit!r}; "
                        f"expected one of {sorted(expected_units)}"
                    ),
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )

        if not observation.license.strip():
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.ERROR,
                    code="missing-license",
                    message="A source license or terms summary is required",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )
        if not observation.source_url.startswith(("https://", "http://")):
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.WARNING,
                    code="non-web-source-url",
                    message="source_url is not an absolute HTTP(S) URL",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )
        if observation.quality_flag == "not_assessed":
            issues.append(
                QualityIssue(
                    severity=QualitySeverity.WARNING,
                    code="quality-not-assessed",
                    message="Provider or pipeline quality metadata have not been assessed",
                    observation_index=index,
                    source_record_id=observation.source_record_id,
                )
            )

    error_count = sum(issue.severity == QualitySeverity.ERROR for issue in issues)
    warning_count = sum(issue.severity == QualitySeverity.WARNING for issue in issues)
    unique_count = len(seen)
    denominator = max(len(items), 1)
    penalty = min(1.0, (error_count * 0.15 + warning_count * 0.04) / denominator)
    score = round(max(0.0, 1.0 - penalty), 6)

    return DataQualityReport(
        observation_count=len(items),
        unique_observation_count=unique_count,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        quality_score=score,
        variable_counts=dict(Counter(item.variable for item in items)),
        unit_counts=dict(Counter(item.unit for item in items)),
        measurement_type_counts=dict(Counter(str(item.measurement_type) for item in items)),
        issues=issues,
    )
