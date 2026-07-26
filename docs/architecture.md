# Architecture

```mermaid
flowchart LR
  UI[Browser laboratory] --> API[FastAPI typed API]
  API --> Core[Deterministic HeatSafe core]
  API --> Research[HeatAQ Nexus benchmark]
  Connectors[Open-data connectors] --> Contract[Normalized observation contract]
  Contract --> Core
  Contract --> Research
  Core --> Explain[Standard / Local AI / BYOK explanation]
  Book[HeatSafe Home reference] --> Map[Book-to-module map]
  Map --> UI
```

A modular monolith keeps scientific logic testable and avoids premature service boundaries. Data connectors normalize provenance before analysis. The static browser is intentionally dependency-light and is served by FastAPI.
