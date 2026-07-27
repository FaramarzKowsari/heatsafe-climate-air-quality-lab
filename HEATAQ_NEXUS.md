# HeatAQ Nexus Benchmark

HeatAQ Nexus is HeatSafe's reproducible CPU-first benchmark for hourly environmental forecasting and compound-event research.

## Research questions

- Which baselines remain competitive at 1, 6, 12, 24 and 48-hour horizons?
- How does model ranking change during high-PM2.5 or high-temperature events?
- Do nominal conformal intervals maintain coverage on future chronological data?
- How much does rolling-origin performance differ from a single final holdout?
- Which models remain useful before neural or foundation-model complexity is introduced?

## No-paid-AI core

The complete benchmark runs with Python, pandas, NumPy and scikit-learn. No paid AI API is required. Local or BYOK language models may later summarize versioned results, but they do not train, score or override the benchmark.

## Models

- persistence;
- 24-hour seasonal naive;
- six-hour moving average;
- linear regression;
- ridge regression;
- random forest;
- gradient boosting.

## Feature engineering

- historical target lags;
- shifted rolling mean, standard deviation, minimum and maximum;
- hour, day-of-week and day-of-year cyclical encodings;
- lagged exogenous variables;
- lagged missingness indicators.

Every rolling or exogenous feature is shifted so it cannot access future information.

## Evaluation

- chronological train/calibration/test split;
- split-conformal prediction intervals;
- rolling-origin evaluation;
- MAE, RMSE, mean bias, R² and sMAPE;
- event precision, recall, F1 and binary Brier score;
- interval coverage, width and interval score;
- deterministic leaderboard and model cards.

## Reproducible artifacts

Each benchmark bundle contains:

```text
report.json
leaderboard.csv
model-cards.json
config.json
experiment-manifest.json
```

The experiment manifest records code revision, dependency versions, random seed and SHA-256 checksums.

## Commands

```bash
heatsafe-nexus synthetic --rows 1500 --output data/synthetic/heataq_nexus.csv

heatsafe-nexus run data/synthetic/heataq_nexus.csv \
  --target-column pm25 \
  --features temperature_c,relative_humidity_pct,wind_speed_kmh,smoke_proxy \
  --horizons 1,6,12,24,48 \
  --event-threshold 35 \
  --output artifacts/heataq-nexus-pm25
```

## Scientific boundary

This benchmark is a reproducible research instrument. A strong publication-grade study still requires versioned real data, independent cities or regions, preregistered evaluation, sensitivity analysis and external replication.
