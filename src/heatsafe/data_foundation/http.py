from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Mapping

import httpx

from heatsafe.data_foundation.cache import JsonDiskCache, canonical_request_key


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 4
    base_backoff_seconds: float = 0.5
    maximum_backoff_seconds: float = 8.0
    jitter_seconds: float = 0.15
    retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass(frozen=True)
class HttpResult:
    payload: dict[str, Any] | str
    status_code: int
    final_url: str
    retrieved_at_utc: datetime
    from_cache: bool
    attempts: int
    response_sha256: str
    etag: str | None
    last_modified: str | None


class FixedWindowRateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be greater than zero")
        self.minimum_interval = 1.0 / requests_per_second
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self, sleeper: Callable[[float], None] = time.sleep) -> None:
        with self._lock:
            now = time.monotonic()
            remaining = self.minimum_interval - (now - self._last_request)
            if remaining > 0:
                sleeper(remaining)
            self._last_request = time.monotonic()


class ResilientHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: FixedWindowRateLimiter | None = None,
        cache: JsonDiskCache | None = None,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.transport = transport
        self.sleeper = sleeper

    @staticmethod
    def _sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _cache_payload(
        self,
        *,
        source_id: str,
        method: str,
        url: str,
        params: Mapping[str, Any] | None,
        response_kind: str,
    ) -> tuple[str, dict[str, Any]]:
        safe_request = {
            "method": method.upper(),
            "url": url,
            "params": dict(params or {}),
            "response_kind": response_kind,
        }
        return canonical_request_key(source_id, safe_request), safe_request

    def request(
        self,
        method: str,
        url: str,
        *,
        source_id: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        response_kind: str = "json",
        cache_ttl: timedelta | None = None,
    ) -> HttpResult:
        cache_key, _ = self._cache_payload(
            source_id=source_id,
            method=method,
            url=url,
            params=params,
            response_kind=response_kind,
        )
        if self.cache is not None and cache_ttl is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return HttpResult(
                    payload=cached["payload"],
                    status_code=int(cached["status_code"]),
                    final_url=str(cached["final_url"]),
                    retrieved_at_utc=datetime.fromisoformat(str(cached["retrieved_at_utc"])),
                    from_cache=True,
                    attempts=int(cached["attempts"]),
                    response_sha256=str(cached["response_sha256"]),
                    etag=cached.get("etag"),
                    last_modified=cached.get("last_modified"),
                )

        policy = self.retry_policy
        last_error: Exception | None = None
        with httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
            follow_redirects=True,
        ) as client:
            for attempt in range(1, policy.maximum_attempts + 1):
                if self.rate_limiter is not None:
                    self.rate_limiter.wait(self.sleeper)
                try:
                    response = client.request(method, url, params=params, headers=headers)
                    if response.status_code in policy.retry_statuses and attempt < policy.maximum_attempts:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = min(float(retry_after), policy.maximum_backoff_seconds)
                        else:
                            delay = min(
                                policy.base_backoff_seconds * (2 ** (attempt - 1)),
                                policy.maximum_backoff_seconds,
                            )
                            delay += random.uniform(0, policy.jitter_seconds)
                        self.sleeper(delay)
                        continue
                    response.raise_for_status()
                    raw = response.content
                    payload: dict[str, Any] | str
                    if response_kind == "json":
                        decoded = response.json()
                        if not isinstance(decoded, dict):
                            raise ValueError("Expected a JSON object response")
                        payload = decoded
                    elif response_kind == "text":
                        payload = response.text
                    else:
                        raise ValueError("response_kind must be 'json' or 'text'")

                    result = HttpResult(
                        payload=payload,
                        status_code=response.status_code,
                        final_url=str(response.url),
                        retrieved_at_utc=datetime.now(UTC),
                        from_cache=False,
                        attempts=attempt,
                        response_sha256=self._sha256(raw),
                        etag=response.headers.get("ETag"),
                        last_modified=response.headers.get("Last-Modified"),
                    )
                    if self.cache is not None and cache_ttl is not None:
                        self.cache.set(
                            cache_key,
                            {
                                "payload": payload,
                                "status_code": result.status_code,
                                "final_url": result.final_url,
                                "retrieved_at_utc": result.retrieved_at_utc.isoformat(),
                                "attempts": result.attempts,
                                "response_sha256": result.response_sha256,
                                "etag": result.etag,
                                "last_modified": result.last_modified,
                            },
                            cache_ttl,
                        )
                    return result
                except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                    last_error = exc
                    if attempt >= policy.maximum_attempts:
                        break
                    delay = min(
                        policy.base_backoff_seconds * (2 ** (attempt - 1)),
                        policy.maximum_backoff_seconds,
                    )
                    delay += random.uniform(0, policy.jitter_seconds)
                    self.sleeper(delay)

        raise RuntimeError(f"HTTP request failed after {policy.maximum_attempts} attempts: {last_error}")
