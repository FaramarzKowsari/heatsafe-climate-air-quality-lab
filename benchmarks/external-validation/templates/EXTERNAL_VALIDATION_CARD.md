# External Validation Card

## Study identity

- Study name:
- Study version:
- Code revision:
- Dataset snapshot identifiers:
- Target and unit:
- Forecast horizons:
- Event threshold and scientific justification:

## Domains

Document every city, region, station-selection rule, temporal interval and source authority.

## Holdout protocol

State whether the study uses leave-one-city-out, leave-one-region-out or both. Confirm that no rows from the external domain were used for fitting or conformal calibration.

## Domain-shift diagnostics

Report target mean shift, target standard-deviation ratio, feature-shift index and event-rate change.

## Statistical comparisons

Report moving-block bootstrap confidence intervals and Diebold–Mariano comparisons against persistence.

## Slices

Report performance by season and event intensity. Avoid selecting a model based only on its best slice.

## Interpretation boundary

External validation supports a claim only for the frozen datasets, domains, period, variables and protocol evaluated. It does not establish causal transportability, official-warning status or universal generalization.
