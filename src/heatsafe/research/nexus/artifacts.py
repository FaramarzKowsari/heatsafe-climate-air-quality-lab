from __future__ import annotations

import csv
import json
from pathlib import Path

from heatsafe.research.nexus.contracts import NexusConfig, NexusReport
from heatsafe.research.provenance import build_experiment_manifest, write_experiment_manifest


def write_nexus_artifacts(
    report: NexusReport,
    *,
    output_directory: str | Path,
    config: NexusConfig,
    input_paths: tuple[str | Path, ...] = (),
    repository_root: str | Path | None = None,
) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)

    report_path = root / "report.json"
    leaderboard_path = root / "leaderboard.csv"
    cards_path = root / "model-cards.json"
    config_path = root / "config.json"

    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    cards_path.write_text(
        json.dumps([card.model_dump(mode="json") for card in report.model_cards], indent=2),
        encoding="utf-8",
    )
    config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    with leaderboard_path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = ["rank", "model", "horizon_hours", "mae", "rmse", "event_f1", "coverage", "interval_width"]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report.leaderboard)

    manifest = build_experiment_manifest(
        f"heataq-nexus-{report.target}",
        configuration=config.model_dump(mode="json"),
        input_paths=input_paths,
        output_paths=(report_path, leaderboard_path, cards_path, config_path),
        random_seed=config.random_state,
        notes=(
            "Chronological train/calibration/test split.",
            "Rolling-origin metrics included for persistence and linear regression.",
            "No paid AI API is used.",
        ),
        repository_root=repository_root,
    )
    manifest_path = write_experiment_manifest(manifest, root / "experiment-manifest.json")

    return {
        "report": str(report_path),
        "leaderboard": str(leaderboard_path),
        "model_cards": str(cards_path),
        "config": str(config_path),
        "experiment_manifest": str(manifest_path),
    }
