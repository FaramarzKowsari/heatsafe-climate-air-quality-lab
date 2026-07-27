from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md", ".txt", ".html", ".htm", ".json", ".yml", ".yaml", ".toml",
    ".py", ".ts", ".js", ".css", ".mmd", ".cff", ".xml",
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


def ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        ".git" in relative.parts
        or ".venv" in relative.parts
        or "node_modules" in relative.parts
        or path.name == Path(__file__).name
    )


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ignored(path) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        for phrase in BANNED:
            if phrase in lowered:
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if phrase in line.lower():
                        findings.append(f"{path.relative_to(ROOT)}:{line_number}: {phrase}")
    if findings:
        print("Scientific identity check failed:")
        print("\n".join(findings))
        return 1
    print("Scientific identity check passed: no prohibited legacy references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
