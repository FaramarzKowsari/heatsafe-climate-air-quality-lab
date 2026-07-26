"""Research utilities for forecasting, compound hazards and reproducibility."""

from heatsafe.research.compound_risk import CompoundRiskResult, analyze_compound_risk
from heatsafe.research.provenance import ExperimentManifest, build_experiment_manifest

__all__ = [
    "CompoundRiskResult",
    "ExperimentManifest",
    "analyze_compound_risk",
    "build_experiment_manifest",
]
