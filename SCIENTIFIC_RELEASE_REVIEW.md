# Scientific Release Review

## Purpose

Scientific Pack 08 converts an already verified official-source experiment
workspace into a reviewed candidate research release. It does not download the
EPA national file again, rerun the forecasting models, publish a GitHub
release, upload files to Zenodo or mint a DOI.

The default source workspace is:

```text
artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025-bulk
```

The default reviewed-release directory is:

```text
artifacts/releases/epa-pm25-2025-first-real-reviewed
```

## Build

Windows users can run:

```text
BUILD_REVIEWED_EPA_RELEASE_08.cmd
```

Command line:

```bash
heatsafe-release-review build \
  --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025-bulk \
  --output artifacts/releases/epa-pm25-2025-first-real-reviewed \
  --overwrite
```

## Verify

```bash
heatsafe-release-review verify \
  artifacts/releases/epa-pm25-2025-first-real-reviewed
```

## Output

The builder creates:

```text
release-summary.html
release-summary.json
README.md
RELEASE_NOTES.md
REVIEW_CHECKLIST.md
PUBLICATION_LIMITATIONS.md
checksums.sha256
release-verification.json
metadata/
  CITATION.cff
  zenodo-deposition.json
  zenodo-github-template.json
  datacite-metadata.json
  release-manifest.json
provenance/
  real-official-experiment-manifest.json
  bulk-source-report.json
  station-selection-report.json
  source-verification.json
experiment/
  data/
  report/
  tables/
  figures/
  nexus/
  metadata/
```

A deterministic ZIP is written next to the release directory:

```text
epa-pm25-2025-first-real-reviewed-v0.1.0.zip
```

## Publication gate

The archive remains a `reviewed-candidate` until every required item in
`REVIEW_CHECKLIST.md` has been checked. The release metadata explicitly records
that no DOI has been minted.

Zenodo supports both `CITATION.cff` and `.zenodo.json` for GitHub software
releases. If both are present at repository root, Zenodo uses `.zenodo.json`.
For that reason, this stage creates a reviewed template inside the archive but
does not automatically add or replace repository-root Zenodo metadata.

## Scientific boundaries

The reviewed release documents a station-level forecasting experiment. It is
not a personal-exposure estimate, countywide air-quality reconstruction,
causal analysis, clinical-risk product, regulatory determination or official
warning service.
