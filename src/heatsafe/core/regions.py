from __future__ import annotations

REGIONAL_WORKFLOWS = {
    "turkiye": {
        "label": "Türkiye",
        "cities": {
            "istanbul": {"latitude": 41.0082, "longitude": 28.9784, "context": ["urban heat", "humid heat", "coastal airflow"]},
            "ankara": {"latitude": 39.9334, "longitude": 32.8597, "context": ["continental heat", "hot-day variability", "night cooling"]},
            "izmir": {"latitude": 38.4237, "longitude": 27.1428, "context": ["Mediterranean heat", "coastal humidity", "wildfire context"]},
            "antalya": {"latitude": 36.8969, "longitude": 30.7133, "context": ["humid heat", "hot nights", "cooling demand"]},
            "adana": {"latitude": 37.0000, "longitude": 35.3213, "context": ["extreme heat", "humidity", "air quality"]},
            "bursa": {"latitude": 40.1950, "longitude": 29.0600, "context": ["urban heat", "industrial air quality", "valley circulation"]},
        },
    },
    "europe": {
        "label": "Europe",
        "cities": {
            "berlin": {"latitude": 52.5200, "longitude": 13.4050, "context": ["Central European flat", "hot nights", "urban heat"]},
            "madrid": {"latitude": 40.4168, "longitude": -3.7038, "context": ["dry heat", "solar gain", "night flushing"]},
            "athens": {"latitude": 37.9838, "longitude": 23.7275, "context": ["Mediterranean heat", "urban heat", "wildfire smoke"]},
            "amsterdam": {"latitude": 52.3676, "longitude": 4.9041, "context": ["humid coastal home", "limited night cooling", "indoor humidity"]},
        },
    },
    "united-states": {
        "label": "United States",
        "cities": {
            "new-york": {"latitude": 40.7128, "longitude": -74.0060, "context": ["humid heat", "urban heat", "air quality"]},
            "los-angeles": {"latitude": 34.0522, "longitude": -118.2437, "context": ["dry heat", "wildfire smoke", "ozone"]},
            "phoenix": {"latitude": 33.4484, "longitude": -112.0740, "context": ["extreme heat", "hot nights", "cooling demand"]},
            "seattle": {"latitude": 47.6062, "longitude": -122.3321, "context": ["wildfire smoke", "increasing heat exposure", "limited home cooling"]},
        },
    },
    "canada": {
        "label": "Canada",
        "cities": {
            "toronto": {"latitude": 43.6532, "longitude": -79.3832, "context": ["humid heat", "urban heat", "air quality"]},
            "vancouver": {"latitude": 49.2827, "longitude": -123.1207, "context": ["wildfire smoke", "coastal climate", "heat dome context"]},
            "calgary": {"latitude": 51.0447, "longitude": -114.0719, "context": ["dry heat", "smoke transport", "rapid weather change"]},
        },
    },
}
