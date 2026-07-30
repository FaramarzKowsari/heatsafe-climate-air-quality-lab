# Reproducibility

1. Use Python 3.11–3.13 and install `pip install -e ".[dev]"`.
2. Run `python scripts/generate_demo_data.py`. The generator uses seed 42.
3. Run `pytest --cov=heatsafe`.
4. Run `make benchmark` to regenerate `benchmarks/heataq-nexus/results/cpu_baselines.json`.
5. Record operating system, Python version, dependency lock or freeze, git commit, and data checksums when publishing results.

The stored synthetic benchmark is a smoke test, not evidence about any real city.

<!-- HEATSAFE_EXPERIMENT_ORCHESTRATOR_REPRODUCIBILITY_V1 -->
## Paper-ready orchestrated experiments

Create and run the included deterministic example:

```bash
heatsafe-experiment run   --spec examples/experiments/heataq-nexus-synthetic.json   --output artifacts/experiments/heataq-nexus-synthetic   --repository-root .
```

Verify every non-release artifact:

```bash
heatsafe-experiment verify artifacts/experiments/heataq-nexus-synthetic
```

The generated directory includes the canonical input, normalized specification,
complete model metrics, uncertainty figures, HTML and Markdown reports,
environment metadata, experiment manifests, exact reproduction scripts,
SHA-256 checksums and a deterministic candidate ZIP archive.

Synthetic data validate software behavior only and are not evidence about a
real city. Review real data identity, limitations and release metadata before
creating a tagged scientific release or DOI.

<!-- HEATSAFE_FIRST_REAL_EXPERIMENT_REPRO_V1 -->
## Reproducing the first official-source experiment

Generate a secret-free plan:

```bash
heatsafe-real-experiment plan   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --output artifacts/plans/epa-aqs-alameda-pm25-2025.json
```

For a live local run, set `EPA_AQS_EMAIL` and `EPA_AQS_KEY`, then execute:

```bash
heatsafe-real-experiment run   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025   --repository-root .
```

Windows users can run `RUN_FIRST_REAL_EPA_EXPERIMENT.cmd`. Credential values
remain in the current process only and are not persisted in plans, snapshots,
reports or repository files.

Verify the completed workspace:

```bash
heatsafe-real-experiment verify   artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025
```

The selected station and contiguous segment are recorded in
`prepared/station-selection-report.json`. The final technical report is
`experiment/report/report.html`.

<!-- HEATSAFE_REVIEWED_RELEASE_REPRO_V1 -->
## Building a reviewed candidate release

```bash
heatsafe-release-review build \
  --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025-bulk \
  --output artifacts/releases/epa-pm25-2025-first-real-reviewed \
  --overwrite
```

Verify the reviewed release:

```bash
heatsafe-release-review verify \
  artifacts/releases/epa-pm25-2025-first-real-reviewed
```

Windows users can run `BUILD_REVIEWED_EPA_RELEASE_08.cmd`. The output remains
local and excluded from Git tracking until the publication checklist is
completed and an explicit release decision is made.

<!-- HEATSAFE_FINAL_METADATA_HARMONIZATION_REPRO_V1 -->
## Final metadata harmonization

After building and verifying Scientific Pack 08, create the final
metadata-harmonized candidate:

```bash
heatsafe-release-review harmonize   --source-release artifacts/releases/epa-pm25-2025-first-real-reviewed   --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025-bulk   --output artifacts/releases/epa-airdata-california-pm25-2025-first-real-reviewed   --release-id epa-airdata-california-pm25-2025-first-real-reviewed   --public-experiment-id epa-airdata-california-pm25-2025-first-real-bulk   --source-collection-year 2025   --local-timezone America/Los_Angeles   --overwrite
```

Verify the result:

```bash
heatsafe-release-review verify-harmonized   artifacts/releases/epa-airdata-california-pm25-2025-first-real-reviewed
```

This operation does not download EPA data, rescan the national file, rerun
models, publish an archive or mint a DOI.

<!-- HEATSAFE_PUBLICATION_HANDOFF_REPRO_V1 -->
## Publication handoff

Prepare the draft-only handoff from the final harmonized release:

```bash
heatsafe-release-review prepare-publication \
  --harmonized-release artifacts/releases/epa-airdata-california-pm25-2025-first-real-reviewed \
  --output artifacts/publication/epa-pm25-2025-v0.1.0-handoff \
  --repository FaramarzKowsari/heatsafe-climate-air-quality-lab \
  --tag epa-pm25-2025-v0.1.0 \
  --overwrite
```

Verify it:

```bash
heatsafe-release-review verify-publication \
  artifacts/publication/epa-pm25-2025-v0.1.0-handoff
```

The handoff contains only draft creation helpers. It does not publish either
platform or mint a DOI.
