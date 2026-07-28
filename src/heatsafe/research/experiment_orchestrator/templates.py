from __future__ import annotations

from pathlib import Path

from heatsafe.research.experiment_orchestrator.contracts import (
    DatasetSpec,
    ExperimentSpec,
    ReleaseSpec,
    ReportSpec,
)
from heatsafe.research.nexus.contracts import NexusConfig


def default_experiment_spec() -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id="heataq-nexus-synthetic-paper-demo",
        title="HeatAQ Nexus synthetic reproducibility demonstration",
        description=(
            "A deterministic CPU-first forecasting experiment that exercises "
            "chronological train/calibration/test evaluation, transparent baselines, "
            "tree models, conformal uncertainty, event metrics and paper-ready outputs."
        ),
        dataset=DatasetSpec(kind="synthetic", rows=720, seed=42),
        nexus=NexusConfig(
            timestamp_column="timestamp",
            target_column="pm25",
            feature_columns=(
                "temperature_c",
                "relative_humidity_pct",
                "wind_speed_kmh",
                "smoke_proxy",
            ),
            horizons=(1, 6, 12, 24),
            event_threshold=35.0,
            alpha=0.1,
            random_state=42,
            rolling_origin_step=24,
            rolling_origin_max_origins=8,
        ),
        report=ReportSpec(
            title="HeatAQ Nexus: Reproducible Synthetic Forecasting Demonstration",
        ),
        release=ReleaseSpec(version="0.1.0", status="candidate"),
        notes=(
            "No paid AI API is used.",
            "The example is intended to validate research-software reproducibility.",
        ),
    )


def write_default_experiment_spec(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        default_experiment_spec().model_dump_json(indent=2),
        encoding="utf-8",
    )
    return output
