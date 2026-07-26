# API

FastAPI generates OpenAPI documentation at `/docs` and `/redoc`. Core endpoints cover health, regions, home profile, one-time ventilation decision, hourly planner, cooling cost, indoor–outdoor comparison, climate trends, heatwave detection, air-quality summary, urban heat, wildfire context, and the CPU benchmark.

All household decision responses expose limitations. Validation errors use standard HTTP 422 responses.
