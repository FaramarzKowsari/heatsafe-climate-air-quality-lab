from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".py",
    ".ts",
    ".js",
    ".css",
    ".mmd",
    ".cff",
    ".xml",
}
BANNED = (
    "heatsafe " + "home",
    "software " + "companion",
    "book " + "companion",
    "google " + "books",
    "book-" + "module-map",
    "book-" + "software-map",
    "book " + "doi",
    "book " + "sales",
)

# Google Books is permitted only as an official personal-profile link on the
# canonical author-identity surfaces. It remains prohibited from research,
# dataset, benchmark, API, tool, methodology and other project pages.
GOOGLE_BOOKS_AUTHOR_IDENTITY_PATHS = {
    Path("AUTHOR.md"),
    Path("README.md"),
    Path("docs/site/index.html"),
    Path("docs/site/about-author/index.html"),
}

# Root-level files beginning with ".heatsafe-" are installer receipts only.
# They are not project documentation, research output, source code, datasets,
# benchmark metadata or public site content.
INSTALLER_METADATA_PREFIX = ".heatsafe-"


def ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    is_root_installer_metadata = (
        len(relative.parts) == 1
        and path.name.startswith(INSTALLER_METADATA_PREFIX)
    )
    return (
        ".git" in relative.parts
        or ".venv" in relative.parts
        or "node_modules" in relative.parts
        or path.name == Path(__file__).name
        or is_root_installer_metadata
    )


def phrase_allowed(path: Path, phrase: str) -> bool:
    return (
        phrase == "google books"
        and path.relative_to(ROOT) in GOOGLE_BOOKS_AUTHOR_IDENTITY_PATHS
    )


def main() -> int:
    findings: list[str] = []

    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ignored(path)
            or path.suffix.lower() not in TEXT_SUFFIXES
        ):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()

        for phrase in BANNED:
            if phrase not in lowered or phrase_allowed(path, phrase):
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if phrase in line.lower():
                    findings.append(
                        f"{path.relative_to(ROOT)}:{line_number}: {phrase}"
                    )

    if findings:
        print("Scientific identity check failed:")
        print("\n".join(findings))
        return 1

    print(
        "Scientific identity check passed: "
        "no prohibited legacy references found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
