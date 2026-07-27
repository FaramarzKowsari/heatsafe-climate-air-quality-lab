from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from heatsafe.api.official_snapshots import router


def test_official_snapshot_capabilities() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/v1/official-snapshots/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["paid_ai_api_required"] is False
    assert body["live_downloads_in_ci"] is False
    assert "immutable snapshots" in body["supports"]


def test_plan_endpoint_rejects_unknown_source() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/api/v1/official-snapshots/plan",
        json={
            "source_id": "unknown-source",
            "dataset_id": "unknown-demo",
            "version": "1.0.0",
            "title": "Unknown source demonstration",
            "description": "A deliberately invalid request used to test validation behavior.",
            "target_variables": ["pm25"],
            "station_selection_protocol": "Use a predetermined monitoring location.",
            "quality_control_protocol": "Preserve provider flags and run checks.",
            "missing_data_policy": "Do not impute missing values.",
            "known_limitations": ["This request is intentionally invalid."],
            "request_parameters": {},
        },
    )
    assert response.status_code == 422
