# Reproducibility

1. Use Python 3.11–3.13 and install `pip install -e ".[dev]"`.
2. Run `python scripts/generate_demo_data.py`. The generator uses seed 42.
3. Run `pytest --cov=heatsafe`.
4. Run `make benchmark` to regenerate `benchmarks/heataq-nexus/results/cpu_baselines.json`.
5. Record operating system, Python version, dependency lock or freeze, git commit, and data checksums when publishing results.

The stored synthetic benchmark is a smoke test, not evidence about any real city.
