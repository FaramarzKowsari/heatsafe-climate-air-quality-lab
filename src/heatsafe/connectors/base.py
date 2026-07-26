from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx

from heatsafe.core.models import NormalizedObservation


class ConnectorError(RuntimeError):
    pass


class BaseConnector(ABC):
    name: str

    def __init__(self, *, timeout_seconds: float = 20.0, transport: httpx.BaseTransport | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds, transport=self.transport, follow_redirects=True)

    @abstractmethod
    def fetch(self, **kwargs: Any) -> list[NormalizedObservation]:
        raise NotImplementedError

    @staticmethod
    def retrieved_now() -> datetime:
        return datetime.now(timezone.utc)
