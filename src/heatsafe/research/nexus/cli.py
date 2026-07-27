from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from heatsafe.data_foundation.snapshot import load_observations
from heatsafe.research.nexus.artifacts import write_nexus_artifacts
from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame, observations_to_hourly_frame
from heatsafe.research.nexus.evaluation import run_nexus_benchmark


def _csv_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _int_list(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _run(args: argparse.Namespace) -> None:
    frame = pd.read_csv(args.csv)
    config = NexusConfig(
        timestamp_column=args.timestamp_column,
        target_column=args.target_column,
        feature_columns=_csv_list(args.features),
        horizons=_int_list(args.horizons),
        event_threshold=args.event_threshold,
        alpha=args.alpha,
        random_state=args.seed,
    )
    report = run_nexus_benchmark(frame, config)
    artifacts = write_nexus_artifacts(
        report,
        output_directory=args.output,
        config=config,
        input_paths=(args.csv,),
        repository_root=args.repository_root,
    )
    print(json.dumps({"artifacts": artifacts, "best_by_horizon": report.best_by_horizon}, indent=2))


def _synthetic(args: argparse.Namespace) -> None:
    frame = generate_synthetic_nexus_frame(rows=args.rows, random_state=args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(json.dumps({"rows": len(frame), "output": str(output)}, indent=2))


def _snapshot_to_csv(args: argparse.Namespace) -> None:
    observations = load_observations(args.snapshot)
    variables = _csv_list(args.variables)
    frame = observations_to_hourly_frame(
        observations,
        variables=variables,
        station_id=args.station_id,
        frequency=args.frequency,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(json.dumps({"rows": len(frame), "columns": list(frame.columns), "output": str(output)}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-nexus",
        description="HeatAQ Nexus reproducible environmental forecasting benchmark",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Run a benchmark from an hourly CSV file")
    run.add_argument("csv")
    run.add_argument("--timestamp-column", default="timestamp")
    run.add_argument("--target-column", default="pm25")
    run.add_argument("--features", default="temperature_c,relative_humidity_pct,wind_speed_kmh,smoke_proxy")
    run.add_argument("--horizons", default="1,6,12,24,48")
    run.add_argument("--event-threshold", type=float, default=35.0)
    run.add_argument("--alpha", type=float, default=0.1)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--output", required=True)
    run.add_argument("--repository-root")
    run.set_defaults(func=_run)

    synthetic = commands.add_parser("synthetic", help="Generate a deterministic synthetic benchmark dataset")
    synthetic.add_argument("--rows", type=int, default=1500)
    synthetic.add_argument("--seed", type=int, default=42)
    synthetic.add_argument("--output", required=True)
    synthetic.set_defaults(func=_synthetic)

    snapshot = commands.add_parser("snapshot-to-csv", help="Build an hourly benchmark table from a Pack 02 snapshot")
    snapshot.add_argument("snapshot")
    snapshot.add_argument("--variables", required=True)
    snapshot.add_argument("--station-id")
    snapshot.add_argument("--frequency", default="1h")
    snapshot.add_argument("--output", required=True)
    snapshot.set_defaults(func=_snapshot_to_csv)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
