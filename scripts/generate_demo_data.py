from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv, math, random

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
with (OUT / "hourly_environment.csv").open("w", newline="", encoding="utf-8") as f:
    fields = ["timestamp_utc", "city", "country", "temperature_c", "relative_humidity_pct", "pm25_ug_m3", "wind_speed_kmh", "measurement_type", "source_name"]
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    for city, country, base_t, base_pm in cities:
        for h in range(24 * 90):
            t = start + timedelta(hours=h)
            daily = 5.2 * math.sin(2 * math.pi * (t.hour - 8) / 24)
            seasonal = 3.0 * math.sin(2 * math.pi * h / (24 * 90))
            heat_event = 6 if 700 <= h < 790 else 0
            temp = base_t + daily + seasonal + heat_event + rng.gauss(0, 0.8)
            humidity = max(20, min(95, 66 - 1.2 * daily + rng.gauss(0, 5)))
            smoke = 35 if 1200 <= h < 1260 and city in {"Toronto", "Los Angeles"} else 0
            pm = max(1, base_pm + 0.25 * humidity + smoke + 6 * math.sin(2 * math.pi * h / 168) + rng.gauss(0, 4))
            wind = max(0, 10 + 4 * math.sin(2 * math.pi * h / 24) + rng.gauss(0, 2))
            w.writerow({"timestamp_utc": t.isoformat(), "city": city, "country": country, "temperature_c": round(temp,2), "relative_humidity_pct": round(humidity,2), "pm25_ug_m3": round(pm,2), "wind_speed_kmh": round(wind,2), "measurement_type": "synthetic", "source_name": "HeatSafe synthetic generator"})

with (OUT / "climate_daily.csv").open("w", newline="", encoding="utf-8") as f:
    fields = ["timestamp", "temperature_c", "minimum_temperature_c", "maximum_temperature_c", "relative_humidity_pct", "city", "source", "measurement_type"]
    w=csv.DictWriter(f, fieldnames=fields); w.writeheader()
    start_d=datetime(1985,1,1,tzinfo=timezone.utc)
    for i in range(365*41):
        t=start_d+timedelta(days=i)
        trend=0.035*(t.year-1985)
        seasonal=10*math.sin(2*math.pi*(t.timetuple().tm_yday-90)/365.25)
        mean=16+seasonal+trend+rng.gauss(0,1.5)
        w.writerow({"timestamp":t.isoformat(),"temperature_c":round(mean,2),"minimum_temperature_c":round(mean-5-rng.random()*2,2),"maximum_temperature_c":round(mean+5+rng.random()*3,2),"relative_humidity_pct":round(max(20,min(95,62-seasonal+rng.gauss(0,8))),2),"city":"Illustrative City","source":"HeatSafe synthetic generator","measurement_type":"synthetic"})

with (OUT / "urban_heat_grid.csv").open("w", newline="", encoding="utf-8") as f:
    fields=["cell_id","latitude","longitude","zone","land_surface_temperature_c","ndvi","impervious_fraction","water_distance_km"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for i in range(240):
        urban=i<160; ndvi=max(0.05,min(0.9,(0.25 if urban else 0.62)+rng.gauss(0,0.12)))
        lst=34+(4 if urban else 0)-5*ndvi+rng.gauss(0,1.2)
        w.writerow({"cell_id":f"cell-{i:03d}","latitude":round(41+(i%20)*0.003,5),"longitude":round(29+(i//20)*0.003,5),"zone":"urban" if urban else "peripheral","land_surface_temperature_c":round(lst,2),"ndvi":round(ndvi,3),"impervious_fraction":round(max(0,min(1,(0.75 if urban else 0.2)+rng.gauss(0,0.1))),3),"water_distance_km":round(rng.uniform(0.2,20),2)})

with (OUT / "fire_events.csv").open("w", newline="", encoding="utf-8") as f:
    fields=["latitude","longitude","acquired_at","confidence","frp_mw","source"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for i in range(20):
        w.writerow({"latitude":round(40.5+rng.random(),5),"longitude":round(28.3+rng.random()*1.5,5),"acquired_at":(start+timedelta(hours=i*3)).isoformat(),"confidence":round(rng.uniform(50,99),1),"frp_mw":round(rng.uniform(2,90),1),"source":"synthetic"})

with (SAMPLE / "home_log.csv").open("w", newline="", encoding="utf-8") as f:
    fields=["timestamp","indoor_temperature_c","outdoor_temperature_c","indoor_humidity_pct","outdoor_humidity_pct","indoor_pm25_ug_m3","outdoor_pm25_ug_m3","event"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for h in range(24*7):
        t=start+timedelta(hours=h); outside=25+6*math.sin(2*math.pi*(t.hour-8)/24); event=None
        if t.hour==21: event="Windows Opened"
        elif t.hour==6: event="Windows Closed"
        indoor=27+2.2*math.sin(2*math.pi*(t.hour-12)/24)+rng.gauss(0,.2)
        w.writerow({"timestamp":t.isoformat(),"indoor_temperature_c":round(indoor,2),"outdoor_temperature_c":round(outside,2),"indoor_humidity_pct":55,"outdoor_humidity_pct":60,"indoor_pm25_ug_m3":10,"outdoor_pm25_ug_m3":14,"event":event or ""})
print("Generated deterministic synthetic and sample data.")
