# Roadmap

## v0.1.x — Scientific independence and foundations

- remove all non-research product coupling;
- establish independent research identity;
- formalize standard, local-AI and BYOK modes;
- add compound-risk and experiment-provenance modules;
- enforce scientific-identity checks in CI;
- preserve no-paid-API workflows.

## v0.2 — Production-grade data foundation

- harden NOAA, EPA AQS, EEA, ECCC, ERA5-Land, FIRMS and Türkiye adapters;
- add rate-limit, retry, cache and license-aware connector behavior;
- add versioned raw-to-normalized data pipelines;
- produce source-specific data cards;
- add station/grid reconciliation and unit harmonization.

## v0.3 — HeatAQ Nexus benchmark

- city-aware datasets;
- rolling-origin evaluation;
- calibrated CPU and neural baselines;
- experiment registry;
- model-card generation;
- reproducible leaderboard;
- versioned benchmark release.

## v0.4 — Geospatial and domain-shift validation

- leave-one-city-out evaluation;
- leave-one-region-out evaluation;
- spatial block cross-validation;
- remote-sensing feature pipeline;
- urban morphology and vegetation features;
- uncertainty under geographic transfer.

## v0.5 — Compound risk science

- transparent additive and interaction-aware formulations;
- threshold and weight sensitivity;
- compound-event detection;
- hot-night persistence analysis;
- comparison against single-hazard baselines;
- preregistered regional validation.

## v0.6 — Advanced AI research layer

- local open-source model benchmarking;
- provider-neutral BYOK adapters;
- structured explanation schemas;
- numeric and citation grounding;
- retrieval over selected scientific documents;
- prompt and model provenance;
- red-team tests for hallucination and decision override.

## v0.7 — Research outputs

- software DOI for a reviewed release;
- dataset DOI for HeatAQ Nexus;
- technical report or preprint;
- reproducibility archive;
- external contributor and replication workflow.

## v1.0 — Stable scientific release

- independent scientific review;
- accessibility audit;
- security and privacy review;
- hardened deployment;
- documented public datasets;
- validated regional benchmarks;
- complete citation and archival workflow.

### Pack 02 implementation status

- typed source registry and access modes;
- resilient retrieval with retry, rate limiting and cache;
- quality assessment and deduplication;
- immutable snapshot manifests and checksum verification;
- NOAA CDO, EPA AQS and NASA FIRMS connector foundations;
- EEA local-Parquet normalization;
- ERA5-Land request specification;
- registry-only Türkiye sources pending verified machine interfaces.

### Pack 03 implementation status

- Pack 02 snapshot-to-hourly dataset builder;
- leakage-controlled temporal and exogenous features;
- persistence, seasonal-naive, moving-average, linear, ridge and tree baselines;
- chronological train/calibration/test evaluation;
- split-conformal intervals;
- rolling-origin evaluation;
- model cards, leaderboard and experiment manifests;
- CLI, API, public research page and dedicated CI workflow.

### Pack 04 implementation status

- leave-one-city-out external validation;
- leave-one-region-out external validation;
- target, feature and event-rate shift diagnostics;
- moving-block bootstrap confidence intervals;
- horizon-aware Diebold–Mariano comparisons;
- seasonal and event-intensity slices;
- geographic robustness leaderboard;
- validation cards and reproducible manifests;
- CLI, API, public research page and dedicated CI workflow.

### Pack 05 implementation status

- official-source Dataset Card contracts;
- immutable artifact checksums and dimensions;
- deterministic registry index;
- benchmark protocol and release contracts;
- release-bundle manifests;
- CLI, API, documentation, public page and dedicated CI workflow.
