from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import pandas as pd

from heatsafe.research.transfer.artifacts import (
    write_external_validation_artifacts,
)
from heatsafe.research.transfer.contracts import (
    ExternalValidationConfig,
    ValidationMode,
)
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
)
from heatsafe.research.transfer.engine import run_external_validation


def _csv_strings(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in value.split(",")
        if item.strip()
    )


def _csv_integers(value: str) -> tuple[int, ...]:
    return tuple(
        int(item.strip())
        for item in value.split(",")
        if item.strip()
    )


def _synthetic(args: argparse.Namespace) -> None:
    frame = generate_synthetic_multicity_frame(
        rows_per_city=args.rows_per_city,
        random_state=args.seed,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(
        json.dumps(
            {
                "rows": len(frame),
                "cities": int(frame["city"].nunique()),
                "regions": int(frame["region"].nunique()),
                "output": str(output),
                "data_origin": "synthetic-domain-shift-demo",
            },
            indent=2,
        )
    )


def _run(args: argparse.Namespace) -> None:
    frame = pd.read_csv(args.csv)
    config = ExternalValidationConfig(
        timestamp_column=args.timestamp_column,
        city_column=args.city_column,
        region_column=args.region_column,
        target_column=args.target_column,
        feature_columns=_csv_strings(args.features),
        horizons=_csv_integers(args.horizons),
        event_threshold=args.event_threshold,
        alpha=args.alpha,
        minimum_rows_per_city=args.minimum_rows_per_city,
        bootstrap_repetitions=args.bootstrap_repetitions,
        block_length=args.block_length,
        random_state=args.seed,
        models=_csv_strings(args.models),
        validation_modes=cast(
            tuple[ValidationMode, ...],
            _csv_strings(args.validation_modes),
        ),
    )
    report = run_external_validation(frame, config)
    artifacts = write_external_validation_artifacts(
        report,
        output_directory=args.output,
        config=config,
        input_paths=(args.csv,),
        repository_root=args.repository_root,
    )
    print(
        json.dumps(
            {
                "artifacts": artifacts,
                "best_model_by_mode_and_horizon": (
                    report.best_model_by_mode_and_horizon
                ),
                "leaderboard": [
                    row.model_dump(mode="json")
                    for row in report.robustness_leaderboard
                ],
            },
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-transfer",
        description=(
            "Multi-city and multi-region external validation "
            "for HeatAQ Nexus"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    synthetic = commands.add_parser(
        "synthetic",
        help="Generate a deterministic multi-city domain-shift dataset",
    )
    synthetic.add_argument("--rows-per-city", type=int, default=720)
    synthetic.add_argument("--seed", type=int, default=42)
    synthetic.add_argument("--output", required=True)
    synthetic.set_defaults(func=_synthetic)

    run = commands.add_parser(
        "run",
        help="Run leave-one-city-out and leave-one-region-out validation",
    )
    run.add_argument("csv")
    run.add_argument("--timestamp-column", default="timestamp")
    run.add_argument("--city-column", default="city")
    run.add_argument("--region-column", default="region")
    run.add_argument("--target-column", default="pm25")
    run.add_argument(
        "--features",
        default=(
            "temperature_c,relative_humidity_pct,"
            "wind_speed_kmh,smoke_proxy"
        ),
    )
    run.add_argument("--horizons", default="1,6,24")
    run.add_argument("--event-threshold", type=float, default=35.0)
    run.add_argument("--alpha", type=float, default=0.1)
    run.add_argument("--minimum-rows-per-city", type=int, default=300)
    run.add_argument("--bootstrap-repetitions", type=int, default=300)
    run.add_argument("--block-length", type=int, default=24)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument(
        "--models",
        default=(
            "persistence,seasonal_naive_24h,ridge,"
            "random_forest,gradient_boosting"
        ),
    )
    run.add_argument(
        "--validation-modes",
        default="leave-one-city-out,leave-one-region-out",
    )
    run.add_argument("--output", required=True)
    run.add_argument("--repository-root")
    run.set_defaults(func=_run)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
