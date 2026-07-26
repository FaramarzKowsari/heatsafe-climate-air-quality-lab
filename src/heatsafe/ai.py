from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

import httpx


AIMode = Literal["standard", "local-ai", "byok"]
POLICY_VERSION = "1.0"
_NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", re.IGNORECASE)


@dataclass(frozen=True)
class AIExplanation:
    mode: str
    text: str
    values_cited: list[str]
    warning: str
    provider: str = "deterministic"
    model: str | None = None
    input_sha256: str = ""
    latency_ms: float | None = None
    grounding_issues: tuple[str, ...] = ()
    policy_version: str = POLICY_VERSION


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)


def input_sha256(result: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(result).encode("utf-8")).hexdigest()


def _flatten_numbers(value: Any) -> set[str]:
    numbers: set[str] = set()
    if isinstance(value, bool) or value is None:
        return numbers
    if isinstance(value, (int, float)):
        numbers.add(str(value))
        numbers.add(f"{float(value):g}")
        return numbers
    if isinstance(value, dict):
        for item in value.values():
            numbers.update(_flatten_numbers(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            numbers.update(_flatten_numbers(item))
    else:
        numbers.update(_NUMBER_PATTERN.findall(str(value)))
    return numbers


def validate_numeric_grounding(text: str, evidence: dict[str, Any]) -> tuple[str, ...]:
    allowed = _flatten_numbers(evidence)
    issues: list[str] = []
    for token in _NUMBER_PATTERN.findall(text):
        normalized = f"{float(token):g}"
        if token not in allowed and normalized not in allowed:
            issues.append(f"Numeric token {token!r} is not present in the supplied evidence")
    return tuple(dict.fromkeys(issues))


def _cited_values(result: dict[str, Any]) -> list[str]:
    values = result.get("input_values", {})
    if isinstance(values, dict):
        return [f"{key}={value}" for key, value in values.items() if value is not None][:12]
    return [str(value) for value in _flatten_numbers(result)][:12]


def deterministic_explanation(result: dict[str, Any]) -> AIExplanation:
    decision = result.get("decision", "Result")
    reasons = result.get("reasons", [])
    text = f"{decision}. " + " ".join(str(reason) for reason in reasons[:6])
    return AIExplanation(
        mode="standard",
        text=text.strip(),
        values_cited=_cited_values(result),
        warning="Generated directly from deterministic output; no language model was used.",
        provider="deterministic",
        model=None,
        input_sha256=input_sha256(result),
        grounding_issues=validate_numeric_grounding(text, result),
    )


def _prompt(result: dict[str, Any]) -> str:
    return (
        "Explain the supplied already-computed HeatSafe result in plain English. "
        "Do not change the decision, thresholds, confidence, measurements, units, timestamps, or limitations. "
        "Do not invent numbers, citations, medical advice, regulatory authority, or causal claims. "
        "State clearly that the language model is only explaining a deterministic or statistical result.\n\n"
        f"EVIDENCE_JSON:\n{_canonical_json(result)}"
    )


def ollama_explanation(
    result: dict[str, Any],
    *,
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434",
    timeout_seconds: float = 60.0,
) -> AIExplanation:
    started = time.perf_counter()
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": _prompt(result), "stream": False, "options": {"temperature": 0}},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    text = str(response.json().get("response", "")).strip()
    latency = (time.perf_counter() - started) * 1000
    issues = validate_numeric_grounding(text, result)
    return AIExplanation(
        mode="local-ai",
        text=text,
        values_cited=_cited_values(result),
        warning="The local model only explains an existing result and must not override it.",
        provider="ollama",
        model=model,
        input_sha256=input_sha256(result),
        latency_ms=round(latency, 3),
        grounding_issues=issues,
    )


def byok_explanation(
    result: dict[str, Any],
    *,
    endpoint: str,
    model: str,
    api_key_env: str = "HEATSAFE_BYOK_API_KEY",
    timeout_seconds: float = 60.0,
) -> AIExplanation:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("endpoint must be an absolute HTTP or HTTPS URL")

    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing secret environment variable: {api_key_env}")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an explanation layer. Explain only the supplied evidence. "
                    "Never alter a decision or invent measurements, citations, units, thresholds, or authority."
                ),
            },
            {"role": "user", "content": _prompt(result)},
        ],
        "temperature": 0,
    }

    started = time.perf_counter()
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    text = str(response.json()["choices"][0]["message"]["content"]).strip()
    latency = (time.perf_counter() - started) * 1000
    issues = validate_numeric_grounding(text, result)
    provider = parsed.hostname or "byok-provider"

    return AIExplanation(
        mode="byok",
        text=text,
        values_cited=_cited_values(result),
        warning="The external model only explains an existing result and may still produce language errors.",
        provider=provider,
        model=model,
        input_sha256=input_sha256(result),
        latency_ms=round(latency, 3),
        grounding_issues=issues,
    )


def capabilities() -> dict[str, dict[str, object]]:
    return {
        "standard": {
            "available": True,
            "requires_ai_api": False,
            "requires_network": False,
            "role": "Deterministic explanation assembled from computed outputs.",
        },
        "local-ai": {
            "available": True,
            "requires_ai_api": False,
            "requires_network": False,
            "requires_local_model_server": True,
            "role": "Optional local language explanation; cannot override scientific output.",
        },
        "byok": {
            "available": True,
            "requires_ai_api": True,
            "requires_user_secret": True,
            "role": "Optional provider-neutral cloud explanation with user-managed credentials.",
        },
    }
