from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PATTERN = re.compile(r"^google[a-zA-Z0-9_-]+\.html$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("verification_file")
    parser.add_argument(
        "--site-root",
        default="docs/site",
    )
    args = parser.parse_args()

    source = Path(args.verification_file).expanduser().resolve()
    site_root = Path(args.site_root).resolve()

    if not source.is_file():
        raise FileNotFoundError(source)
    if not PATTERN.fullmatch(source.name):
        raise ValueError(
            "Google verification filename must look like "
            "googlexxxxxxxxxxxxxxxx.html"
        )

    content = source.read_text(
        encoding="utf-8",
        errors="strict",
    ).strip()
    expected = f"google-site-verification: {source.name}"
    if content != expected:
        raise ValueError(
            "Verification file content is not the exact Google token. "
            f"Expected: {expected}"
        )

    site_root.mkdir(parents=True, exist_ok=True)
    target = site_root / source.name
    shutil.copy2(source, target)

    print("Google Search Console verification file installed:")
    print(target)
    print()
    print("Public verification URL after deployment:")
    print(
        "https://faramarzkowsari.github.io/"
        "heatsafe-climate-air-quality-lab/"
        + source.name
    )
    print()
    print(
        "Keep this file in the repository after verification; "
        "removing it can remove verified ownership."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
