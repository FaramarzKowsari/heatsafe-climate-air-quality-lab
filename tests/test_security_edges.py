import pytest
from pydantic import ValidationError
from heatsafe.core.models import NormalizedObservation, CoolingCostInput

def test_invalid_coordinates_rejected():
    with pytest.raises(ValidationError):
        NormalizedObservation(source_name="x",source_dataset="y",latitude=100,longitude=0,timestamp_utc="2026-01-01T00:00:00Z",variable="t",value=1,unit="C",measurement_type="observed",retrieved_at="2026-01-01T00:00:00Z",license="x",source_url="https://example.org")

def test_impossible_duty_cycle_rejected():
    with pytest.raises(ValidationError):
        CoolingCostInput(device_power_w=1000,estimated_duty_cycle=1.5,daily_runtime_hours=4,number_of_days=3,electricity_price_per_kwh=.2)
