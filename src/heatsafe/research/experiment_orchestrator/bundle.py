from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable


CHECKSUM_FILE = "checksums.sha256"
RELEASE_DIRECTORY = "release"


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_bundle_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.as_posix() == CHECKSUM_FILE:
            continue
        if relative.parts and relative.parts[0] == RELEASE_DIRECTORY:
            continue
        yield path


def write_checksums(root: str | Path) -> Path:
    output_root = Path(root)
    lines = [
        f"{sha256_path(path)}  {path.relative_to(output_root).as_posix()}"
        for path in iter_bundle_files(output_root)
    ]
    checksum_path = output_root / CHECKSUM_FILE
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def verify_checksums(root: str | Path) -> dict[str, Any]:
    output_root = Path(root)
    checksum_path = output_root / CHECKSUM_FILE
    if not checksum_path.is_file():
        return {
            "valid": False,
            "checked": 0,
            "failures": [f"Missing {CHECKSUM_FILE}"],
        }

    failures: list[str] = []
    checked = 0
    for raw_line in checksum_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            failures.append(f"Malformed checksum line: {line}")
            continue
        target = output_root / relative
        checked += 1
        if not target.is_file():
            failures.append(f"Missing artifact: {relative}")
            continue
        actual = sha256_path(target)
        if actual != expected:
            failures.append(
                f"Checksum mismatch: {relative}; expected {expected}, got {actual}"
            )

    return {
        "valid": not failures,
        "checked": checked,
        "failures": failures,
    }


def write_artifact_index(
    root: str | Path,
    *,
    experiment_id: str,
    categories: dict[str, list[str]],
) -> Path:
    output_root = Path(root)
    payload = {
        "experiment_id": experiment_id,
        "artifact_categories": categories,
        "all_files": [
            path.relative_to(output_root).as_posix()
            for path in iter_bundle_files(output_root)
        ],
    }
    output = output_root / "artifact-index.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output


def create_deterministic_archive(
    root: str | Path,
    *,
    archive_name: str,
) -> Path:
    output_root = Path(root)
    release_root = output_root / RELEASE_DIRECTORY
    release_root.mkdir(parents=True, exist_ok=True)
    archive_path = release_root / archive_name

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        files = [
            path
            for path in sorted(output_root.rglob("*"))
            if path.is_file()
            and not (
                path.relative_to(output_root).parts
                and path.relative_to(output_root).parts[0] == RELEASE_DIRECTORY
            )
        ]
        for path in files:
            relative = path.relative_to(output_root).as_posix()
            info = zipfile.ZipInfo(relative)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    return archive_path
