from __future__ import annotations

from pathlib import Path

from heatsafe.research.transfer.artifacts import (
    write_external_validation_artifacts,
)
from heatsafe.research.transfer.contracts import ExternalValidationConfig
from heatsafe.research.transfer.dataset import (
    generate_synthetic_multicity_frame,
)
from heatsafe.research.transfer.engine import run_external_validation


def main() -> None:
    root = Path("artifacts/external-validation-demo")
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / "synthetic-multicity.csv"
    frame = generate_synthetic_multicity_frame(
        rows_per_city=720,
        random_state=42,
    )
    frame.to_csv(input_path, index=False)

    config = ExternalValidationConfig(
        feature_columns=(
            "temperature_c",
            "relative_humidity_pct",
            "wind_speed_kmh",
            "smoke_proxy",
        ),
        horizons=(1, 6, 24),
    )
    report = run_external_validation(frame, config)
    write_external_validation_artifacts(
        report,
        output_directory=root,
        config=config,
        input_paths=(input_path,),
        repository_root=Path.cwd(),
    )
    print(f"External-validation artifacts written to {root}")


if __name__ == "__main__":
    main()
