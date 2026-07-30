from __future__ import annotations

import hashlib
import html
import json
import shutil
import zipfile
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from heatsafe.research.official_experiment.runner import (
    verify_real_official_experiment,
)
from heatsafe.research.release_review.builder import (
    verify_reviewed_release,
)


DEFAULT_RELEASE_ID = (
    "epa-airdata-california-pm25-2025-first-real-reviewed"
)
DEFAULT_PUBLIC_EXPERIMENT_ID = (
    "epa-airdata-california-pm25-2025-first-real-bulk"
)
DEFAULT_VERSION = "0.1.0"
DEFAULT_LOCAL_TIMEZONE = "America/Los_Angeles"
REPOSITORY_URL = (
    "https://github.com/FaramarzKowsari/"
    "heatsafe-climate-air-quality-lab"
)
PROJECT_URL = (
    "https://faramarzkowsari.github.io/"
    "heatsafe-climate-air-quality-lab/"
)
CREATOR_ORCID = "0000-0003-1692-0453"


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


def _all_files(root: Path) -> Iterable[Path]:
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
        for item in _all_files(root)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _prepare_output(
    source_release: Path,
    output: Path,
    *,
    overwrite: bool,
) -> None:
    if output.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output already exists: {output}. Use --overwrite."
            )
        resolved = output.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe path: {resolved}")
        shutil.rmtree(output)
    shutil.copytree(source_release, output)


def _selected_geography(
    bulk_report: dict[str, Any],
) -> dict[str, str]:
    raw = bulk_report.get("selected_geography")
    if not isinstance(raw, dict):
        raise ValueError(
            "bulk-source-report.json has no selected_geography object"
        )
    return {
        "state_code": str(raw.get("state_code", "")),
        "state_name": str(raw.get("state_name", "")),
        "county_code": str(raw.get("county_code", "")),
        "county_name": str(raw.get("county_name", "")),
    }


def _source_execution_id(
    output: Path,
    source_manifest: dict[str, Any],
) -> str:
    run_summary_path = output / "experiment/run-summary.json"
    if run_summary_path.is_file():
        run_summary = _read_json(run_summary_path)
        value = run_summary.get("experiment_id")
        if value:
            return str(value)

    spec_path = output / "experiment/experiment-spec.original.json"
    if spec_path.is_file():
        spec = _read_json(spec_path)
        value = spec.get("experiment_id")
        if value:
            return str(value)

    value = source_manifest.get("experiment_id")
    return str(value or "unknown-source-experiment")


def _selected_station(
    station_report: dict[str, Any],
    source_manifest: dict[str, Any],
) -> str:
    selected = station_report.get("selected_station")
    if isinstance(selected, dict) and selected.get("station_id"):
        return str(selected["station_id"])

    selected = source_manifest.get("selected_station")
    if isinstance(selected, dict) and selected.get("station_id"):
        return str(selected["station_id"])

    return "unknown"


def _public_title(geography: dict[str, str]) -> str:
    county = geography["county_name"]
    state = geography["state_name"]
    return (
        f"US EPA AirData {county} County, {state} PM2.5 "
        "Forecasting Benchmark — Reviewed Official-Source Release"
    )


def _keywords(geography: dict[str, str]) -> list[str]:
    return [
        "US EPA AirData",
        "PM2.5",
        "air quality",
        "forecasting",
        "environmental data",
        "reproducibility",
        "uncertainty",
        f"{geography['county_name']} County",
        geography["state_name"],
        "official-source data",
    ]


def _first_sunday(year: int, month: int) -> datetime:
    first = datetime(year, month, 1, tzinfo=UTC)
    days_until_sunday = (6 - first.weekday()) % 7
    return first + timedelta(days=days_until_sunday)


def _pacific_offset_for_utc(value: datetime) -> timezone:
    year = value.year
    second_sunday_march = _first_sunday(year, 3) + timedelta(days=7)
    first_sunday_november = _first_sunday(year, 11)

    dst_start_utc = second_sunday_march.replace(
        hour=10,
        minute=0,
        second=0,
        microsecond=0,
    )
    dst_end_utc = first_sunday_november.replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )
    if dst_start_utc <= value < dst_end_utc:
        return timezone(timedelta(hours=-7), name="PDT")
    return timezone(timedelta(hours=-8), name="PST")


def _to_local(
    value: datetime,
    local_timezone: str,
) -> tuple[datetime, str]:
    try:
        zone = ZoneInfo(local_timezone)
        return value.astimezone(zone), "IANA zoneinfo"
    except ZoneInfoNotFoundError:
        if local_timezone != "America/Los_Angeles":
            raise
        fallback = _pacific_offset_for_utc(value)
        return (
            value.astimezone(fallback),
            "built-in US Pacific DST fallback",
        )


def _time_basis(
    *,
    start_utc_text: str,
    end_utc_text: str,
    source_collection_year: int,
    local_timezone: str,
) -> dict[str, Any]:
    start_utc = _parse_datetime(start_utc_text)
    end_utc = _parse_datetime(end_utc_text)
    start_local, start_timezone_resolution = _to_local(
        start_utc,
        local_timezone,
    )
    end_local, end_timezone_resolution = _to_local(
        end_utc,
        local_timezone,
    )
    timezone_resolution = (
        start_timezone_resolution
        if start_timezone_resolution == end_timezone_resolution
        else (
            f"start={start_timezone_resolution}; "
            f"end={end_timezone_resolution}"
        )
    )

    boundary_crossed = (
        end_utc.year > source_collection_year
        and end_local.year == source_collection_year
    )
    if boundary_crossed:
        explanation = (
            f"The EPA source archive is the {source_collection_year} "
            "collection-year hourly product. AirData provides both local "
            "and GMT timestamps. The selected segment is evaluated in UTC, "
            f"so its final local sample at {end_local.isoformat()} appears "
            f"as {end_utc.isoformat()} in UTC. This does not imply that the "
            f"source archive contains local-year {end_utc.year} samples."
        )
    else:
        explanation = (
            "The evaluated interval is reported in UTC. Local timestamps "
            f"are also recorded using {local_timezone} for interpretation."
        )

    return {
        "source_collection_year": source_collection_year,
        "evaluation_timestamp_basis": "UTC",
        "local_timezone": local_timezone,
        "timezone_resolution": timezone_resolution,
        "segment_start_utc": start_utc.isoformat(),
        "segment_end_utc": end_utc.isoformat(),
        "segment_start_local": start_local.isoformat(),
        "segment_end_local": end_local.isoformat(),
        "utc_year_boundary_crossed": boundary_crossed,
        "explanation": explanation,
        "scientific_basis": (
            "EPA AirData hourly files include Date Local, Time Local, "
            "Date GMT and Time GMT fields. The release uses GMT values "
            "for chronological evaluation and preserves the local-time "
            "interpretation in this metadata record."
        ),
    }


def _description(
    *,
    title: str,
    geography: dict[str, str],
    station_id: str,
    rows: int,
    time_basis: dict[str, Any],
) -> str:
    return (
        f"{title}. This reviewed candidate research release contains a "
        "reproducible station-level PM2.5 forecasting benchmark derived "
        "from the official US EPA AirData 2025 hourly parameter 88101 "
        f"product. Rows for {geography['county_name']} County, "
        f"{geography['state_name']} were filtered locally and monitoring "
        f"station {station_id} was selected by a declared temporal-"
        f"continuity rule. The evaluated segment contains {rows} hourly "
        f"rows from {time_basis['segment_start_utc']} through "
        f"{time_basis['segment_end_utc']}. "
        f"{time_basis['explanation']} The archive includes canonical "
        "input data, complete model metrics, uncertainty results, tables, "
        "SVG figures, HTML and Markdown reports, source provenance, "
        "environment metadata, checksums and exact reproduction "
        "instructions. This is research software output, not an official "
        "warning service, medical product, personal-exposure estimate or "
        "countywide causal analysis."
    )


def _citation_cff(
    *,
    title: str,
    version: str,
    release_date: str,
    description: str,
    keywords: list[str],
) -> str:
    safe_title = title.replace('"', "'")
    safe_description = description.replace('"', "'")
    lines = [
        "cff-version: 1.2.0",
        (
            'message: "If you use this reviewed experiment archive, '
            'cite this dataset release and the HeatSafe software repository."'
        ),
        f'title: "{safe_title}"',
        "type: dataset",
        f'version: "{version}"',
        f'date-released: "{release_date}"',
        f'abstract: "{safe_description}"',
        "authors:",
        '  - family-names: "Kowsari"',
        '    given-names: "Faramarz"',
        f'    orcid: "https://orcid.org/{CREATOR_ORCID}"',
        f'repository-code: "{REPOSITORY_URL}"',
        f'url: "{PROJECT_URL}"',
        'license: "CC-BY-4.0"',
        "keywords:",
    ]
    lines.extend(f'  - "{item}"' for item in keywords)
    return "\n".join(lines) + "\n"


def _zenodo_metadata(
    *,
    title: str,
    version: str,
    release_date: str,
    description: str,
    keywords: list[str],
    geography: dict[str, str],
    time_basis: dict[str, Any],
) -> dict[str, Any]:
    return {
        "title": title,
        "upload_type": "dataset",
        "description": description,
        "creators": [
            {
                "name": "Kowsari, Faramarz",
                "orcid": CREATOR_ORCID,
            }
        ],
        "publication_date": release_date,
        "version": version,
        "access_right": "open",
        "license": "cc-by-4.0",
        "keywords": keywords,
        "locations": [
            {
                "place": (
                    f"{geography['county_name']} County, "
                    f"{geography['state_name']}, United States"
                )
            }
        ],
        "dates": [
            {
                "start": str(time_basis["segment_start_utc"]),
                "end": str(time_basis["segment_end_utc"]),
                "type": "Collected",
                "description": (
                    "Chronological evaluation interval in UTC; local-time "
                    "equivalents are recorded in metadata/time-basis.json."
                ),
            }
        ],
        "related_identifiers": [
            {
                "identifier": REPOSITORY_URL,
                "relation": "isSupplementTo",
                "resource_type": "software",
            },
            {
                "identifier": PROJECT_URL,
                "relation": "isDocumentedBy",
                "resource_type": "publication-technicalnote",
            },
        ],
        "notes": (
            "Final harmonized reviewed-candidate metadata. Inspect "
            "REVIEW_CHECKLIST.md, PUBLICATION_LIMITATIONS.md, identifier "
            "crosswalk, time-basis record, provenance and checksums before "
            "publishing. No DOI has been minted by this build."
        ),
    }


def _datacite_metadata(
    *,
    title: str,
    release_date: str,
    description: str,
    keywords: list[str],
    geography: dict[str, str],
    time_basis: dict[str, Any],
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
                                    f"https://orcid.org/{CREATOR_ORCID}"
                                ),
                                "nameIdentifierScheme": "ORCID",
                                "schemeUri": "https://orcid.org",
                            }
                        ],
                    }
                ],
                "titles": [{"title": title}],
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
                "subjects": [{"subject": item} for item in keywords],
                "dates": [
                    {
                        "date": (
                            f"{time_basis['segment_start_utc']}/"
                            f"{time_basis['segment_end_utc']}"
                        ),
                        "dateType": "Collected",
                    }
                ],
                "geoLocations": [
                    {
                        "geoLocationPlace": (
                            f"{geography['county_name']} County, "
                            f"{geography['state_name']}, United States"
                        )
                    }
                ],
                "url": REPOSITORY_URL,
                "rightsList": [
                    {
                        "rights": (
                            "Creative Commons Attribution 4.0 International"
                        ),
                        "rightsUri": (
                            "https://creativecommons.org/licenses/by/4.0/"
                        ),
                        "rightsIdentifier": "CC-BY-4.0",
                        "rightsIdentifierScheme": "SPDX",
                    }
                ],
                "relatedIdentifiers": [
                    {
                        "relatedIdentifier": REPOSITORY_URL,
                        "relatedIdentifierType": "URL",
                        "relationType": "IsSupplementTo",
                        "resourceTypeGeneral": "Software",
                    }
                ],
            },
        }
    }


def _best_by_horizon(summary: dict[str, Any]) -> dict[str, str]:
    raw = summary.get("best_by_horizon")
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in sorted(
            raw.items(),
            key=lambda item: int(str(item[0])),
        )
    }


def _summary_html(summary: dict[str, Any]) -> str:
    geography = summary["selected_geography"]
    time_basis = summary["time_basis"]
    best = summary["best_by_horizon"]
    best_rows = "".join(
        "<tr><td>"
        + html.escape(str(horizon))
        + " h</td><td>"
        + html.escape(str(model))
        + "</td></tr>"
        for horizon, model in best.items()
    ) or "<tr><td colspan='2'>Not available</td></tr>"
    limitations = "".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in summary["limitations"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(summary['title'])}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f7fa;color:#172033}}
main{{max-width:1040px;margin:0 auto;padding:40px 24px 64px}}
.hero,.card{{background:#fff;border:1px solid #dbe3ec;border-radius:18px;padding:28px;margin-bottom:20px}}
h1{{font-size:2rem;margin:0 0 12px}} h2{{margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}
.metric{{background:#f3f7fb;border-radius:14px;padding:16px}}
.metric strong{{display:block;font-size:1.2rem;margin-bottom:6px;overflow-wrap:anywhere}}
table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;border-bottom:1px solid #e4e9ef;padding:10px}}
.badge{{display:inline-block;background:#e9f7ef;color:#176b3a;padding:6px 10px;border-radius:999px;font-weight:700}}
.warning{{background:#fff8e6;border-left:4px solid #d49b00;padding:14px 16px}}
.info{{background:#eef7ff;border-left:4px solid #1683c4;padding:14px 16px}}
code{{background:#edf1f5;padding:2px 6px;border-radius:5px;overflow-wrap:anywhere}}
</style>
</head>
<body><main>
<section class="hero">
<span class="badge">Final metadata harmonized — reviewed candidate — no DOI minted</span>
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
<h2>Canonical identifiers</h2>
<p><strong>Public release ID</strong><br><code>{html.escape(summary['release_id'])}</code></p>
<p><strong>Public experiment ID</strong><br><code>{html.escape(summary['public_experiment_id'])}</code></p>
<p><strong>Source execution ID preserved in provenance</strong><br><code>{html.escape(summary['source_execution_id'])}</code></p>
</section>
<section class="card">
<h2>Evaluated interval</h2>
<p><strong>UTC:</strong> <code>{html.escape(str(time_basis['segment_start_utc']))}</code>
through <code>{html.escape(str(time_basis['segment_end_utc']))}</code></p>
<p><strong>Local ({html.escape(str(time_basis['local_timezone']))}):</strong>
<code>{html.escape(str(time_basis['segment_start_local']))}</code>
through <code>{html.escape(str(time_basis['segment_end_local']))}</code></p>
<div class="info">{html.escape(str(time_basis['explanation']))}</div>
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
<div class="warning">Complete the publication checklist before creating a GitHub release or publishing on Zenodo.</div>
</section>
<section class="card">
<h2>Key files</h2>
<p><a href="experiment/report/report.html">Harmonized full HTML report</a></p>
<p><a href="metadata/identifier-crosswalk.json">Identifier crosswalk</a></p>
<p><a href="metadata/time-basis.json">UTC and local-time basis</a></p>
<p><a href="metadata/zenodo-deposition.json">Zenodo deposition metadata</a></p>
<p><a href="REVIEW_CHECKLIST.md">Publication review checklist</a></p>
<p><a href="checksums.sha256">SHA-256 checksums</a></p>
</section>
</main></body></html>
"""


def _backup_public_metadata(output: Path) -> None:
    backup = output / "provenance/pre-harmonization"
    candidates = (
        "release-summary.json",
        "release-summary.html",
        "README.md",
        "RELEASE_NOTES.md",
        "REVIEW_CHECKLIST.md",
        "PUBLICATION_LIMITATIONS.md",
        "metadata/CITATION.cff",
        "metadata/zenodo-deposition.json",
        "metadata/zenodo-github-template.json",
        "metadata/datacite-metadata.json",
        "metadata/release-manifest.json",
        "experiment/report/report.html",
        "experiment/report/report.md",
    )
    for relative in candidates:
        source = output / relative
        if source.is_file():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def _harmonize_report(
    output: Path,
    *,
    public_experiment_id: str,
    source_execution_id: str,
    title: str,
    time_basis: dict[str, Any],
) -> None:
    html_path = output / "experiment/report/report.html"
    if html_path.is_file():
        text = html_path.read_text(encoding="utf-8")
        text = text.replace(source_execution_id, public_experiment_id)
        marker = "<!-- HEATSAFE_FINAL_METADATA_HARMONIZATION_V1 -->"
        note = (
            marker
            + '<aside style="max-width:1040px;margin:18px auto;padding:16px;'
            'border:1px solid #b8d8eb;border-left:5px solid #1683c4;'
            'border-radius:12px;background:#eef7ff;font-family:system-ui">'
            "<strong>Final metadata harmonization</strong><br>"
            f"Public experiment ID: <code>{html.escape(public_experiment_id)}</code><br>"
            f"Source execution ID preserved in provenance: "
            f"<code>{html.escape(source_execution_id)}</code><br>"
            f"{html.escape(str(time_basis['explanation']))}"
            "</aside>"
        )
        if marker not in text:
            if "<body>" in text:
                text = text.replace("<body>", "<body>" + note, 1)
            else:
                text = note + text
        html_path.write_text(text, encoding="utf-8")

    markdown_path = output / "experiment/report/report.md"
    if markdown_path.is_file():
        text = markdown_path.read_text(encoding="utf-8")
        text = text.replace(source_execution_id, public_experiment_id)
        marker = "<!-- HEATSAFE_FINAL_METADATA_HARMONIZATION_V1 -->"
        note = (
            marker
            + "\n\n## Final metadata harmonization\n\n"
            f"- Public title: **{title}**\n"
            f"- Public experiment ID: `{public_experiment_id}`\n"
            f"- Source execution ID preserved in provenance: "
            f"`{source_execution_id}`\n"
            f"- Time-basis explanation: {time_basis['explanation']}\n\n"
        )
        if marker not in text:
            text = note + text
        markdown_path.write_text(text, encoding="utf-8")


def verify_harmonized_release(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    base = verify_reviewed_release(root)
    failures = [str(item) for item in base.get("failures", [])]

    required = (
        "metadata/identifier-crosswalk.json",
        "metadata/time-basis.json",
        "metadata/final-publication-metadata.json",
        "provenance/pre-harmonization/release-summary.json",
        "experiment/report/report.html",
    )
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing harmonization artifact: {relative}")

    if (root / "release-summary.json").is_file():
        summary = _read_json(root / "release-summary.json")
        if summary.get("release_id") != DEFAULT_RELEASE_ID:
            failures.append("Canonical release ID is not installed")
        if (
            summary.get("public_experiment_id")
            != DEFAULT_PUBLIC_EXPERIMENT_ID
        ):
            failures.append("Canonical public experiment ID is not installed")
        selected = summary.get("selected_geography")
        if not isinstance(selected, dict) or not selected.get("county_name"):
            failures.append("Selected geography is missing")
        if summary.get("doi_minted") is not False:
            failures.append("DOI state must remain false")
        time_basis = summary.get("time_basis")
        if not isinstance(time_basis, dict):
            failures.append("Time-basis metadata is missing")
        elif (
            time_basis.get("utc_year_boundary_crossed") is True
            and str(time_basis.get("segment_end_local", ""))[:4] != "2025"
        ):
            failures.append(
                "UTC year-boundary explanation is inconsistent"
            )

    report_path = root / "experiment/report/report.html"
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        if DEFAULT_PUBLIC_EXPERIMENT_ID not in report:
            failures.append("Public experiment ID is absent from report")
        if "Final metadata harmonization" not in report:
            failures.append("Report harmonization note is absent")

    for path_name in (
        "metadata/CITATION.cff",
        "metadata/zenodo-github-template.json",
        "metadata/datacite-metadata.json",
    ):
        path_obj = root / path_name
        if path_obj.is_file():
            text = path_obj.read_text(encoding="utf-8")
            if "Alameda County" in text:
                failures.append(
                    f"Stale Alameda public metadata remains in {path_name}"
                )

    return {
        "valid": not failures,
        "checked_files": base.get("checked_files", 0),
        "failures": failures,
        "base_release_verification": base,
    }


def harmonize_reviewed_release(
    source_release: str | Path,
    *,
    workspace: str | Path,
    output_directory: str | Path,
    release_id: str = DEFAULT_RELEASE_ID,
    version: str = DEFAULT_VERSION,
    public_experiment_id: str = DEFAULT_PUBLIC_EXPERIMENT_ID,
    source_collection_year: int = 2025,
    local_timezone: str = DEFAULT_LOCAL_TIMEZONE,
    overwrite: bool = False,
) -> dict[str, Any]:
    source_root = Path(source_release)
    workspace_root = Path(workspace)
    output = Path(output_directory)

    source_verification = verify_reviewed_release(source_root)
    if not bool(source_verification.get("valid")):
        raise RuntimeError(
            "Source reviewed release failed verification: "
            + "; ".join(
                str(item)
                for item in source_verification.get("failures", [])
            )
        )

    workspace_verification = verify_real_official_experiment(
        workspace_root
    )
    if not bool(workspace_verification.get("valid")):
        raise RuntimeError(
            "Source experiment failed verification: "
            + "; ".join(
                str(item)
                for item in workspace_verification.get("failures", [])
            )
        )

    _prepare_output(source_root, output, overwrite=overwrite)
    _backup_public_metadata(output)

    bulk_report = _read_json(
        workspace_root / "raw-source/bulk-source-report.json"
    )
    station_report = _read_json(
        workspace_root / "prepared/station-selection-report.json"
    )
    source_manifest = _read_json(
        workspace_root / "real-official-experiment-manifest.json"
    )
    old_summary = _read_json(output / "release-summary.json")

    geography = _selected_geography(bulk_report)
    station_id = _selected_station(station_report, source_manifest)
    source_execution_id = _source_execution_id(
        output,
        source_manifest,
    )
    rows = int(station_report.get("selected_segment_rows", 0))
    start_utc = str(
        station_report.get("selected_segment_start_utc", "unknown")
    )
    end_utc = str(
        station_report.get("selected_segment_end_utc", "unknown")
    )
    if "unknown" in {start_utc, end_utc}:
        raise ValueError("Selected segment timestamps are missing")

    time_basis = _time_basis(
        start_utc_text=start_utc,
        end_utc_text=end_utc,
        source_collection_year=source_collection_year,
        local_timezone=local_timezone,
    )
    title = _public_title(geography)
    keywords = _keywords(geography)
    description = _description(
        title=title,
        geography=geography,
        station_id=station_id,
        rows=rows,
        time_basis=time_basis,
    )
    release_date = datetime.now(UTC).date().isoformat()

    limitations = [
        "Monitoring-site measurements are not equivalent to personal or population exposure.",
        "The selected station represents one monitoring location and not an entire county.",
        "The station was selected for temporal continuity, not geographic representativeness.",
        "Instrument, method, POC and sampling changes can affect comparability.",
        "The archive is not an official warning service or medical decision product.",
        "Results apply only to the declared source ZIP, selected segment, split protocol and software revision.",
        "EPA method metadata and the PM2.5 pre-generated-file advisory require review before publication claims.",
        "The source archive is labeled by collection year while chronological evaluation uses UTC; local and UTC interval endpoints must be read together.",
    ]

    summary = dict(old_summary)
    summary.update(
        {
            "release_id": release_id,
            "release_version": version,
            "release_status": "final-metadata-harmonized-reviewed-candidate",
            "doi_minted": False,
            "title": title,
            "description": description,
            "public_experiment_id": public_experiment_id,
            "source_execution_id": source_execution_id,
            "identifier_harmonization": {
                "public_release_id": release_id,
                "public_experiment_id": public_experiment_id,
                "source_execution_id": source_execution_id,
                "source_execution_id_preserved": True,
            },
            "selected_geography": geography,
            "selected_station": station_id,
            "selected_segment_rows": rows,
            "segment_start_utc": time_basis["segment_start_utc"],
            "segment_end_utc": time_basis["segment_end_utc"],
            "time_basis": time_basis,
            "best_by_horizon": _best_by_horizon(old_summary),
            "keywords": keywords,
            "limitations": limitations,
            "publication_decision": (
                "Final human review is required before GitHub Release, "
                "Zenodo publication or DOI minting."
            ),
        }
    )

    metadata = output / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)

    identifier_crosswalk = {
        "public_release_id": release_id,
        "public_experiment_id": public_experiment_id,
        "source_execution_id": source_execution_id,
        "source_execution_id_preserved": True,
        "requested_geography": bulk_report.get("requested_geography"),
        "selected_geography": geography,
        "geography_fallback_used": bool(
            bulk_report.get("geography_fallback_used", False)
        ),
        "explanation": (
            "The public identifiers describe the actual California "
            "AirData release. The source execution identifier is retained "
            "unchanged in provenance because it records the historical "
            "execution plan that originally requested Alameda County."
        ),
    }
    _write_json(
        metadata / "identifier-crosswalk.json",
        identifier_crosswalk,
    )
    _write_json(metadata / "time-basis.json", time_basis)

    final_publication_metadata = {
        "title": title,
        "release_id": release_id,
        "public_experiment_id": public_experiment_id,
        "source_execution_id": source_execution_id,
        "version": version,
        "publication_date_prepared": release_date,
        "doi": None,
        "doi_minted": False,
        "creator": {
            "name": "Faramarz Kowsari",
            "orcid": CREATOR_ORCID,
        },
        "selected_geography": geography,
        "selected_station": station_id,
        "time_basis": time_basis,
        "keywords": keywords,
        "license": "CC-BY-4.0",
        "repository": REPOSITORY_URL,
        "project_url": PROJECT_URL,
    }
    _write_json(
        metadata / "final-publication-metadata.json",
        final_publication_metadata,
    )

    zenodo = _zenodo_metadata(
        title=title,
        version=version,
        release_date=release_date,
        description=description,
        keywords=keywords,
        geography=geography,
        time_basis=time_basis,
    )
    _write_json(
        metadata / "zenodo-deposition.json",
        {"metadata": zenodo},
    )
    _write_json(
        metadata / "zenodo-github-template.json",
        zenodo,
    )
    _write_json(
        metadata / "datacite-metadata.json",
        _datacite_metadata(
            title=title,
            release_date=release_date,
            description=description,
            keywords=keywords,
            geography=geography,
            time_basis=time_basis,
        ),
    )
    (metadata / "CITATION.cff").write_text(
        _citation_cff(
            title=title,
            version=version,
            release_date=release_date,
            description=description,
            keywords=keywords,
        ),
        encoding="utf-8",
    )

    _write_json(output / "release-summary.json", summary)
    (output / "release-summary.html").write_text(
        _summary_html(summary),
        encoding="utf-8",
    )

    _harmonize_report(
        output,
        public_experiment_id=public_experiment_id,
        source_execution_id=source_execution_id,
        title=title,
        time_basis=time_basis,
    )

    run_summary_path = output / "experiment/run-summary.json"
    if run_summary_path.is_file():
        run_summary = _read_json(run_summary_path)
        run_summary["source_experiment_id"] = source_execution_id
        run_summary["public_release_experiment_id"] = (
            public_experiment_id
        )
        run_summary["metadata_harmonization"] = {
            "status": "final",
            "identifier_crosswalk": (
                "../../metadata/identifier-crosswalk.json"
            ),
            "time_basis": "../../metadata/time-basis.json",
        }
        _write_json(run_summary_path, run_summary)

    release_notes = f"""# Release Notes

## {title}

**Version:** {version}  
**Status:** Final metadata harmonized; reviewed candidate; no DOI minted  
**Public release ID:** `{release_id}`  
**Public experiment ID:** `{public_experiment_id}`  
**Source execution ID:** `{source_execution_id}`  
**Release date prepared:** {release_date}

This archive packages the first verified official-source HeatSafe PM2.5
forecasting experiment for final human review.

## Data identity

- Official product: US EPA AirData hourly PM2.5 FRM/FEM Mass, parameter 88101.
- Selected geography: {geography['county_name']} County, {geography['state_name']}.
- Selected station: `{station_id}`.
- Evaluated UTC interval: `{time_basis['segment_start_utc']}` through `{time_basis['segment_end_utc']}`.
- Local interval ({local_timezone}): `{time_basis['segment_start_local']}` through `{time_basis['segment_end_local']}`.
- Hourly rows: {rows}.
- Source ZIP SHA-256: `{summary['bulk_zip_sha256']}`.

## UTC year-boundary explanation

{time_basis['explanation']}

## Identifier policy

The public release and experiment identifiers describe the actual California
AirData result. The historical source execution identifier remains unchanged
inside provenance because it records the original execution plan.

## Important

This package is not evidence of personal exposure, countywide conditions,
causal effects, clinical risk or official warning authority. Complete
`REVIEW_CHECKLIST.md` before publication.
"""
    (output / "RELEASE_NOTES.md").write_text(
        release_notes,
        encoding="utf-8",
    )

    checklist = f"""# Publication Review Checklist

Do not publish or mint a DOI until every required item is checked.

## Scientific identity

- [ ] Confirm selected geography: {geography['county_name']} County, {geography['state_name']}.
- [ ] Confirm selected station: `{station_id}`.
- [ ] Confirm public experiment ID: `{public_experiment_id}`.
- [ ] Confirm source execution ID is preserved only as provenance: `{source_execution_id}`.
- [ ] Confirm UTC interval and local-time equivalents in `metadata/time-basis.json`.
- [ ] Confirm the source-year/UTC-year boundary explanation.
- [ ] Confirm the official bulk ZIP SHA-256.
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

- [ ] Run harmonized-release verification and confirm every checksum.
- [ ] Open the harmonized HTML report.
- [ ] Confirm canonical input and normalized specification are present.
- [ ] Confirm the repository commit is publicly accessible.
- [ ] Compare identifier crosswalk with source provenance.

## Metadata and publication

- [ ] Review `metadata/CITATION.cff`.
- [ ] Review `metadata/zenodo-deposition.json`.
- [ ] Review `metadata/datacite-metadata.json`.
- [ ] Review `metadata/final-publication-metadata.json`.
- [ ] Confirm DOI is still absent before publication.
- [ ] Add the DOI only after Zenodo creates it.
- [ ] Create a GitHub tag and release only after final approval.
- [ ] Preserve the published ZIP without post-publication modification.
"""
    (output / "REVIEW_CHECKLIST.md").write_text(
        checklist,
        encoding="utf-8",
    )

    limitation_lines = "\n".join(f"- {item}" for item in limitations)
    (output / "PUBLICATION_LIMITATIONS.md").write_text(
        "# Publication Limitations\n\n"
        + limitation_lines
        + "\n\n## Time-basis interpretation\n\n"
        + str(time_basis["explanation"])
        + "\n\n## Identifier interpretation\n\n"
        "The public IDs describe the final release. The source execution "
        "ID is a historical provenance identifier and must not be used as "
        "the public title, keyword or release identity.\n",
        encoding="utf-8",
    )

    readme = f"""# Final Metadata-Harmonized Reviewed Candidate

**{title}**

Public release ID: `{release_id}`  
Public experiment ID: `{public_experiment_id}`  
Source execution ID retained in provenance: `{source_execution_id}`

Start with:

1. `release-summary.html`
2. `experiment/report/report.html`
3. `metadata/identifier-crosswalk.json`
4. `metadata/time-basis.json`
5. `REVIEW_CHECKLIST.md`
6. `PUBLICATION_LIMITATIONS.md`
7. `checksums.sha256`

## Verify

```bash
heatsafe-release-review verify-harmonized .
```

## Publication status

No GitHub Release, Zenodo deposition or DOI is created automatically.
This remains a reviewed candidate until every checklist item is approved.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    release_manifest = {
        "release_id": release_id,
        "public_experiment_id": public_experiment_id,
        "source_execution_id": source_execution_id,
        "version": version,
        "status": "final-metadata-harmonized-reviewed-candidate",
        "doi": None,
        "selected_geography": geography,
        "selected_station": station_id,
        "time_basis": time_basis,
        "source_release": str(source_root.resolve()),
        "source_workspace": str(workspace_root.resolve()),
        "source_release_verification": source_verification,
        "source_experiment_verification": workspace_verification,
        "source_experiment_manifest_sha256": _sha256(
            workspace_root / "real-official-experiment-manifest.json"
        ),
        "source_bulk_report_sha256": _sha256(
            workspace_root / "raw-source/bulk-source-report.json"
        ),
        "source_station_report_sha256": _sha256(
            workspace_root / "prepared/station-selection-report.json"
        ),
        "publication_gate": {
            "review_checklist_required": True,
            "doi_minted": False,
            "automatic_publish": False,
            "metadata_harmonized": True,
        },
    }
    _write_json(
        metadata / "release-manifest.json",
        release_manifest,
    )

    checksums = _write_checksums(output)
    verification = verify_harmonized_release(output)
    if not verification["valid"]:
        raise RuntimeError(
            "Harmonized release failed verification: "
            + "; ".join(str(item) for item in verification["failures"])
        )

    _write_json(
        output / "harmonization-verification.json",
        verification,
    )
    checksums = _write_checksums(output)
    verification = verify_harmonized_release(output)
    if not verification["valid"]:
        raise RuntimeError(
            "Harmonized release failed final verification: "
            + "; ".join(str(item) for item in verification["failures"])
        )

    archive = output.with_name(f"{release_id}-v{version}.zip")
    _deterministic_zip(output, archive)

    return {
        "release_directory": str(output),
        "release_archive": str(archive),
        "release_summary_html": str(
            output / "release-summary.html"
        ),
        "release_summary_json": str(
            output / "release-summary.json"
        ),
        "identifier_crosswalk": str(
            metadata / "identifier-crosswalk.json"
        ),
        "time_basis": str(metadata / "time-basis.json"),
        "citation_cff": str(metadata / "CITATION.cff"),
        "zenodo_metadata": str(
            metadata / "zenodo-deposition.json"
        ),
        "checksums": str(checksums),
        "verification": verification,
    }
