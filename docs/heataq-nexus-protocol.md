# HeatAQ Nexus Protocol

## 1. Freeze a Pack 02 snapshot

Verify checksums and retain source, quality and license metadata.

## 2. Build one location-aware hourly table

Do not combine multiple stations without an explicit spatial aggregation protocol.

## 3. Define target and event threshold

The event threshold must be scientifically justified for the variable, unit, region and intended research question.

## 4. Construct historical features

All target rolling features are shifted by one time step. All exogenous variables are lagged before use.

## 5. Split chronologically

Training data precede calibration data, which precede final test data. Random shuffling is prohibited.

## 6. Fit baselines

Begin with persistence and seasonal baselines. Complexity is justified only by robust improvement over these references.

## 7. Calibrate uncertainty

Use calibration residuals that are not reused for final scoring.

## 8. Evaluate rolling origins

Refit selected models using only data available before each origin.

## 9. Write artifacts

Store configuration, metrics, leaderboard, model cards and experiment manifest.

## 10. Extend to domain shift

Publication-grade studies should add leave-one-city-out and leave-one-region-out evaluation.
