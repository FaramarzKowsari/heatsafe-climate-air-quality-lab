# HeatSafe Official Snapshot Registry and Benchmark Release System

This subsystem converts provider downloads and normalized outputs into immutable, versioned research objects.

## Core guarantees

- every artifact has a SHA-256 checksum;
- every dataset has a semantic version and dataset card;
- every release names exact dataset-card versions;
- CSV row and column counts can be verified;
- official-source citations, access dates and terms are preserved;
- registry indices are deterministic and hashable;
- release candidates are separated from DOI-backed archival releases.

## Supported source families

The repository already maintains source descriptors for NOAA NCEI, US EPA AQS, EEA air quality, NASA FIRMS, ERA5-Land and Türkiye sources. Pack 05 does not invent undocumented endpoints. It registers frozen artifacts created by authorized connectors or manual official downloads.

## Workflow

```text
Official provider
→ raw frozen snapshot
→ normalized snapshot
→ quality report
→ Dataset Card
→ checksum verification
→ Registry Index
→ benchmark execution
→ Benchmark Release Candidate
→ manual review
→ archival deposit and DOI
```

## CLI

```bash
heatsafe-registry templates --output artifacts/registry-templates

heatsafe-registry verify \
  registry/datasets/epa-aqs-city-2025-1.0.0.json \
  --snapshot-root data/snapshots/epa-aqs-city-2025

heatsafe-registry index registry \
  --output registry/index.json

heatsafe-registry bundle \
  registry/releases/heatsafe-pm25-1.0.0.json \
  --registry-root registry \
  --output artifacts/release-bundle
```

## DOI boundary

The repository can prepare a complete release bundle, but it does not fabricate or automatically claim a DOI. A DOI is added only after the frozen bundle is deposited in Zenodo or another preservation service and manually reviewed.
