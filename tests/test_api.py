from fastapi.testclient import TestClient
from heatsafe.api.app import app
client=TestClient(app)

def test_health_and_index():
    assert client.get("/api/v1/health").json()["status"]=="ok"
    assert client.get("/").status_code==200

def test_ventilation_api():
    r=client.post("/api/v1/ventilation/decision",json={"indoor_temperature_c":30,"outdoor_temperature_c":23,"pm25_ug_m3":8,"smoke_context":"none"})
    assert r.status_code==200 and r.json()["decision"]=="Favorable Ventilation"

def test_cost_api():
    r=client.post("/api/v1/cooling/cost",json={"device_power_w":1000,"estimated_duty_cycle":.5,"daily_runtime_hours":10,"number_of_days":20,"electricity_price_per_kwh":.2})
    assert r.status_code==200 and r.json()["central"]["energy_kwh"]==100

def test_air_quality_length_validation():
    r=client.post("/api/v1/air-quality/summary",json={"timestamps":["2026-01-01T00:00:00Z"],"values":[1,2]})
    assert r.status_code==422

def test_benchmark_horizon_validation():
    r=client.post("/api/v1/benchmark/run",json={"values":[10.0]*200,"horizons":[2]})
    assert r.status_code==422
