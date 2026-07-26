# Production-Grade Data Foundation

## Purpose

The HeatSafe data foundation separates retrieval, normalization, quality control, snapshots and scientific analysis. A connector does not become scientifically trustworthy merely because it returns rows.

## Pipeline

```text
official or local source
→ resilient retrieval
→ source-specific parsing
→ NormalizedObservation contract
→ quality assessment
→ deduplication
→ immutable JSONL snapshot
→ checksums and manifest
→ analysis or model training
```

## Implemented foundations

### NOAA NCEI Climate Data Online

- token-based access;
- GHCN Daily station requests;
- metric unit request;
- pagination;
- explicit station and datatype identity;
- provider attributes retained in the quality flag;
- approximate one-year request boundary;
- cache, rate limiting and retry support.

### US EPA AQS

- email and API-key access;
- sample-level county requests;
- GMT timestamps;
- station, method, duration and qualifier retention;
- PM2.5 parameter normalization;
- cache, rate limiting and retry support.

### NASA FIRMS

- MAP_KEY access;
- Area CSV API;
- VIIRS/MODIS source selection;
- fire radiative power normalization;
- confidence, product version and day/night metadata;
- no unsupported smoke-attribution claim.

### European Environment Agency

- local zipped-Parquet workflow;
- flexible column mapping;
- station, verification and validity retention;
- archive and reporting-country terms must be reviewed.

### ERA5-Land

- validated request specification;
- no hidden automatic high-volume download;
- credentials, storage, licensing and versioning remain explicit.

### Türkiye

Machine-readable endpoints and redistribution terms must be verified before automation. The registry records these sources without embedding undocumented endpoints.

## Reliability controls

- exponential retry with jitter;
- Retry-After support;
- fixed-window rate limiting;
- JSON disk cache with TTL;
- canonical request hashing;
- response SHA-256;
- ETag and Last-Modified capture;
- atomic snapshot writes;
- snapshot checksum verification;
- duplicate and range checks;
- unit and license checks.

## Credentials

Secrets belong in environment variables:

```text
NOAA_CDO_TOKEN
EPA_AQS_EMAIL
EPA_AQS_KEY
NASA_FIRMS_MAP_KEY
CDSAPI_URL
CDSAPI_KEY
```

Never commit credentials or place them in public browser JavaScript.

## Commands

```bash
heatsafe-data sources
heatsafe-data quality data/example-observations.jsonl
heatsafe-data snapshot data/example-observations.jsonl \
  --source-id noaa-cdo-ghcnd \
  --snapshot-id noaa-demo-001 \
  --output artifacts/noaa-demo-001
heatsafe-data verify artifacts/noaa-demo-001
```

## Scientific limitations

- A successful API response does not guarantee representativeness.
- Source quality flags and method metadata must be interpreted.
- Forecast, reanalysis, satellite and station observations remain distinct.
- Cache freshness must match the scientific question.
- Dataset snapshots are citable artifacts only after license review and versioned release.
