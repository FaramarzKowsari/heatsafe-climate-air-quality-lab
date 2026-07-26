from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import httpx

from heatsafe.data_foundation.cache import JsonDiskCache
from heatsafe.data_foundation.http import ResilientHttpClient, RetryPolicy


def test_retry_then_success() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "temporary"}, request=request)
        return httpx.Response(200, json={"results": [1]}, request=request)

    client = ResilientHttpClient(
        transport=httpx.MockTransport(handler),
        retry_policy=RetryPolicy(maximum_attempts=2, base_backoff_seconds=0, jitter_seconds=0),
        sleeper=lambda _: None,
    )
    result = client.request("GET", "https://example.org/data", source_id="test")
    assert result.attempts == 2
    assert result.payload == {"results": [1]}


def test_cache_avoids_second_transport_call(tmp_path: Path) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"value": 42}, request=request)

    client = ResilientHttpClient(
        transport=httpx.MockTransport(handler),
        cache=JsonDiskCache(tmp_path),
    )
    first = client.request(
        "GET",
        "https://example.org/data",
        source_id="test",
        cache_ttl=timedelta(hours=1),
    )
    second = client.request(
        "GET",
        "https://example.org/data",
        source_id="test",
        cache_ttl=timedelta(hours=1),
    )
    assert first.from_cache is False
    assert second.from_cache is True
    assert calls["count"] == 1
