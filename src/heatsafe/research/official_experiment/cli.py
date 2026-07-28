from __future__ import annotations

import argparse
import json

from heatsafe.research.official_experiment.runner import (
    run_real_official_experiment,
    verify_real_official_experiment,
    write_real_experiment_plan,
)


def _plan(args: argparse.Namespace) -> None:
    output = write_real_experiment_plan(args.config, args.output)
    print(json.dumps({"plan": str(output)}, indent=2))


def _run(args: argparse.Namespace) -> None:
    result = run_real_official_experiment(
        args.config,
        workspace=args.workspace,
        repository_root=args.repository_root,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _verify(args: argparse.Namespace) -> None:
    result = verify_real_official_experiment(args.workspace)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["valid"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-real-experiment",
        description=(
            "Plan, run and verify a real official-source HeatSafe experiment"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser(
        "plan",
        help="Write a secret-free acquisition and experiment plan",
    )
    plan.add_argument("--config", required=True)
    plan.add_argument("--output", required=True)
    plan.set_defaults(func=_plan)

    run = commands.add_parser(
        "run",
        help="Acquire, freeze, prepare and evaluate official observations",
    )
    run.add_argument("--config", required=True)
    run.add_argument("--workspace", required=True)
    run.add_argument("--repository-root")
    run.add_argument("--overwrite", action="store_true")
    run.set_defaults(func=_run)

    verify = commands.add_parser(
        "verify",
        help="Verify snapshot and experiment integrity",
    )
    verify.add_argument("workspace")
    verify.set_defaults(func=_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
