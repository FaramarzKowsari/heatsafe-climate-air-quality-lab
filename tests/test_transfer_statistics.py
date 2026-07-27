from __future__ import annotations

import numpy as np

from heatsafe.research.transfer.statistics import (
    block_bootstrap_mean_ci,
    diebold_mariano,
)


def test_block_bootstrap_is_deterministic() -> None:
    values = np.linspace(-1, 2, 120)
    first = block_bootstrap_mean_ci(
        values,
        repetitions=50,
        block_length=12,
        alpha=0.1,
        random_state=9,
    )
    second = block_bootstrap_mean_ci(
        values,
        repetitions=50,
        block_length=12,
        alpha=0.1,
        random_state=9,
    )
    assert first == second
    assert first[0] <= float(np.mean(values)) <= first[1]


def test_diebold_mariano_detects_better_candidate() -> None:
    baseline = np.linspace(2.0, 4.0, 200)
    candidate = baseline * 0.25
    statistic, p_value = diebold_mariano(
        baseline,
        candidate,
        horizon=6,
    )
    assert statistic > 0
    assert 0 <= p_value <= 1
