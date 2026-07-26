from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from heatsafe.data_foundation.cache import JsonDiskCache
from heatsafe.data_foundation.http import (
    FixedWindowRateLimiter,
    ResilientHttpClient,
    RetryPolicy,
)


class ConnectorError(RuntimeError):
    pass


class BaseConnector:
    name: str

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
        cache: JsonDiskCache | None = None,
        retry_policy: RetryPolicy | None = None,
        requests_per_second: float | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.cache = cache
        self.retry_policy = retry_policy or RetryPolicy()
        self.rate_limiter = (
            FixedWindowRateLimiter(requests_per_second)
            if requests_per_second is not None
            else None
        )

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
            follow_redirects=True,
        )

    def _resilient_client(self) -> ResilientHttpClient:
        return ResilientHttpClient(
            timeout_seconds=self.timeout_seconds,
            retry_policy=self.retry_policy,
            rate_limiter=self.rate_limiter,
            cache=self.cache,
            transport=self.transport,
        )

    @staticmethod
    def retrieved_now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def default_cache_ttl() -> timedelta:
        return timedelta(hours=6)
