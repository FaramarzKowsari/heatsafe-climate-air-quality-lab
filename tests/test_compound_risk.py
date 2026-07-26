from __future__ import annotations

import pytest

from heatsafe.research.compound_risk import analyze_compound_risk


def test_compound_risk_is_transparent_and_bounded() -> None:
    result = analyze_compound_risk(
        {"heat": 0.9, "pm25": 0.6, "humidity": 0.7},
        weights={"heat": 2, "pm25": 1, "humidity": 1},
        interaction_strength=0.15,
    )
    assert 0 <= result.additive_score <= 1
    assert 0 <= result.interaction_adjusted_score <= 1
    assert result.dominant_component == "heat"
    assert set(result.leave_one_out_scores) == {"heat", "pm25", "humidity"}
    assert result.weight_sensitivity_interval[0] <= result.weight_sensitivity_interval[1]
    assert "not a validated" in result.limitations[0]


def test_equal_weights_are_normalized() -> None:
    result = analyze_compound_risk({"heat": 0.8, "pm25": 0.2})
    assert result.normalized_weights == {"heat": 0.5, "pm25": 0.5}


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_component_range_validation(value: float) -> None:
    with pytest.raises(ValueError, match="0–1"):
        analyze_compound_risk({"heat": value, "pm25": 0.5})


def test_weight_names_must_match() -> None:
    with pytest.raises(ValueError, match="match component names"):
        analyze_compound_risk({"heat": 0.8, "pm25": 0.4}, weights={"heat": 1.0, "smoke": 1.0})
