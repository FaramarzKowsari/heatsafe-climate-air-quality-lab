from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class AIExplanation:
    mode: str
    text: str
    values_cited: list[str]
    warning: str


def deterministic_explanation(result: dict[str, Any]) -> AIExplanation:
    decision = result.get("decision", "Result")
    reasons = result.get("reasons", [])
    text = f"{decision}. " + " ".join(str(reason) for reason in reasons[:4])
    values = [str(value) for key, value in result.get("input_values", {}).items() if value is not None][:8]
    return AIExplanation(
        mode="standard",
        text=text,
        values_cited=values,
        warning="Generated from deterministic output; no language model was used.",
    )


def ollama_explanation(result: dict[str, Any], *, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> AIExplanation:
    prompt = (
        "Explain the following already-computed HeatSafe result in plain English. "
        "Do not change the decision, invent values, or provide medical advice.\n\n"
        f"{result}"
    )
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    text = response.json().get("response", "")
    return AIExplanation(
        mode="local-ai",
        text=text,
        values_cited=[str(value) for value in result.get("input_values", {}).values() if value is not None][:8],
        warning="The language model only explains a deterministic result and must not override it.",
    )


def byok_explanation(result: dict[str, Any], *, endpoint: str, api_key_env: str = "HEATSAFE_BYOK_API_KEY", model: str) -> AIExplanation:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing secret environment variable: {api_key_env}")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Explain only the supplied deterministic result. Do not alter it or invent measurements.",
            },
            {"role": "user", "content": str(result)},
        ],
        "temperature": 0,
    }
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    return AIExplanation(
        mode="byok",
        text=text,
        values_cited=[str(value) for value in result.get("input_values", {}).values() if value is not None][:8],
        warning="The external model only explains a deterministic result and may still produce language errors.",
    )
