# Architecture

```mermaid
flowchart LR
  Browser[Browser research laboratory] --> API[FastAPI typed API]
  CLI[Scientific CLI] --> Core[Deterministic core]
  API --> Core
  API --> Research[HeatAQ Nexus and compound-risk research]
  Connectors[Open-data and credentialed connectors] --> Contract[Normalized provenance contract]
  Local[Local CSV / JSON / synthetic data] --> Contract
  Contract --> Core
  Contract --> Research
  Core --> Standard[Standard no-LLM explanation]
  Core --> LocalAI[Optional local AI]
  Core --> BYOK[Optional provider-neutral BYOK]
  Research --> Manifest[Experiment manifests and checksums]
  Manifest --> Release[Versioned scientific artifacts]
```

A modular monolith keeps scientific logic testable and avoids premature service boundaries. Data connectors normalize provenance before analysis. The scientific core does not depend on a language model or a paid provider. Optional AI layers explain existing results and remain subordinate to deterministic outputs.
