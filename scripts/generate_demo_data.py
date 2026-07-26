from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
SAMPLE = ROOT / "data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)
SAMPLE.mkdir(parents=True, exist_ok=True)
rng = random.Random(42)

cities = [
    ("Istanbul", "Türkiye", 24.5, 12.0),
    ("Ankara", "Türkiye", 25.5, 18.0),
    ("Madrid", "Spain", 28.0, 10.0),
    ("Berlin", "Germany", 22.5, 9.0),
    ("Toronto", "Canada", 23.0, 8.0),
    ("Los Angeles", "United States", 25.0, 14.0),
]
start = datetime(2025, 6, 1, tzinfo=timezone.utc)

with (OUT / "hourly_environment.csv").open("w", newline="", encoding="utf-8") as file:
    fields = [
        "timestamp_utc",
        "city",
        "country",
        "temperature_c",
        "relative_humidity_pct",
        "pm25_ug_m3",
        "wind_speed_kmh",
        "measurement_type",
        "source_name",
    ]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    for city, country, base_temperature, base_pm25 in cities:
        for hour in range(24 * 90):
            timestamp = start + timedelta(hours=hour)
            daily = 5.2 * math.sin(2 * math.pi * (timestamp.hour - 8) / 24)
            seasonal = 3.0 * math.sin(2 * math.pi * hour / (24 * 90))
            heat_event = 6 if 700 <= hour < 790 else 0
            temperature = base_temperature + daily + seasonal + heat_event + rng.gauss(0, 0.8)
            humidity = max(20, min(95, 66 - 1.2 * daily + rng.gauss(0, 5)))
            smoke = 35 if 1200 <= hour < 1260 and city in {"Toronto", "Los Angeles"} else 0
            pm25 = max(
                1,
                base_pm25
                + 0.25 * humidity
                + smoke
                + 6 * math.sin(2 * math.pi * hour / 168)
                + rng.gauss(0, 4),
            )
            wind = max(0, 10 + 4 * math.sin(2 * math.pi * hour / 24) + rng.gauss(0, 2))
            writer.writerow(
                {
                    "timestamp_utc": timestamp.isoformat(),
                    "city": city,
                    "country": country,
                    "temperature_c": round(temperature, 2),
                    "relative_humidity_pct": round(humidity, 2),
                    "pm25_ug_m3": round(pm25, 2),
                    "wind_speed_kmh": round(wind, 2),
                    "measurement_type": "synthetic",
                    "source_name": "HeatSafe synthetic generator",
                }
            )

with (OUT / "climate_daily.csv").open("w", newline="", encoding="utf-8") as file:
    fields = [
        "timestamp",
        "temperature_c",
        "minimum_temperature_c",
        "maximum_temperature_c",
        "relative_humidity_pct",
        "city",
        "source",
        "measurement_type",
    ]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    start_date = datetime(1985, 1, 1, tzinfo=timezone.utc)
    for day in range(365 * 41):
        timestamp = start_date + timedelta(days=day)
        trend = 0.035 * (timestamp.year - 1985)
        seasonal = 10 * math.sin(2 * math.pi * (timestamp.timetuple().tm_yday - 90) / 365.25)
        mean = 16 + seasonal + trend + rng.gauss(0, 1.5)
        writer.writerow(
            {
                "timestamp": timestamp.isoformat(),
                "temperature_c": round(mean, 2),
                "minimum_temperature_c": round(mean - 5 - rng.random() * 2, 2),
                "maximum_temperature_c": round(mean + 5 + rng.random() * 3, 2),
                "relative_humidity_pct": round(max(20, min(95, 62 - seasonal + rng.gauss(0, 8))), 2),
                "city": "Illustrative City",
                "source": "HeatSafe synthetic generator",
                "measurement_type": "synthetic",
            }
        )

with (OUT / "urban_heat_grid.csv").open("w", newline="", encoding="utf-8") as file:
    fields = [
        "cell_id",
        "latitude",
        "longitude",
        "zone",
        "land_surface_temperature_c",
        "ndvi",
        "impervious_fraction",
        "water_distance_km",
    ]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    for index in range(240):
        urban = index < 160
        ndvi = max(0.05, min(0.9, (0.25 if urban else 0.62) + rng.gauss(0, 0.12)))
        land_surface_temperature = 34 + (4 if urban else 0) - 5 * ndvi + rng.gauss(0, 1.2)
        writer.writerow(
            {
                "cell_id": f"cell-{index:03d}",
                "latitude": round(41 + (index % 20) * 0.003, 5),
                "longitude": round(29 + (index // 20) * 0.003, 5),
                "zone": "urban" if urban else "peripheral",
                "land_surface_temperature_c": round(land_surface_temperature, 2),
                "ndvi": round(ndvi, 3),
                "impervious_fraction": round(
                    max(0, min(1, (0.75 if urban else 0.2) + rng.gauss(0, 0.1))),
                    3,
                ),
                "water_distance_km": round(rng.uniform(0.2, 20), 2),
            }
        )

with (OUT / "fire_events.csv").open("w", newline="", encoding="utf-8") as file:
    fields = ["latitude", "longitude", "acquired_at", "confidence", "frp_mw", "source"]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    for index in range(20):
        writer.writerow(
            {
                "latitude": round(40.5 + rng.random(), 5),
                "longitude": round(28.3 + rng.random() * 1.5, 5),
                "acquired_at": (start + timedelta(hours=index * 3)).isoformat(),
                "confidence": round(rng.uniform(50, 99), 1),
                "frp_mw": round(rng.uniform(2, 90), 1),
                "source": "synthetic",
            }
        )

with (SAMPLE / "home_log.csv").open("w", newline="", encoding="utf-8") as file:
    fields = [
        "timestamp",
        "indoor_temperature_c",
        "outdoor_temperature_c",
        "indoor_humidity_pct",
        "outdoor_humidity_pct",
        "indoor_pm25_ug_m3",
        "outdoor_pm25_ug_m3",
        "event",
    ]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    for hour in range(24 * 7):
        timestamp = start + timedelta(hours=hour)
        outside = 25 + 6 * math.sin(2 * math.pi * (timestamp.hour - 8) / 24)
        event = None
        if timestamp.hour == 21:
            event = "Windows Opened"
        elif timestamp.hour == 6:
            event = "Windows Closed"
        indoor = 27 + 2.2 * math.sin(2 * math.pi * (timestamp.hour - 12) / 24) + rng.gauss(0, 0.2)
        writer.writerow(
            {
                "timestamp": timestamp.isoformat(),
                "indoor_temperature_c": round(indoor, 2),
                "outdoor_temperature_c": round(outside, 2),
                "indoor_humidity_pct": 55,
                "outdoor_humidity_pct": 60,
                "indoor_pm25_ug_m3": 10,
                "outdoor_pm25_ug_m3": 14,
                "event": event or "",
            }
        )

print("Generated deterministic synthetic and sample data.")
