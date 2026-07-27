from __future__ import annotations

import argparse
import json
from pathlib import Path

from heatsafe.core.models import NormalizedObservation
from heatsafe.data_foundation.official_snapshots.acquisition import (
    ExternalAcquisitionRequired,
    acquire_observations,
    write_external_request_specification,
)
from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
    OfficialSnapshotConfig,
)
from heatsafe.data_foundation.official_snapshots.pipeline import (
    freeze_official_snapshot,
)
from heatsafe.data_foundation.official_snapshots.planning import (
    build_acquisition_plan,
)
from heatsafe.data_foundation.registry import DEFAULT_REGISTRY
from heatsafe.data_foundation.snapshot import verify_snapshot


def _load_config(path: str | Path) -> OfficialSnapshotConfig:
    return OfficialSnapshotConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _read_jsonl(path: str | Path) -> list[NormalizedObservation]:
    return [
        NormalizedObservation.model_validate_json(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _plan(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    source = DEFAULT_REGISTRY.get(config.source_id)
    plan = build_acquisition_plan(config, source)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({"plan": str(output)}, indent=2))


def _request_spec(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    path = write_external_request_specification(config, args.output)
    print(json.dumps({"request_specification": str(path)}, indent=2))


def _freeze_jsonl(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    release = freeze_official_snapshot(
        _read_jsonl(args.jsonl),
        config=config,
        output_root=args.output_root,
        registry_root=args.registry_root,
        repository_root=args.repository_root,
        acquisition_mode=AcquisitionMode.NORMALIZED_JSONL,
        overwrite=args.overwrite,
    )
    print(release.model_dump_json(indent=2))


def _acquire(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    try:
        observations = acquire_observations(config)
    except ExternalAcquisitionRequired as exc:
        if args.request_spec_output:
            output = Path(args.request_spec_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(exc.request_specification, indent=2),
                encoding="utf-8",
            )
        raise SystemExit(str(exc)) from exc

    source_mode = (
        AcquisitionMode.LOCAL_FILE
        if config.source_id == "eea-air-quality-parquet"
        else AcquisitionMode.LIVE_CONNECTOR
    )
    release = freeze_official_snapshot(
        observations,
        config=config,
        output_root=args.output_root,
        registry_root=args.registry_root,
        repository_root=args.repository_root,
        acquisition_mode=source_mode,
        overwrite=args.overwrite,
    )
    print(release.model_dump_json(indent=2))


def _verify(args: argparse.Namespace) -> None:
    print(json.dumps(verify_snapshot(args.snapshot_directory), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-official",
        description=(
            "Prepare, acquire, freeze, register and verify official-source "
            "environmental snapshots"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser(
        "plan",
        help="Validate a source recipe and write a secret-free acquisition plan",
    )
    plan.add_argument("--config", required=True)
    plan.add_argument("--output", required=True)
    plan.set_defaults(func=_plan)

    request_spec = commands.add_parser(
        "request-spec",
        help="Write an explicit external request specification, currently ERA5-Land",
    )
    request_spec.add_argument("--config", required=True)
    request_spec.add_argument("--output", required=True)
    request_spec.set_defaults(func=_request_spec)

    freeze = commands.add_parser(
        "freeze-jsonl",
        help="Freeze normalized observations into a registered official snapshot",
    )
    freeze.add_argument("jsonl")
    freeze.add_argument("--config", required=True)
    freeze.add_argument("--output-root", required=True)
    freeze.add_argument("--registry-root", required=True)
    freeze.add_argument("--repository-root")
    freeze.add_argument("--overwrite", action="store_true")
    freeze.set_defaults(func=_freeze_jsonl)

    acquire = commands.add_parser(
        "acquire",
        help="Use an implemented official connector, then freeze and register",
    )
    acquire.add_argument("--config", required=True)
    acquire.add_argument("--output-root", required=True)
    acquire.add_argument("--registry-root", required=True)
    acquire.add_argument("--repository-root")
    acquire.add_argument("--request-spec-output")
    acquire.add_argument("--overwrite", action="store_true")
    acquire.set_defaults(func=_acquire)

    verify = commands.add_parser(
        "verify",
        help="Verify the frozen snapshot checksums and record count",
    )
    verify.add_argument("snapshot_directory")
    verify.set_defaults(func=_verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
