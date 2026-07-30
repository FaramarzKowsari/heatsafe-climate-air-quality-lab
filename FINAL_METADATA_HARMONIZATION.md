# Final Metadata Harmonization

Scientific Pack 08.1 converts the verified reviewed candidate into a
metadata-harmonized candidate suitable for final human publication review.

## Canonical public identity

- Release ID: `epa-airdata-california-pm25-2025-first-real-reviewed`
- Public experiment ID:
  `epa-airdata-california-pm25-2025-first-real-bulk`
- The original source execution ID remains unchanged in provenance.

The public identity is geography-stable at the California AirData level,
while the selected county and monitoring station remain explicit metadata.

## Actual result identity

The current verified run selected:

- San Diego County, California
- Monitoring station `06-073-1201`
- 3,998 hourly rows
- UTC interval from `2025-07-18T18:00:00+00:00`
  through `2026-01-01T07:00:00+00:00`

## Time-basis interpretation

EPA AirData hourly products contain both local and GMT timestamps. The
forecasting pipeline evaluates chronological order in UTC. For the selected
California segment, the final UTC timestamp corresponds to the final local
hour of December 31, 2025 in `America/Los_Angeles`.

The harmonized release therefore records both UTC and local intervals and
explains the source-year/UTC-year boundary explicitly.

## Safety gate

This pack does not:

- create a GitHub Release;
- upload to Zenodo;
- mint or claim a DOI;
- rerun the forecasting models;
- rescan the national EPA file;
- modify the source execution provenance.

Publication remains blocked until the final checklist is reviewed.
