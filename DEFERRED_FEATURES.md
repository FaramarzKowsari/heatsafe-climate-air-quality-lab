# Intentionally Deferred Features

The research preview implements each analytical domain at a functional core level. The following production integrations remain deliberately deferred:

- credentialed, rate-limit-aware NOAA CDO production adapter;
- credentialed US EPA AQS production adapter;
- large-download Copernicus ERA5-Land ingestion and cache management;
- NASA FIRMS production adapter and trajectory-model integration;
- EEA bulk Parquet ingestion;
- ECCC collection-specific production ingestion;
- verified machine interfaces for Türkiye MGM and the national air-quality network;
- Landsat/Sentinel raster tiling and map-server deployment;
- trained and validated neural time-series models;
- preregistered leave-one-city-out and leave-one-region-out evaluation on versioned real data;
- adaptive conformal prediction under distribution shift;
- operational authentication, rate limiting, observability and managed database deployment;
- independent replication and scientific review;
- software and dataset DOI issuance for reviewed releases.

Deferred items are not represented as completed. Adapter contracts, provenance requirements, environment variables, workflow notes and roadmap milestones are retained so implementation can proceed without redesigning the platform.
