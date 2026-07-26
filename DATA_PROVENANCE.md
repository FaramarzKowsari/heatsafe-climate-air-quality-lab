# Data Provenance

Every normalized observation records provider, dataset, source record or station identifier when available, coordinates, UTC and local time, time zone, variable, value, unit, measurement type, quality flag, retrieval time, license text, and source URL.

Synthetic demonstrations are marked `measurement_type=synthetic` and are not historical observations. Cached live responses may be added only when provider terms permit redistribution and must include retrieval time and checksum.

## Snapshot provenance contract

A HeatSafe dataset snapshot contains `observations.jsonl`,
`quality-report.json`, and `manifest.json`. The manifest records the source
descriptor, software version, code revision, parameters, record count and
SHA-256 checksums. Verification fails when an artifact changes or the JSONL
record count differs from the manifest.
