# First Real Official-Source Experiment

## Purpose

This stage moves HeatSafe from synthetic software validation to a real
official-source forecasting experiment.

The included workflow acquires 2025 PM2.5 sample measurements for Alameda
County, California, from the US EPA Air Quality System API, freezes the
normalized observations into an immutable HeatSafe snapshot, selects one
monitoring station using a deterministic continuity rule, and runs the
paper-ready HeatAQ Nexus experiment orchestrator.

No paid AI API is required.

## Why EPA-only comes first

EPA AQS provides timestamped PM2.5 observations suitable for an hourly
forecasting benchmark. NOAA GHCN Daily data use a different temporal
resolution. Combining daily weather values with hourly PM2.5 without a
predeclared temporal-alignment protocol could create misleading precision.

The first real experiment therefore uses EPA PM2.5 only. NOAA augmentation is
reserved for a separate, explicitly daily or properly aligned experiment.

## Data identity

The official recipe requests:

- source: US EPA Air Quality System;
- endpoint family: Sample Data by County;
- parameter: PM2.5, code `88101`;
- state: California, code `06`;
- county: Alameda, code `001`;
- period: 2025-01-01 through 2025-12-31.

The immutable snapshot preserves source records, station IDs, coordinates,
sample duration, method code, qualifiers, units, retrieval metadata, licensing
context, quality reports and SHA-256 checksums.

## Credential boundary

The live connector requires:

```text
EPA_AQS_EMAIL
EPA_AQS_KEY
```

The one-click Windows runner prompts for these values. They are held only in
the current PowerShell process and are cleared after the run. They are not
written to:

- the repository;
- `.env`;
- acquisition plans;
- snapshot metadata;
- reports;
- manifests;
- GitHub Actions artifacts.

The committed CI workflow performs only secret-free plan validation and unit
tests. It does not make a live EPA request.

## Deterministic station selection

The county request may contain multiple monitoring stations, instruments and
POCs. The benchmark does not silently pool the entire county into one time
series.

The preparation stage:

1. retains the configured PM2.5 variable;
2. prefers records whose quality metadata identify hourly sampling;
3. excludes non-finite and below-policy values;
4. collapses duplicate station-timestamp records by arithmetic mean while
   recording the duplicate count;
5. measures the longest strictly contiguous hourly run for every station;
6. selects the station with the longest run;
7. breaks ties by total hourly points, then station ID;
8. uses only the selected contiguous segment;
9. performs no target interpolation inside that segment.

This rule optimizes temporal continuity for model evaluation. It does not
claim that the selected station is geographically representative.

## Secret-free plan

```bash
heatsafe-real-experiment plan   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --output artifacts/plans/epa-aqs-alameda-pm25-2025.json
```

## Live run

Windows:

```text
RUN_FIRST_REAL_EPA_EXPERIMENT.cmd
```

Command line:

```bash
heatsafe-real-experiment run   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025   --repository-root .
```

## Verification

```bash
heatsafe-real-experiment verify   artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025
```

## Output

The workspace contains:

```text
execution-plan.json
official-snapshots/
registry/
prepared/
  selected-station-hourly.csv
  station-selection-report.json
real-experiment-spec.json
experiment/
  data/
  nexus/
  tables/
  figures/
  report/
  metadata/
  checksums.sha256
  release/
real-official-experiment-manifest.json
OPEN_REPORT.cmd
open-report.sh
```

The final HTML report is:

```text
experiment/report/report.html
```

## Scientific boundaries

A successful run establishes that the declared official-source snapshot,
station-selection rule, experiment configuration, artifacts and checksums are
internally reproducible. It does not establish:

- population exposure;
- countywide representativeness;
- causal effects;
- clinical or medical risk;
- official warning authority;
- performance outside the selected station and period.

Review the report, station-selection record, Dataset Card and limitations
before creating a tagged release or depositing a candidate archive.
