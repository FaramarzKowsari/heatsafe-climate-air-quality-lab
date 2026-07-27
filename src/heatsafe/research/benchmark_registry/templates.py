from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import HttpUrl

from heatsafe.research.benchmark_registry.contracts import (
    BenchmarkProtocol,
    BenchmarkRelease,
    DatasetCard,
    SourceCitation,
    SnapshotArtifact,
    SpatialCoverage,
    TemporalCoverage,
)


def dataset_card_template() -> DatasetCard:
    now = datetime.now(UTC)
    return DatasetCard(
        dataset_id="replace-me-dataset",
        version="0.1.0",
        title="Replace with an official dataset snapshot title",
        description=(
            "Describe the exact frozen official-source snapshot, variables, "
            "selection rules and intended benchmark role."
        ),
        source_id="replace-me-source",
        role="external-test",
        target_variables=("pm25",),
        feature_variables=("temperature_c",),
        units={"pm25": "ug/m3", "temperature_c": "degC"},
        spatial=SpatialCoverage(countries=("Replace me",)),
        temporal=TemporalCoverage(
            start_utc=now,
            end_utc=now.replace(year=now.year + 1),
            nominal_resolution="hourly",
        ),
        station_selection_protocol="Document the deterministic station-selection rule.",
        quality_control_protocol="Document source flags, exclusions and range checks.",
        missing_data_policy="Document imputation, exclusion and completeness thresholds.",
        known_limitations=("Replace with a concrete limitation.",),
        citation=SourceCitation(
            authority="Replace with official authority",
            dataset_name="Replace with dataset name",
            homepage=HttpUrl("https://example.org/"),
            documentation_url=HttpUrl("https://example.org/docs"),
            citation_text="Replace with the provider citation.",
            license_summary="Replace with verified provider terms.",
            access_date_utc=now,
        ),
        artifacts=(
            SnapshotArtifact(
                relative_path="replace-me.csv",
                kind="raw",
                media_type="text/csv",
                size_bytes=0,
                sha256="0000000000000000000000000000000000000000000000000000000000000000",
                rows=0,
                columns=0,
            ),
        ),
        created_at_utc=now,
        status="draft",
        tags=("template",),
    )


def benchmark_release_template() -> BenchmarkRelease:
    now = datetime.now(UTC)
    protocol = BenchmarkProtocol(
        protocol_id="heatsafe-official-benchmark",
        version="0.1.0",
        title="HeatSafe Official Benchmark Protocol",
        target_variable="pm25",
        forecast_horizons_hours=(1, 6, 24),
        event_threshold=35.0,
        split_strategy="Chronological train-calibration-test",
        external_validation_strategy="Leave-one-city-out and leave-one-region-out",
        models=("persistence", "ridge"),
        metrics=("mae", "rmse", "event_f1", "interval_coverage"),
        random_seed=42,
        source_code_revision="replace-me",
        prohibited_claims=(
            "Official warning authority",
            "Medical prediction",
            "Universal geographic generalization",
        ),
        created_at_utc=now,
    )
    return BenchmarkRelease(
        release_id="heatsafe-official-benchmark-candidate",
        version="0.1.0",
        title="HeatSafe Official Benchmark Candidate",
        dataset_cards=("datasets/replace-me-dataset-0.1.0.json",),
        protocol=protocol,
        result_artifacts=(
            SnapshotArtifact(
                relative_path="replace-me-result.json",
                kind="benchmark-result",
                media_type="application/json",
                size_bytes=0,
                sha256="0000000000000000000000000000000000000000000000000000000000000000",
            ),
        ),
        release_notes=("Replace with release notes.",),
        created_at_utc=now,
        status="candidate",
    )


def write_templates(output_directory: str | Path) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    dataset_path = root / "dataset-card-template.json"
    release_path = root / "benchmark-release-template.json"
    dataset_path.write_text(dataset_card_template().model_dump_json(indent=2), encoding="utf-8")
    release_path.write_text(benchmark_release_template().model_dump_json(indent=2), encoding="utf-8")
    return {"dataset_card": str(dataset_path), "benchmark_release": str(release_path)}
