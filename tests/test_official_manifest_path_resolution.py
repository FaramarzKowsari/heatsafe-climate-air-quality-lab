from __future__ import annotations

from pathlib import Path

from heatsafe.research.official_experiment.runner import (
    _resolve_manifest_artifact,
)


def test_already_workspace_prefixed_relative_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("artifacts/local-real-experiments/example")
    target = workspace / "official-snapshots/dataset/0.1.0"
    target.mkdir(parents=True)

    resolved = _resolve_manifest_artifact(
        workspace,
        str(target),
    )

    assert resolved == target
    assert resolved.exists()


def test_workspace_relative_manifest_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = Path("artifacts/local-real-experiments/example")
    target = workspace / "prepared/selected-station-hourly.csv"
    target.parent.mkdir(parents=True)
    target.write_text("timestamp,pm25\n", encoding="utf-8")

    resolved = _resolve_manifest_artifact(
        workspace,
        "prepared/selected-station-hourly.csv",
    )

    assert resolved == target
    assert resolved.is_file()


def test_absolute_manifest_path_is_preserved(
    tmp_path: Path,
) -> None:
    target = tmp_path / "manifest.json"
    target.write_text("{}", encoding="utf-8")

    resolved = _resolve_manifest_artifact(
        tmp_path / "workspace",
        target,
    )

    assert resolved == target
