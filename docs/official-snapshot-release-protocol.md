# Official Snapshot Release Protocol

## 1. Predeclare the scientific question

State the target variable, spatial domain, temporal period, benchmark role and known limitations before acquisition.

## 2. Select an official source

Use the HeatSafe source registry. Do not embed undocumented endpoints.

## 3. Freeze the request recipe

Store all non-secret request parameters and the names of required credential environment variables.

## 4. Acquire through an authorized path

Use an implemented connector, an official local download or an explicit provider request specification.

## 5. Normalize without erasing provenance

Retain source name, dataset, record identifier, station or detection identifier, timestamps, coordinates, units, measurement type, quality flags, license and source URL.

## 6. Assess quality deterministically

Check duplicates, timestamps, ranges, units, licenses, URLs and provider quality metadata.

## 7. Apply predeclared gates

Do not change thresholds after observing the result merely to obtain a verified status.

## 8. Write immutable artifacts

Create observations JSONL, quality report, manifest, acquisition plan and benchmark table with SHA-256 checksums.

## 9. Generate the Dataset Card

Record exact coverage, variables, units, protocols, citations, limitations and release status.

## 10. Update the registry

Build a deterministic index and preserve the snapshot release record separately from benchmark releases.

## 11. Review redistribution

A valid checksum does not grant redistribution rights. Follow the provider-specific license and archive policy.

## 12. Benchmark only frozen versions

Every reported result must name the exact Dataset Card version and code revision.
