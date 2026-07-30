# Scientific Pack 09.1 — Reserved DOI Injection

Reserved DOI:

```text
10.5281/zenodo.21710054
```

Zenodo draft:

```text
https://zenodo.org/uploads/21710054
```

## Purpose

This pack injects the reserved DOI into the final reviewed candidate, rebuilds
all checksums, creates a new deterministic DOI-aware ZIP, and produces a new
draft-only publication handoff.

## Important state

- DOI is reserved.
- DOI is not yet registered publicly.
- Zenodo publication has not occurred.
- GitHub Release must remain a draft.
- The existing Zenodo draft must be preserved.
- The old ZIP and old SHA256SUMS in the Zenodo draft must be replaced.
- The three Basic information errors visible in Zenodo must be completed.

## DOI-aware output

Release directory:

```text
artifacts/releases/
epa-airdata-california-pm25-2025-first-real-reviewed-doi-final/
```

Release ZIP:

```text
artifacts/releases/
epa-airdata-california-pm25-2025-first-real-reviewed-v0.1.0-doi-final.zip
```

Publication handoff:

```text
artifacts/publication/
epa-pm25-2025-v0.1.0-doi-final-handoff/
```

## Publication boundary

This pack does not publish Zenodo, register the DOI, publish GitHub Release,
or claim that the DOI resolves publicly. Registration occurs only when the
Zenodo draft is published.
