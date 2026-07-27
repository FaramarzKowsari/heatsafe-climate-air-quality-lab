from __future__ import annotations

import argparse
import json
from pathlib import Path

from heatsafe.research.benchmark_registry.registry import write_registry_index
from heatsafe.research.benchmark_registry.release import create_release_bundle
from heatsafe.research.benchmark_registry.templates import write_templates
from heatsafe.research.benchmark_registry.validation import (
    assert_dataset_snapshot,
    load_benchmark_release,
    load_dataset_card,
)


def _templates(args: argparse.Namespace) -> None:
    print(json.dumps(write_templates(args.output), indent=2))


def _verify(args: argparse.Namespace) -> None:
    card = load_dataset_card(args.card)
    report = assert_dataset_snapshot(card, args.snapshot_root)
    print(json.dumps(report, indent=2))


def _index(args: argparse.Namespace) -> None:
    path = write_registry_index(args.registry_root, args.output)
    print(json.dumps({"index": str(path)}, indent=2))


def _bundle(args: argparse.Namespace) -> None:
    release = load_benchmark_release(args.release)
    result = create_release_bundle(
        release,
        registry_root=args.registry_root,
        output_directory=args.output,
    )
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-registry",
        description="Immutable official-source snapshot and benchmark release registry",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    templates = commands.add_parser("templates")
    templates.add_argument("--output", required=True)
    templates.set_defaults(func=_templates)

    verify = commands.add_parser("verify")
    verify.add_argument("card")
    verify.add_argument("--snapshot-root", required=True)
    verify.set_defaults(func=_verify)

    index = commands.add_parser("index")
    index.add_argument("registry_root")
    index.add_argument("--output")
    index.set_defaults(func=_index)

    bundle = commands.add_parser("bundle")
    bundle.add_argument("release")
    bundle.add_argument("--registry-root", required=True)
    bundle.add_argument("--output", required=True)
    bundle.set_defaults(func=_bundle)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
