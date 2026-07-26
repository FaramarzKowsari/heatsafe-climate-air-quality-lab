from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import kendalltau
from sklearn.linear_model import TheilSenRegressor

from .models import ClimateRecord


@dataclass(frozen=True)
class TrendResult:
    record_count: int
    completeness_pct: float
    start: str
    end: str
    annual_means: list[dict[str, float]]
    annual_minima: list[dict[str, float]]
    annual_maxima: list[dict[str, float]]
    cooling_degree_days: list[dict[str, float]]
    hot_day_counts: list[dict[str, float]]
    hot_night_counts: list[dict[str, float]]
    anomalies: list[dict[str, float]]
    ols_slope_c_per_decade: float
    theil_sen_slope_c_per_decade: float
    mann_kendall_tau: float
    mann_kendall_p_value: float
    bootstrap_ci_c_per_decade: tuple[float, float]
    change_point_year: int | None
    warnings: list[str]


def records_to_frame(records: Iterable[ClimateRecord]) -> pd.DataFrame:
    rows = [record.model_dump() for record in records]
    if not rows:
        raise ValueError("At least one climate record is required")
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    frame["year"] = frame["timestamp"].dt.year
    frame["date"] = frame["timestamp"].dt.date
    return frame


def _annual_series(frame: pd.DataFrame, column: str, agg: str = "mean") -> pd.Series:
    grouped = frame.groupby("year")[column]
    if agg == "mean":
        return grouped.mean().dropna()
    if agg == "min":
        return grouped.min().dropna()
    if agg == "max":
        return grouped.max().dropna()
    raise ValueError(f"Unsupported aggregation: {agg}")


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def _bootstrap_slope_ci(x: np.ndarray, y: np.ndarray, seed: int = 42, samples: int = 500) -> tuple[float, float]:
    if len(x) < 3:
        slope = _slope(x, y)
        return slope, slope
    rng = np.random.default_rng(seed)
    slopes: list[float] = []
    n = len(x)
    for _ in range(samples):
        idx = rng.integers(0, n, n)
        xs, ys = x[idx], y[idx]
        if len(np.unique(xs)) < 2:
            continue
        slopes.append(_slope(xs, ys))
    if not slopes:
        slope = _slope(x, y)
        return slope, slope
    low, high = np.quantile(np.array(slopes), [0.025, 0.975])
    return float(low), float(high)


def _change_point(years: np.ndarray, values: np.ndarray) -> int | None:
    if len(values) < 8:
        return None
    overall = np.mean(values)
    best_score = 0.0
    best_year: int | None = None
    for index in range(3, len(values) - 3):
        left = values[:index]
        right = values[index:]
        score = (len(left) * abs(np.mean(left) - overall)) + (len(right) * abs(np.mean(right) - overall))
        if score > best_score:
            best_score = score
            best_year = int(years[index])
    return best_year


def analyze_climate_trend(
    records: list[ClimateRecord],
    *,
    base_temperature_c: float = 18.0,
    hot_day_threshold_c: float = 35.0,
    hot_night_threshold_c: float = 20.0,
    baseline_years: tuple[int, int] | None = None,
) -> TrendResult:
    frame = records_to_frame(records)
    start = frame["timestamp"].min()
    end = frame["timestamp"].max()
    expected_days = max(1, (end.date() - start.date()).days + 1)
    observed_days = frame["date"].nunique()
    completeness = min(100.0, 100 * observed_days / expected_days)

    annual = _annual_series(frame, "temperature_c", "mean")
    minima_column = "minimum_temperature_c" if frame["minimum_temperature_c"].notna().any() else "temperature_c"
    maxima_column = "maximum_temperature_c" if frame["maximum_temperature_c"].notna().any() else "temperature_c"
    annual_min = _annual_series(frame, minima_column, "min")
    annual_max = _annual_series(frame, maxima_column, "max")

    daily = frame.groupby("date").agg(
        year=("year", "first"),
        mean_temp=("temperature_c", "mean"),
        min_temp=(minima_column, "min"),
        max_temp=(maxima_column, "max"),
    )
    daily["cdd"] = (daily["mean_temp"] - base_temperature_c).clip(lower=0)
    cdd = daily.groupby("year")["cdd"].sum()
    hot_days = daily.assign(hot=(daily["max_temp"] >= hot_day_threshold_c)).groupby("year")["hot"].sum()
    hot_nights = daily.assign(hot=(daily["min_temp"] >= hot_night_threshold_c)).groupby("year")["hot"].sum()

    years = annual.index.to_numpy(dtype=float)
    values = annual.to_numpy(dtype=float)
    ols = _slope(years, values)
    if len(years) >= 3:
        model = TheilSenRegressor(random_state=42).fit(years.reshape(-1, 1), values)
        theil = float(model.coef_[0])
        tau, p_value = kendalltau(years, values)
    else:
        theil = ols
        tau, p_value = 0.0, 1.0
    ci_low, ci_high = _bootstrap_slope_ci(years, values)

    if baseline_years:
        baseline = annual.loc[(annual.index >= baseline_years[0]) & (annual.index <= baseline_years[1])]
        if baseline.empty:
            baseline_mean = float(annual.mean())
        else:
            baseline_mean = float(baseline.mean())
    else:
        baseline_mean = float(annual.iloc[: min(10, len(annual))].mean())
    anomaly = annual - baseline_mean

    warnings: list[str] = []
    if completeness < 90:
        warnings.append(f"Data completeness is {completeness:.1f}%; trend estimates may be sensitive to missing days.")
    if len(annual) < 10:
        warnings.append("Fewer than ten annual values are available; long-term climate interpretation is limited.")
    warnings.append("Trend results describe the supplied series and are not an attribution analysis.")

    def pack(series: pd.Series, key: str = "value") -> list[dict[str, float]]:
        return [{"year": int(year), key: round(float(value), 4)} for year, value in series.items()]

    return TrendResult(
        record_count=len(frame),
        completeness_pct=round(completeness, 2),
        start=start.isoformat(),
        end=end.isoformat(),
        annual_means=pack(annual, "temperature_c"),
        annual_minima=pack(annual_min, "minimum_temperature_c"),
        annual_maxima=pack(annual_max, "maximum_temperature_c"),
        cooling_degree_days=pack(cdd, "cdd"),
        hot_day_counts=pack(hot_days, "count"),
        hot_night_counts=pack(hot_nights, "count"),
        anomalies=pack(anomaly, "anomaly_c"),
        ols_slope_c_per_decade=round(ols * 10, 4),
        theil_sen_slope_c_per_decade=round(theil * 10, 4),
        mann_kendall_tau=round(float(tau or 0.0), 4),
        mann_kendall_p_value=round(float(p_value or 1.0), 6),
        bootstrap_ci_c_per_decade=(round(ci_low * 10, 4), round(ci_high * 10, 4)),
        change_point_year=_change_point(years, values),
        warnings=warnings,
    )
