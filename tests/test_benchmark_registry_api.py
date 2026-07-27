from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from heatsafe.api.benchmark_registry import router


def test_registry_capabilities() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/v1/benchmark-registry/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["paid_ai_api_required"] is False
    assert body["live_provider_credentials_required_for_verification"] is False
