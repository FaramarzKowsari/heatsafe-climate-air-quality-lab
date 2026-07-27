# External Validation Protocol

## 1. Freeze every input dataset

Use Pack 02 snapshots and retain source identifiers, retrieval times, licenses, quality reports and SHA-256 checksums.

## 2. Harmonize variables

Confirm equivalent units, temporal resolution, station meaning, aggregation methods and quality flags across cities.

## 3. Predeclare domains

Define city and region membership before model fitting. Do not redraw boundaries after seeing results.

## 4. Construct features inside each city

Lagged and rolling variables must be generated independently within each city so that no city or future time contaminates another.

## 5. Hold out the complete external domain

No record from the held-out city or region may enter fitting, feature normalization, hyperparameter selection or conformal calibration.

## 6. Fit and calibrate on source domains

Split each source city chronologically. Pool early segments for fitting and later source segments for uncertainty calibration.

## 7. Evaluate the untouched domain

Report point, event and interval metrics for every model and horizon.

## 8. Quantify shift

Report target shift, feature shift and event-rate shift. A performance change without a shift diagnosis is incomplete.

## 9. Compare forecasts statistically

Use moving-block bootstrap confidence intervals and horizon-aware Diebold–Mariano comparisons against persistence.

## 10. Report slices

Publish season and event-intensity slices, including weak and failed cases.

## 11. Rank for robustness

A geographic leaderboard should consider mean performance, worst-domain performance, event skill and interval calibration.

## 12. Preserve artifacts

Store configuration, fold metrics, slices, leaderboard, validation card and experiment manifest.
