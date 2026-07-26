from __future__ import annotations

import pytest

from heatsafe.ai import byok_explanation, capabilities, deterministic_explanation, input_sha256, validate_numeric_grounding


def test_standard_mode_requires_no_ai_api() -> None:
    result = {
        "decision": "Conditional",
        "reasons": ["Outdoor air is 3.0°C cooler.", "PM2.5 is 18.0 µg/m³."],
        "input_values": {"indoor": 29.0, "outdoor": 26.0, "pm25": 18.0},
    }
    explanation = deterministic_explanation(result)
    assert explanation.mode == "standard"
    assert explanation.provider == "deterministic"
    assert explanation.input_sha256 == input_sha256(result)
    assert explanation.grounding_issues == ()
    assert capabilities()["standard"]["requires_ai_api"] is False


def test_numeric_grounding_flags_invented_value() -> None:
    evidence = {"input_values": {"temperature": 29.0}}
    issues = validate_numeric_grounding("Temperature is 29.0 and should improve in 15 minutes.", evidence)
    assert any("15" in issue for issue in issues)
    assert not any("29" in issue for issue in issues)


def test_byok_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HEATSAFE_BYOK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="HEATSAFE_BYOK_API_KEY"):
        byok_explanation(
            {"decision": "Result", "reasons": [], "input_values": {}},
            endpoint="https://example.invalid/v1/chat/completions",
            model="example-model",
        )


def test_hash_is_stable_for_key_order() -> None:
    assert input_sha256({"a": 1, "b": 2}) == input_sha256({"b": 2, "a": 1})
