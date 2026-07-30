from __future__ import annotations

import argparse
import json

from heatsafe.research.release_review.builder import (
    build_reviewed_release,
    verify_reviewed_release,
)
from heatsafe.research.release_review.contracts import (
    ReviewedReleaseConfig,
)
from heatsafe.research.release_review.harmonizer import (
    DEFAULT_LOCAL_TIMEZONE,
    DEFAULT_PUBLIC_EXPERIMENT_ID,
    DEFAULT_RELEASE_ID,
    DEFAULT_VERSION,
    harmonize_reviewed_release,
    verify_harmonized_release,
)


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


def _harmonize(args: argparse.Namespace) -> None:
    result = harmonize_reviewed_release(
        args.source_release,
        workspace=args.workspace,
        output_directory=args.output,
        release_id=args.release_id,
        version=args.version,
        public_experiment_id=args.public_experiment_id,
        source_collection_year=args.source_collection_year,
        local_timezone=args.local_timezone,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _verify_harmonized(args: argparse.Namespace) -> None:
    result = verify_harmonized_release(args.release_directory)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["valid"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-release-review",
        description=(
            "Build, harmonize and verify reviewed scientific releases "
            "from verified official-source experiment workspaces"
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

    harmonize = commands.add_parser(
        "harmonize",
        help=(
            "Create a final metadata-harmonized release from an "
            "existing reviewed candidate without rerunning models"
        ),
    )
    harmonize.add_argument("--source-release", required=True)
    harmonize.add_argument("--workspace", required=True)
    harmonize.add_argument("--output", required=True)
    harmonize.add_argument(
        "--release-id",
        default=DEFAULT_RELEASE_ID,
    )
    harmonize.add_argument(
        "--public-experiment-id",
        default=DEFAULT_PUBLIC_EXPERIMENT_ID,
    )
    harmonize.add_argument(
        "--version",
        default=DEFAULT_VERSION,
    )
    harmonize.add_argument(
        "--source-collection-year",
        type=int,
        default=2025,
    )
    harmonize.add_argument(
        "--local-timezone",
        default=DEFAULT_LOCAL_TIMEZONE,
    )
    harmonize.add_argument("--overwrite", action="store_true")
    harmonize.set_defaults(func=_harmonize)

    verify_harmonized = commands.add_parser(
        "verify-harmonized",
        help=(
            "Verify checksums, final identifiers, geography and "
            "UTC/local-time metadata"
        ),
    )
    verify_harmonized.add_argument("release_directory")
    verify_harmonized.set_defaults(func=_verify_harmonized)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
