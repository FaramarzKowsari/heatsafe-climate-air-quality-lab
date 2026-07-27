from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from heatsafe.api.external_validation import router
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
)


def test_external_validation_capabilities_are_api_free() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get(
        "/api/v1/external-validation/capabilities"
    )
    assert response.status_code == 200
    assert response.json()["paid_ai_api_required"] is False


def test_external_validation_api_runs() -> None:
    frame = generate_synthetic_multicity_frame(
        rows_per_city=360,
        random_state=21,
    )
    selected_cities = frame["city"].drop_duplicates().iloc[:3].tolist()
    frame = frame[frame["city"].isin(selected_cities)].copy()
    frame["relative_humidity_pct"] = frame[
        "relative_humidity_pct"
    ].ffill().bfill()

    app = FastAPI()
    app.include_router(router)
    payload = {
        "timestamps": frame["timestamp"].astype(str).tolist(),
        "cities": frame["city"].tolist(),
        "regions": frame["region"].tolist(),
        "target_values": frame["pm25"].tolist(),
        "covariates": {
            "temperature_c": frame["temperature_c"].tolist(),
            "wind_speed_kmh": frame["wind_speed_kmh"].tolist(),
        },
        "horizons": [1],
        "bootstrap_repetitions": 20,
        "block_length": 12,
        "models": ["persistence", "ridge"],
    }
    response = TestClient(app).post(
        "/api/v1/external-validation/run",
        json=payload,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["study_name"] == "HeatSafe Multi-City External Validation"
    assert body["fold_metrics"]
