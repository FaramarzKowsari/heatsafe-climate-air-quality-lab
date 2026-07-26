# Final QA Report — v0.1.0 Research Preview

**Build date:** 2026-07-26  
**Mode:** BUILD_ONLY  
**Author:** Faramarz Kowsari

## Source audit

- Master repository prompt inspected.
- HeatSafe Home Word reference parsed into **100 unique prompt records**.
- MHTML project-history snapshot inspected.
- SHA-256 identifiers recorded in `docs/source-audit.md`.
- Book concepts mapped to software routes in `docs/book-companion/book-module-map.md`.

## Passed locally

| Check | Result |
|---|---|
| Python syntax compilation | Passed |
| Pytest | **30 passed** |
| Python test coverage | **78% total** |
| TypeScript strict compilation | Passed with TypeScript 5.8.3 |
| FastAPI startup | Passed |
| `/api/v1/health` smoke test | HTTP 200 |
| Browser root smoke test | HTTP 200 |
| OpenAPI documentation smoke test | HTTP 200 |
| Editable package build/install in active environment | Passed |
| CLI ventilation workflow | Passed |
| CLI cooling-cost workflow | Passed |
| Synthetic benchmark generation | Passed for 1, 6, 12, 24, and 48 hour horizons |
| Relative Markdown links | Passed |
| Common high-confidence secret patterns | None found |
| Deterministic synthetic data checksums | Generated |
| Book prompt count | 100 |

## Environment

- Linux 6.12 x86_64
- Python 3.13.5
- Node.js 22.16.0
- npm 10.9.2
- TypeScript 5.8.3
- Git 2.47.3

## Not locally verifiable in this container

| Check | Status | Reason / mitigation |
|---|---|---|
| Docker image build | Deferred | Docker/Podman is not installed. A non-root Dockerfile and GitHub Actions Docker build job are included. |
| Ruff execution | Deferred | The package index returned HTTP 503 and Ruff was not preinstalled. CI installs and runs Ruff. Source imports were manually audited and Python compilation passed. |
| Mypy execution | Deferred | Mypy was not preinstalled and the package index was unavailable. CI runs Mypy on the deterministic typed core. |
| npm package-lock generation | Deferred | The package registry was unavailable. The compiled browser JavaScript is committed and `toolchain.lock.json` records TypeScript 5.8.3 plus the generated asset checksum. |
| Isolated dependency download | Deferred | The package index was unavailable. Editable installation with existing verified dependencies passed; `requirements.lock` records the tested versions. |
| GitHub Actions run | Pending publication | Workflows cannot run until the repository is published. |
| GitHub Pages deployment | Pending publication | The deployment workflow and static site are included. |
| Zenodo DOI | Pending release | No DOI is claimed or fabricated. |

## Scientific safeguards verified

- Deterministic engine makes the primary ventilation decision.
- LLM modes only explain computed results.
- Satellite land-surface temperature is distinguished from air temperature.
- Observed, satellite-derived, reanalysis, modeled, forecast, user-entered, estimated, and synthetic data are distinct.
- Wildfire proximity does not claim definitive causal attribution.
- AQI conversion is explicitly labeled by standard.
- Home profile does not emit a certified score.
- Comparator describes associations rather than controlled causation.
- CO2 is treated as a ventilation clue, not a complete air-quality score.
- No medical diagnosis, official warning, building certification, or guaranteed outcome is claimed.

## Release decision

The artifact is suitable for publication as **v0.1.0 — Research Preview** after the owner reviews the repository metadata. It should not be labeled v1.0.0. Docker, Ruff, Mypy, GitHub Actions, Pages, and DOI status must be checked after publication before claiming a fully verified production release.
