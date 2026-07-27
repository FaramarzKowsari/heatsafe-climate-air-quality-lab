from __future__ import annotations

from pathlib import Path

from heatsafe.research.nexus.artifacts import write_nexus_artifacts
from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.nexus.dataset import generate_synthetic_nexus_frame
from heatsafe.research.nexus.evaluation import run_nexus_benchmark


def main() -> None:
    root = Path("artifacts/heataq-nexus-demo")
    root.mkdir(parents=True, exist_ok=True)
    input_path = root / "synthetic-hourly.csv"
    frame = generate_synthetic_nexus_frame(rows=1_500, random_state=42)
    frame.to_csv(input_path, index=False)
    config = NexusConfig(
        feature_columns=("temperature_c", "relative_humidity_pct", "wind_speed_kmh", "smoke_proxy"),
    )
    report = run_nexus_benchmark(frame, config)
    write_nexus_artifacts(
        report,
        output_directory=root,
        config=config,
        input_paths=(input_path,),
        repository_root=Path.cwd(),
    )
    print(f"HeatAQ Nexus artifacts written to {root}")


if __name__ == "__main__":
    main()
