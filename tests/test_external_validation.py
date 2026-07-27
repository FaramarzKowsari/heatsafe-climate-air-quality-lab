from __future__ import annotations

from heatsafe.research.transfer.contracts import ExternalValidationConfig
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
)
from heatsafe.research.transfer.engine import run_external_validation


def test_external_validation_builds_geographic_leaderboard() -> None:
    frame = generate_synthetic_multicity_frame(
        rows_per_city=420,
        random_state=17,
    )
    config = ExternalValidationConfig(
        feature_columns=(
            "temperature_c",
            "relative_humidity_pct",
            "wind_speed_kmh",
            "smoke_proxy",
        ),
        horizons=(1,),
        minimum_rows_per_city=360,
        bootstrap_repetitions=30,
        block_length=12,
        models=("persistence", "ridge"),
    )
    report = run_external_validation(frame, config)
    assert len(report.fold_metrics) == (8 + 4) * 2
    assert report.slice_metrics
    assert len(report.robustness_leaderboard) == 2
    assert report.robustness_leaderboard[0].rank == 1
    assert "leave-one-city-out|1h" in report.best_model_by_mode_and_horizon
    assert "leave-one-region-out|1h" in report.best_model_by_mode_and_horizon
    assert all(
        0 <= metric.dm_p_value <= 1
        for metric in report.fold_metrics
    )
    assert all(
        metric.bootstrap_skill_ci_lower
        <= metric.bootstrap_skill_ci_upper
        for metric in report.fold_metrics
    )


def test_external_validation_is_deterministic() -> None:
    frame = generate_synthetic_multicity_frame(
        rows_per_city=380,
        random_state=3,
    )
    config = ExternalValidationConfig(
        feature_columns=("temperature_c", "wind_speed_kmh"),
        horizons=(1,),
        minimum_rows_per_city=340,
        bootstrap_repetitions=20,
        block_length=12,
        models=("persistence", "ridge"),
        validation_modes=("leave-one-city-out",),
        random_state=99,
    )
    first = run_external_validation(frame, config)
    second = run_external_validation(frame, config)
    assert first.fold_metrics == second.fold_metrics
    assert first.robustness_leaderboard == second.robustness_leaderboard
