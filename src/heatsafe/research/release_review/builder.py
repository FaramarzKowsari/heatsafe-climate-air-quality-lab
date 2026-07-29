from __future__ import annotations

import hashlib
import html
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from heatsafe.research.official_experiment.runner import (
    verify_real_official_experiment,
)
from heatsafe.research.release_review.contracts import (
    ReleaseBuildResult,
    ReviewedReleaseConfig,
)


def _read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise FileNotFoundError(path)
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"Release directory is not empty: {path}. "
                "Use --overwrite to replace it."
            )
        resolved = path.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe path: {resolved}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_file(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _all_release_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "checksums.sha256"
            and path.suffix.lower() != ".zip"
        ):
            yield path


def _write_checksums(root: Path) -> Path:
    path = root / "checksums.sha256"
    lines = [
        f"{_sha256(item)}  {item.relative_to(root).as_posix()}"
        for item in _all_release_files(root)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def verify_reviewed_release(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    checksum_path = root / "checksums.sha256"
    failures: list[str] = []
    checked = 0

    if not checksum_path.is_file():
        return {
            "valid": False,
            "checked_files": 0,
            "failures": ["Missing checksums.sha256"],
        }

    for raw_line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        expected, separator, relative = raw_line.partition("  ")
        if not separator:
            failures.append(f"Malformed checksum line: {raw_line}")
            continue
        target = root / relative
        if not target.is_file():
            failures.append(f"Missing file: {relative}")
            continue
        checked += 1
        actual = _sha256(target)
        if actual != expected:
            failures.append(f"Checksum mismatch: {relative}")

    required = (
        "README.md",
        "RELEASE_NOTES.md",
        "REVIEW_CHECKLIST.md",
        "PUBLICATION_LIMITATIONS.md",
        "release-summary.html",
        "release-summary.json",
        "metadata/CITATION.cff",
        "metadata/zenodo-deposition.json",
        "metadata/zenodo-github-template.json",
        "metadata/datacite-metadata.json",
        "metadata/release-manifest.json",
        "provenance/real-official-experiment-manifest.json",
        "provenance/bulk-source-report.json",
        "provenance/station-selection-report.json",
        "experiment/report/report.html",
    )
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing required release artifact: {relative}")

    return {
        "valid": not failures,
        "checked_files": checked,
        "failures": failures,
    }


def _deterministic_zip(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            info = zipfile.ZipInfo(
                relative.as_posix(),
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def _normalize_best_by_horizon(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(model)
        for key, model in sorted(
            value.items(),
            key=lambda item: int(str(item[0])),
        )
    }


def _selected_geography(
    bulk_report: dict[str, Any],
) -> dict[str, str]:
    selected = bulk_report.get("selected_geography")
    if isinstance(selected, dict):
        return {
            "state_code": str(selected.get("state_code", "06")),
            "state_name": str(selected.get("state_name", "California")),
            "county_code": str(selected.get("county_code", "001")),
            "county_name": str(selected.get("county_name", "Alameda")),
        }
    return {
        "state_code": "06",
        "state_name": "California",
        "county_code": "001",
        "county_name": "Alameda",
    }


def _release_description(
    *,
    geography: dict[str, str],
    station_id: str,
    rows: int,
    start_utc: str,
    end_utc: str,
) -> str:
    county = geography["county_name"]
    return (
        "A reviewed candidate research release containing a reproducible "
        "station-level PM2.5 forecasting benchmark derived from the official "
        f"US EPA AirData 2025 hourly 88101 product. Rows for {county} County, "
        f"California were filtered locally and monitoring station {station_id} "
        f"was selected by a declared temporal-continuity rule. The evaluated "
        f"segment contains {rows} hourly rows from {start_utc} through "
        f"{end_utc}. The archive includes canonical input data, complete model "
        "metrics, uncertainty results, tables, SVG figures, HTML and Markdown "
        "reports, source provenance, environment metadata, checksums and exact "
        "reproduction instructions. This is research software output, not an "
        "official warning service, medical product, exposure estimate or "
        "countywide causal analysis."
    )


def _citation_cff(
    *,
    config: ReviewedReleaseConfig,
    release_date: str,
    description: str,
) -> str:
    title = config.title.replace('"', "'")
    abstract = description.replace('"', "'")
    lines = [
        "cff-version: 1.2.0",
        'message: "If you use this reviewed experiment archive, cite this dataset release and the HeatSafe software repository."',
        f'title: "{title}"',
        "type: dataset",
        f'version: "{config.version}"',
        f'date-released: "{release_date}"',
        f'abstract: "{abstract}"',
        "authors:",
        '  - family-names: "Kowsari"',
        '    given-names: "Faramarz"',
        f'    orcid: "https://orcid.org/{config.creator_orcid}"',
        f'repository-code: "{config.repository_url}"',
        f'url: "{config.project_url}"',
        f'license: "{config.license_spdx}"',
        "keywords:",
    ]
    lines.extend(f'  - "{item}"' for item in config.keywords)
    return "\n".join(lines) + "\n"


def _zenodo_metadata(
    *,
    config: ReviewedReleaseConfig,
    release_date: str,
    description: str,
) -> dict[str, Any]:
    return {
        "title": config.title,
        "upload_type": "dataset",
        "description": description,
        "creators": [
            {
                "name": config.creator_name,
                "orcid": config.creator_orcid,
            }
        ],
        "publication_date": release_date,
        "version": config.version,
        "access_right": config.access_right,
        "license": config.zenodo_license,
        "keywords": list(config.keywords),
        "related_identifiers": [
            {
                "identifier": config.repository_url,
                "relation": "isSupplementTo",
                "resource_type": "software",
            },
            {
                "identifier": config.project_url,
                "relation": "isDocumentedBy",
                "resource_type": "publication-technicalnote",
            },
        ],
        "notes": (
            "Reviewed candidate metadata. Inspect REVIEW_CHECKLIST.md, "
            "PUBLICATION_LIMITATIONS.md, source provenance and checksums "
            "before publishing. No DOI has been minted by this build."
        ),
    }


def _datacite_metadata(
    *,
    config: ReviewedReleaseConfig,
    release_date: str,
    description: str,
) -> dict[str, Any]:
    return {
        "data": {
            "type": "dois",
            "attributes": {
                "event": "publish",
                "creators": [
                    {
                        "name": "Faramarz Kowsari",
                        "nameType": "Personal",
                        "givenName": "Faramarz",
                        "familyName": "Kowsari",
                        "nameIdentifiers": [
                            {
                                "nameIdentifier": (
                                    "https://orcid.org/"
                                    f"{config.creator_orcid}"
                                ),
                                "nameIdentifierScheme": "ORCID",
                                "schemeUri": "https://orcid.org",
                            }
                        ],
                    }
                ],
                "titles": [{"title": config.title}],
                "publisher": "Zenodo",
                "publicationYear": int(release_date[:4]),
                "types": {
                    "resourceTypeGeneral": "Dataset",
                    "resourceType": (
                        "Reproducible environmental forecasting "
                        "experiment archive"
                    ),
                },
                "descriptions": [
                    {
                        "description": description,
                        "descriptionType": "Abstract",
                    }
                ],
                "subjects": [
                    {"subject": keyword}
                    for keyword in config.keywords
                ],
                "url": config.repository_url,
                "rightsList": [
                    {
                        "rights": "Creative Commons Attribution 4.0 International",
                        "rightsUri": (
                            "https://creativecommons.org/licenses/by/4.0/"
                        ),
                        "rightsIdentifier": "CC-BY-4.0",
                        "rightsIdentifierScheme": "SPDX",
                    }
                ],
                "relatedIdentifiers": [
                    {
                        "relatedIdentifier": config.repository_url,
                        "relatedIdentifierType": "URL",
                        "relationType": "IsSupplementTo",
                        "resourceTypeGeneral": "Software",
                    }
                ],
            },
        }
    }


def _write_summary_html(
    *,
    output: Path,
    summary: dict[str, Any],
) -> None:
    best = summary["best_by_horizon"]
    best_rows = "".join(
        "<tr><td>"
        + html.escape(str(horizon))
        + " h</td><td>"
        + html.escape(str(model))
        + "</td></tr>"
        for horizon, model in best.items()
    ) or "<tr><td colspan='2'>Not available</td></tr>"

    geography = summary["selected_geography"]
    limitations = "".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in summary["limitations"]
    )
    content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(summary['title'])}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f7fa;color:#172033}}
main{{max-width:980px;margin:0 auto;padding:40px 24px 64px}}
.hero,.card{{background:#fff;border:1px solid #dbe3ec;border-radius:18px;padding:28px;margin-bottom:20px}}
h1{{font-size:2rem;margin:0 0 12px}} h2{{margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}
.metric{{background:#f3f7fb;border-radius:14px;padding:16px}}
.metric strong{{display:block;font-size:1.25rem;margin-bottom:6px}}
table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;border-bottom:1px solid #e4e9ef;padding:10px}}
.badge{{display:inline-block;background:#e9f7ef;color:#176b3a;padding:6px 10px;border-radius:999px;font-weight:700}}
.warning{{background:#fff8e6;border-left:4px solid #d49b00;padding:14px 16px}}
code{{background:#edf1f5;padding:2px 6px;border-radius:5px}}
</style>
</head>
<body><main>
<section class="hero">
<span class="badge">Reviewed candidate — no DOI minted</span>
<h1>{html.escape(summary['title'])}</h1>
<p>{html.escape(summary['description'])}</p>
</section>
<section class="grid">
<div class="metric"><strong>{html.escape(geography['county_name'])}</strong>Selected county</div>
<div class="metric"><strong>{html.escape(summary['selected_station'])}</strong>Monitoring station</div>
<div class="metric"><strong>{summary['selected_segment_rows']:,}</strong>Hourly rows</div>
<div class="metric"><strong>{html.escape(summary['release_version'])}</strong>Release version</div>
</section>
<section class="card">
<h2>Evaluated interval</h2>
<p><code>{html.escape(summary['segment_start_utc'])}</code> through
<code>{html.escape(summary['segment_end_utc'])}</code></p>
<p>Official source ZIP SHA-256:
<code>{html.escape(summary['bulk_zip_sha256'])}</code></p>
</section>
<section class="card">
<h2>Best model by forecast horizon</h2>
<table><thead><tr><th>Horizon</th><th>Model</th></tr></thead>
<tbody>{best_rows}</tbody></table>
</section>
<section class="card">
<h2>Scientific boundaries</h2>
<ul>{limitations}</ul>
<div class="warning">Review all files and metadata before creating a GitHub release or publishing on Zenodo.</div>
</section>
<section class="card">
<h2>Key files</h2>
<p><a href="experiment/report/report.html">Full HTML report</a></p>
<p><a href="metadata/zenodo-deposition.json">Zenodo deposition metadata</a></p>
<p><a href="REVIEW_CHECKLIST.md">Publication review checklist</a></p>
<p><a href="checksums.sha256">SHA-256 checksums</a></p>
</section>
</main></body></html>
"""
    output.write_text(content, encoding="utf-8")


def build_reviewed_release(
    workspace: str | Path,
    *,
    output_directory: str | Path,
    config: ReviewedReleaseConfig | None = None,
    overwrite: bool = False,
) -> ReleaseBuildResult:
    release_config = config or ReviewedReleaseConfig()
    workspace_input = Path(workspace)
    workspace_root = workspace_input.resolve()
    output_root = Path(output_directory)

    verification = verify_real_official_experiment(workspace_input)
    if not bool(verification.get("valid")):
        raise RuntimeError(
            "The source experiment failed verification: "
            + "; ".join(
                str(item)
                for item in verification.get("failures", [])
            )
        )

    _prepare_output(output_root, overwrite=overwrite)

    experiment_root = workspace_root / "experiment"
    source_manifest = _read_json(
        workspace_root / "real-official-experiment-manifest.json"
    )
    bulk_report = _read_json(
        workspace_root / "raw-source/bulk-source-report.json"
    )
    station_report = _read_json(
        workspace_root / "prepared/station-selection-report.json"
    )
    run_summary = _read_json(experiment_root / "run-summary.json")
    environment = _read_json(
        experiment_root / "metadata/environment.json",
        required=False,
    )

    selected_geography = _selected_geography(bulk_report)
    selected_station_payload = station_report.get("selected_station", {})
    if not isinstance(selected_station_payload, dict):
        selected_station_payload = {}
    manifest_station = source_manifest.get("selected_station", {})
    if not isinstance(manifest_station, dict):
        manifest_station = {}
    selected_station = str(
        selected_station_payload.get(
            "station_id",
            manifest_station.get("station_id", "unknown"),
        )
    )
    segment_rows = int(station_report.get("selected_segment_rows", 0))
    start_utc = str(
        station_report.get("selected_segment_start_utc", "unknown")
    )
    end_utc = str(
        station_report.get("selected_segment_end_utc", "unknown")
    )
    best_by_horizon = _normalize_best_by_horizon(
        run_summary.get("best_by_horizon")
    )

    limitations = [
        "Monitoring-site measurements are not equivalent to personal or population exposure.",
        "The selected station represents one monitoring location and not an entire county.",
        "The station was selected for temporal continuity, not geographic representativeness.",
        "Instrument, method, POC and sampling changes can affect comparability.",
        "The archive is not an official warning service or medical decision product.",
        "Results apply only to the declared source ZIP, selected segment, split protocol and software revision.",
        "EPA method metadata and the PM2.5 pre-generated-file advisory require review before publication claims.",
    ]

    description = _release_description(
        geography=selected_geography,
        station_id=selected_station,
        rows=segment_rows,
        start_utc=start_utc,
        end_utc=end_utc,
    )
    release_date = datetime.now(UTC).date().isoformat()

    _copy_tree(experiment_root / "report", output_root / "experiment/report")
    if release_config.include_tables:
        _copy_tree(experiment_root / "tables", output_root / "experiment/tables")
    if release_config.include_figures:
        _copy_tree(experiment_root / "figures", output_root / "experiment/figures")
    if release_config.include_nexus_artifacts:
        _copy_tree(experiment_root / "nexus", output_root / "experiment/nexus")
    _copy_tree(experiment_root / "metadata", output_root / "experiment/metadata")

    for relative in (
        "experiment-spec.json",
        "experiment-spec.original.json",
        "run-summary.json",
        "orchestration-manifest.json",
        "artifact-index.json",
        "verification.json",
        "reproduce.sh",
        "reproduce.cmd",
    ):
        source = experiment_root / relative
        if source.is_file():
            _copy_file(source, output_root / "experiment" / relative)

    if release_config.include_canonical_input:
        _copy_tree(experiment_root / "data", output_root / "experiment/data")

    provenance_root = output_root / "provenance"
    _copy_file(
        workspace_root / "real-official-experiment-manifest.json",
        provenance_root / "real-official-experiment-manifest.json",
    )
    _copy_file(
        workspace_root / "raw-source/bulk-source-report.json",
        provenance_root / "bulk-source-report.json",
    )
    _copy_file(
        workspace_root / "prepared/station-selection-report.json",
        provenance_root / "station-selection-report.json",
    )
    verification_after_fix = workspace_root / "verification-after-path-fix.json"
    if verification_after_fix.is_file():
        _copy_file(
            verification_after_fix,
            provenance_root / "source-verification.json",
        )

    metadata_root = output_root / "metadata"
    metadata_root.mkdir(parents=True, exist_ok=True)

    zenodo = _zenodo_metadata(
        config=release_config,
        release_date=release_date,
        description=description,
    )
    zenodo_deposition_path = metadata_root / "zenodo-deposition.json"
    zenodo_deposition_path.write_text(
        json.dumps({"metadata": zenodo}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    zenodo_github_path = metadata_root / "zenodo-github-template.json"
    zenodo_github_path.write_text(
        json.dumps(zenodo, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    citation_path = metadata_root / "CITATION.cff"
    citation_path.write_text(
        _citation_cff(
            config=release_config,
            release_date=release_date,
            description=description,
        ),
        encoding="utf-8",
    )

    datacite_path = metadata_root / "datacite-metadata.json"
    datacite_path.write_text(
        json.dumps(
            _datacite_metadata(
                config=release_config,
                release_date=release_date,
                description=description,
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = {
        "release_id": release_config.release_id,
        "release_version": release_config.version,
        "release_status": "reviewed-candidate",
        "doi_minted": False,
        "title": release_config.title,
        "description": description,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "creator": {
            "name": "Faramarz Kowsari",
            "orcid": release_config.creator_orcid,
        },
        "source_workspace": str(workspace_root),
        "source_experiment_verification": verification,
        "source_code_revision": environment.get("code_revision"),
        "source_environment": environment,
        "requested_geography": bulk_report.get("requested_geography"),
        "selected_geography": selected_geography,
        "geography_fallback_used": bool(
            bulk_report.get("geography_fallback_used", False)
        ),
        "selected_station": selected_station,
        "selected_segment_rows": segment_rows,
        "segment_start_utc": start_utc,
        "segment_end_utc": end_utc,
        "bulk_zip_sha256": str(
            bulk_report.get(
                "zip_sha256",
                source_manifest.get("bulk_zip_sha256", "unknown"),
            )
        ),
        "best_by_horizon": best_by_horizon,
        "limitations": limitations,
        "publication_decision": (
            "Review required before GitHub release, Zenodo upload or DOI."
        ),
    }
    summary_json_path = output_root / "release-summary.json"
    summary_json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_html_path = output_root / "release-summary.html"
    _write_summary_html(output=summary_html_path, summary=summary)

    release_notes = f"""# Release Notes

## {release_config.title}

**Version:** {release_config.version}  
**Status:** Reviewed candidate; no DOI minted  
**Release date prepared:** {release_date}

This archive packages the first verified official-source HeatSafe PM2.5
forecasting experiment for independent scientific review.

### Data identity

- Official product: US EPA AirData hourly PM2.5 FRM/FEM Mass, parameter 88101.
- Selected geography: {selected_geography['county_name']} County, California.
- Selected station: `{selected_station}`.
- Evaluated interval: `{start_utc}` through `{end_utc}`.
- Hourly rows: {segment_rows}.
- Source ZIP SHA-256: `{summary['bulk_zip_sha256']}`.

### Included evidence

- canonical experiment input;
- complete model metrics and best-by-horizon results;
- uncertainty, event and rolling-origin evaluation artifacts;
- HTML and Markdown technical reports;
- publication-ready SVG figures and tables;
- source, station-selection and environment provenance;
- Zenodo, DataCite and Citation File Format metadata;
- SHA-256 checksums and release verification.

### Important

This package is not evidence of personal exposure, countywide conditions,
causal effects, clinical risk or official warning authority. Read
`PUBLICATION_LIMITATIONS.md` and complete `REVIEW_CHECKLIST.md` before
publication.
"""
    (output_root / "RELEASE_NOTES.md").write_text(
        release_notes,
        encoding="utf-8",
    )

    checklist = """# Publication Review Checklist

Do not publish or mint a DOI until every required item is checked.

## Scientific identity

- [ ] Confirm the selected geography and station in `release-summary.json`.
- [ ] Confirm the evaluated UTC interval and row count.
- [ ] Confirm the official bulk ZIP SHA-256.
- [ ] Confirm the code revision and dependency environment.
- [ ] Confirm whether geographic fallback was used.
- [ ] Review EPA method names, POCs, qualifiers and any active data advisory.

## Results

- [ ] Inspect the complete all-model metrics table.
- [ ] Inspect best model selections for every forecast horizon.
- [ ] Inspect uncertainty coverage and interval width.
- [ ] Inspect event metrics and rolling-origin evaluation.
- [ ] Confirm baselines remain visible and were not omitted.
- [ ] Confirm no unsupported causal, medical or exposure claim appears.

## Reproducibility

- [ ] Run release verification and confirm every SHA-256 checksum.
- [ ] Open the HTML report from the release directory.
- [ ] Test the included reproduction command in a clean environment.
- [ ] Confirm the canonical input and normalized specification are present.
- [ ] Confirm the software repository commit is publicly accessible.

## Metadata and publication

- [ ] Review `metadata/CITATION.cff`.
- [ ] Review `metadata/zenodo-deposition.json`.
- [ ] Review `metadata/datacite-metadata.json`.
- [ ] Choose the final public title and description.
- [ ] Add the DOI only after Zenodo creates it.
- [ ] Create a GitHub tag and release only after final approval.
- [ ] Preserve the reviewed release ZIP without post-publication modification.
"""
    (output_root / "REVIEW_CHECKLIST.md").write_text(
        checklist,
        encoding="utf-8",
    )

    limitation_lines = "\n".join(f"- {item}" for item in limitations)
    (output_root / "PUBLICATION_LIMITATIONS.md").write_text(
        "# Publication Limitations\n\n"
        + limitation_lines
        + "\n\n## Interpretation boundary\n\n"
        "The archive supports reproducibility and technical evaluation. "
        "It does not transform a station-level forecasting benchmark into "
        "an exposure model, health diagnosis, regulatory assessment, "
        "countywide estimate or official warning system.\n",
        encoding="utf-8",
    )

    readme = f"""# Reviewed Candidate Research Release

This directory is a self-contained scientific review package for:

**{release_config.title}**

Start with:

1. `release-summary.html`
2. `experiment/report/report.html`
3. `REVIEW_CHECKLIST.md`
4. `PUBLICATION_LIMITATIONS.md`
5. `checksums.sha256`

## Verify

```bash
heatsafe-release-review verify .
```

## Zenodo

`metadata/zenodo-deposition.json` is suitable as a reviewed metadata starting
point for a manual Zenodo deposition. `metadata/zenodo-github-template.json`
is a template for a future repository-root `.zenodo.json` file. Neither file
publishes the release or mints a DOI automatically.

## Status

Reviewed candidate. No DOI has been minted.
"""
    (output_root / "README.md").write_text(readme, encoding="utf-8")

    release_manifest = {
        "release_id": release_config.release_id,
        "version": release_config.version,
        "status": "reviewed-candidate",
        "doi": None,
        "source_workspace": str(workspace_root),
        "source_experiment_manifest_sha256": _sha256(
            workspace_root / "real-official-experiment-manifest.json"
        ),
        "source_bulk_report_sha256": _sha256(
            workspace_root / "raw-source/bulk-source-report.json"
        ),
        "source_station_report_sha256": _sha256(
            workspace_root / "prepared/station-selection-report.json"
        ),
        "files": [
            {
                "path": path.relative_to(output_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in _all_release_files(output_root)
            if path.name != "release-manifest.json"
        ],
        "publication_gate": {
            "review_checklist_required": True,
            "doi_minted": False,
            "automatic_publish": False,
        },
    }
    release_manifest_path = metadata_root / "release-manifest.json"
    release_manifest_path.write_text(
        json.dumps(release_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    checksums_path = _write_checksums(output_root)
    release_verification = verify_reviewed_release(output_root)
    if not bool(release_verification["valid"]):
        raise RuntimeError(
            "Reviewed release failed verification: "
            + "; ".join(
                str(item)
                for item in release_verification["failures"]
            )
        )

    verification_path = output_root / "release-verification.json"
    verification_path.write_text(
        json.dumps(release_verification, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    checksums_path = _write_checksums(output_root)
    release_verification = verify_reviewed_release(output_root)
    if not bool(release_verification["valid"]):
        raise RuntimeError(
            "Reviewed release failed final verification: "
            + "; ".join(
                str(item)
                for item in release_verification["failures"]
            )
        )

    archive_path: Path | None = None
    if release_config.create_zip:
        archive_path = output_root.with_name(
            f"{release_config.release_id}-v{release_config.version}.zip"
        )
        _deterministic_zip(output_root, archive_path)

    return ReleaseBuildResult(
        release_directory=str(output_root),
        release_archive=(
            str(archive_path) if archive_path is not None else None
        ),
        release_manifest=str(release_manifest_path),
        release_summary_html=str(summary_html_path),
        release_summary_json=str(summary_json_path),
        zenodo_metadata=str(zenodo_deposition_path),
        citation_cff=str(citation_path),
        checksums=str(checksums_path),
        verification=release_verification,
    )
