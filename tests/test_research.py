import numpy as np
import pandas as pd

from heatsafe.research.benchmark import rolling_origin_mae, run_benchmark


def test_benchmark_models_and_intervals():
    rng = np.random.default_rng(42)
    values = 15 + 4 * np.sin(np.arange(700) * 2 * np.pi / 24) + rng.normal(0, 1, 700)
    result = run_benchmark(pd.Series(values), horizons=(1, 6))
    assert len(result.metrics) == 12
    assert all(metric.prediction_interval_coverage is not None for metric in result.metrics)
    assert set(result.best_by_horizon) == {1, 6}


def test_rolling_origin():
    assert rolling_origin_mae(pd.Series(range(200)), horizon=1) > 0
