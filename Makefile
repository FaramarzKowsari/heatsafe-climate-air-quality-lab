.PHONY: setup test lint typecheck demo run benchmark docs package clean experiment real-experiment-plan real-experiment
PYTHON ?= python

setup:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	$(PYTHON) -m heatsafe serve --host 0.0.0.0 --port 8000

demo: generate-demo
	$(PYTHON) -m heatsafe ventilation --indoor 29 --outdoor 24 --pm25 12 --humidity 55 --wind 9 --cross-ventilation

generate-demo:
	$(PYTHON) scripts/generate_demo_data.py

test:
	$(PYTHON) -m pytest --cov=heatsafe --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src tests scripts

typecheck:
	$(PYTHON) -m mypy src/heatsafe

benchmark: generate-demo
	$(PYTHON) -m heatsafe benchmark data/synthetic/hourly_environment.csv --column pm25_ug_m3 --output benchmarks/heataq-nexus/results/cpu_baselines.json

docs:
	$(PYTHON) scripts/check_links.py

package:
	$(PYTHON) scripts/package_release.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info src/*.egg-info
# HEATSAFE_EXPERIMENT_ORCHESTRATOR_MAKE_TARGET_V1
experiment:
	$(PYTHON) -m heatsafe.research.experiment_orchestrator.cli run --spec examples/experiments/heataq-nexus-synthetic.json --output artifacts/experiments/heataq-nexus-synthetic --repository-root . --overwrite

# HEATSAFE_FIRST_REAL_EXPERIMENT_MAKE_V1
real-experiment-plan:
	$(PYTHON) -m heatsafe.research.official_experiment.cli plan --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json --output artifacts/plans/epa-aqs-alameda-pm25-2025.json

real-experiment:
	$(PYTHON) -m heatsafe.research.official_experiment.cli run --config examples/real-experiments/epa-aqs-alameda-pm25-2025.json --workspace artifacts/local-real-experiments/epa-aqs-alameda-pm25-2025 --repository-root .
