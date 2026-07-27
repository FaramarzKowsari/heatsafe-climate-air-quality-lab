# HeatSafe Official Snapshot Acquisition and Release Pipeline

Pack 06 turns official environmental source records into immutable, quality-gated, benchmark-ready research snapshots.

## Scientific purpose

A provider download is not yet a research dataset. A defensible snapshot must preserve:

- the official authority and citation;
- the exact request recipe;
- credential names without credential values;
- normalized observations;
- provider and pipeline quality metadata;
- immutable checksums;
- a versioned Dataset Card;
- a deterministic registry index;
- a benchmark-ready table;
- explicit scientific limitations.

## Supported acquisition paths

| Source | Pack 06 mode | Notes |
|---|---|---|
| NOAA NCEI CDO | Live connector | Requires `NOAA_CDO_TOKEN` |
| US EPA AQS | Live connector | Requires `EPA_AQS_EMAIL` and `EPA_AQS_KEY` |
| NASA FIRMS | Live connector | Requires `NASA_FIRMS_MAP_KEY` |
| EEA Air Quality | Local official Parquet | No undocumented endpoint is embedded |
| ERA5-Land | Explicit request specification | Authorized Copernicus download remains external |
| Normalized JSONL | Freeze existing connector output | Useful for controlled review and release |

## Pipeline

```text
Official source recipe
→ secret-free acquisition plan
→ connector or authorized local file
→ NormalizedObservation records
→ deterministic quality assessment
→ quality gate
→ immutable snapshot
→ benchmark-table.csv
→ Dataset Card
→ Registry Index
→ Snapshot Release Record
```

## Quality gates

Each release evaluates:

- minimum observation count;
- minimum unique-record fraction;
- minimum quality score;
- maximum allowed errors;
- minimum records for every target variable.

A failed gate produces a `draft` Dataset Card rather than silently claiming verification.

## CLI examples

Create a secret-free plan:

```bash
heatsafe-official plan \
  --config examples/official-snapshots/epa-aqs-alameda-plan.json \
  --output artifacts/official-plans/epa-aqs-alameda.json
```

Acquire through an implemented connector and freeze:

```bash
heatsafe-official acquire \
  --config examples/official-snapshots/epa-aqs-alameda-plan.json \
  --output-root data/official-snapshots \
  --registry-root registry \
  --repository-root .
```

Freeze previously normalized observations:

```bash
heatsafe-official freeze-jsonl observations.jsonl \
  --config examples/official-snapshots/epa-aqs-alameda-plan.json \
  --output-root data/official-snapshots \
  --registry-root registry \
  --repository-root .
```

Write an ERA5-Land request specification:

```bash
heatsafe-official request-spec \
  --config examples/official-snapshots/era5-land-example.json \
  --output artifacts/requests/era5-land.json
```

Verify a snapshot:

```bash
heatsafe-official verify \
  data/official-snapshots/epa-aqs-alameda-pm25-2025q3/0.1.0
```

## Credential boundary

Pack 06 never writes token, key, password, authorization or email values into acquisition plans. Plans contain only required environment-variable names.

## Scientific boundary

A `verified` snapshot means its files, checksums, declared quality gates and registry metadata are internally consistent. It does not prove representativeness, causal validity, universal transferability, medical validity or official warning authority.
