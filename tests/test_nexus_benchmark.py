from __future__ import annotations

from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame
from heatsafe.research.nexus.evaluation import run_nexus_benchmark


def test_nexus_benchmark_produces_leaderboard_and_uncertainty() -> None:
    frame = generate_synthetic_nexus_frame(rows=700, random_state=7)
    config = NexusConfig(
        feature_columns=("temperature_c", "relative_humidity_pct", "wind_speed_kmh", "smoke_proxy"),
        horizons=(1, 6),
        minimum_valid_rows=180,
        rolling_origin_max_origins=5,
    )
    report = run_nexus_benchmark(frame, config)
    assert set(report.best_by_horizon) == {1, 6}
    assert len(report.metrics) >= 12
    assert report.leaderboard
    assert report.rolling_origin_metrics
    assert all(0 <= metric.prediction_interval_coverage <= 1 for metric in report.metrics)
    assert all(metric.mean_interval_width >= 0 for metric in report.metrics)
    assert any(card.model == "random_forest" for card in report.model_cards)
    assert report.leakage_controls


def test_nexus_is_deterministic_for_fixed_seed() -> None:
    frame = generate_synthetic_nexus_frame(rows=600, random_state=11)
    config = NexusConfig(
        feature_columns=("temperature_c", "relative_humidity_pct"),
        horizons=(1,),
        minimum_valid_rows=180,
        rolling_origin_max_origins=3,
        random_state=99,
    )
    first = run_nexus_benchmark(frame, config)
    second = run_nexus_benchmark(frame, config)
    assert first.metrics == second.metrics
    assert first.best_by_horizon == second.best_by_horizon
