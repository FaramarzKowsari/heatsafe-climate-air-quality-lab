from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass(frozen=True)
class ForecastMetrics:
    model: str
    horizon_hours: int
    n_test: int
    mae: float
    rmse: float
    mean_bias: float
    r2: float
    event_precision: float
    event_recall: float
    event_f1: float
    prediction_interval_coverage: float | None
    interval_width: float | None


@dataclass(frozen=True)
class BenchmarkReport:
    target: str
    horizons: list[int]
    metrics: list[ForecastMetrics]
    best_by_horizon: dict[int, str]
    split_description: str
    limitations: list[str]

    def model_dump(self) -> dict[str, object]:
        return {
            "target": self.target,
            "horizons": self.horizons,
            "metrics": [asdict(metric) for metric in self.metrics],
            "best_by_horizon": self.best_by_horizon,
            "split_description": self.split_description,
            "limitations": self.limitations,
        }


def _features(series: pd.Series, horizon: int, lags: tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)) -> pd.DataFrame:
    frame = pd.DataFrame({"target": pd.to_numeric(series, errors="coerce")})
    for lag in lags:
        frame[f"lag_{lag}"] = frame["target"].shift(lag)
    frame["hour_sin"] = np.sin(2 * np.pi * np.arange(len(frame)) / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * np.arange(len(frame)) / 24)
    frame["rolling_mean_6"] = frame["target"].shift(1).rolling(6).mean()
    frame["rolling_mean_24"] = frame["target"].shift(1).rolling(24).mean()
    frame["future"] = frame["target"].shift(-horizon)
    return frame.dropna()


def _event_scores(y_true: np.ndarray, y_pred: np.ndarray, threshold: float) -> tuple[float, float, float]:
    truth = y_true >= threshold
    predicted = y_pred >= threshold
    tp = int(np.sum(truth & predicted))
    fp = int(np.sum(~truth & predicted))
    fn = int(np.sum(truth & ~predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _metric(
    model: str,
    horizon: int,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    event_threshold: float,
    interval: tuple[np.ndarray, np.ndarray] | None = None,
) -> ForecastMetrics:
    precision, recall, f1 = _event_scores(y_true, y_pred, event_threshold)
    coverage = None
    width = None
    if interval is not None:
        low, high = interval
        coverage = float(np.mean((y_true >= low) & (y_true <= high)))
        width = float(np.mean(high - low))
    return ForecastMetrics(
        model=model,
        horizon_hours=horizon,
        n_test=len(y_true),
        mae=round(float(mean_absolute_error(y_true, y_pred)), 4),
        rmse=round(float(mean_squared_error(y_true, y_pred) ** 0.5), 4),
        mean_bias=round(float(np.mean(y_pred - y_true)), 4),
        r2=round(float(r2_score(y_true, y_pred)), 4),
        event_precision=round(precision, 4),
        event_recall=round(recall, 4),
        event_f1=round(f1, 4),
        prediction_interval_coverage=round(coverage, 4) if coverage is not None else None,
        interval_width=round(width, 4) if width is not None else None,
    )


def _conformal_interval(y_cal: np.ndarray, pred_cal: np.ndarray, pred_test: np.ndarray, alpha: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    residuals = np.abs(y_cal - pred_cal)
    quantile = float(np.quantile(residuals, min(1.0, (1 - alpha) * (len(residuals) + 1) / len(residuals))))
    return pred_test - quantile, pred_test + quantile


def run_benchmark(
    series: pd.Series,
    *,
    target: str = "PM2.5",
    horizons: tuple[int, ...] = (1, 6, 12, 24, 48),
    event_threshold: float = 35.0,
    random_state: int = 42,
) -> BenchmarkReport:
    metrics: list[ForecastMetrics] = []
    best: dict[int, str] = {}

    for horizon in horizons:
        frame = _features(series, horizon)
        if len(frame) < 100:
            raise ValueError(f"At least 100 valid rows are required for horizon {horizon}")
        split = int(len(frame) * 0.7)
        calibration_split = max(split + 1, int(len(frame) * 0.85))
        train = frame.iloc[:split]
        calibration = frame.iloc[split:calibration_split]
        test = frame.iloc[calibration_split:]
        feature_columns = [column for column in frame.columns if column not in {"target", "future"}]
        x_train = train[feature_columns].to_numpy()
        y_train = train["future"].to_numpy()
        x_cal = calibration[feature_columns].to_numpy()
        y_cal = calibration["future"].to_numpy()
        x_test = test[feature_columns].to_numpy()
        y_test = test["future"].to_numpy()

        model_predictions: dict[str, np.ndarray] = {
            "persistence": test["target"].to_numpy(),
            "seasonal_naive_24h": test["lag_24"].to_numpy(),
            "moving_average_6h": test["rolling_mean_6"].to_numpy(),
        }
        fitted_models = {
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestRegressor(n_estimators=80, max_depth=8, random_state=random_state, n_jobs=1),
            "gradient_boosting": GradientBoostingRegressor(random_state=random_state, n_estimators=100, max_depth=3),
        }
        for name, model in fitted_models.items():
            model.fit(x_train, y_train)
            model_predictions[name] = model.predict(x_test)

        calibration_models: dict[str, np.ndarray] = {
            "persistence": calibration["target"].to_numpy(),
            "seasonal_naive_24h": calibration["lag_24"].to_numpy(),
            "moving_average_6h": calibration["rolling_mean_6"].to_numpy(),
        }
        for name, model in fitted_models.items():
            calibration_models[name] = model.predict(x_cal)

        horizon_metrics: list[ForecastMetrics] = []
        for name, prediction in model_predictions.items():
            interval = _conformal_interval(y_cal, calibration_models[name], prediction)
            result = _metric(
                name,
                horizon,
                y_test,
                prediction,
                event_threshold=event_threshold,
                interval=interval,
            )
            metrics.append(result)
            horizon_metrics.append(result)
        best[horizon] = min(horizon_metrics, key=lambda metric: metric.mae).model

    return BenchmarkReport(
        target=target,
        horizons=list(horizons),
        metrics=metrics,
        best_by_horizon=best,
        split_description="Chronological 70% train, 15% conformal calibration, 15% test; no random shuffling.",
        limitations=[
            "This compact benchmark is designed for CPU reproducibility, not final operational deployment.",
            "A strong domain-shift study should additionally use leave-one-city-out and leave-one-region-out splits.",
            "Model comparisons are meaningful only for the supplied data and preprocessing version.",
        ],
    )


def rolling_origin_mae(series: pd.Series, horizon: int = 1, minimum_train: int = 100) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy()
    errors: list[float] = []
    for index in range(minimum_train, len(values) - horizon):
        prediction = values[index - 1]
        actual = values[index + horizon - 1]
        errors.append(abs(prediction - actual))
    if not errors:
        raise ValueError("Series is too short for rolling-origin evaluation")
    return float(np.mean(errors))


try:
    import torch
    from torch import nn

    class TinyLSTMForecaster(nn.Module):
        """Small CPU-friendly neural baseline; not trained by default."""

        def __init__(self, input_size: int = 1, hidden_size: int = 16) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
            self.head = nn.Linear(hidden_size, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            output, _ = self.lstm(x)
            return self.head(output[:, -1, :])

except ImportError:  # pragma: no cover
    TinyLSTMForecaster = None  # type: ignore[assignment]
