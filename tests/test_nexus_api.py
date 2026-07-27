from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from heatsafe.api.heataq_nexus import router
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame


def test_nexus_capabilities_require_no_paid_ai() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/v1/nexus/capabilities")
    assert response.status_code == 200
    assert response.json()["paid_ai_api_required"] is False


def test_nexus_api_runs_small_benchmark() -> None:
    frame = generate_synthetic_nexus_frame(rows=400)
    app = FastAPI()
    app.include_router(router)
    payload = {
        "timestamps": frame["timestamp"].astype(str).tolist(),
        "target_values": frame["pm25"].tolist(),
        "covariates": {
            "temperature_c": frame["temperature_c"].tolist(),
            "wind_speed_kmh": frame["wind_speed_kmh"].tolist(),
        },
        "horizons": [1],
        "event_threshold": 35.0,
    }
    response = TestClient(app).post("/api/v1/nexus/run", json=payload)
    assert response.status_code == 200
    assert response.json()["benchmark_name"] == "HeatAQ Nexus"
