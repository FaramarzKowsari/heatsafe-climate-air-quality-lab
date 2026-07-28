from __future__ import annotations

import argparse
import json
from heatsafe.research.experiment_orchestrator.runner import (
    load_experiment_spec,
    run_experiment,
    verify_experiment_directory,
)
from heatsafe.research.experiment_orchestrator.templates import (
    write_default_experiment_spec,
)


def _template(args: argparse.Namespace) -> None:
    output = write_default_experiment_spec(args.output)
    print(json.dumps({"template": str(output)}, indent=2))


def _run(args: argparse.Namespace) -> None:
    spec = load_experiment_spec(args.spec)
    result = run_experiment(
        spec,
        spec_path=args.spec,
        output_directory=args.output,
        repository_root=args.repository_root,
        overwrite=args.overwrite,
    )
    print(result.model_dump_json(indent=2))


def _verify(args: argparse.Namespace) -> None:
    report = verify_experiment_directory(args.directory)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-experiment",
        description=(
            "Run, report, package and verify reproducible HeatSafe experiments"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    template = commands.add_parser(
        "template",
        help="Write a complete synthetic experiment specification",
    )
    template.add_argument("--output", required=True)
    template.set_defaults(func=_template)

    run = commands.add_parser(
        "run",
        help="Run an experiment and generate paper-ready artifacts",
    )
    run.add_argument("--spec", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--repository-root")
    run.add_argument("--overwrite", action="store_true")
    run.set_defaults(func=_run)

    verify = commands.add_parser(
        "verify",
        help="Verify all SHA-256 checksums in an experiment directory",
    )
    verify.add_argument("directory")
    verify.set_defaults(func=_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
