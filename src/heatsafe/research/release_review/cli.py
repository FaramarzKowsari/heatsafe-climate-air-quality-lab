from __future__ import annotations

import argparse
import json

from heatsafe.research.release_review.builder import (
    build_reviewed_release,
    verify_reviewed_release,
)
from heatsafe.research.release_review.contracts import ReviewedReleaseConfig


def _build(args: argparse.Namespace) -> None:
    config = ReviewedReleaseConfig(
        release_id=args.release_id,
        version=args.version,
        title=args.title,
    )
    result = build_reviewed_release(
        args.workspace,
        output_directory=args.output,
        config=config,
        overwrite=args.overwrite,
    )
    print(result.model_dump_json(indent=2))


def _verify(args: argparse.Namespace) -> None:
    result = verify_reviewed_release(args.release_directory)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["valid"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-release-review",
        description=(
            "Build and verify a reviewed candidate research release from "
            "an existing verified official-source experiment workspace"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser(
        "build",
        help="Create a reviewed candidate release archive",
    )
    build.add_argument("--workspace", required=True)
    build.add_argument("--output", required=True)
    build.add_argument(
        "--release-id",
        default="epa-pm25-2025-first-real-reviewed",
    )
    build.add_argument("--version", default="0.1.0")
    build.add_argument(
        "--title",
        default=(
            "US EPA AirData PM2.5 Forecasting Benchmark — "
            "First Reviewed Official-Source Release"
        ),
    )
    build.add_argument("--overwrite", action="store_true")
    build.set_defaults(func=_build)

    verify = commands.add_parser(
        "verify",
        help="Verify every checksum and required release artifact",
    )
    verify.add_argument("release_directory")
    verify.set_defaults(func=_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
