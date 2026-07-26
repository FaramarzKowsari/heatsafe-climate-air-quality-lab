from __future__ import annotations

import argparse
import json
from pathlib import Path

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.quality import assess_observations
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import verify_snapshot, write_snapshot


def _read_jsonl(path: Path) -> list[NormalizedObservation]:
    return [
        NormalizedObservation.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sources(_: argparse.Namespace) -> None:
    print(json.dumps([source.model_dump(mode="json") for source in DEFAULT_REGISTRY.list()], indent=2))


def _quality(args: argparse.Namespace) -> None:
    report = assess_observations(_read_jsonl(Path(args.jsonl)))
    print(report.model_dump_json(indent=2))


def _snapshot(args: argparse.Namespace) -> None:
    observations = _read_jsonl(Path(args.jsonl))
    quality = assess_observations(observations)
    manifest = write_snapshot(
        args.output,
        snapshot_id=args.snapshot_id,
        source=DEFAULT_REGISTRY.get(args.source_id),
        observations=observations,
        quality=quality,
        parameters={"input_jsonl": args.jsonl},
        repository_root=args.repository_root,
    )
    print(manifest.model_dump_json(indent=2))


def _verify(args: argparse.Namespace) -> None:
    print(json.dumps(verify_snapshot(args.directory), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-data",
        description="HeatSafe production-grade environmental data foundation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources = subparsers.add_parser("sources", help="List registered environmental data sources")
    sources.set_defaults(func=_sources)

    quality = subparsers.add_parser("quality", help="Assess a NormalizedObservation JSONL file")
    quality.add_argument("jsonl")
    quality.set_defaults(func=_quality)

    snapshot = subparsers.add_parser("snapshot", help="Create a verifiable dataset snapshot")
    snapshot.add_argument("jsonl")
    snapshot.add_argument("--source-id", required=True)
    snapshot.add_argument("--snapshot-id", required=True)
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--repository-root")
    snapshot.set_defaults(func=_snapshot)

    verify = subparsers.add_parser("verify", help="Verify snapshot checksums and record count")
    verify.add_argument("directory")
    verify.set_defaults(func=_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
