from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring


BASE_URL = (
    "https://faramarzkowsari.github.io/"
    "heatsafe-climate-air-quality-lab/"
)


def page_url(site_root: Path, page: Path) -> str:
    relative = page.relative_to(site_root)
    if relative.as_posix() == "index.html":
        return BASE_URL
    return BASE_URL + quote(
        relative.parent.as_posix().strip("/") + "/",
        safe="/-._~",
    )


def discover_urls(site_root: Path) -> list[str]:
    urls = [
        page_url(site_root, page)
        for page in sorted(site_root.rglob("index.html"))
    ]
    return sorted(set(urls))


def build_xml(urls: list[str]) -> str:
    root = Element(
        "urlset",
        {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )
    for url in urls:
        node = SubElement(root, "url")
        SubElement(node, "loc").text = url
    xml = tostring(
        root,
        encoding="unicode",
        short_empty_elements=True,
    )
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", default="docs/site")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    site_root = Path(args.site_root)
    if not site_root.is_dir():
        raise FileNotFoundError(site_root)

    urls = discover_urls(site_root)
    xml = build_xml(urls)
    text = "\n".join(urls) + "\n"

    outputs = {
        site_root / "sitemap.xml": xml,
        site_root / "sitemap.txt": text,
    }
    stale = []
    for path, content in outputs.items():
        current = (
            path.read_text(encoding="utf-8")
            if path.is_file()
            else None
        )
        if current != content:
            stale.append(path)
            if not args.check:
                path.write_text(content, encoding="utf-8")

    if args.check and stale:
        print("Sitemap files are not current:")
        for path in stale:
            print(f"  {path}")
        return 1

    print(f"Discovered {len(urls)} public HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
