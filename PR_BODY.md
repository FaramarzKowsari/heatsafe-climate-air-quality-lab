## Purpose

Resolve the initial CI failure caused by Ruff violations in utility scripts and tests.

## Changes

- Split multi-module imports into one import per line.
- Expand one-line compound statements and semicolon-separated statements.
- Normalize spacing and readability in synthetic-data generation scripts.
- Reformat tests without changing their assertions or scientific behavior.
- Move local imports to module scope where appropriate.

## Verification

- `30 passed` with the existing pytest suite.
- Python compilation succeeded for `src`, `tests`, and `scripts`.
- Markdown link check succeeded.
- Secret-pattern check succeeded.
- No core scientific algorithms, API behavior, frontend code, or Docker configuration changed.

## Expected CI result

The `ruff check src tests scripts` stage should pass, allowing the Python matrix to continue to mypy, pytest, link checks, and secret checks.
