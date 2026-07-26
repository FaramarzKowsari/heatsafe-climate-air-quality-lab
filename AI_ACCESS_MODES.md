# AI Access Modes

HeatSafe separates scientific computation from language-model assistance.

## Mode 0 — Standard deterministic mode

- Default and always available
- No language model
- No paid AI API
- No external model account
- Decisions and metrics come directly from typed scientific functions
- Explanations are assembled from computed reasons and input values
- Suitable for CI, offline demonstrations, teaching and reproducibility

## Mode 1 — Local AI

- Optional
- Uses a locally hosted model endpoint such as Ollama
- Raw household or research inputs can remain on the user's machine
- The model may explain an existing result
- It may not change the decision, threshold, measurement or uncertainty estimate
- Numeric-grounding checks flag values not present in the supplied evidence

## Mode 2 — BYOK

- Optional
- A researcher provides a compatible provider endpoint and server-side secret
- Secrets are read from environment variables
- Keys must never be embedded in GitHub Pages or committed files
- Provider, model, input hash, latency and grounding warnings are recorded
- Cloud AI is never required to run the scientific core

## Allowed AI tasks

- plain-language explanation of computed outputs;
- documentation assistance;
- optional code or query assistance;
- retrieval over explicitly selected scientific documents;
- hypothesis generation clearly labeled as speculative;
- experiment-summary drafting from versioned metrics.

## Prohibited AI behavior

- replacing a deterministic safety-related outcome;
- inventing sensor values, citations or source timestamps;
- presenting generated text as measured evidence;
- silently changing units or thresholds;
- claiming medical, regulatory or causal authority;
- sending secrets or private household data without explicit configuration.

## Grounding contract

Every AI explanation should record:

- mode;
- provider and model;
- SHA-256 hash of the canonical input;
- cited input values;
- latency;
- numeric-grounding issues;
- policy version;
- an explicit warning that the model cannot override the scientific result.
