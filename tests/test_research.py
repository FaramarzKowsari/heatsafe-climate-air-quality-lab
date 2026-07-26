import numpy as np, pandas as pd
from heatsafe.research.benchmark import run_benchmark, rolling_origin_mae

def test_benchmark_models_and_intervals():
    rng=np.random.default_rng(42)
    values=15+4*np.sin(np.arange(700)*2*np.pi/24)+rng.normal(0,1,700)
    r=run_benchmark(pd.Series(values),horizons=(1,6))
    assert len(r.metrics)==12
    assert all(m.prediction_interval_coverage is not None for m in r.metrics)
    assert set(r.best_by_horizon)=={1,6}

def test_rolling_origin():
    assert rolling_origin_mae(pd.Series(range(200)),horizon=1)>0
