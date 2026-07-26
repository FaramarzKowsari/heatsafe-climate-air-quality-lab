# Methodology

## Scientific boundary

HeatSafe is an educational and research decision-support system. It is not an official warning service, medical device, building-certification tool or emergency-response system.

## Data identity and provenance

Observed, satellite-derived, reanalysis, modeled, forecast, user-entered, estimated and synthetic records remain distinct. Normalized records retain source, timestamp, location, unit, quality flag, retrieval context, license information and source URL where available.

## Deterministic environmental decisions

The ventilation engine evaluates data availability first, then smoke context and PM2.5, the indoor–outdoor temperature gradient, humidity, wind, solar exposure and ventilation configuration. It exposes every reason, missing input, source timestamp, confidence level and limitation.

## Climate trends

The trend module aggregates daily observations by year and reports annual means, extrema, hot-day and hot-night counts, cooling degree days, anomalies, OLS slope, Theil–Sen slope, Kendall rank trend, a bootstrap slope interval and a documented change-point screen. Short or incomplete records produce warnings.

## Heatwave detection

Events can be defined by an absolute threshold, a percentile threshold based on a selected reference period or a temperature–humidity compound rule. Consecutive qualifying days are grouped, and event duration, peak, cumulative excess, hot nights, completeness and limitations are returned.

## Air quality

Raw concentrations remain primary. AQI conversion is optional and explicitly names its standard. Implemented converters are never relabeled as a different regional index.

## Urban heat

The urban module operates on satellite-derived land-surface temperature and related cells. Land-surface temperature is not presented as near-surface air temperature.

## Wildfire context

Fire proximity, wind direction and PM2.5 changes are treated as contextual evidence. They do not establish causal smoke attribution without a validated transport and source-apportionment method.

## Forecast benchmark

CPU baselines include persistence, 24-hour seasonal naive, six-hour moving average, linear regression, random forest and gradient boosting. Chronological train/calibration/test splits avoid random leakage. Split-conformal residual intervals are reported alongside point and event metrics. Neural models remain optional baselines until evaluated.

## Compound-risk analysis

The compound-risk module accepts normalized 0–1 hazard components and exposed weights. It returns:

- a weighted additive score;
- a pairwise co-exceedance term;
- an interaction-adjusted exploratory score;
- the dominant component;
- leave-one-component-out values;
- a weight-perturbation sensitivity interval;
- explicit limitations.

The score is an exploratory research construct, not a validated health, safety or regulatory index. Weights and interaction strength must be justified and sensitivity-tested for each study.

## AI explanation

The standard explanation is deterministic. Local and BYOK models may explain an already-computed result but cannot modify it. Input hashes, provider metadata and numeric-grounding issues are recorded.

## Reproducibility

Experiment manifests capture code revision, environment, dependency versions, seed, configuration and checksums for input and output artifacts. Published comparisons should follow the protocol in `EXPERIMENT_PROTOCOL.md`.
