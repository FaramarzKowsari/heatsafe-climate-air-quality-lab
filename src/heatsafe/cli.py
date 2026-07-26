from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import uvicorn

from heatsafe.core.cooling import estimate_cooling_cost
from heatsafe.core.models import CoolingCostInput, VentilationInput
from heatsafe.core.ventilation import decide_ventilation
from heatsafe.research.benchmark import run_benchmark


def _ventilation(args: argparse.Namespace) -> None:
    result = decide_ventilation(
        VentilationInput(
            indoor_temperature_c=args.indoor,
            outdoor_temperature_c=args.outdoor,
            pm25_ug_m3=args.pm25,
            outdoor_humidity_pct=args.humidity,
            wind_speed_kmh=args.wind,
            smoke_context=args.smoke,
            cross_ventilation=args.cross_ventilation,
        )
    )
    print(result.model_dump_json(indent=2))


def _cooling(args: argparse.Namespace) -> None:
    result = estimate_cooling_cost(
        CoolingCostInput(
            device_power_w=args.power,
            estimated_duty_cycle=args.duty,
            daily_runtime_hours=args.hours,
            number_of_days=args.days,
            electricity_price_per_kwh=args.price,
            currency=args.currency,
            number_of_rooms=args.rooms,
            cooling_strategy=args.strategy,
        )
    )
    print(result.model_dump_json(indent=2))


def _benchmark(args: argparse.Namespace) -> None:
    frame = pd.read_csv(args.csv)
    report = run_benchmark(frame[args.column], target=args.column)
    output = report.model_dump()
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


def _serve(args: argparse.Namespace) -> None:
    uvicorn.run("heatsafe.api.app:app", host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="heatsafe", description="HeatSafe research and household decision-support CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the API and browser application")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_serve)

    ventilation = subparsers.add_parser("ventilation", help="Evaluate one ventilation decision")
    ventilation.add_argument("--indoor", type=float, required=True)
    ventilation.add_argument("--outdoor", type=float, required=True)
    ventilation.add_argument("--pm25", type=float)
    ventilation.add_argument("--humidity", type=float)
    ventilation.add_argument("--wind", type=float)
    ventilation.add_argument("--smoke", choices=["none", "possible", "likely", "unknown"], default="unknown")
    ventilation.add_argument("--cross-ventilation", action="store_true")
    ventilation.set_defaults(func=_ventilation)

    cooling = subparsers.add_parser("cooling", help="Estimate cooling energy and cost")
    cooling.add_argument("--power", type=float, required=True)
    cooling.add_argument("--duty", type=float, required=True)
    cooling.add_argument("--hours", type=float, required=True)
    cooling.add_argument("--days", type=int, required=True)
    cooling.add_argument("--price", type=float, required=True)
    cooling.add_argument("--currency", default="USD")
    cooling.add_argument("--rooms", type=int, default=1)
    cooling.add_argument("--strategy", choices=["whole-home", "zone", "single-room"], default="single-room")
    cooling.set_defaults(func=_cooling)

    benchmark = subparsers.add_parser("benchmark", help="Run the CPU baseline benchmark on a CSV column")
    benchmark.add_argument("csv")
    benchmark.add_argument("--column", default="pm25_ug_m3")
    benchmark.add_argument("--output")
    benchmark.set_defaults(func=_benchmark)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
