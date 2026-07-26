from datetime import datetime, timezone
import pytest
from heatsafe.core.models import ClimateRecord

@pytest.fixture
def climate_records():
    out=[]
    for year in range(2000,2025):
        for month in (1,4,7,10):
            temp=14+(year-2000)*0.05+(8 if month==7 else 0)
            out.append(ClimateRecord(timestamp=datetime(year,month,15,tzinfo=timezone.utc),temperature_c=temp,minimum_temperature_c=temp-5,maximum_temperature_c=temp+6,relative_humidity_pct=55))
    return out
