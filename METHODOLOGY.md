# Methodology

## Scientific boundary

HeatSafe is an educational and research decision-support system. It is not an official warning service, medical device, building-certification tool, or emergency-response system.

## Deterministic household decisions

The ventilation engine evaluates data availability first, then smoke context and PM2.5, then the indoor–outdoor temperature gradient, humidity, wind, solar exposure, and ventilation configuration. It returns one of four labeled outcomes and exposes every reason, missing input, source timestamp, confidence level, and limitation.

## Climate trends

The trend module aggregates daily observations by year and reports annual means, extrema, hot-day and hot-night counts, cooling degree days, anomalies, OLS slope, Theil–Sen slope, Kendall rank trend, a bootstrap slope interval, and a simple documented change-point screen. Short or incomplete records produce warnings.

## Heatwave detection

Events can be defined by an absolute threshold, a percentile threshold based on a selected reference period, or a temperature-humidity compound rule. Consecutive qualifying days are grouped, and event duration, peak, cumulative excess, hot nights, completeness, and limitations are returned.

## Air quality

Raw concentrations remain primary. AQI conversion is optional and explicitly names its standard. The implemented illustrative converter supports US EPA PM2.5 and PM10 breakpoint logic; it is never relabeled as a European index.

## Urban heat

The urban module operates on satellite-derived land-surface temperature and related cells. It explicitly states that land-surface temperature is not near-surface air temperature.

## Forecast benchmark

CPU baselines include persistence, 24-hour seasonal naive, six-hour moving average, linear regression, random forest, and gradient boosting. Chronological train/calibration/test splits avoid random leakage. Split-conformal residual intervals are reported alongside point metrics. A small LSTM class is included as an optional research baseline, but no superiority claim is made without evaluation.
