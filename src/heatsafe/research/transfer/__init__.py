"""Multi-city external validation and domain-shift research tools."""

from heatsafe.research.transfer.contracts import (
    ExternalValidationConfig,
    ExternalValidationReport,
)
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
    validate_multicity_frame,
)
from heatsafe.research.transfer.engine import run_external_validation

__all__ = [
    "ExternalValidationConfig",
    "ExternalValidationReport",
    "generate_synthetic_multicity_frame",
    "run_external_validation",
    "validate_multicity_frame",
]
