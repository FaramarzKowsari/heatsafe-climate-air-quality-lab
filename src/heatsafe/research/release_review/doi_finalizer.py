from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from heatsafe.research.release_review.harmonizer import (
    verify_harmonized_release,
)
from heatsafe.research.release_review.publication import (
    verify_publication_handoff,
)


DEFAULT_RESERVED_DOI = "10.5281/zenodo.21710054"
DEFAULT_VERSION = "0.1.0"
DOI_PATTERN = re.compile(r"^10\.5281/zenodo\.\d+$")
DOI_URL_PREFIX = "https://doi.org/"


def normalize_reserved_doi(value: str) -> str:
    normalized = value.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "doi:",
        "DOI:",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break
    if not DOI_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Reserved DOI must match 10.5281/zenodo.<record-number>"
        )
    return normalized


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_release_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "checksums.sha256"
            and path.suffix.lower() != ".zip"
        ):
            yield path


def _write_release_checksums(root: Path) -> Path:
    output = root / "checksums.sha256"
    lines = [
        f"{_sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in _iter_release_files(root)
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _iter_handoff_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "HANDOFF_CHECKSUMS.sha256"
        ):
            yield path


def _write_handoff_checksums(root: Path) -> Path:
    output = root / "HANDOFF_CHECKSUMS.sha256"
    lines = [
        f"{_sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in _iter_handoff_files(root)
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _prepare_copy(
    source: Path,
    output: Path,
    *,
    overwrite: bool,
) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    if output.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output already exists: {output}. Use --overwrite."
            )
        resolved = output.resolve()
        if resolved == Path.cwd().resolve() or len(resolved.parts) < 3:
            raise ValueError(f"Refusing to remove unsafe path: {resolved}")
        shutil.rmtree(output)
    shutil.copytree(source, output)


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


def _inject_cff_doi(path: Path, doi: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith("doi:"):
            lines[index] = f'doi: "{doi}"'
            replaced = True
            break
    if not replaced:
        insert_at = 0
        for index, line in enumerate(lines):
            if line.startswith("version:"):
                insert_at = index + 1
                break
        lines.insert(insert_at, f'doi: "{doi}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_markdown_doi(
    path: Path,
    *,
    doi: str,
    heading: str = "Reserved DOI",
) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "<!-- HEATSAFE_RESERVED_DOI_09_1 -->"
    block = (
        f"\n\n{marker}\n"
        f"## {heading}\n\n"
        f"- DOI: `{doi}`\n"
        f"- DOI URL: `{DOI_URL_PREFIX}{doi}`\n"
        "- Status: reserved in a Zenodo draft; not yet registered publicly.\n"
        "- Publication remains blocked until the Zenodo record is reviewed.\n"
    )
    if marker not in text:
        text = text.rstrip() + block + "\n"
    else:
        text = re.sub(
            rf"{re.escape(marker)}.*\Z",
            block.strip() + "\n",
            text,
            flags=re.DOTALL,
        )
    path.write_text(text, encoding="utf-8")


def _inject_report_banner(
    path: Path,
    *,
    doi: str,
) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    marker = "<!-- HEATSAFE_RESERVED_DOI_09_1 -->"
    banner = (
        marker
        + '<aside style="max-width:1040px;margin:18px auto;padding:16px;'
        'border:1px solid #c9b458;border-left:5px solid #a67c00;'
        'border-radius:12px;background:#fff8e1;font-family:system-ui">'
        "<strong>Reserved Zenodo DOI</strong><br>"
        f"<code>{html.escape(doi)}</code><br>"
        "This DOI is reserved in a Zenodo draft and is not registered "
        "until the record is published."
        "</aside>"
    )
    if marker not in text:
        if "<body>" in text:
            text = text.replace("<body>", "<body>" + banner, 1)
        else:
            text = banner + text
    else:
        text = re.sub(
            rf"{re.escape(marker)}<aside.*?</aside>",
            banner,
            text,
            count=1,
            flags=re.DOTALL,
        )
    path.write_text(text, encoding="utf-8")


def _update_release_summary_html(
    path: Path,
    *,
    doi: str,
) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    marker = "<!-- HEATSAFE_RESERVED_DOI_09_1 -->"
    block = (
        marker
        + '<section class="card">'
        "<h2>Reserved Zenodo DOI</h2>"
        f"<p><code>{html.escape(doi)}</code></p>"
        f'<p><a href="{DOI_URL_PREFIX}{html.escape(doi)}">'
        f"{DOI_URL_PREFIX}{html.escape(doi)}</a></p>"
        '<div class="warning">The DOI is reserved but not registered '
        "until the Zenodo draft is published.</div>"
        "</section>"
    )
    if marker not in text:
        if "</main>" in text:
            text = text.replace("</main>", block + "</main>", 1)
        else:
            text += block
    path.write_text(text, encoding="utf-8")


def _update_datacite(path: Path, doi: str) -> None:
    payload = _read_json(path)
    data = payload.setdefault("data", {})
    if not isinstance(data, dict):
        raise ValueError("DataCite metadata has invalid data object")
    attributes = data.setdefault("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError(
            "DataCite metadata has invalid attributes object"
        )
    attributes["doi"] = doi
    attributes["event"] = "publish"
    _write_json(path, payload)


def _update_zenodo_metadata(path: Path, doi: str) -> None:
    payload = _read_json(path)
    payload["reserved_doi"] = doi
    payload["reserved_doi_url"] = f"{DOI_URL_PREFIX}{doi}"
    payload["reserved_doi_status"] = (
        "reserved in draft; registration pending publication"
    )
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        notes = str(metadata.get("notes", "")).strip()
        doi_note = (
            f"Reserved DOI: {doi}. The DOI is not registered until "
            "this Zenodo draft is published."
        )
        if doi_note not in notes:
            metadata["notes"] = (
                notes + " " + doi_note
            ).strip()
    _write_json(path, payload)


def _final_release_status(
    *,
    doi: str,
    original_summary: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(original_summary)
    updated.update(
        {
            "doi": doi,
            "doi_url": f"{DOI_URL_PREFIX}{doi}",
            "doi_reserved": True,
            "doi_registered": False,
            "doi_minted": False,
            "release_status": (
                "reserved-doi-finalized-reviewed-candidate"
            ),
            "publication_decision": (
                "Review the Zenodo draft, resolve all required metadata "
                "errors, replace draft files with this DOI-aware archive, "
                "preview again, and publish only after approval."
            ),
        }
    )
    return updated


def _final_metadata_status(
    *,
    doi: str,
    original: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(original)
    updated.update(
        {
            "doi": doi,
            "doi_url": f"{DOI_URL_PREFIX}{doi}",
            "doi_reserved": True,
            "doi_registered": False,
            "doi_status": (
                "reserved in Zenodo draft; registration pending publication"
            ),
            "publication_status": "draft-review-required",
            "updated_at_utc": datetime.now(UTC).isoformat(),
        }
    )
    return updated


def _identifier_status(
    *,
    doi: str,
    original: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(original)
    updated["reserved_doi"] = doi
    updated["reserved_doi_url"] = f"{DOI_URL_PREFIX}{doi}"
    updated["reserved_doi_registered"] = False
    return updated


def _update_release_manifest(
    path: Path,
    *,
    doi: str,
) -> None:
    payload = _read_json(path)
    payload["doi"] = doi
    payload["doi_url"] = f"{DOI_URL_PREFIX}{doi}"
    payload["doi_reserved"] = True
    payload["doi_registered"] = False
    payload["status"] = (
        "reserved-doi-finalized-reviewed-candidate"
    )
    gate = payload.setdefault("publication_gate", {})
    if isinstance(gate, dict):
        gate["doi_reserved"] = True
        gate["doi_registered"] = False
        gate["automatic_publish"] = False
    _write_json(path, payload)


def verify_doi_final_release(
    path: str | Path,
    *,
    reserved_doi: str = DEFAULT_RESERVED_DOI,
) -> dict[str, Any]:
    root = Path(path)
    doi = normalize_reserved_doi(reserved_doi)
    failures: list[str] = []

    checksum_path = root / "checksums.sha256"
    checked = 0
    if not checksum_path.is_file():
        failures.append("Missing checksums.sha256")
    else:
        for line in checksum_path.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            expected, separator, relative = line.partition("  ")
            if not separator:
                failures.append(f"Malformed checksum line: {line}")
                continue
            target = root / relative
            if not target.is_file():
                failures.append(f"Missing file: {relative}")
                continue
            checked += 1
            if _sha256(target) != expected:
                failures.append(f"Checksum mismatch: {relative}")

    required = (
        "release-summary.json",
        "release-summary.html",
        "README.md",
        "RELEASE_NOTES.md",
        "metadata/CITATION.cff",
        "metadata/final-publication-metadata.json",
        "metadata/identifier-crosswalk.json",
        "metadata/zenodo-deposition.json",
        "metadata/datacite-metadata.json",
        "metadata/release-manifest.json",
        "metadata/doi-registration.json",
        "experiment/report/report.html",
    )
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing DOI-aware file: {relative}")

    summary_path = root / "release-summary.json"
    if summary_path.is_file():
        summary = _read_json(summary_path)
        if summary.get("doi") != doi:
            failures.append("Release summary DOI mismatch")
        if summary.get("doi_reserved") is not True:
            failures.append("Release summary does not mark DOI reserved")
        if summary.get("doi_registered") is not False:
            failures.append(
                "Release summary incorrectly marks DOI registered"
            )

    citation_path = root / "metadata/CITATION.cff"
    if citation_path.is_file():
        citation = citation_path.read_text(encoding="utf-8")
        if f'doi: "{doi}"' not in citation:
            failures.append("CITATION.cff lacks reserved DOI")

    datacite_path = root / "metadata/datacite-metadata.json"
    if datacite_path.is_file():
        datacite = _read_json(datacite_path)
        actual = (
            datacite.get("data", {})
            .get("attributes", {})
            .get("doi")
        )
        if actual != doi:
            failures.append("DataCite DOI mismatch")

    report_path = root / "experiment/report/report.html"
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        if doi not in report:
            failures.append("HTML report lacks reserved DOI")

    return {
        "valid": not failures,
        "reserved_doi": doi,
        "doi_registered": False,
        "checked_files": checked,
        "failures": failures,
    }


def finalize_reserved_doi_release(
    harmonized_release: str | Path,
    *,
    output_directory: str | Path,
    reserved_doi: str = DEFAULT_RESERVED_DOI,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = Path(harmonized_release)
    output = Path(output_directory)
    doi = normalize_reserved_doi(reserved_doi)

    source_verification = verify_harmonized_release(source)
    if not bool(source_verification.get("valid")):
        raise RuntimeError(
            "Source harmonized release failed verification: "
            + "; ".join(
                str(item)
                for item in source_verification.get("failures", [])
            )
        )

    _prepare_copy(source, output, overwrite=overwrite)

    summary_path = output / "release-summary.json"
    summary = _final_release_status(
        doi=doi,
        original_summary=_read_json(summary_path),
    )
    _write_json(summary_path, summary)

    final_metadata_path = (
        output / "metadata/final-publication-metadata.json"
    )
    final_metadata = _final_metadata_status(
        doi=doi,
        original=_read_json(final_metadata_path),
    )
    _write_json(final_metadata_path, final_metadata)

    crosswalk_path = output / "metadata/identifier-crosswalk.json"
    _write_json(
        crosswalk_path,
        _identifier_status(
            doi=doi,
            original=_read_json(crosswalk_path),
        ),
    )

    citation_path = output / "metadata/CITATION.cff"
    _inject_cff_doi(citation_path, doi)
    _update_zenodo_metadata(
        output / "metadata/zenodo-deposition.json",
        doi,
    )
    github_zenodo = output / "metadata/zenodo-github-template.json"
    if github_zenodo.is_file():
        github_payload = _read_json(github_zenodo)
        notes = str(github_payload.get("notes", "")).strip()
        doi_note = (
            f"Reserved DOI: {doi}. Registration is pending publication."
        )
        if doi_note not in notes:
            github_payload["notes"] = (
                notes + " " + doi_note
            ).strip()
        _write_json(github_zenodo, github_payload)

    _update_datacite(
        output / "metadata/datacite-metadata.json",
        doi,
    )
    _update_release_manifest(
        output / "metadata/release-manifest.json",
        doi=doi,
    )

    doi_registration = {
        "doi": doi,
        "doi_url": f"{DOI_URL_PREFIX}{doi}",
        "provider": "Zenodo",
        "status": "reserved-in-draft",
        "registered": False,
        "reservation_observed_at_utc": (
            datetime.now(UTC).isoformat()
        ),
        "publication_required_for_registration": True,
        "source": "user-confirmed Zenodo draft reservation",
    }
    _write_json(
        output / "metadata/doi-registration.json",
        doi_registration,
    )

    _append_markdown_doi(
        output / "README.md",
        doi=doi,
        heading="Reserved Zenodo DOI",
    )
    _append_markdown_doi(
        output / "RELEASE_NOTES.md",
        doi=doi,
        heading="Reserved Zenodo DOI",
    )
    _append_markdown_doi(
        output / "REVIEW_CHECKLIST.md",
        doi=doi,
        heading="DOI-aware publication checks",
    )
    _append_markdown_doi(
        output / "PUBLICATION_LIMITATIONS.md",
        doi=doi,
        heading="DOI registration boundary",
    )
    _update_release_summary_html(
        output / "release-summary.html",
        doi=doi,
    )
    _inject_report_banner(
        output / "experiment/report/report.html",
        doi=doi,
    )
    report_md = output / "experiment/report/report.md"
    if report_md.is_file():
        _append_markdown_doi(
            report_md,
            doi=doi,
            heading="Reserved Zenodo DOI",
        )

    _write_release_checksums(output)
    verification = verify_doi_final_release(
        output,
        reserved_doi=doi,
    )
    if not verification["valid"]:
        raise RuntimeError(
            "DOI-aware release failed verification: "
            + "; ".join(
                str(item) for item in verification["failures"]
            )
        )

    _write_json(
        output / "doi-finalization-verification.json",
        verification,
    )
    _write_release_checksums(output)
    verification = verify_doi_final_release(
        output,
        reserved_doi=doi,
    )
    if not verification["valid"]:
        raise RuntimeError(
            "DOI-aware release failed final verification: "
            + "; ".join(
                str(item) for item in verification["failures"]
            )
        )

    version = str(summary.get("release_version", DEFAULT_VERSION))
    archive = output.with_name(
        f"{summary['release_id']}-v{version}-doi-final.zip"
    )
    _deterministic_zip(output, archive)

    return {
        "release_directory": str(output),
        "release_archive": str(archive),
        "reserved_doi": doi,
        "doi_url": f"{DOI_URL_PREFIX}{doi}",
        "doi_registered": False,
        "verification": verification,
    }


def _replace_text(
    path: Path,
    replacements: dict[str, str],
) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def _doi_handoff_readiness_html(
    *,
    doi: str,
    archive_name: str,
    archive_sha256: str,
) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reserved DOI Finalization | HeatSafe Research Lab</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f4f7fa;color:#172033}}
main{{max-width:980px;margin:0 auto;padding:40px 24px 64px}}
.hero,.card{{background:#fff;border:1px solid #d9e2ec;border-radius:18px;padding:28px;margin-bottom:20px}}
.badge{{display:inline-block;background:#fff3cd;color:#7a5600;padding:6px 10px;border-radius:999px;font-weight:700}}
.ok{{background:#eaf8ef;border-left:4px solid #2e8b57;padding:14px 16px}}
.warn{{background:#fff8e6;border-left:4px solid #d49b00;padding:14px 16px}}
code{{background:#edf1f5;padding:2px 6px;border-radius:5px;overflow-wrap:anywhere}}
</style>
</head>
<body><main>
<section class="hero">
<span class="badge">Reserved DOI injected — publication still blocked</span>
<h1>Scientific Pack 09.1</h1>
<p>The reserved Zenodo DOI has been inserted into citation, publication and integrity metadata. All release checksums and the deterministic ZIP were regenerated.</p>
</section>
<section class="card">
<h2>Reserved DOI</h2>
<p><code>{html.escape(doi)}</code></p>
<p><a href="{DOI_URL_PREFIX}{html.escape(doi)}">{DOI_URL_PREFIX}{html.escape(doi)}</a></p>
<div class="warn">The DOI is not registered until the Zenodo draft is published.</div>
</section>
<section class="card">
<h2>DOI-aware archive</h2>
<p><code>{html.escape(archive_name)}</code></p>
<p>SHA-256:</p>
<p><code>{archive_sha256}</code></p>
<div class="ok">The DOI-aware release and handoff passed checksum and consistency verification.</div>
</section>
<section class="card">
<h2>Required replacement</h2>
<ol>
<li>In the existing Zenodo draft, remove the old ZIP and old SHA256SUMS file.</li>
<li>Upload the two new files from this handoff's <code>assets</code> directory.</li>
<li>Complete the three Basic information errors shown by Zenodo.</li>
<li>Save draft and Preview.</li>
<li>Do not publish until every field and file is reviewed.</li>
<li>Replace the old assets in the GitHub draft release with the new DOI-aware files.</li>
</ol>
</section>
</main></body></html>
"""


def verify_doi_final_handoff(
    path: str | Path,
    *,
    reserved_doi: str = DEFAULT_RESERVED_DOI,
) -> dict[str, Any]:
    root = Path(path)
    doi = normalize_reserved_doi(reserved_doi)
    failures: list[str] = []
    checked = 0

    checksum_path = root / "HANDOFF_CHECKSUMS.sha256"
    if not checksum_path.is_file():
        failures.append("Missing HANDOFF_CHECKSUMS.sha256")
    else:
        for line in checksum_path.read_text(
            encoding="utf-8"
        ).splitlines():
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
        "DOI_FINALIZATION_READINESS.html",
        "DOI_FINALIZATION_HANDOFF.json",
        "ZENODO_REPLACE_FILES_09_1.md",
        "GITHUB_REPLACE_ASSETS_09_1.md",
        "GITHUB_RELEASE_NOTES.md",
        "RESERVED_DOI.txt",
        "assets/SHA256SUMS.txt",
        "assets/CITATION.cff",
        "assets/final-publication-metadata.json",
        "assets/identifier-crosswalk.json",
        "assets/time-basis.json",
        "assets/zenodo-deposition.json",
    )
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing DOI handoff file: {relative}")

    handoff_path = root / "DOI_FINALIZATION_HANDOFF.json"
    if handoff_path.is_file():
        handoff = _read_json(handoff_path)
        if handoff.get("reserved_doi") != doi:
            failures.append("DOI handoff mismatch")
        if handoff.get("doi_registered") is not False:
            failures.append("DOI handoff incorrectly marks registration")
        if handoff.get("publishing_enabled") is not False:
            failures.append("Publishing must remain disabled")

    citation_path = root / "assets/CITATION.cff"
    if citation_path.is_file():
        if f'doi: "{doi}"' not in citation_path.read_text(
            encoding="utf-8"
        ):
            failures.append("Handoff CITATION.cff lacks DOI")

    return {
        "valid": not failures,
        "reserved_doi": doi,
        "doi_registered": False,
        "checked_files": checked,
        "failures": failures,
    }


def finalize_reserved_doi_handoff(
    publication_handoff: str | Path,
    *,
    doi_final_release: str | Path,
    output_directory: str | Path,
    reserved_doi: str = DEFAULT_RESERVED_DOI,
    overwrite: bool = False,
) -> dict[str, Any]:
    source_handoff = Path(publication_handoff)
    release_root = Path(doi_final_release)
    output = Path(output_directory)
    doi = normalize_reserved_doi(reserved_doi)

    source_verification = verify_publication_handoff(source_handoff)
    if not bool(source_verification.get("valid")):
        raise RuntimeError(
            "Source publication handoff failed verification: "
            + "; ".join(
                str(item)
                for item in source_verification.get("failures", [])
            )
        )
    release_verification = verify_doi_final_release(
        release_root,
        reserved_doi=doi,
    )
    if not release_verification["valid"]:
        raise RuntimeError(
            "DOI-aware release failed verification: "
            + "; ".join(
                str(item)
                for item in release_verification["failures"]
            )
        )

    _prepare_copy(
        source_handoff,
        output,
        overwrite=overwrite,
    )

    assets = output / "assets"
    for path in assets.iterdir():
        if path.is_file():
            path.unlink()

    summary = _read_json(release_root / "release-summary.json")
    version = str(summary.get("release_version", DEFAULT_VERSION))
    archive = release_root.with_name(
        f"{summary['release_id']}-v{version}-doi-final.zip"
    )
    if not archive.is_file():
        raise FileNotFoundError(archive)

    shutil.copy2(archive, assets / archive.name)
    for relative in (
        "metadata/CITATION.cff",
        "metadata/final-publication-metadata.json",
        "metadata/identifier-crosswalk.json",
        "metadata/time-basis.json",
        "metadata/zenodo-deposition.json",
        "release-summary.json",
        "metadata/doi-registration.json",
    ):
        source = release_root / relative
        shutil.copy2(source, assets / source.name)

    archive_sha = _sha256(assets / archive.name)
    sha_lines = [
        f"{archive_sha}  {archive.name}",
    ]
    for name in (
        "CITATION.cff",
        "final-publication-metadata.json",
        "identifier-crosswalk.json",
        "time-basis.json",
        "zenodo-deposition.json",
        "release-summary.json",
        "doi-registration.json",
    ):
        target = assets / name
        sha_lines.append(f"{_sha256(target)}  {name}")
    (assets / "SHA256SUMS.txt").write_text(
        "\n".join(sha_lines) + "\n",
        encoding="utf-8",
    )

    notes_path = output / "GITHUB_RELEASE_NOTES.md"
    notes = notes_path.read_text(encoding="utf-8")
    notes = notes.replace(
        "**DOI:** Pending Zenodo draft review and publication",
        f"**Reserved DOI:** `{doi}`  \n"
        "**DOI status:** Reserved in Zenodo draft; registration pending publication",
    )
    old_archive_pattern = re.compile(
        r"epa-airdata-california-pm25-2025-first-real-reviewed"
        r"-v0\.1\.0(?:-doi-final)?\.zip"
    )
    notes = old_archive_pattern.sub(archive.name, notes)
    notes = re.sub(
        r"Archive SHA-256:\n\n```text\n[0-9a-f]{64}\n```",
        f"Archive SHA-256:\n\n```text\n{archive_sha}\n```",
        notes,
    )
    if doi not in notes:
        notes += (
            "\n\n## Reserved Zenodo DOI\n\n"
            f"- `{doi}`\n"
            f"- `{DOI_URL_PREFIX}{doi}`\n"
            "- Registration occurs only when the Zenodo draft is published.\n"
        )
    notes_path.write_text(notes, encoding="utf-8")

    zenodo_guide = f"""# Replace Files in the Existing Zenodo Draft

Reserved DOI:

```text
{doi}
```

Draft URL currently used:

```text
https://zenodo.org/uploads/21710054
```

## Do not create another upload

Keep the existing Zenodo draft so the reserved DOI remains attached to it.

## Replace the old files

Delete only the two old uploaded files from the draft:

1. the old release ZIP;
2. the old `SHA256SUMS.txt`.

Then upload these two new files from this handoff's `assets` directory:

1. `{archive.name}`
2. `SHA256SUMS.txt`

New archive SHA-256:

```text
{archive_sha}
```

## Complete the form

The screenshot showed three errors in Basic information. Complete all required
fields, then press **Save draft** and **Preview**.

Confirm:

- Resource type: Dataset
- Title matches `GITHUB_RELEASE_NOTES.md`
- Creator: Faramarz Kowsari
- ORCID: 0000-0003-1692-0453
- License: CC-BY-4.0
- DOI choice remains: No, I need one
- Reserved DOI remains: {doi}

## Stop before publication

Do not press Publish until the metadata, preview, new archive name and
SHA-256 have been checked.
"""
    (output / "ZENODO_REPLACE_FILES_09_1.md").write_text(
        zenodo_guide,
        encoding="utf-8",
    )

    github_guide = f"""# Replace Assets in the GitHub Draft Release

Use the existing GitHub draft release for tag:

```text
epa-pm25-2025-v0.1.0
```

Do not create a duplicate release.

## Replace assets

Remove the old release ZIP and old metadata assets from the GitHub draft.
Upload the DOI-aware files from this handoff's `assets` directory:

- `{archive.name}`
- `SHA256SUMS.txt`
- `CITATION.cff`
- `final-publication-metadata.json`
- `identifier-crosswalk.json`
- `time-basis.json`
- `doi-registration.json`

Replace the draft description with the updated
`GITHUB_RELEASE_NOTES.md`.

Reserved DOI:

```text
{doi}
```

Keep the GitHub release as a draft until the Zenodo record has been published
and the DOI resolves.
"""
    (output / "GITHUB_REPLACE_ASSETS_09_1.md").write_text(
        github_guide,
        encoding="utf-8",
    )

    (output / "RESERVED_DOI.txt").write_text(
        doi + "\n",
        encoding="utf-8",
    )

    handoff = {
        "reserved_doi": doi,
        "doi_url": f"{DOI_URL_PREFIX}{doi}",
        "doi_registered": False,
        "zenodo_draft_record": "21710054",
        "zenodo_draft_url": (
            "https://zenodo.org/uploads/21710054"
        ),
        "publishing_enabled": False,
        "github_release_mode": "draft-only",
        "zenodo_mode": "existing-draft-only",
        "doi_final_archive": archive.name,
        "doi_final_archive_sha256": archive_sha,
        "source_publication_handoff": str(
            source_handoff.resolve()
        ),
        "source_doi_final_release": str(
            release_root.resolve()
        ),
        "next_required_action": (
            "Replace old draft files, resolve Zenodo Basic information "
            "errors, save and preview; do not publish yet."
        ),
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    _write_json(
        output / "DOI_FINALIZATION_HANDOFF.json",
        handoff,
    )
    (output / "DOI_FINALIZATION_READINESS.html").write_text(
        _doi_handoff_readiness_html(
            doi=doi,
            archive_name=archive.name,
            archive_sha256=archive_sha,
        ),
        encoding="utf-8",
    )

    _write_handoff_checksums(output)
    verification = verify_doi_final_handoff(
        output,
        reserved_doi=doi,
    )
    if not verification["valid"]:
        raise RuntimeError(
            "DOI-final handoff failed verification: "
            + "; ".join(
                str(item) for item in verification["failures"]
            )
        )
    _write_json(
        output / "DOI_FINALIZATION_HANDOFF_VERIFICATION.json",
        verification,
    )
    _write_handoff_checksums(output)
    verification = verify_doi_final_handoff(
        output,
        reserved_doi=doi,
    )
    if not verification["valid"]:
        raise RuntimeError(
            "DOI-final handoff failed final verification: "
            + "; ".join(
                str(item) for item in verification["failures"]
            )
        )

    return {
        "handoff_directory": str(output),
        "readiness_html": str(
            output / "DOI_FINALIZATION_READINESS.html"
        ),
        "reserved_doi": doi,
        "doi_registered": False,
        "archive": str(assets / archive.name),
        "archive_sha256": archive_sha,
        "verification": verification,
    }
