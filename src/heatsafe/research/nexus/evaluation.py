from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from heatsafe.research.nexus.contracts import (
    ForecastMetric,
    ModelCard,
    NexusConfig,
    NexusReport,
    RollingOriginMetric,
)
from heatsafe.research.nexus.features import SupervisedFrame, build_supervised_frame


def _conformal_quantile(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    residuals = np.abs(y_true - y_pred)
    if len(residuals) < 2:
        raise ValueError("At least two calibration residuals are required")
    rank = int(np.ceil((len(residuals) + 1) * (1 - alpha)))
    rank = min(max(rank, 1), len(residuals))
    return float(np.partition(residuals, rank - 1)[rank - 1])


def _event_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float,
) -> tuple[float, float, float, float]:
    truth = y_true >= threshold
    predicted = y_pred >= threshold
    tp = int(np.sum(truth & predicted))
    fp = int(np.sum(~truth & predicted))
    fn = int(np.sum(truth & ~predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    brier = float(np.mean((predicted.astype(float) - truth.astype(float)) ** 2))
    return precision, recall, f1, brier


def _smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = np.abs(y_true) + np.abs(y_pred)
    valid = denominator > 1e-12
    if not np.any(valid):
        return 0.0
    return float(np.mean(200 * np.abs(y_pred[valid] - y_true[valid]) / denominator[valid]))


def _interval_score(
    y_true: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    alpha: float,
) -> float:
    width = high - low
    below = np.maximum(low - y_true, 0)
    above = np.maximum(y_true - high, 0)
    return float(np.mean(width + (2 / alpha) * below + (2 / alpha) * above))


def _metric(
    *,
    model: str,
    horizon: int,
    n_train: int,
    n_calibration: int,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    event_threshold: float,
    alpha: float,
    conformal_quantile: float,
) -> ForecastMetric:
    low = y_pred - conformal_quantile
    high = y_pred + conformal_quantile
    precision, recall, f1, brier = _event_metrics(y_true, y_pred, event_threshold)
    return ForecastMetric(
        model=model,
        horizon_hours=horizon,
        n_train=n_train,
        n_calibration=n_calibration,
        n_test=len(y_true),
        mae=round(float(mean_absolute_error(y_true, y_pred)), 6),
        rmse=round(float(mean_squared_error(y_true, y_pred) ** 0.5), 6),
        mean_bias=round(float(np.mean(y_pred - y_true)), 6),
        r2=round(float(r2_score(y_true, y_pred)), 6),
        smape_pct=round(_smape(y_true, y_pred), 6),
        event_precision=round(precision, 6),
        event_recall=round(recall, 6),
        event_f1=round(f1, 6),
        event_brier=round(brier, 6),
        prediction_interval_coverage=round(float(np.mean((y_true >= low) & (y_true <= high))), 6),
        mean_interval_width=round(float(np.mean(high - low)), 6),
        interval_score=round(_interval_score(y_true, low, high, alpha), 6),
        conformal_quantile=round(conformal_quantile, 6),
    )


def _fitted_models(random_state: int) -> dict[str, Any]:
    return {
        "linear_regression": LinearRegression(),
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(
            n_estimators=120,
            max_depth=10,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=1,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            random_state=random_state,
            n_estimators=120,
            max_depth=3,
            learning_rate=0.05,
        ),
    }


def _baseline_predictions(split: pd.DataFrame) -> dict[str, np.ndarray]:
    predictions: dict[str, np.ndarray] = {
        "persistence": split["origin_target"].to_numpy(dtype=float),
    }
    if "target_lag_24" in split.columns:
        predictions["seasonal_naive_24h"] = split["target_lag_24"].to_numpy(dtype=float)
    if "target_roll_mean_6" in split.columns:
        predictions["moving_average_6h"] = split["target_roll_mean_6"].to_numpy(dtype=float)
    return predictions


def _split(
    supervised: SupervisedFrame,
    config: NexusConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = supervised.frame
    train_end = int(len(frame) * config.train_fraction)
    calibration_end = int(len(frame) * (config.train_fraction + config.calibration_fraction))
    if train_end < 100 or calibration_end <= train_end or calibration_end >= len(frame):
        raise ValueError("Chronological split produced an invalid partition")
    return frame.iloc[:train_end], frame.iloc[train_end:calibration_end], frame.iloc[calibration_end:]


def _rolling_origin(
    supervised: SupervisedFrame,
    config: NexusConfig,
    horizon: int,
) -> list[RollingOriginMetric]:
    frame = supervised.frame
    feature_columns = list(supervised.feature_columns)
    minimum_train = max(120, int(len(frame) * 0.50))
    candidates = list(range(minimum_train, len(frame), config.rolling_origin_step))
    candidates = candidates[-config.rolling_origin_max_origins :]
    if not candidates:
        return []

    predictions: dict[str, list[float]] = {"persistence": [], "linear_regression": []}
    actuals: list[float] = []
    for origin in candidates:
        train = frame.iloc[:origin]
        test_row = frame.iloc[[origin]]
        actual = float(test_row["future_target"].iloc[0])
        actuals.append(actual)
        predictions["persistence"].append(float(test_row["origin_target"].iloc[0]))
        model = LinearRegression()
        model.fit(train[feature_columns].to_numpy(), train["future_target"].to_numpy())
        predictions["linear_regression"].append(float(model.predict(test_row[feature_columns].to_numpy())[0]))

    y_true = np.asarray(actuals, dtype=float)
    results: list[RollingOriginMetric] = []
    for model_name, values in predictions.items():
        y_pred = np.asarray(values, dtype=float)
        results.append(
            RollingOriginMetric(
                model=model_name,
                horizon_hours=horizon,
                origins=len(y_true),
                mae=round(float(mean_absolute_error(y_true, y_pred)), 6),
                rmse=round(float(mean_squared_error(y_true, y_pred) ** 0.5), 6),
                mean_bias=round(float(np.mean(y_pred - y_true)), 6),
            )
        )
    return results


def _model_cards(feature_columns: list[str]) -> list[ModelCard]:
    common_prohibited = [
        "Operational warning authority",
        "Medical or clinical risk prediction",
        "Causal attribution without a dedicated study",
        "Performance claims outside the evaluated data and split protocol",
    ]
    return [
        ModelCard(
            model="persistence",
            model_family="deterministic baseline",
            intended_use="Reference forecast using the value available at the forecast origin.",
            training_protocol="No fitted parameters.",
            input_features=["origin_target"],
            uncertainty_method="Split-conformal residual interval calibrated on the chronological calibration partition.",
            strengths=["Transparent", "Fast", "Difficult to beat at short horizons"],
            limitations=["Cannot anticipate rapid regime changes", "No exogenous information"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="seasonal_naive_24h",
            model_family="deterministic seasonal baseline",
            intended_use="Reference forecast using the value from the same hour one day earlier.",
            training_protocol="No fitted parameters.",
            input_features=["target_lag_24"],
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Captures daily periodicity", "Transparent"],
            limitations=["Weak during non-periodic events", "Requires continuous hourly history"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="moving_average_6h",
            model_family="deterministic smoothing baseline",
            intended_use="Reference forecast based on recent historical mean.",
            training_protocol="No fitted parameters.",
            input_features=["target_roll_mean_6"],
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Stable", "Noise resistant"],
            limitations=["Lags abrupt changes", "Can suppress extremes"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="linear_regression",
            model_family="linear statistical model",
            intended_use="Interpretable baseline over lagged, rolling, cyclical and exogenous features.",
            training_protocol="Fit on the chronological training partition only.",
            input_features=feature_columns,
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Interpretable", "Fast", "Strong diagnostic baseline"],
            limitations=["Linear functional form", "Sensitive to collinearity and regime shifts"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="ridge",
            model_family="regularized linear model",
            intended_use="Stable linear baseline when lagged features are correlated.",
            training_protocol="Fit on the chronological training partition only; alpha=1.0.",
            input_features=feature_columns,
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Regularized", "Fast", "Handles correlated lag features"],
            limitations=["Linear functional form", "Fixed regularization strength"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="random_forest",
            model_family="tree ensemble",
            intended_use="Nonlinear CPU baseline for interactions among historical and exogenous features.",
            training_protocol="120 trees, bounded depth, fixed random seed, chronological training partition.",
            input_features=feature_columns,
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Nonlinear", "Interaction aware", "Minimal scaling assumptions"],
            limitations=["Can extrapolate poorly", "Feature importance is not causal"],
            prohibited_claims=common_prohibited,
        ),
        ModelCard(
            model="gradient_boosting",
            model_family="boosted tree ensemble",
            intended_use="Nonlinear CPU baseline optimized sequentially over residual errors.",
            training_protocol="120 estimators, learning rate 0.05, fixed random seed.",
            input_features=feature_columns,
            uncertainty_method="Split-conformal residual interval.",
            strengths=["Strong tabular baseline", "Captures nonlinear structure"],
            limitations=["Sensitive to tuning", "Can overfit unusual episodes"],
            prohibited_claims=common_prohibited,
        ),
    ]


def run_nexus_benchmark(frame: pd.DataFrame, config: NexusConfig) -> NexusReport:
    metrics: list[ForecastMetric] = []
    rolling_metrics: list[RollingOriginMetric] = []
    best_by_horizon: dict[int, str] = {}
    all_feature_columns: set[str] = set()

    for horizon in config.horizons:
        supervised = build_supervised_frame(frame, config, horizon=horizon)
        all_feature_columns.update(supervised.feature_columns)
        train, calibration, test = _split(supervised, config)
        feature_columns = list(supervised.feature_columns)
        x_train = train[feature_columns].to_numpy(dtype=float)
        y_train = train["future_target"].to_numpy(dtype=float)
        x_cal = calibration[feature_columns].to_numpy(dtype=float)
        y_cal = calibration["future_target"].to_numpy(dtype=float)
        x_test = test[feature_columns].to_numpy(dtype=float)
        y_test = test["future_target"].to_numpy(dtype=float)

        calibration_predictions = _baseline_predictions(calibration)
        test_predictions = _baseline_predictions(test)
        for name, model in _fitted_models(config.random_state).items():
            model.fit(x_train, y_train)
            calibration_predictions[name] = model.predict(x_cal)
            test_predictions[name] = model.predict(x_test)

        horizon_metrics: list[ForecastMetric] = []
        for model_name, prediction in test_predictions.items():
            quantile = _conformal_quantile(
                y_cal,
                calibration_predictions[model_name],
                config.alpha,
            )
            result = _metric(
                model=model_name,
                horizon=horizon,
                n_train=len(train),
                n_calibration=len(calibration),
                y_true=y_test,
                y_pred=prediction,
                event_threshold=config.event_threshold,
                alpha=config.alpha,
                conformal_quantile=quantile,
            )
            metrics.append(result)
            horizon_metrics.append(result)

        best_by_horizon[horizon] = min(horizon_metrics, key=lambda item: item.mae).model
        rolling_metrics.extend(_rolling_origin(supervised, config, horizon))

    leaderboard = [
        {
            "rank": rank,
            "model": metric.model,
            "horizon_hours": metric.horizon_hours,
            "mae": metric.mae,
            "rmse": metric.rmse,
            "event_f1": metric.event_f1,
            "coverage": metric.prediction_interval_coverage,
            "interval_width": metric.mean_interval_width,
        }
        for rank, metric in enumerate(
            sorted(metrics, key=lambda item: (item.horizon_hours, item.mae)),
            start=1,
        )
    ]

    timestamps = pd.to_datetime(frame[config.timestamp_column], utc=True)
    target = pd.to_numeric(frame[config.target_column], errors="coerce")
    summary = {
        "rows": len(frame),
        "start_utc": timestamps.min().isoformat(),
        "end_utc": timestamps.max().isoformat(),
        "target_missing": int(target.isna().sum()),
        "target_mean": round(float(target.mean()), 6),
        "target_std": round(float(target.std()), 6),
        "event_rate": round(float((target >= config.event_threshold).mean()), 6),
    }

    feature_list = sorted(all_feature_columns)
    return NexusReport(
        target=config.target_column,
        timestamp_column=config.timestamp_column,
        feature_columns=feature_list,
        horizons=list(config.horizons),
        event_threshold=config.event_threshold,
        metrics=metrics,
        rolling_origin_metrics=rolling_metrics,
        best_by_horizon=best_by_horizon,
        leaderboard=leaderboard,
        model_cards=_model_cards(feature_list),
        dataset_summary=summary,
        split_description=(
            f"Chronological {config.train_fraction:.0%} train, "
            f"{config.calibration_fraction:.0%} calibration, "
            "remainder test; no random shuffling."
        ),
        leakage_controls=[
            "Target lags use only observations before the forecast origin.",
            "Rolling statistics are computed after shifting the target by one step.",
            "Exogenous variables are lagged before entering the feature matrix.",
            "Scoring uses a final chronological test partition not used for fitting or conformal calibration.",
            "Rolling-origin evaluation fits each statistical model only on earlier rows.",
        ],
        limitations=[
            "Results apply only to the supplied dataset version, variables, locations and time period.",
            "Split-conformal coverage can degrade under temporal or geographic distribution shift.",
            "Binary event Brier uses thresholded predictions rather than calibrated event probabilities.",
            "Tree-model feature importance must not be interpreted causally.",
            "A production claim requires external-city and external-region validation.",
            "The benchmark is research software, not an operational warning or health-risk system.",
        ],
    )
