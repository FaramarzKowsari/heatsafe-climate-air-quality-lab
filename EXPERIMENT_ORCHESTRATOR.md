# Reproducible Experiment Orchestrator

## Purpose

The HeatSafe experiment orchestrator converts a frozen input identity and an immutable JSON specification into a complete, verifiable, paper-ready result bundle.

It is designed for:

- CPU-first environmental forecasting;
- synthetic smoke tests;
- canonical CSV inputs;
- frozen official snapshots;
- chronological evaluation;
- uncertainty-aware benchmarking;
- technical reports, preprints and reviewed releases.

No paid AI API is required.

## Command line

Create a complete template:

```bash
heatsafe-experiment template --output experiment.json
```

Run an experiment:

```bash
heatsafe-experiment run   --spec examples/experiments/heataq-nexus-synthetic.json   --output artifacts/experiments/heataq-nexus-synthetic   --repository-root .
```

Verify all checksums:

```bash
heatsafe-experiment verify artifacts/experiments/heataq-nexus-synthetic
```

Use `--overwrite` only when the existing output directory may be safely replaced.

## Supported data modes

### Synthetic

A deterministic HeatAQ Nexus table is generated with an explicit seed. This mode is appropriate for CI, demonstrations and software regression tests.

### CSV

A user-provided table is loaded and copied into the bundle as the canonical input artifact. The self-contained reproduction specification points to that copy.

### Frozen snapshot

A HeatSafe snapshot is loaded through the existing snapshot contract and converted into an hourly benchmark table. Variables, station selection and frequency remain explicit in the experiment specification.

## Output contract

Each successful run contains:

```text
experiment-spec.json
experiment-spec.original.json
data/
  input.csv
  dataset-descriptor.json
nexus/
  report.json
  leaderboard.csv
  model-cards.json
  config.json
  experiment-manifest.json
tables/
  all-model-metrics.csv
  rolling-origin-metrics.csv
  best-by-horizon.csv
  results-summary.json
figures/
  best-mae-by-horizon.svg
  coverage-by-horizon.svg
  event-f1-by-horizon.svg
report/
  report.md
  report.html
metadata/
  environment.json
  CITATION.cff
  zenodo-candidate.json
orchestration-manifest.json
artifact-index.json
verification.json
checksums.sha256
reproduce.sh
reproduce.cmd
release/
  <experiment>-<version>-candidate.zip
```

## Scientific safeguards

The orchestrator preserves the existing HeatAQ Nexus controls:

- chronological train, calibration and test partitions;
- no random time-series shuffling;
- persistence, seasonal-naive and moving-average baselines;
- linear, regularized and tree-based models;
- split-conformal prediction intervals;
- point, event and probabilistic metrics;
- rolling-origin evaluation;
- complete model reporting;
- explicit limitations and prohibited claims.

## Paper-ready reporting

The HTML and Markdown reports include:

- experiment identity;
- canonical input checksum;
- configuration;
- dataset summary;
- best model by horizon;
- complete results for every evaluated model;
- uncertainty coverage and interval width;
- SVG figures;
- leakage controls;
- limitations;
- exact reproduction and verification commands.

## Candidate release metadata

The generated `CITATION.cff` and `zenodo-candidate.json` are preparation artifacts only. They do not mint or claim a DOI. A DOI should be created only after review, a tagged release and validation of the real data identity.

## CI workflow

The dedicated workflow validates Python 3.11–3.13, runs linting and type checking, executes the orchestrator tests, generates the synthetic paper-ready demonstration, verifies all checksums and uploads the Python 3.12 result bundle as a workflow artifact.
