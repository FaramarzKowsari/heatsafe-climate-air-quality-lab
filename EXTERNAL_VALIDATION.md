# HeatSafe Multi-City External Validation Laboratory

This module extends HeatAQ Nexus from internal chronological evaluation to complete geographic holdouts.

## Scientific questions

- Does a model trained on several cities remain accurate in a city it has never seen?
- Does a model trained outside a region transfer to that region?
- How does forecast skill change under target, feature and event-rate shift?
- Are uncertainty intervals still calibrated in external domains?
- Does the model remain competitive with persistence during extreme episodes?
- How stable are model rankings across seasons, cities and regions?

## Validation modes

### Leave-one-city-out

One complete city is excluded from fitting and conformal calibration. All remaining cities form the source-domain pool.

### Leave-one-region-out

Every city in one region is excluded. Models are fitted and calibrated only with cities from other regions.

## Domain-shift diagnostics

Each external fold records:

- target mean shift;
- target standard-deviation ratio;
- standardized feature-shift index;
- source-domain event rate;
- external-domain event rate.

## Statistical inference

### Moving-block bootstrap

Paired forecast-skill differences are resampled in contiguous blocks so that short-range temporal dependence is not destroyed.

### Diebold–Mariano comparison

Each candidate is compared with persistence using a horizon-aware long-run variance estimate.

## Metrics

- MAE, RMSE, mean bias, R² and sMAPE;
- event precision, recall and F1;
- conformal interval coverage and mean width;
- relative MAE skill against persistence;
- bootstrap confidence interval for absolute-error skill;
- Diebold–Mariano statistic and p-value.

## Sliced evaluation

Results are reported separately for:

- winter, spring, summer and autumn;
- below-threshold, elevated and extreme target intensity.

## Reproducible artifacts

```text
external-validation-report.json
fold-metrics.csv
slice-metrics.csv
geographic-robustness-leaderboard.csv
config.json
external-validation-card.md
experiment-manifest.json
```

## No-paid-AI core

The complete laboratory runs with NumPy, pandas and scikit-learn. No paid AI API is required. Optional local or BYOK language models may summarize frozen artifacts, but they cannot alter metrics or model rankings.

## Example

```bash
heatsafe-transfer synthetic \
  --rows-per-city 720 \
  --output data/synthetic/multicity.csv

heatsafe-transfer run data/synthetic/multicity.csv \
  --target-column pm25 \
  --features temperature_c,relative_humidity_pct,wind_speed_kmh,smoke_proxy \
  --horizons 1,6,24 \
  --bootstrap-repetitions 300 \
  --output artifacts/external-validation
```

## Scientific boundary

Synthetic demonstration results are software tests, not evidence of geographic generalization. Publication-grade claims require frozen real-world snapshots, source harmonization, station-selection protocols, sensitivity analysis and independent replication.
