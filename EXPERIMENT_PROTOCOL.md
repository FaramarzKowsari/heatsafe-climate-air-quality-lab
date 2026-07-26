# Experiment Protocol

## 1. Define the task

Record the target, horizon, spatial unit, temporal resolution, intended use and exclusion criteria before training.

## 2. Freeze data identity

Every row must retain provider, dataset, measurement type, timestamp, coordinates, unit, quality flag, retrieval time, source URL and license context.

## 3. Establish baselines

At minimum compare:

- persistence;
- seasonal naive;
- moving average;
- linear regression;
- one tree-based model.

Neural or foundation-model results are not meaningful without these baselines.

## 4. Prevent leakage

- Never randomly shuffle time-series forecasting data.
- Fit scalers and imputers on training data only.
- Keep future-derived features out of the input matrix.
- For spatial transfer, isolate complete cities or regions.
- Keep calibration data separate from final test data.

## 5. Evaluate multiple dimensions

Point metrics:

- MAE
- RMSE
- mean bias
- R² where appropriate

Event metrics:

- precision
- recall
- F1
- false-alarm rate
- missed-event rate

Probabilistic metrics:

- prediction-interval coverage
- mean interval width
- calibration error
- Brier score for event probabilities

## 6. Stress-test reliability

Evaluate:

- missing inputs;
- sensor disagreement;
- seasonal extremes;
- smoke episodes;
- unseen cities;
- unseen regions;
- data-source changes;
- threshold sensitivity;
- out-of-distribution inputs.

## 7. Quantify uncertainty

Use calibration data that are not reused for final testing. Report nominal and observed coverage. Wider intervals are not automatically better; coverage and sharpness must be interpreted together.

## 8. Record provenance

Generate an experiment manifest containing:

- experiment identifier;
- code revision;
- Python and platform versions;
- dependency versions;
- random seed;
- configuration;
- checksums of input and output artifacts;
- notes and limitations.

## 9. Report all relevant results

Do not hide weaker models, failed experiments or negative results. Separate exploratory results from confirmatory conclusions.

## 10. Release reproducibly

A scientific release should include:

- tagged source code;
- immutable configuration;
- data-access instructions;
- checksums;
- model and data cards;
- evaluation tables;
- plots;
- limitations;
- citation metadata;
- exact reproduction commands.
