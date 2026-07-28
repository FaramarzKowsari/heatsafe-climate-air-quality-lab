# Reproducibility

1. Use Python 3.11–3.13 and install `pip install -e ".[dev]"`.
2. Run `python scripts/generate_demo_data.py`. The generator uses seed 42.
3. Run `pytest --cov=heatsafe`.
4. Run `make benchmark` to regenerate `benchmarks/heataq-nexus/results/cpu_baselines.json`.
5. Record operating system, Python version, dependency lock or freeze, git commit, and data checksums when publishing results.

The stored synthetic benchmark is a smoke test, not evidence about any real city.

<!-- HEATSAFE_EXPERIMENT_ORCHESTRATOR_REPRODUCIBILITY_V1 -->
## Paper-ready orchestrated experiments

Create and run the included deterministic example:

```bash
heatsafe-experiment run   --spec examples/experiments/heataq-nexus-synthetic.json   --output artifacts/experiments/heataq-nexus-synthetic   --repository-root .
```

Verify every non-release artifact:

```bash
heatsafe-experiment verify artifacts/experiments/heataq-nexus-synthetic
```

The generated directory includes the canonical input, normalized specification,
complete model metrics, uncertainty figures, HTML and Markdown reports,
environment metadata, experiment manifests, exact reproduction scripts,
SHA-256 checksums and a deterministic candidate ZIP archive.

Synthetic data validate software behavior only and are not evidence about a
real city. Review real data identity, limitations and release metadata before
creating a tagged scientific release or DOI.
