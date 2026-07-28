# Experiment Examples

Generate a template:

```bash
heatsafe-experiment template --output experiment.json
```

Run the included deterministic demonstration:

```bash
heatsafe-experiment run   --spec examples/experiments/heataq-nexus-synthetic.json   --output artifacts/experiments/heataq-nexus-synthetic   --repository-root .
```

Verify the complete output:

```bash
heatsafe-experiment verify artifacts/experiments/heataq-nexus-synthetic
```

The example uses synthetic data only. It validates software behavior and must not be presented as evidence about a real location.
