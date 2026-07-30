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

### Pack 06 implementation status

- secret-free official acquisition plans;
- NOAA, EPA and NASA FIRMS connector orchestration;
- EEA local Parquet acquisition;
- ERA5-Land request specifications;
- deterministic quality gates;
- immutable snapshot and benchmark-table export;
- automated Dataset Cards and registry indexing;
- CLI, API, public page and dedicated CI workflow.

<!-- HEATSAFE_FIRST_REAL_EXPERIMENT_ROADMAP_V1 -->
### Pack 07.1 implementation status

- secret-free real-experiment execution plans;
- local credential boundary for EPA AQS acquisition;
- immutable 2025 Alameda County PM2.5 snapshot recipe;
- deterministic monitoring-station selection by temporal continuity;
- strictly contiguous hourly benchmark preparation without target imputation;
- integration with the paper-ready experiment orchestrator;
- snapshot, prepared-input and experiment verification;
- one-click Windows runner that opens the final HTML report;
- public documentation page and dedicated Python 3.11–3.13 CI workflow;
- deliberate separation of hourly EPA data from daily NOAA data until a
  defensible temporal-alignment protocol is implemented.

<!-- HEATSAFE_REVIEWED_RELEASE_ROADMAP_V1 -->
### Pack 08 implementation status

- verified-source publication gate;
- curated reviewed candidate release directory;
- deterministic ZIP with SHA-256 checksums;
- release summary in JSON and HTML;
- Citation File Format dataset metadata;
- reviewed Zenodo deposition metadata and GitHub template;
- DataCite metadata starting point;
- scientific limitations and publication checklist;
- dedicated Python 3.11-3.13 CI workflow;
- no automatic upload, publication or DOI claim.

<!-- HEATSAFE_SCIENTIFIC_PACK_08_1_ROADMAP_V1 -->
## Scientific Pack 08.1 — Final metadata harmonization

- [x] Separate public release identity from historical execution identity.
- [x] Harmonize the actual San Diego geography and station metadata.
- [x] Record UTC and local-time interval endpoints.
- [x] Explain the source-year/UTC-year boundary.
- [x] Regenerate Citation File Format, Zenodo and DataCite metadata.
- [x] Preserve the pre-harmonization candidate and source provenance.
- [ ] Complete final human publication checklist.
- [ ] Create a GitHub Release only after approval.
- [ ] Publish to Zenodo and add the DOI only after approval.

<!-- HEATSAFE_SCIENTIFIC_PACK_09_ROADMAP_V1 -->
## Scientific Pack 09 — publication handoff

- [x] Verify and stage the final harmonized research archive.
- [x] Generate exact GitHub release notes and Zenodo form guidance.
- [x] Generate SHA-256 checksums for publication assets.
- [x] Provide a GitHub draft-only creation command.
- [x] Preserve repository-root software citation metadata.
- [x] Block automatic GitHub and Zenodo publication.
- [ ] Create and review the GitHub draft release.
- [ ] Create and review the Zenodo draft upload.
- [ ] Reserve the Zenodo DOI.
- [ ] Inject the reserved DOI and rebuild the final archive.
- [ ] Publish Zenodo, verify DOI resolution, then publish GitHub.
