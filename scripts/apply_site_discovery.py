from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


BASE_URL = (
    "https://faramarzkowsari.github.io/"
    "heatsafe-climate-air-quality-lab/"
)
SITE_NAME = "HeatSafe Climate & Air Quality Intelligence Lab"
DEFAULT_DESCRIPTION = (
    "Open-source environmental intelligence and AI research for extreme "
    "heat, PM2.5, air quality, wildfire smoke, urban climate, forecasting, "
    "uncertainty and resilient homes."
)
SOCIAL_IMAGE = BASE_URL + "assets/heatsafe-social-card.png"
FAVICON_URL = BASE_URL + "assets/favicon-96.png"
REPOSITORY_URL = (
    "https://github.com/FaramarzKowsari/"
    "heatsafe-climate-air-quality-lab"
)
DOI = "10.5281/zenodo.21710054"
DOI_URL = "https://doi.org/" + DOI
SEO_START = "<!-- HEATSAFE_DISCOVERY_SEO_V1_START -->"
SEO_END = "<!-- HEATSAFE_DISCOVERY_SEO_V1_END -->"
JSONLD_START = "<!-- HEATSAFE_DISCOVERY_JSONLD_V1_START -->"
JSONLD_END = "<!-- HEATSAFE_DISCOVERY_JSONLD_V1_END -->"


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return " ".join(value.split())


def _extract_title(text: str) -> str:
    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return _clean_text(match.group(1))
    heading = re.search(
        r"<h1[^>]*>(.*?)</h1>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if heading:
        return _clean_text(heading.group(1)) + " | HeatSafe Research Lab"
    return SITE_NAME


def _extract_description(text: str) -> str:
    patterns = (
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
    )
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            value = _clean_text(match.group(1))
            if value:
                return value
    paragraph = re.search(
        r"<p(?:\s+class=[\"'][^\"']*(?:lead|lede)[^\"']*[\"'])?[^>]*>"
        r"(.*?)</p>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if paragraph:
        value = _clean_text(paragraph.group(1))
        if value:
            return value[:280]
    return DEFAULT_DESCRIPTION


def _page_url(site_root: Path, page: Path) -> str:
    relative = page.relative_to(site_root)
    if relative.as_posix() == "index.html":
        return BASE_URL
    return BASE_URL + relative.parent.as_posix().strip("/") + "/"


def _relative_root(site_root: Path, page: Path) -> str:
    depth = len(page.relative_to(site_root).parent.parts)
    return "../" * depth or "./"


def _remove_existing_metadata(text: str) -> str:
    patterns = (
        r"<link\b(?=[^>]*\brel=[\"']canonical[\"'])[^>]*>\s*",
        r"<link\b(?=[^>]*\brel=[\"'](?:icon|shortcut icon|apple-touch-icon)"
        r"[\"'])[^>]*>\s*",
        r"<link\b(?=[^>]*\brel=[\"']manifest[\"'])[^>]*>\s*",
        r"<link\b(?=[^>]*\brel=[\"']sitemap[\"'])[^>]*>\s*",
        r"<meta\b(?=[^>]*\bname=[\"']robots[\"'])[^>]*>\s*",
        r"<meta\b(?=[^>]*\bname=[\"']googlebot[\"'])[^>]*>\s*",
        r"<meta\b(?=[^>]*\bproperty=[\"']og:[^\"']+[\"'])[^>]*>\s*",
        r"<meta\b(?=[^>]*\bname=[\"']twitter:[^\"']+[\"'])[^>]*>\s*",
    )
    for pattern in patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )
    text = re.sub(
        rf"{re.escape(SEO_START)}.*?{re.escape(SEO_END)}\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def _person() -> dict[str, Any]:
    return {
        "@type": "Person",
        "@id": BASE_URL + "#faramarz-kowsari",
        "name": "Faramarz Kowsari",
        "url": BASE_URL + "about-author/",
        "image": BASE_URL + "assets/faramarz-kowsari-profile.jpg",
        "jobTitle": [
            "Software Engineer",
            "AI Researcher",
            "Author",
        ],
        "sameAs": [
            "https://orcid.org/0000-0003-1692-0453",
            "https://scholar.google.com/citations?user=G7tP5WMAAAAJ&hl=en",
            "https://github.com/FaramarzKowsari",
            "https://www.linkedin.com/in/faramarzkowsari",
            "https://faramarzkowsari.github.io/",
            (
                "https://zenodo.org/search?q=creators.orcid%3A%22"
                "0000-0003-1692-0453%22&l=list&p=1&s=10&sort=bestmatch"
            ),
        ],
    }


def _home_graph() -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [
            _person(),
            {
                "@type": "WebSite",
                "@id": BASE_URL + "#website",
                "url": BASE_URL,
                "name": SITE_NAME,
                "alternateName": "HeatSafe Research Lab",
                "description": DEFAULT_DESCRIPTION,
                "inLanguage": "en",
                "author": {
                    "@id": BASE_URL + "#faramarz-kowsari"
                },
            },
            {
                "@type": "SoftwareSourceCode",
                "@id": BASE_URL + "#software",
                "name": SITE_NAME,
                "description": DEFAULT_DESCRIPTION,
                "codeRepository": REPOSITORY_URL,
                "url": BASE_URL,
                "license": (
                    "https://www.apache.org/licenses/LICENSE-2.0"
                ),
                "programmingLanguage": [
                    "Python",
                    "JavaScript",
                    "HTML",
                    "CSS",
                ],
                "author": {
                    "@id": BASE_URL + "#faramarz-kowsari"
                },
                "keywords": [
                    "air quality",
                    "PM2.5",
                    "extreme heat",
                    "heatwaves",
                    "wildfire smoke",
                    "urban heat",
                    "environmental intelligence",
                    "forecasting",
                    "reproducible research",
                ],
            },
            {
                "@type": "ResearchProject",
                "@id": BASE_URL + "#research-project",
                "name": SITE_NAME,
                "description": DEFAULT_DESCRIPTION,
                "url": BASE_URL,
                "founder": {
                    "@id": BASE_URL + "#faramarz-kowsari"
                },
                "sameAs": [
                    REPOSITORY_URL,
                    DOI_URL,
                ],
                "keywords": [
                    "climate risk",
                    "air quality",
                    "heat resilience",
                    "open environmental data",
                    "scientific computing",
                ],
            },
        ],
    }


def _dataset_graph() -> dict[str, Any]:
    archive_url = (
        REPOSITORY_URL
        + "/releases/download/epa-pm25-2025-v0.1.0/"
        + "epa-airdata-california-pm25-2025-first-real-reviewed-"
        + "v0.1.0-doi-final.zip"
    )
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": DOI_URL,
        "name": (
            "US EPA AirData San Diego County, California PM2.5 "
            "Forecasting Benchmark v0.1.0"
        ),
        "description": (
            "A reproducible station-level PM2.5 forecasting benchmark "
            "derived from the official US EPA AirData 2025 hourly "
            "parameter 88101 product for San Diego County, California."
        ),
        "url": BASE_URL + "dataset/epa-pm25-san-diego-v0-1-0/",
        "sameAs": DOI_URL,
        "identifier": [
            DOI,
            DOI_URL,
        ],
        "creator": _person(),
        "license": (
            "https://creativecommons.org/licenses/by/4.0/"
        ),
        "datePublished": "2026-07-30",
        "version": "0.1.0",
        "keywords": [
            "US EPA AirData",
            "PM2.5",
            "air quality",
            "forecasting",
            "San Diego County",
            "reproducible research",
            "environmental data",
        ],
        "temporalCoverage": (
            "2025-07-18T18:00:00Z/2026-01-01T07:00:00Z"
        ),
        "spatialCoverage": {
            "@type": "Place",
            "name": "San Diego County, California, United States",
        },
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "application/zip",
                "contentUrl": archive_url,
                "name": "DOI-aware reproducible research archive",
            }
        ],
        "isBasedOn": {
            "@type": "Dataset",
            "name": (
                "US EPA AirData hourly PM2.5 FRM/FEM Mass, "
                "parameter 88101"
            ),
            "url": "https://aqs.epa.gov/aqsweb/airdata/download_files.html",
        },
        "citation": DOI_URL,
    }


def _profile_graph(page_url: str) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "@id": page_url + "#profile",
        "url": page_url,
        "mainEntity": _person(),
    }


def _webpage_graph(
    page_url: str,
    title: str,
    description: str,
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": page_url + "#webpage",
        "url": page_url,
        "name": title,
        "description": description,
        "isPartOf": {
            "@id": BASE_URL + "#website"
        },
        "author": {
            "@id": BASE_URL + "#faramarz-kowsari"
        },
        "inLanguage": "en",
    }


def _jsonld_for(
    site_root: Path,
    page: Path,
    page_url: str,
    title: str,
    description: str,
) -> dict[str, Any]:
    relative = page.relative_to(site_root).as_posix()
    if relative == "index.html":
        return _home_graph()
    if relative == "about-author/index.html":
        return _profile_graph(page_url)
    if relative == (
        "dataset/epa-pm25-san-diego-v0-1-0/index.html"
    ):
        return _dataset_graph()
    return _webpage_graph(page_url, title, description)


def _metadata_block(
    *,
    page_url: str,
    title: str,
    description: str,
    relative_root: str,
) -> str:
    escaped_title = html.escape(title, quote=True)
    escaped_description = html.escape(description, quote=True)
    escaped_url = html.escape(page_url, quote=True)
    manifest = relative_root + "site.webmanifest"
    icon = relative_root + "assets/favicon-96.png"
    return f"""{SEO_START}
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{escaped_url}">
<link rel="icon" type="image/png" sizes="96x96" href="{icon}">
<link rel="apple-touch-icon" href="{icon}">
<link rel="manifest" href="{manifest}">
<link rel="sitemap" type="application/xml" href="{BASE_URL}sitemap.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}">
<meta property="og:title" content="{escaped_title}">
<meta property="og:description" content="{escaped_description}">
<meta property="og:url" content="{escaped_url}">
<meta property="og:image" content="{SOCIAL_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="HeatSafe Climate and Air Quality Intelligence Lab">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escaped_title}">
<meta name="twitter:description" content="{escaped_description}">
<meta name="twitter:image" content="{SOCIAL_IMAGE}">
{SEO_END}"""


def _jsonld_block(payload: dict[str, Any]) -> str:
    value = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"{JSONLD_START}\n"
        '<script type="application/ld+json">'
        + value
        + "</script>\n"
        f"{JSONLD_END}"
    )


def transform_page(site_root: Path, page: Path) -> str:
    original = page.read_text(encoding="utf-8")
    text = _remove_existing_metadata(original)
    text = text.replace("<!-- HEATSAFE_PERSON_JSONLD_V1 -->", "")
    text = re.sub(
        rf"{re.escape(JSONLD_START)}.*?{re.escape(JSONLD_END)}\s*",
        "",
        text,
        flags=re.DOTALL,
    )

    title = _extract_title(text)
    description = _extract_description(text)
    page_url = _page_url(site_root, page)
    relative_root = _relative_root(site_root, page)
    metadata = _metadata_block(
        page_url=page_url,
        title=title,
        description=description,
        relative_root=relative_root,
    )
    jsonld = _jsonld_block(
        _jsonld_for(
            site_root,
            page,
            page_url,
            title,
            description,
        )
    )

    if "</head>" not in text:
        raise ValueError(f"Missing </head> in {page}")
    return text.replace(
        "</head>",
        metadata + "\n" + jsonld + "\n</head>",
        1,
    )


def apply(
    site_root: Path,
    *,
    check: bool,
) -> list[str]:
    changed: list[str] = []
    for page in sorted(site_root.rglob("index.html")):
        transformed = transform_page(site_root, page)
        original = page.read_text(encoding="utf-8")
        if transformed != original:
            changed.append(page.relative_to(site_root).as_posix())
            if not check:
                page.write_text(transformed, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site-root",
        default="docs/site",
    )
    parser.add_argument(
        "--check",
        action="store_true",
    )
    args = parser.parse_args()
    site_root = Path(args.site_root)
    if not site_root.is_dir():
        raise FileNotFoundError(site_root)

    changed = apply(site_root, check=args.check)
    if args.check and changed:
        print("Site discovery metadata is not current:")
        for item in changed:
            print(f"  {item}")
        return 1

    action = "would update" if args.check else "updated"
    print(f"{action} {len(changed)} HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
