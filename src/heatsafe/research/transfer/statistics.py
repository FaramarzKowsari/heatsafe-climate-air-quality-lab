from __future__ import annotations

import math

import numpy as np


def conformal_quantile(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    residuals = np.abs(y_true - y_pred)
    if len(residuals) < 2:
        raise ValueError("At least two calibration residuals are required")
    rank = int(np.ceil((len(residuals) + 1) * (1 - alpha)))
    rank = min(max(rank, 1), len(residuals))
    return float(np.partition(residuals, rank - 1)[rank - 1])


def block_bootstrap_mean_ci(
    values: np.ndarray,
    *,
    repetitions: int,
    block_length: int,
    alpha: float,
    random_state: int,
) -> tuple[float, float]:
    clean = np.asarray(values, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) < 3:
        mean = float(np.mean(clean)) if len(clean) else 0.0
        return mean, mean

    block = min(max(2, block_length), len(clean))
    starts = np.arange(0, len(clean) - block + 1)
    rng = np.random.default_rng(random_state)
    draws = np.empty(repetitions, dtype=float)

    for repetition in range(repetitions):
        sampled: list[float] = []
        while len(sampled) < len(clean):
            start = int(rng.choice(starts))
            sampled.extend(clean[start : start + block].tolist())
        draws[repetition] = float(np.mean(sampled[: len(clean)]))

    low = float(np.quantile(draws, alpha / 2))
    high = float(np.quantile(draws, 1 - alpha / 2))
    return low, high


def diebold_mariano(
    baseline_errors: np.ndarray,
    candidate_errors: np.ndarray,
    *,
    horizon: int,
) -> tuple[float, float]:
    baseline = np.asarray(baseline_errors, dtype=float)
    candidate = np.asarray(candidate_errors, dtype=float)
    if len(baseline) != len(candidate):
        raise ValueError("Error vectors must have equal length")
    if len(baseline) < 5:
        return 0.0, 1.0

    differential = np.abs(baseline) - np.abs(candidate)
    mean_difference = float(np.mean(differential))
    centered = differential - mean_difference
    n = len(centered)
    variance = float(np.dot(centered, centered) / n)

    max_lag = min(max(horizon - 1, 0), n - 2)
    for lag in range(1, max_lag + 1):
        covariance = float(np.dot(centered[lag:], centered[:-lag]) / n)
        weight = 1 - lag / (max_lag + 1)
        variance += 2 * weight * covariance

    variance = max(variance, 0.0)
    if variance <= 1e-15:
        return 0.0, 1.0

    statistic = mean_difference / math.sqrt(variance / n)
    p_value = math.erfc(abs(statistic) / math.sqrt(2))
    return float(statistic), float(min(max(p_value, 0.0), 1.0))


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = np.abs(y_true) + np.abs(y_pred)
    valid = denominator > 1e-12
    if not np.any(valid):
        return 0.0
    return float(np.mean(200 * np.abs(y_pred[valid] - y_true[valid]) / denominator[valid]))


def event_scores(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float,
) -> tuple[float, float, float]:
    truth = y_true >= threshold
    predicted = y_pred >= threshold
    true_positive = int(np.sum(truth & predicted))
    false_positive = int(np.sum(~truth & predicted))
    false_negative = int(np.sum(truth & ~predicted))
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return precision, recall, f1
