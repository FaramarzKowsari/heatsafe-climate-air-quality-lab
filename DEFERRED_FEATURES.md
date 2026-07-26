# Intentionally Deferred Features

The v0.1.0 research preview implements every required analytical domain at a functional core level, while the following production integrations remain deliberately deferred:

- Credentialed, rate-limit-aware NOAA CDO production adapter
- Credentialed US EPA AQS production adapter
- Large-download Copernicus ERA5-Land ingestion and cache management
- NASA FIRMS production adapter and trajectory-model integration
- EEA bulk Parquet ingestion
- ECCC collection-specific production ingestion
- Verified machine interfaces for Türkiye MGM and the national air-quality network
- Eurostat, EIA, and EPİAŞ live regional price adapters
- Landsat/Sentinel raster tiling and map-server deployment
- Trained and validated neural time-series model
- Preregistered leave-one-city-out and leave-one-region-out benchmark on versioned real data
- Encrypted remote backup for household logs
- Operational authentication, rate limiting, observability, and managed database deployment
- Verified Google Books URL, book DOI, software DOI, and dataset DOI

These items are not represented as completed. Adapter contracts, provenance requirements, environment variables, workflow notes, and roadmap milestones are included so implementation can proceed without redesigning the repository.
