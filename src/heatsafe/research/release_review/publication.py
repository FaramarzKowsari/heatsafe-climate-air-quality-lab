from __future__ import annotations

import hashlib
import html
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from heatsafe.research.release_review.harmonizer import (
    verify_harmonized_release,
)


DEFAULT_REPOSITORY = "FaramarzKowsari/heatsafe-climate-air-quality-lab"
DEFAULT_TAG = "epa-pm25-2025-v0.1.0"
DEFAULT_VERSION = "0.1.0"
DEFAULT_ZENODO_URL = "https://zenodo.org/uploads/new"
DEFAULT_GITHUB_RELEASE_URL = (
    "https://github.com/FaramarzKowsari/"
    "heatsafe-climate-air-quality-lab/releases/new"
)
CREATOR_ORCID = "0000-0003-1692-0453"
REPOSITORY_URL = (
    "https://github.com/FaramarzKowsari/"
    "heatsafe-climate-air-quality-lab"
)
PROJECT_URL = (
    "https://faramarzkowsari.github.io/"
    "heatsafe-climate-air-quality-lab/"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _all_handoff_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HANDOFF_CHECKSUMS.sha256":
            yield path


def _write_handoff_checksums(root: Path) -> Path:
    output = root / "HANDOFF_CHECKSUMS.sha256"
    lines = [
        f"{_sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in _all_handoff_files(root)
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Publication handoff already exists: {path}. "
                "Use --overwrite to replace it."
            )
        resolved = path.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe path: {resolved}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _publication_title(summary: dict[str, Any]) -> str:
    geography = summary.get("selected_geography")
    if not isinstance(geography, dict):
        geography = {}
    county = str(geography.get("county_name", "San Diego"))
    state = str(geography.get("state_name", "California"))
    version = str(summary.get("release_version", DEFAULT_VERSION))
    return (
        f"US EPA AirData {county} County, {state} PM2.5 "
        f"Forecasting Benchmark v{version}"
    )


def _release_notes(
    *,
    title: str,
    tag: str,
    summary: dict[str, Any],
    archive_name: str,
    archive_sha256: str,
) -> str:
    geography = summary["selected_geography"]
    time_basis = summary["time_basis"]
    best = summary.get("best_by_horizon", {})
    best_lines = "\n".join(
        f"- **{horizon} h:** `{model}`"
        for horizon, model in best.items()
    ) or "- Model summary is available inside the release archive."

    return f"""# {title}

**Tag:** `{tag}`  
**Status:** Draft publication handoff  
**DOI:** Pending Zenodo draft review and publication

This release contains the final metadata-harmonized, checksum-verified
research archive for the first official-source HeatSafe PM2.5 forecasting
benchmark.

## Verified result

- Selected geography: **{geography['county_name']} County, {geography['state_name']}**
- Monitoring station: `{summary['selected_station']}`
- Hourly rows: **{summary['selected_segment_rows']:,}**
- UTC interval: `{time_basis['segment_start_utc']}` through `{time_basis['segment_end_utc']}`
- Local interval ({time_basis['local_timezone']}): `{time_basis['segment_start_local']}` through `{time_basis['segment_end_local']}`
- Public experiment ID: `{summary['public_experiment_id']}`
- Source execution ID preserved in provenance: `{summary['source_execution_id']}`

## Best model by horizon

{best_lines}

## Release assets

- `{archive_name}`
- `SHA256SUMS.txt`
- `CITATION.cff`
- `final-publication-metadata.json`
- `identifier-crosswalk.json`
- `time-basis.json`

Archive SHA-256:

```text
{archive_sha256}
```

## Scientific boundary

This is a reproducible station-level forecasting benchmark. It is not an
official warning service, medical product, personal-exposure estimate,
countywide reconstruction or causal health analysis.

## Citation and DOI

The Zenodo DOI is intentionally not inserted before the Zenodo draft is
reviewed and a DOI is reserved. After the reserved DOI is supplied, the final
archive must be regenerated before either the Zenodo record or this GitHub
draft is published.
"""


def _zenodo_guide(
    *,
    title: str,
    summary: dict[str, Any],
    archive_name: str,
    archive_sha256: str,
) -> str:
    geography = summary["selected_geography"]
    time_basis = summary["time_basis"]
    keywords = summary.get("keywords", [])
    keyword_lines = "\n".join(f"- {item}" for item in keywords)

    return f"""# Zenodo Draft Form Guide

Create a **draft only**. Do not press Publish yet.

## Files to upload

Upload these two files from the `assets` directory:

1. `{archive_name}`
2. `SHA256SUMS.txt`

The archive SHA-256 must be:

```text
{archive_sha256}
```

## Basic information

**Does the upload already have a DOI?**  
No.

After saving the draft, use **Get a DOI now!** if you want to reserve the DOI
before publication. Do not delete the draft after reserving the DOI.

**Resource type**  
Dataset

**Title**

```text
{title}
```

**Publication date**  
Use the date on which the record will first become publicly available.

**Creator**

```text
Faramarz Kowsari
ORCID: https://orcid.org/{CREATOR_ORCID}
```

## Description

Use the complete description stored in:

```text
assets/final-publication-metadata.json
```

or copy the `description` value from:

```text
assets/zenodo-deposition.json
```

## Geography

```text
{geography['county_name']} County, {geography['state_name']}, United States
```

## Evaluated interval

UTC:

```text
{time_basis['segment_start_utc']}
through
{time_basis['segment_end_utc']}
```

Local time:

```text
{time_basis['segment_start_local']}
through
{time_basis['segment_end_local']}
```

## License

```text
Creative Commons Attribution 4.0 International
CC-BY-4.0
```

## Keywords

{keyword_lines}

## Related identifiers

Repository:

```text
{REPOSITORY_URL}
```

Project documentation:

```text
{PROJECT_URL}
```

Use relations equivalent to:

- Is supplement to — software repository
- Is documented by — project documentation

## Required sequence

1. Upload the ZIP and SHA256SUMS.
2. Fill and save the metadata.
3. Preview the Zenodo record.
4. Reserve the DOI if desired.
5. Copy the reserved DOI into `RESERVED_DOI.txt`.
6. Do not publish.
7. Run the DOI-finalization pack before publishing either platform.
"""


def _publication_sequence(*, tag: str, title: str) -> str:
    return f"""# Controlled Publication Sequence

## Phase 1 — completed

- Verified official EPA experiment
- Reviewed candidate archive
- Final metadata harmonization
- Checksum-verified final ZIP

## Phase 2 — this handoff

1. Inspect `PUBLICATION_READINESS.html`.
2. Inspect `GITHUB_RELEASE_NOTES.md`.
3. Inspect `ZENODO_DRAFT_FORM_GUIDE.md`.
4. Create a GitHub **draft** release for tag `{tag}`.
5. Create a Zenodo **draft** upload.
6. Reserve a DOI in Zenodo if desired.
7. Do not publish either draft.

## Phase 3 — after DOI reservation

Provide the reserved DOI for a DOI-injection and final rebuild step. The next
pack will:

- insert the DOI into Citation File Format and publication metadata;
- update the GitHub release notes;
- regenerate all checksums;
- rebuild the deterministic final ZIP;
- verify that the reserved DOI is present and consistent.

## Phase 4 — publication

Only after final DOI-aware verification:

1. Replace the files in the Zenodo draft with the DOI-aware final ZIP.
2. Preview and publish Zenodo.
3. Confirm the DOI resolves.
4. Publish the GitHub draft release titled:

```text
{title}
```

5. Add the registered DOI to the repository documentation.

Publishing is intentionally excluded from Scientific Pack 09.
"""


def _github_draft_script(
    *,
    repository: str,
    tag: str,
    title: str,
    archive_name: str,
) -> str:
    return rf'''@echo off
setlocal EnableExtensions
title HeatSafe GitHub Draft Release 09

set "ROOT=%~dp0"
set "REPO={repository}"
set "TAG={tag}"
set "TITLE={title}"
set "ARCHIVE=%ROOT%assets\{archive_name}"
set "SHA=%ROOT%assets\SHA256SUMS.txt"
set "CITATION=%ROOT%assets\CITATION.cff"
set "FINALMETA=%ROOT%assets\final-publication-metadata.json"
set "CROSSWALK=%ROOT%assets\identifier-crosswalk.json"
set "TIMEBASIS=%ROOT%assets\time-basis.json"
set "NOTES=%ROOT%GITHUB_RELEASE_NOTES.md"

echo.
echo ==============================================================================
echo Create GitHub DRAFT Release Only
echo ==============================================================================
echo.
echo Repository: %REPO%
echo Tag:        %TAG%
echo Title:      %TITLE%
echo.
echo This command creates a DRAFT. It does not publish the release.
echo.

where gh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: GitHub CLI gh.exe was not found.
  echo Use OPEN_GITHUB_RELEASE_PAGE_09.cmd for the manual method.
  goto :fail
)

gh auth status
if errorlevel 1 (
  echo ERROR: GitHub CLI is not authenticated.
  echo Run: gh auth login
  goto :fail
)

for %%F in ("%ARCHIVE%" "%SHA%" "%CITATION%" "%FINALMETA%" "%CROSSWALK%" "%TIMEBASIS%" "%NOTES%") do (
  if not exist "%%~F" (
    echo ERROR: Missing required file:
    echo %%~F
    goto :fail
  )
)

gh release view "%TAG%" --repo "%REPO%" >nul 2>&1
if not errorlevel 1 (
  echo ERROR: A release already exists for tag %TAG%.
  echo Review it manually instead of creating a duplicate.
  goto :fail
)

set /p "CONFIRM=Type CREATE-DRAFT to continue: "
if /I not "%CONFIRM%"=="CREATE-DRAFT" (
  echo Cancelled.
  goto :fail
)

gh release create "%TAG%" ^
  "%ARCHIVE%#Final harmonized research archive" ^
  "%SHA%#SHA-256 checksums" ^
  "%CITATION%#Dataset citation metadata" ^
  "%FINALMETA%#Final publication metadata" ^
  "%CROSSWALK%#Identifier crosswalk" ^
  "%TIMEBASIS%#UTC and local-time basis" ^
  --repo "%REPO%" ^
  --target main ^
  --title "%TITLE%" ^
  --notes-file "%NOTES%" ^
  --draft ^
  --latest=false

if errorlevel 1 goto :fail

echo.
echo ==============================================================================
echo SUCCESS: GitHub draft release created.
echo ==============================================================================
echo.
echo Do not publish it until the Zenodo DOI-aware archive is finalized.
echo.
start "" "https://github.com/%REPO%/releases"
pause
exit /b 0

:fail
echo.
echo No GitHub release was published.
echo.
pause
exit /b 1
'''


def _open_github_script() -> str:
    return rf'''@echo off
setlocal
set "ROOT=%~dp0"
start "" "{DEFAULT_GITHUB_RELEASE_URL}"
start "" explorer.exe "%ROOT%assets"
start "" notepad.exe "%ROOT%GITHUB_RELEASE_NOTES.md"
exit /b 0
'''


def _open_zenodo_script() -> str:
    return rf'''@echo off
setlocal
set "ROOT=%~dp0"
start "" "{DEFAULT_ZENODO_URL}"
start "" explorer.exe "%ROOT%assets"
start "" notepad.exe "%ROOT%ZENODO_DRAFT_FORM_GUIDE.md"
exit /b 0
'''


def _readiness_html(
    *,
    title: str,
    tag: str,
    summary: dict[str, Any],
    archive_name: str,
    archive_size: int,
    archive_sha256: str,
) -> str:
    geography = summary["selected_geography"]
    time_basis = summary["time_basis"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Publication Handoff | HeatSafe Research Lab</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f4f7fa;color:#172033}}
main{{max-width:1040px;margin:0 auto;padding:36px 24px 64px}}
.hero,.card{{background:#fff;border:1px solid #d9e2ec;border-radius:18px;padding:28px;margin-bottom:20px}}
h1{{font-size:2rem;margin:0 0 12px}} h2{{margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}
.metric{{background:#f2f6fa;border-radius:14px;padding:16px}}
.metric strong{{display:block;font-size:1.15rem;margin-bottom:6px;overflow-wrap:anywhere}}
.badge{{display:inline-block;background:#fff3cd;color:#7a5600;padding:6px 10px;border-radius:999px;font-weight:700}}
.ok{{background:#eaf8ef;border-left:4px solid #2e8b57;padding:14px 16px}}
.warn{{background:#fff8e6;border-left:4px solid #d49b00;padding:14px 16px}}
code{{background:#edf1f5;padding:2px 6px;border-radius:5px;overflow-wrap:anywhere}}
a{{color:#086a9b}}
</style>
</head>
<body><main>
<section class="hero">
<span class="badge">Draft handoff — publication blocked</span>
<h1>{html.escape(title)}</h1>
<p>The final harmonized archive has passed integrity verification. This handoff prepares a GitHub draft release and a Zenodo draft upload without publishing either platform or claiming a DOI.</p>
</section>
<section class="grid">
<div class="metric"><strong>{html.escape(tag)}</strong>Proposed Git tag</div>
<div class="metric"><strong>{html.escape(geography['county_name'])}</strong>Selected county</div>
<div class="metric"><strong>{html.escape(summary['selected_station'])}</strong>Monitoring station</div>
<div class="metric"><strong>{summary['selected_segment_rows']:,}</strong>Hourly rows</div>
</section>
<section class="card">
<h2>Final archive</h2>
<p><code>{html.escape(archive_name)}</code></p>
<p>Size: {archive_size:,} bytes</p>
<p>SHA-256:</p>
<p><code>{archive_sha256}</code></p>
<div class="ok">The archive and its harmonized release directory passed verification before this handoff was generated.</div>
</section>
<section class="card">
<h2>Time basis</h2>
<p>UTC: <code>{html.escape(str(time_basis['segment_start_utc']))}</code> through <code>{html.escape(str(time_basis['segment_end_utc']))}</code></p>
<p>Local: <code>{html.escape(str(time_basis['segment_start_local']))}</code> through <code>{html.escape(str(time_basis['segment_end_local']))}</code></p>
</section>
<section class="card">
<h2>Next controlled actions</h2>
<ol>
<li>Review <a href="GITHUB_RELEASE_NOTES.md">GitHub release notes</a>.</li>
<li>Review <a href="ZENODO_DRAFT_FORM_GUIDE.md">Zenodo draft guide</a>.</li>
<li>Create drafts only.</li>
<li>Reserve a DOI in Zenodo if desired.</li>
<li>Do not publish before DOI-aware regeneration.</li>
</ol>
<div class="warn">Scientific Pack 09 deliberately contains no command that publishes Zenodo or converts a GitHub draft into a public release.</div>
</section>
<section class="card">
<h2>Files</h2>
<p><a href="PUBLICATION_SEQUENCE.md">Controlled publication sequence</a></p>
<p><a href="PUBLICATION_HANDOFF.json">Machine-readable handoff</a></p>
<p><a href="assets/SHA256SUMS.txt">Asset checksums</a></p>
</section>
</main></body></html>
"""


def verify_publication_handoff(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    failures: list[str] = []
    checksum_path = root / "HANDOFF_CHECKSUMS.sha256"
    checked = 0

    if not checksum_path.is_file():
        failures.append("Missing HANDOFF_CHECKSUMS.sha256")
    else:
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, separator, relative = line.partition("  ")
            if not separator:
                failures.append(f"Malformed checksum line: {line}")
                continue
            target = root / relative
            if not target.is_file():
                failures.append(f"Missing handoff file: {relative}")
                continue
            checked += 1
            if _sha256(target) != expected:
                failures.append(f"Checksum mismatch: {relative}")

    required = (
        "PUBLICATION_READINESS.html",
        "PUBLICATION_HANDOFF.json",
        "PUBLICATION_SEQUENCE.md",
        "GITHUB_RELEASE_NOTES.md",
        "ZENODO_DRAFT_FORM_GUIDE.md",
        "CREATE_GITHUB_DRAFT_RELEASE_09.cmd",
        "OPEN_GITHUB_RELEASE_PAGE_09.cmd",
        "OPEN_ZENODO_DRAFT_09.cmd",
        "assets/SHA256SUMS.txt",
        "assets/CITATION.cff",
        "assets/final-publication-metadata.json",
        "assets/identifier-crosswalk.json",
        "assets/time-basis.json",
        "assets/zenodo-deposition.json",
    )
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing required handoff file: {relative}")

    handoff_path = root / "PUBLICATION_HANDOFF.json"
    if handoff_path.is_file():
        handoff = _read_json(handoff_path)
        if handoff.get("github_release_mode") != "draft-only":
            failures.append("GitHub release mode is not draft-only")
        if handoff.get("zenodo_mode") != "draft-only":
            failures.append("Zenodo mode is not draft-only")
        if handoff.get("doi_minted") is not False:
            failures.append("DOI state must remain false")
        if handoff.get("publishing_enabled") is not False:
            failures.append("Publishing must remain disabled")

    draft_script = root / "CREATE_GITHUB_DRAFT_RELEASE_09.cmd"
    if draft_script.is_file():
        text = draft_script.read_text(encoding="ascii", errors="ignore")
        if "--draft" not in text:
            failures.append("GitHub draft script lacks --draft")
        if "--draft=false" in text:
            failures.append("GitHub draft script can publish")
        if "actions/publish" in text.lower():
            failures.append("Zenodo publish action found in draft script")

    return {
        "valid": not failures,
        "checked_files": checked,
        "failures": failures,
    }


def prepare_publication_handoff(
    harmonized_release: str | Path,
    *,
    output_directory: str | Path,
    repository: str = DEFAULT_REPOSITORY,
    tag: str = DEFAULT_TAG,
    overwrite: bool = False,
) -> dict[str, Any]:
    release_root = Path(harmonized_release)
    output = Path(output_directory)

    release_verification = verify_harmonized_release(release_root)
    if not bool(release_verification.get("valid")):
        raise RuntimeError(
            "Harmonized release failed verification: "
            + "; ".join(
                str(item)
                for item in release_verification.get("failures", [])
            )
        )

    summary = _read_json(release_root / "release-summary.json")
    final_metadata = _read_json(
        release_root / "metadata/final-publication-metadata.json"
    )
    identifier_crosswalk = _read_json(
        release_root / "metadata/identifier-crosswalk.json"
    )
    time_basis = _read_json(release_root / "metadata/time-basis.json")
    zenodo_deposition = _read_json(
        release_root / "metadata/zenodo-deposition.json"
    )

    version = str(summary.get("release_version", DEFAULT_VERSION))
    archive = release_root.with_name(
        f"{summary['release_id']}-v{version}.zip"
    )
    if not archive.is_file():
        raise FileNotFoundError(f"Final harmonized ZIP not found: {archive}")

    archive_sha256 = _sha256(archive)
    archive_size = archive.stat().st_size
    title = _publication_title(summary)

    _prepare_output(output, overwrite=overwrite)
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    shutil.copy2(archive, assets / archive.name)
    copy_map = {
        release_root / "metadata/CITATION.cff": assets / "CITATION.cff",
        release_root / "metadata/final-publication-metadata.json": (
            assets / "final-publication-metadata.json"
        ),
        release_root / "metadata/identifier-crosswalk.json": (
            assets / "identifier-crosswalk.json"
        ),
        release_root / "metadata/time-basis.json": assets / "time-basis.json",
        release_root / "metadata/zenodo-deposition.json": (
            assets / "zenodo-deposition.json"
        ),
        release_root / "release-summary.json": assets / "release-summary.json",
    }
    for source, target in copy_map.items():
        shutil.copy2(source, target)

    sha_lines = [
        f"{archive_sha256}  {archive.name}",
        f"{_sha256(assets / 'CITATION.cff')}  CITATION.cff",
        (
            f"{_sha256(assets / 'final-publication-metadata.json')}  "
            "final-publication-metadata.json"
        ),
        (
            f"{_sha256(assets / 'identifier-crosswalk.json')}  "
            "identifier-crosswalk.json"
        ),
        f"{_sha256(assets / 'time-basis.json')}  time-basis.json",
    ]
    (assets / "SHA256SUMS.txt").write_text(
        "\n".join(sha_lines) + "\n",
        encoding="utf-8",
    )

    (output / "GITHUB_RELEASE_NOTES.md").write_text(
        _release_notes(
            title=title,
            tag=tag,
            summary=summary,
            archive_name=archive.name,
            archive_sha256=archive_sha256,
        ),
        encoding="utf-8",
    )
    (output / "ZENODO_DRAFT_FORM_GUIDE.md").write_text(
        _zenodo_guide(
            title=title,
            summary=summary,
            archive_name=archive.name,
            archive_sha256=archive_sha256,
        ),
        encoding="utf-8",
    )
    (output / "PUBLICATION_SEQUENCE.md").write_text(
        _publication_sequence(tag=tag, title=title),
        encoding="utf-8",
    )

    scripts = {
        "CREATE_GITHUB_DRAFT_RELEASE_09.cmd": _github_draft_script(
            repository=repository,
            tag=tag,
            title=title,
            archive_name=archive.name,
        ),
        "OPEN_GITHUB_RELEASE_PAGE_09.cmd": _open_github_script(),
        "OPEN_ZENODO_DRAFT_09.cmd": _open_zenodo_script(),
    }
    for name, script in scripts.items():
        (output / name).write_text(
            script.replace("\n", "\r\n"),
            encoding="ascii",
        )

    (output / "RESERVED_DOI.txt").write_text(
        "Paste the reserved Zenodo DOI here after creating and saving "
        "the draft. Do not publish yet.\n",
        encoding="utf-8",
    )

    handoff = {
        "publication_handoff_id": (
            "epa-airdata-california-pm25-2025-publication-handoff"
        ),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "repository": repository,
        "repository_url": REPOSITORY_URL,
        "project_url": PROJECT_URL,
        "tag": tag,
        "release_title": title,
        "release_version": version,
        "release_id": summary["release_id"],
        "public_experiment_id": summary["public_experiment_id"],
        "selected_geography": summary["selected_geography"],
        "selected_station": summary["selected_station"],
        "selected_segment_rows": summary["selected_segment_rows"],
        "time_basis": time_basis,
        "archive": {
            "path": str((assets / archive.name).resolve()),
            "name": archive.name,
            "size_bytes": archive_size,
            "sha256": archive_sha256,
        },
        "citation": {
            "creator": "Faramarz Kowsari",
            "orcid": CREATOR_ORCID,
            "license": "CC-BY-4.0",
        },
        "final_publication_metadata": final_metadata,
        "identifier_crosswalk": identifier_crosswalk,
        "zenodo_metadata": zenodo_deposition,
        "github_release_mode": "draft-only",
        "zenodo_mode": "draft-only",
        "doi_minted": False,
        "publishing_enabled": False,
        "next_required_input": "Reserved Zenodo DOI after draft review",
        "source_release_verification": release_verification,
    }
    _write_json(output / "PUBLICATION_HANDOFF.json", handoff)

    (output / "PUBLICATION_READINESS.html").write_text(
        _readiness_html(
            title=title,
            tag=tag,
            summary=summary,
            archive_name=archive.name,
            archive_size=archive_size,
            archive_sha256=archive_sha256,
        ),
        encoding="utf-8",
    )

    _write_handoff_checksums(output)
    verification = verify_publication_handoff(output)
    if not verification["valid"]:
        raise RuntimeError(
            "Publication handoff failed verification: "
            + "; ".join(str(item) for item in verification["failures"])
        )

    _write_json(output / "PUBLICATION_HANDOFF_VERIFICATION.json", verification)
    _write_handoff_checksums(output)
    verification = verify_publication_handoff(output)
    if not verification["valid"]:
        raise RuntimeError(
            "Publication handoff failed final verification: "
            + "; ".join(str(item) for item in verification["failures"])
        )

    return {
        "handoff_directory": str(output),
        "readiness_html": str(output / "PUBLICATION_READINESS.html"),
        "github_release_notes": str(output / "GITHUB_RELEASE_NOTES.md"),
        "zenodo_guide": str(output / "ZENODO_DRAFT_FORM_GUIDE.md"),
        "github_draft_script": str(
            output / "CREATE_GITHUB_DRAFT_RELEASE_09.cmd"
        ),
        "zenodo_open_script": str(output / "OPEN_ZENODO_DRAFT_09.cmd"),
        "archive_sha256": archive_sha256,
        "verification": verification,
    }
