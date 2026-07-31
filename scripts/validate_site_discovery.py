from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from xml.etree import ElementTree


BASE_URL = (
    "https://faramarzkowsari.github.io/"
    "heatsafe-climate-air-quality-lab/"
)


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _extract(
    pattern: str,
    text: str,
) -> str | None:
    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def _page_url(site_root: Path, page: Path) -> str:
    relative = page.relative_to(site_root)
    if relative.as_posix() == "index.html":
        return BASE_URL
    return BASE_URL + relative.parent.as_posix().strip("/") + "/"


def _jsonld_payloads(text: str) -> list[object]:
    payloads: list[object] = []
    for raw in re.findall(
        r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        payloads.append(json.loads(raw))
    return payloads


def _types(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        current = value.get("@type")
        if isinstance(current, str):
            found.add(current)
        elif isinstance(current, list):
            found.update(
                item for item in current if isinstance(item, str)
            )
        for nested in value.values():
            found.update(_types(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_types(nested))
    return found


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def validate(site_root: Path) -> dict[str, object]:
    failures: list[str] = []
    pages = sorted(site_root.rglob("index.html"))
    page_urls = {_page_url(site_root, page) for page in pages}

    if not pages:
        failures.append("No index.html pages found")

    for page in pages:
        relative = page.relative_to(site_root).as_posix()
        text = page.read_text(encoding="utf-8")
        expected_url = _page_url(site_root, page)

        if _count(r"<title\b", text) != 1:
            failures.append(f"{relative}: expected one title")
        if _count(
            r'<meta\s+name=["\']description["\']',
            text,
        ) != 1:
            failures.append(
                f"{relative}: expected one meta description"
            )
        canonical = _extract(
            r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']',
            text,
        )
        if canonical != expected_url:
            failures.append(
                f"{relative}: canonical mismatch ({canonical})"
            )
        robots = _extract(
            r'<meta\s+name=["\']robots["\']\s+content=["\'](.*?)["\']',
            text,
        )
        if not robots or "index" not in robots or "follow" not in robots:
            failures.append(f"{relative}: robots meta is not index/follow")
        for required in (
            "og:title",
            "og:description",
            "og:url",
            "og:image",
            "twitter:card",
        ):
            if required.startswith("og:"):
                pattern = (
                    r'<meta\s+property=["\']'
                    + re.escape(required)
                    + r'["\']'
                )
            else:
                pattern = (
                    r'<meta\s+name=["\']'
                    + re.escape(required)
                    + r'["\']'
                )
            if not re.search(pattern, text, flags=re.IGNORECASE):
                failures.append(f"{relative}: missing {required}")
        if 'rel="icon"' not in text:
            failures.append(f"{relative}: missing favicon")
        if 'rel="manifest"' not in text:
            failures.append(f"{relative}: missing web manifest")

        try:
            payloads = _jsonld_payloads(text)
        except json.JSONDecodeError as exc:
            failures.append(f"{relative}: invalid JSON-LD: {exc}")
            payloads = []
        if not payloads:
            failures.append(f"{relative}: no JSON-LD")
        page_types: set[str] = set()
        for payload in payloads:
            page_types.update(_types(payload))
        if relative == "index.html":
            for needed in (
                "WebSite",
                "SoftwareSourceCode",
                "ResearchProject",
                "Person",
            ):
                if needed not in page_types:
                    failures.append(
                        f"index.html: missing JSON-LD type {needed}"
                    )
        if relative == (
            "dataset/epa-pm25-san-diego-v0-1-0/index.html"
        ) and "Dataset" not in page_types:
            failures.append("dataset landing page lacks Dataset JSON-LD")

    sitemap_path = site_root / "sitemap.xml"
    if not sitemap_path.is_file():
        failures.append("Missing sitemap.xml")
        sitemap_urls: set[str] = set()
    else:
        try:
            root = ElementTree.parse(sitemap_path).getroot()
            namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            sitemap_urls = {
                (node.text or "").strip()
                for node in root.findall("s:url/s:loc", namespace)
            }
        except ElementTree.ParseError as exc:
            failures.append(f"Invalid sitemap.xml: {exc}")
            sitemap_urls = set()
        missing = page_urls - sitemap_urls
        extra = sitemap_urls - page_urls
        if missing:
            failures.append(
                "Sitemap missing: " + ", ".join(sorted(missing))
            )
        if extra:
            failures.append(
                "Sitemap has unknown URLs: " + ", ".join(sorted(extra))
            )

    robots_path = site_root / "robots.txt"
    if not robots_path.is_file():
        failures.append("Missing robots.txt")
    else:
        robots = robots_path.read_text(encoding="utf-8")
        expected = "Sitemap: " + BASE_URL + "sitemap.xml"
        if expected not in robots:
            failures.append("robots.txt does not reference sitemap.xml")
        if re.search(
            r"Disallow:\s*/\s*$",
            robots,
            flags=re.MULTILINE,
        ):
            failures.append("robots.txt blocks the whole site")

    manifest = site_root / "site.webmanifest"
    if not manifest.is_file():
        failures.append("Missing site.webmanifest")
    else:
        try:
            json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"Invalid site.webmanifest: {exc}")

    favicon = site_root / "assets/favicon-96.png"
    if not favicon.is_file():
        failures.append("Missing favicon-96.png")
    else:
        try:
            width, height = _png_dimensions(favicon)
            if width != height or width < 48:
                failures.append(
                    f"Favicon must be square and >=48px, got {width}x{height}"
                )
        except ValueError as exc:
            failures.append(f"Invalid favicon PNG: {exc}")

    card = site_root / "assets/heatsafe-social-card.png"
    if not card.is_file():
        failures.append("Missing heatsafe-social-card.png")
    else:
        try:
            width, height = _png_dimensions(card)
            if (width, height) != (1200, 630):
                failures.append(
                    f"Social card must be 1200x630, got {width}x{height}"
                )
        except ValueError as exc:
            failures.append(f"Invalid social card PNG: {exc}")

    page_404 = site_root / "404.html"
    if not page_404.is_file():
        failures.append("Missing 404.html")
    else:
        text = page_404.read_text(encoding="utf-8")
        if 'content="noindex,follow"' not in text:
            failures.append("404.html must use noindex,follow")

    for file in site_root.glob("google*.html"):
        expected = f"google-site-verification: {file.name}"
        if expected not in file.read_text(
            encoding="utf-8",
            errors="ignore",
        ):
            failures.append(
                f"{file.name}: invalid Search Console verification content"
            )

    report = {
        "valid": not failures,
        "html_pages": len(pages),
        "sitemap_urls": len(page_urls),
        "base_url": BASE_URL,
        "failures": failures,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", default="docs/site")
    parser.add_argument(
        "--report",
        default="artifacts/site-discovery-validation.json",
    )
    args = parser.parse_args()
    site_root = Path(args.site_root)
    if not site_root.is_dir():
        raise FileNotFoundError(site_root)

    report = validate(site_root)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
