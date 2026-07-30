# Scientific Pack 09 — Publication Handoff and Draft Creation

Scientific Pack 09 converts the checksum-verified, metadata-harmonized EPA
release into a controlled publication handoff.

## Safety model

The pack prepares two drafts:

- a GitHub Release draft;
- a Zenodo upload draft.

It deliberately does **not**:

- publish the GitHub release;
- publish the Zenodo record;
- call the Zenodo publish API;
- claim or fabricate a DOI;
- modify the harmonized source release;
- rerun models or rescan the EPA file.

## Proposed Git identity

- Tag: `epa-pm25-2025-v0.1.0`
- Release title: `US EPA AirData San Diego County, California PM2.5 Forecasting Benchmark v0.1.0`

## Draft workflow

1. Build the local publication handoff.
2. Review the release notes and asset SHA-256.
3. Create a GitHub draft release.
4. Create and save a Zenodo draft.
5. Upload the final harmonized ZIP and `SHA256SUMS.txt`.
6. Reserve a DOI in Zenodo if desired.
7. Do not publish either draft.
8. Supply the reserved DOI for DOI injection and final archive rebuilding.

## Why DOI injection is a separate step

A reserved DOI can be embedded in the archive's citation metadata before the
record becomes public. Inserting it changes files and checksums, so the final
ZIP must be rebuilt and reverified after reservation.

## Root repository metadata

The repository-root `CITATION.cff` continues to describe the HeatSafe
software under Apache-2.0. Dataset-specific Citation File Format and Zenodo
metadata remain inside the release assets. Scientific Pack 09 does not replace
the software citation with dataset metadata.
