from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Mapping


@dataclass(frozen=True)
class CompoundRiskResult:
    """Transparent exploratory multi-hazard result.

    Scores are normalized to 0–1 and are not validated health, safety,
    regulatory, or clinical indices.
    """

    components: dict[str, float]
    normalized_weights: dict[str, float]
    additive_score: float
    pairwise_coexceedance: float
    interaction_strength: float
    interaction_adjusted_score: float
    dominant_component: str
    leave_one_out_scores: dict[str, float]
    weight_sensitivity_interval: tuple[float, float]
    limitations: tuple[str, ...]

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _validate_components(components: Mapping[str, float]) -> dict[str, float]:
    if len(components) < 2:
        raise ValueError("At least two hazard components are required")
    clean: dict[str, float] = {}
    for name, raw_value in components.items():
        key = str(name).strip()
        if not key:
            raise ValueError("Component names must be non-empty")
        value = float(raw_value)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Component {key!r} must be normalized to the 0–1 interval")
        clean[key] = value
    return clean


def _normalized_weights(components: Mapping[str, float], weights: Mapping[str, float] | None) -> dict[str, float]:
    if weights is None:
        equal = 1.0 / len(components)
        return {name: equal for name in components}

    missing = set(components) - set(weights)
    extra = set(weights) - set(components)
    if missing or extra:
        raise ValueError(f"Weights must match component names exactly; missing={sorted(missing)}, extra={sorted(extra)}")

    positive: dict[str, float] = {}
    for name, raw_weight in weights.items():
        weight = float(raw_weight)
        if weight <= 0:
            raise ValueError(f"Weight for {name!r} must be greater than zero")
        positive[name] = weight

    total = sum(positive.values())
    return {name: weight / total for name, weight in positive.items()}


def _weighted_score(components: Mapping[str, float], weights: Mapping[str, float]) -> float:
    return sum(components[name] * weights[name] for name in components)


def _coexceedance(components: Mapping[str, float]) -> float:
    pairs = [left * right for left, right in combinations(components.values(), 2)]
    return sum(pairs) / len(pairs) if pairs else 0.0


def _sensitivity_interval(
    components: Mapping[str, float],
    weights: Mapping[str, float],
    *,
    perturbation: float,
    interaction_strength: float,
) -> tuple[float, float]:
    values: list[float] = []
    for changed_name in components:
        for factor in (1.0 - perturbation, 1.0 + perturbation):
            candidate = dict(weights)
            candidate[changed_name] *= factor
            total = sum(candidate.values())
            normalized = {name: value / total for name, value in candidate.items()}
            additive = _weighted_score(components, normalized)
            adjusted = min(1.0, additive + interaction_strength * _coexceedance(components))
            values.append(adjusted)
    return min(values), max(values)


def analyze_compound_risk(
    components: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
    interaction_strength: float = 0.15,
    sensitivity_perturbation: float = 0.25,
) -> CompoundRiskResult:
    """Analyze normalized multi-hazard components with exposed assumptions.

    ``interaction_strength`` controls an explicitly exploratory pairwise
    co-exceedance adjustment. It must be justified and sensitivity-tested in
    any scientific study.
    """

    clean = _validate_components(components)
    if not 0.0 <= interaction_strength <= 1.0:
        raise ValueError("interaction_strength must be between 0 and 1")
    if not 0.0 < sensitivity_perturbation < 1.0:
        raise ValueError("sensitivity_perturbation must be between 0 and 1")

    normalized = _normalized_weights(clean, weights)
    additive = _weighted_score(clean, normalized)
    pairwise = _coexceedance(clean)
    adjusted = min(1.0, additive + interaction_strength * pairwise)
    dominant = max(clean, key=clean.get)

    leave_one_out: dict[str, float] = {}
    for omitted in clean:
        reduced_components = {name: value for name, value in clean.items() if name != omitted}
        reduced_weights = {name: normalized[name] for name in reduced_components}
        total = sum(reduced_weights.values())
        reduced_weights = {name: value / total for name, value in reduced_weights.items()}
        reduced_additive = _weighted_score(reduced_components, reduced_weights)
        reduced_adjusted = min(1.0, reduced_additive + interaction_strength * _coexceedance(reduced_components))
        leave_one_out[omitted] = round(reduced_adjusted, 6)

    sensitivity = _sensitivity_interval(
        clean,
        normalized,
        perturbation=sensitivity_perturbation,
        interaction_strength=interaction_strength,
    )

    return CompoundRiskResult(
        components=clean,
        normalized_weights={name: round(value, 8) for name, value in normalized.items()},
        additive_score=round(additive, 6),
        pairwise_coexceedance=round(pairwise, 6),
        interaction_strength=interaction_strength,
        interaction_adjusted_score=round(adjusted, 6),
        dominant_component=dominant,
        leave_one_out_scores=leave_one_out,
        weight_sensitivity_interval=(round(sensitivity[0], 6), round(sensitivity[1], 6)),
        limitations=(
            "The score is exploratory and is not a validated health, safety, clinical, or regulatory index.",
            "All components must be normalized using a documented reference population or distribution.",
            "Weights and interaction strength can materially change rankings and must be justified.",
            "Correlated components can be counted more than once unless the study design addresses dependence.",
            "Missing hazards, exposure differences, vulnerability, and measurement error can change interpretation.",
        ),
    )
