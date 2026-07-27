from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.features import build_supervised_frame
from heatsafe.research.transfer.contracts import (
    ExternalValidationConfig,
    ExternalValidationReport,
    FoldMetric,
    RobustnessRow,
    ShiftDiagnostic,
    SliceMetric,
    ValidationMode,
)
from heatsafe.research.transfer.dataset import validate_multicity_frame
from heatsafe.research.transfer.statistics import (
    block_bootstrap_mean_ci,
    conformal_quantile,
    diebold_mariano,
    event_scores,
    smape,
)


def _estimators(random_state: int) -> dict[str, Any]:
    return {
        "linear_regression": LinearRegression(),
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(
            n_estimators=80,
            max_depth=10,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=1,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=3,
            random_state=random_state,
        ),
    }


def _season(timestamp: pd.Series) -> pd.Series:
    month = pd.to_datetime(timestamp, utc=True).dt.month
    return pd.Series(
        np.select(
            [
                month.isin([12, 1, 2]),
                month.isin([3, 4, 5]),
                month.isin([6, 7, 8]),
            ],
            ["winter", "spring", "summer"],
            default="autumn",
        ),
        index=timestamp.index,
        dtype="object",
    )


def _intensity(values: np.ndarray, threshold: float) -> np.ndarray:
    return np.select(
        [
            values < threshold,
            values < threshold * 1.5,
        ],
        ["below-threshold", "elevated"],
        default="extreme",
    )


def _prepare_city_frames(
    frame: pd.DataFrame,
    config: ExternalValidationConfig,
    *,
    horizon: int,
) -> tuple[dict[str, pd.DataFrame], tuple[str, ...], dict[str, str]]:
    clean = validate_multicity_frame(
        frame,
        timestamp_column=config.timestamp_column,
        city_column=config.city_column,
        region_column=config.region_column,
        target_column=config.target_column,
        feature_columns=config.feature_columns,
        minimum_rows_per_city=config.minimum_rows_per_city,
    )
    city_frames: dict[str, pd.DataFrame] = {}
    feature_columns: tuple[str, ...] | None = None
    city_regions: dict[str, str] = {}

    minimum_valid = max(100, min(180, config.minimum_rows_per_city - 80))
    nexus_config = NexusConfig(
        timestamp_column=config.timestamp_column,
        target_column=config.target_column,
        feature_columns=config.feature_columns,
        horizons=(horizon,),
        event_threshold=config.event_threshold,
        alpha=config.alpha,
        minimum_valid_rows=minimum_valid,
        expected_frequency=config.expected_frequency,
        random_state=config.random_state,
    )

    for city, group in clean.groupby(config.city_column, sort=True):
        city_name = str(city)
        region = str(group[config.region_column].iloc[0])
        supervised = build_supervised_frame(
            group.drop(columns=[config.city_column, config.region_column]),
            nexus_config,
            horizon=horizon,
        )
        city_frame = supervised.frame.copy()
        city_frame["city"] = city_name
        city_frame["region"] = region
        city_frames[city_name] = city_frame
        city_regions[city_name] = region
        if feature_columns is None:
            feature_columns = supervised.feature_columns
        elif feature_columns != supervised.feature_columns:
            raise ValueError("Supervised feature columns differ across cities")

    if feature_columns is None:
        raise ValueError("No city frames were created")
    return city_frames, feature_columns, city_regions


def _source_split(
    frames: list[pd.DataFrame],
    *,
    train_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_parts: list[pd.DataFrame] = []
    calibration_parts: list[pd.DataFrame] = []

    for frame in frames:
        cut = int(len(frame) * train_fraction)
        if cut < 100 or len(frame) - cut < 20:
            raise ValueError("A source domain is too small for train/calibration splitting")
        train_parts.append(frame.iloc[:cut])
        calibration_parts.append(frame.iloc[cut:])

    return (
        pd.concat(train_parts, ignore_index=True),
        pd.concat(calibration_parts, ignore_index=True),
    )


def _baseline_predictions(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    predictions: dict[str, np.ndarray] = {
        "persistence": frame["origin_target"].to_numpy(dtype=float),
    }
    if "target_lag_24" in frame.columns:
        predictions["seasonal_naive_24h"] = frame["target_lag_24"].to_numpy(
            dtype=float
        )
    if "target_roll_mean_6" in frame.columns:
        predictions["moving_average_6h"] = frame[
            "target_roll_mean_6"
        ].to_numpy(dtype=float)
    return predictions


def _fit_predictions(
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: tuple[str, ...],
    config: ExternalValidationConfig,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    calibration_predictions = _baseline_predictions(calibration)
    test_predictions = _baseline_predictions(test)

    x_train = train[list(feature_columns)].to_numpy(dtype=float)
    y_train = train["future_target"].to_numpy(dtype=float)
    x_calibration = calibration[list(feature_columns)].to_numpy(dtype=float)
    x_test = test[list(feature_columns)].to_numpy(dtype=float)

    estimators = _estimators(config.random_state)
    for model_name in config.models:
        if model_name not in estimators:
            continue
        model = estimators[model_name]
        model.fit(x_train, y_train)
        calibration_predictions[model_name] = model.predict(x_calibration)
        test_predictions[model_name] = model.predict(x_test)

    required = set(config.models) | {"persistence"}
    missing = sorted(
        model_name
        for model_name in required
        if model_name not in calibration_predictions
        or model_name not in test_predictions
    )
    if missing:
        raise ValueError(f"Predictions could not be created for: {missing}")
    return calibration_predictions, test_predictions


def _shift_diagnostic(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: tuple[str, ...],
    threshold: float,
) -> ShiftDiagnostic:
    train_target = train["future_target"].to_numpy(dtype=float)
    test_target = test["future_target"].to_numpy(dtype=float)
    train_std = float(np.std(train_target, ddof=1))
    test_std = float(np.std(test_target, ddof=1))
    target_std_ratio = test_std / train_std if train_std > 1e-12 else 0.0

    train_features = train[list(feature_columns)].to_numpy(dtype=float)
    test_features = test[list(feature_columns)].to_numpy(dtype=float)
    train_means = np.mean(train_features, axis=0)
    test_means = np.mean(test_features, axis=0)
    train_stds = np.std(train_features, axis=0, ddof=1)
    safe_stds = np.where(train_stds > 1e-12, train_stds, 1.0)
    feature_shift_index = float(
        np.mean(np.abs(test_means - train_means) / safe_stds)
    )

    return ShiftDiagnostic(
        target_mean_shift=round(
            float(np.mean(test_target) - np.mean(train_target)),
            6,
        ),
        target_std_ratio=round(target_std_ratio, 6),
        feature_shift_index=round(feature_shift_index, 6),
        train_event_rate=round(float(np.mean(train_target >= threshold)), 6),
        test_event_rate=round(float(np.mean(test_target >= threshold)), 6),
    )


def _slice_metrics(
    *,
    test: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    config: ExternalValidationConfig,
    validation_mode: ValidationMode,
    holdout_domain: str,
    horizon: int,
) -> list[SliceMetric]:
    y_true = test["future_target"].to_numpy(dtype=float)
    seasons = _season(test["target_timestamp"]).to_numpy()
    intensities = _intensity(y_true, config.event_threshold)
    results: list[SliceMetric] = []

    for model_name in config.models:
        y_pred = predictions[model_name]
        slice_groups: tuple[
            tuple[Literal["season", "intensity"], np.ndarray],
            ...,
        ] = (
            ("season", seasons),
            ("intensity", intensities),
        )
        for slice_type, labels in slice_groups:
            for value in sorted(set(labels.tolist())):
                mask = labels == value
                count = int(np.sum(mask))
                if count < 5:
                    continue
                precision, recall, f1 = event_scores(
                    y_true[mask],
                    y_pred[mask],
                    config.event_threshold,
                )
                del precision, recall
                results.append(
                    SliceMetric(
                        validation_mode=validation_mode,
                        holdout_domain=holdout_domain,
                        model=model_name,
                        horizon_hours=horizon,
                        slice_type=slice_type,
                        slice_value=str(value),
                        n=count,
                        mae=round(
                            float(mean_absolute_error(y_true[mask], y_pred[mask])),
                            6,
                        ),
                        rmse=round(
                            float(
                                mean_squared_error(
                                    y_true[mask],
                                    y_pred[mask],
                                )
                                ** 0.5
                            ),
                            6,
                        ),
                        mean_bias=round(
                            float(np.mean(y_pred[mask] - y_true[mask])),
                            6,
                        ),
                        event_f1=round(f1, 6),
                    )
                )
    return results


def _evaluate_fold(
    *,
    validation_mode: ValidationMode,
    holdout_domain: str,
    holdout_region: str | None,
    source_frames: list[pd.DataFrame],
    test: pd.DataFrame,
    feature_columns: tuple[str, ...],
    horizon: int,
    config: ExternalValidationConfig,
) -> tuple[list[FoldMetric], list[SliceMetric]]:
    train, calibration = _source_split(
        source_frames,
        train_fraction=config.source_train_fraction,
    )
    calibration_predictions, test_predictions = _fit_predictions(
        train,
        calibration,
        test,
        feature_columns,
        config,
    )
    y_calibration = calibration["future_target"].to_numpy(dtype=float)
    y_test = test["future_target"].to_numpy(dtype=float)
    persistence_prediction = test_predictions["persistence"]
    persistence_errors = y_test - persistence_prediction
    persistence_mae = float(
        mean_absolute_error(y_test, persistence_prediction)
    )
    diagnostic = _shift_diagnostic(
        train,
        test,
        feature_columns,
        config.event_threshold,
    )

    fold_metrics: list[FoldMetric] = []
    for model_index, model_name in enumerate(config.models):
        prediction = test_predictions[model_name]
        calibration_prediction = calibration_predictions[model_name]
        quantile = conformal_quantile(
            y_calibration,
            calibration_prediction,
            config.alpha,
        )
        low = prediction - quantile
        high = prediction + quantile
        precision, recall, f1 = event_scores(
            y_test,
            prediction,
            config.event_threshold,
        )
        mae = float(mean_absolute_error(y_test, prediction))
        skill = 1 - mae / persistence_mae if persistence_mae > 1e-12 else 0.0
        skill_series = np.abs(persistence_errors) - np.abs(y_test - prediction)
        ci_low, ci_high = block_bootstrap_mean_ci(
            skill_series,
            repetitions=config.bootstrap_repetitions,
            block_length=config.block_length,
            alpha=config.alpha,
            random_state=config.random_state
            + horizon * 101
            + model_index * 17
            + len(holdout_domain),
        )
        dm_statistic, dm_p_value = diebold_mariano(
            persistence_errors,
            y_test - prediction,
            horizon=horizon,
        )
        fold_metrics.append(
            FoldMetric(
                validation_mode=validation_mode,
                holdout_domain=holdout_domain,
                holdout_region=holdout_region,
                model=model_name,
                horizon_hours=horizon,
                train_domains=len(source_frames),
                n_train=len(train),
                n_calibration=len(calibration),
                n_test=len(test),
                mae=round(mae, 6),
                rmse=round(
                    float(mean_squared_error(y_test, prediction) ** 0.5),
                    6,
                ),
                mean_bias=round(float(np.mean(prediction - y_test)), 6),
                r2=round(float(r2_score(y_test, prediction)), 6),
                smape_pct=round(smape(y_test, prediction), 6),
                event_precision=round(precision, 6),
                event_recall=round(recall, 6),
                event_f1=round(f1, 6),
                prediction_interval_coverage=round(
                    float(np.mean((y_test >= low) & (y_test <= high))),
                    6,
                ),
                mean_interval_width=round(
                    float(np.mean(high - low)),
                    6,
                ),
                conformal_quantile=round(quantile, 6),
                relative_mae_skill_vs_persistence=round(skill, 6),
                bootstrap_skill_ci_lower=round(ci_low, 6),
                bootstrap_skill_ci_upper=round(ci_high, 6),
                dm_statistic=round(dm_statistic, 6),
                dm_p_value=round(dm_p_value, 6),
                shift=diagnostic,
            )
        )

    slices = _slice_metrics(
        test=test,
        predictions=test_predictions,
        config=config,
        validation_mode=validation_mode,
        holdout_domain=holdout_domain,
        horizon=horizon,
    )
    return fold_metrics, slices


def _leaderboard(metrics: list[FoldMetric]) -> list[RobustnessRow]:
    rows: list[RobustnessRow] = []
    models = sorted({metric.model for metric in metrics})
    for model in models:
        selected = [metric for metric in metrics if metric.model == model]
        rows.append(
            RobustnessRow(
                rank=0,
                model=model,
                folds=len(
                    {
                        (
                            metric.validation_mode,
                            metric.holdout_domain,
                            metric.horizon_hours,
                        )
                        for metric in selected
                    }
                ),
                horizons=len({metric.horizon_hours for metric in selected}),
                mean_mae=round(
                    float(np.mean([metric.mae for metric in selected])),
                    6,
                ),
                median_mae=round(
                    float(np.median([metric.mae for metric in selected])),
                    6,
                ),
                worst_domain_mae=round(
                    float(max(metric.mae for metric in selected)),
                    6,
                ),
                mean_relative_skill=round(
                    float(
                        np.mean(
                            [
                                metric.relative_mae_skill_vs_persistence
                                for metric in selected
                            ]
                        )
                    ),
                    6,
                ),
                mean_event_f1=round(
                    float(np.mean([metric.event_f1 for metric in selected])),
                    6,
                ),
                mean_interval_coverage=round(
                    float(
                        np.mean(
                            [
                                metric.prediction_interval_coverage
                                for metric in selected
                            ]
                        )
                    ),
                    6,
                ),
                mean_feature_shift_index=round(
                    float(
                        np.mean(
                            [
                                metric.shift.feature_shift_index
                                for metric in selected
                            ]
                        )
                    ),
                    6,
                ),
            )
        )

    ordered = sorted(
        rows,
        key=lambda item: (
            item.mean_mae,
            item.worst_domain_mae,
            -item.mean_relative_skill,
        ),
    )
    return [
        item.model_copy(update={"rank": rank})
        for rank, item in enumerate(ordered, start=1)
    ]


def run_external_validation(
    frame: pd.DataFrame,
    config: ExternalValidationConfig,
) -> ExternalValidationReport:
    clean = validate_multicity_frame(
        frame,
        timestamp_column=config.timestamp_column,
        city_column=config.city_column,
        region_column=config.region_column,
        target_column=config.target_column,
        feature_columns=config.feature_columns,
        minimum_rows_per_city=config.minimum_rows_per_city,
    )
    cities = sorted(clean[config.city_column].unique().astype(str).tolist())
    regions = sorted(clean[config.region_column].unique().astype(str).tolist())
    fold_metrics: list[FoldMetric] = []
    slice_metrics: list[SliceMetric] = []

    for horizon in config.horizons:
        city_frames, feature_columns, city_regions = _prepare_city_frames(
            clean,
            config,
            horizon=horizon,
        )

        if "leave-one-city-out" in config.validation_modes:
            for holdout_city in sorted(city_frames):
                source_frames = [
                    city_frame
                    for city, city_frame in city_frames.items()
                    if city != holdout_city
                ]
                metrics, slices = _evaluate_fold(
                    validation_mode="leave-one-city-out",
                    holdout_domain=holdout_city,
                    holdout_region=city_regions[holdout_city],
                    source_frames=source_frames,
                    test=city_frames[holdout_city],
                    feature_columns=feature_columns,
                    horizon=horizon,
                    config=config,
                )
                fold_metrics.extend(metrics)
                slice_metrics.extend(slices)

        if (
            "leave-one-region-out" in config.validation_modes
            and len(regions) >= 3
        ):
            for holdout_region in regions:
                source_frames = [
                    city_frame
                    for city, city_frame in city_frames.items()
                    if city_regions[city] != holdout_region
                ]
                test_frames = [
                    city_frame
                    for city, city_frame in city_frames.items()
                    if city_regions[city] == holdout_region
                ]
                if not source_frames or not test_frames:
                    continue
                metrics, slices = _evaluate_fold(
                    validation_mode="leave-one-region-out",
                    holdout_domain=holdout_region,
                    holdout_region=holdout_region,
                    source_frames=source_frames,
                    test=pd.concat(test_frames, ignore_index=True),
                    feature_columns=feature_columns,
                    horizon=horizon,
                    config=config,
                )
                fold_metrics.extend(metrics)
                slice_metrics.extend(slices)

    leaderboard = _leaderboard(fold_metrics)
    best: dict[str, str] = {}
    for mode in config.validation_modes:
        for horizon in config.horizons:
            selected = [
                metric
                for metric in fold_metrics
                if metric.validation_mode == mode
                and metric.horizon_hours == horizon
            ]
            if not selected:
                continue
            model_mae: dict[str, list[float]] = {}
            for metric in selected:
                model_mae.setdefault(metric.model, []).append(metric.mae)
            best[f"{mode}|{horizon}h"] = min(
                model_mae,
                key=lambda model: float(np.mean(model_mae[model])),
            )

    timestamps = pd.to_datetime(clean[config.timestamp_column], utc=True)
    target = pd.to_numeric(clean[config.target_column], errors="coerce")
    dataset_summary: dict[str, Any] = {
        "rows": len(clean),
        "cities": len(cities),
        "regions": len(regions),
        "start_utc": timestamps.min().isoformat(),
        "end_utc": timestamps.max().isoformat(),
        "target_missing": int(target.isna().sum()),
        "target_mean": round(float(target.mean()), 6),
        "target_std": round(float(target.std()), 6),
        "event_rate": round(
            float((target >= config.event_threshold).mean()),
            6,
        ),
        "rows_by_city": {
            str(city): int(count)
            for city, count in clean.groupby(config.city_column).size().items()
        },
    }

    return ExternalValidationReport(
        target=config.target_column,
        horizons=list(config.horizons),
        validation_modes=list(config.validation_modes),
        cities=cities,
        regions=regions,
        fold_metrics=fold_metrics,
        slice_metrics=slice_metrics,
        robustness_leaderboard=leaderboard,
        best_model_by_mode_and_horizon=best,
        dataset_summary=dataset_summary,
        protocol=[
            "Construct leakage-controlled supervised features independently within each city.",
            "Hold out one complete city or region as an unseen external domain.",
            "Split source domains chronologically into fitting and conformal-calibration partitions.",
            "Fit models only on source-domain training rows.",
            "Calibrate uncertainty only on source-domain calibration rows.",
            "Evaluate point, event and interval metrics on the untouched external domain.",
            "Use moving-block bootstrap for paired skill uncertainty.",
            "Use a horizon-aware Diebold-Mariano comparison against persistence.",
            "Report seasonal and event-intensity slices without changing model selection.",
        ],
        limitations=[
            "Synthetic demonstration data do not establish real-world transferability.",
            "Real external validation requires harmonized units, station metadata and versioned source snapshots.",
            "Leave-one-domain-out estimates depend on the number and diversity of available domains.",
            "The Diebold-Mariano normal approximation can be unstable for short or strongly nonstationary series.",
            "Bootstrap intervals quantify sampling variation, not every form of structural uncertainty.",
            "Geographic transfer performance does not imply causal transportability.",
            "This is research software, not an official warning, medical or regulatory system.",
        ],
    )
