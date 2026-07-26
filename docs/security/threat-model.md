# Threat Model

Assets include API keys, household logs, coarse location, scientific provenance, and model integrity. Threats include secret leakage, malicious CSV content, denial of service through oversized requests, dependency compromise, stale environmental data, provenance spoofing, and LLM instruction injection.

Controls in this preview include typed validation, request bounds, no dynamic code execution, environment-only secrets, non-root container, read-only container runtime, dependency scanning workflow, deterministic primary decisions, data-type labels, and explicit freshness/provenance fields. Production deployments should add reverse-proxy rate limits, maximum body size, authentication where needed, audit logging without private payloads, and encrypted storage.
