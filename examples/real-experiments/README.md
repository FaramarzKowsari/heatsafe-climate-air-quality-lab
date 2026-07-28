# Real Official-Source Experiment Examples

The included EPA AQS example performs a local, credentialed acquisition from
the official US EPA Air Quality System API. Credentials are read only from
environment variables and are never written into plans, snapshots, reports or
repository files.

## Secret-free plan

```bash
heatsafe-real-experiment plan   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --output artifacts/plans/epa-aqs-alameda-pm25-2025.json
```

## Live local run

Set `EPA_AQS_EMAIL` and `EPA_AQS_KEY`, then run:

```bash
heatsafe-real-experiment run   --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json   --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025   --repository-root .
```

Windows users can run `RUN_FIRST_REAL_EPA_EXPERIMENT.cmd` from the repository
root. It prompts for credentials, keeps them only in the current process,
creates or reuses `.venv`, executes the pipeline and opens the HTML report.

Generated local official data and reports are excluded from Git tracking.
Review the output before creating a tagged release or depositing an archive.
