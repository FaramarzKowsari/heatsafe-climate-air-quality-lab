from __future__ import annotations

import csv
from pathlib import Path

from heatsafe.research.provenance import (
    build_experiment_manifest,
    write_experiment_manifest,
)
from heatsafe.research.transfer.contracts import (
    ExternalValidationConfig,
    ExternalValidationReport,
)


def write_external_validation_artifacts(
    report: ExternalValidationReport,
    *,
    output_directory: str | Path,
    config: ExternalValidationConfig,
    input_paths: tuple[str | Path, ...] = (),
    repository_root: str | Path | None = None,
) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)

    report_path = root / "external-validation-report.json"
    folds_path = root / "fold-metrics.csv"
    slices_path = root / "slice-metrics.csv"
    leaderboard_path = root / "geographic-robustness-leaderboard.csv"
    config_path = root / "config.json"
    validation_card_path = root / "external-validation-card.md"

    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    fold_rows = [metric.model_dump(mode="json") for metric in report.fold_metrics]
    flattened_folds: list[dict[str, object]] = []
    for row in fold_rows:
        shift = row.pop("shift")
        flattened_folds.append(
            {
                **row,
                **{
                    f"shift_{key}": value
                    for key, value in dict(shift).items()
                },
            }
        )
    if flattened_folds:
        with folds_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=list(flattened_folds[0]),
            )
            writer.writeheader()
            writer.writerows(flattened_folds)
    else:
        folds_path.write_text("", encoding="utf-8")

    slice_rows = [
        metric.model_dump(mode="json")
        for metric in report.slice_metrics
    ]
    if slice_rows:
        with slices_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(slice_rows[0]))
            writer.writeheader()
            writer.writerows(slice_rows)
    else:
        slices_path.write_text("", encoding="utf-8")

    leaderboard_rows = [
        row.model_dump(mode="json")
        for row in report.robustness_leaderboard
    ]
    if leaderboard_rows:
        with leaderboard_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=list(leaderboard_rows[0]),
            )
            writer.writeheader()
            writer.writerows(leaderboard_rows)
    else:
        leaderboard_path.write_text("", encoding="utf-8")

    validation_card_path.write_text(
        "\n".join(
            [
                "# HeatSafe External Validation Card",
                "",
                f"- Study: {report.study_name}",
                f"- Version: {report.study_version}",
                f"- Target: {report.target}",
                f"- Cities: {len(report.cities)}",
                f"- Regions: {len(report.regions)}",
                f"- Horizons: {', '.join(map(str, report.horizons))} hours",
                f"- Validation modes: {', '.join(report.validation_modes)}",
                "",
                "## Protocol",
                "",
                *[f"- {item}" for item in report.protocol],
                "",
                "## Limitations",
                "",
                *[f"- {item}" for item in report.limitations],
                "",
                "## Interpretation boundary",
                "",
                "This artifact documents geographic external validation. "
                "It does not establish operational warning authority, "
                "clinical validity, causal transportability or universal "
                "performance outside the evaluated domains.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    output_paths = (
        report_path,
        folds_path,
        slices_path,
        leaderboard_path,
        config_path,
        validation_card_path,
    )
    manifest = build_experiment_manifest(
        f"external-validation-{report.target}",
        configuration=config.model_dump(mode="json"),
        input_paths=input_paths,
        output_paths=output_paths,
        random_seed=config.random_state,
        notes=(
            "Complete cities and regions are held out as external domains.",
            "Moving-block bootstrap and Diebold-Mariano comparisons are included.",
            "No paid AI API is used.",
        ),
        repository_root=repository_root,
    )
    manifest_path = write_experiment_manifest(
        manifest,
        root / "experiment-manifest.json",
    )

    return {
        "report": str(report_path),
        "fold_metrics": str(folds_path),
        "slice_metrics": str(slices_path),
        "leaderboard": str(leaderboard_path),
        "config": str(config_path),
        "validation_card": str(validation_card_path),
        "experiment_manifest": str(manifest_path),
    }
