from __future__ import annotations

import argparse
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from heatsafe.core.models import MeasurementType, NormalizedObservation
from heatsafe.data_foundation.official_snapshots.contracts import (
    AcquisitionMode,
)
from heatsafe.data_foundation.official_snapshots.pipeline import (
    freeze_official_snapshot,
)
from heatsafe.data_foundation.snapshot import (
    load_observations,
)
from heatsafe.research.experiment_orchestrator.contracts import (
    DatasetSpec,
    ExperimentSpec,
    ReleaseSpec,
    ReportSpec,
)
from heatsafe.research.experiment_orchestrator.runner import (
    run_experiment,
)
from heatsafe.research.nexus.contracts import NexusConfig
from heatsafe.research.official_experiment.preparation import (
    prepare_hourly_station_frame,
)
from heatsafe.research.official_experiment.runner import (
    _load_real_config,
    _load_snapshot_config,
    _prepare_workspace,
    _write_open_report_scripts,
    verify_real_official_experiment,
    write_real_experiment_plan,
)
from heatsafe.research.provenance import sha256_file


AIRDATA_URL = (
    "https://aqs.epa.gov/aqsweb/airdata/hourly_88101_2025.zip"
)
EXPECTED_COLUMNS = (
    "State Code",
    "County Code",
    "Site Num",
    "Parameter Code",
    "POC",
    "Latitude",
    "Longitude",
    "Parameter Name",
    "Date GMT",
    "Time GMT",
    "Sample Measurement",
    "Units of Measure",
    "Qualifier",
    "Method Type",
    "Method Code",
    "Method Name",
    "State Name",
    "County Name",
    "Date of Last Change",
)


def _csv_member(archive: zipfile.ZipFile) -> str:
    members = [
        name
        for name in archive.namelist()
        if name.lower().endswith(".csv")
        and not name.endswith("/")
    ]
    if len(members) != 1:
        raise ValueError(
            "Expected exactly one CSV member in the EPA AirData ZIP; "
            f"found {len(members)}"
        )
    return members[0]


def validate_airdata_zip(
    path: str | Path,
    *,
    minimum_size_bytes: int = 1_000_000,
) -> dict[str, Any]:
    zip_path = Path(path)
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    if zip_path.stat().st_size < minimum_size_bytes:
        raise ValueError(
            "The EPA AirData ZIP is unexpectedly small and may be incomplete"
        )

    with zipfile.ZipFile(zip_path) as archive:
        member = _csv_member(archive)
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupt ZIP member: {bad_member}")
        with archive.open(member) as stream:
            header = pd.read_csv(stream, nrows=0)
        missing = sorted(set(EXPECTED_COLUMNS) - set(header.columns))
        if missing:
            raise ValueError(
                "EPA hourly CSV is missing required columns: "
                + ", ".join(missing)
            )

    return {
        "zip_path": str(zip_path.resolve()),
        "zip_size_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256_file(zip_path),
        "csv_member": member,
        "source_url": AIRDATA_URL,
    }


def _chunk_iterator(
    zip_path: Path,
    member: str,
    *,
    chunksize: int,
) -> Iterator[pd.DataFrame]:
    archive = zipfile.ZipFile(zip_path)
    stream = archive.open(member)
    try:
        reader = pd.read_csv(
            stream,
            usecols=list(EXPECTED_COLUMNS),
            dtype={
                "State Code": "string",
                "County Code": "string",
                "Site Num": "string",
                "Parameter Code": "string",
                "POC": "string",
                "Latitude": "string",
                "Longitude": "string",
                "Date GMT": "string",
                "Time GMT": "string",
                "Sample Measurement": "string",
                "Method Code": "string",
            },
            chunksize=chunksize,
            low_memory=False,
        )
        for chunk in reader:
            yield chunk
    finally:
        stream.close()
        archive.close()


def load_alameda_pm25_observations(
    path: str | Path,
    *,
    chunksize: int = 250_000,
    minimum_zip_size_bytes: int = 1_000_000,
) -> tuple[list[NormalizedObservation], dict[str, Any]]:
    zip_path = Path(path)
    metadata = validate_airdata_zip(
        zip_path,
        minimum_size_bytes=minimum_zip_size_bytes,
    )
    member = str(metadata["csv_member"])
    retrieved_at = datetime.now(UTC)

    observations: list[NormalizedObservation] = []
    scanned_rows = 0
    geographic_rows = 0
    invalid_rows = 0
    method_names: set[str] = set()
    units: set[str] = set()

    for chunk in _chunk_iterator(
        zip_path,
        member,
        chunksize=chunksize,
    ):
        scanned_rows += len(chunk)
        state = chunk["State Code"].str.zfill(2)
        county = chunk["County Code"].str.zfill(3)
        parameter = chunk["Parameter Code"].str.zfill(5)
        selected = chunk.loc[
            (state == "06")
            & (county == "001")
            & (parameter == "88101")
        ].copy()
        geographic_rows += len(selected)
        if selected.empty:
            continue

        timestamps = pd.to_datetime(
            selected["Date GMT"].astype(str)
            + " "
            + selected["Time GMT"].astype(str),
            utc=True,
            errors="coerce",
        )
        measurements = pd.to_numeric(
            selected["Sample Measurement"],
            errors="coerce",
        )
        latitudes = pd.to_numeric(
            selected["Latitude"],
            errors="coerce",
        )
        longitudes = pd.to_numeric(
            selected["Longitude"],
            errors="coerce",
        )

        valid = (
            timestamps.notna()
            & measurements.notna()
            & latitudes.notna()
            & longitudes.notna()
        )
        invalid_rows += int((~valid).sum())
        selected = selected.loc[valid].copy()
        timestamps = timestamps.loc[valid]
        measurements = measurements.loc[valid]
        latitudes = latitudes.loc[valid]
        longitudes = longitudes.loc[valid]

        for index, row in selected.iterrows():
            station_id = (
                f"{str(row['State Code']).zfill(2)}-"
                f"{str(row['County Code']).zfill(3)}-"
                f"{str(row['Site Num']).zfill(4)}"
            )
            method_name = str(row.get("Method Name") or "unknown")
            method_names.add(method_name)
            unit = str(row.get("Units of Measure") or "source-unit")
            units.add(unit)
            qualifier = str(row.get("Qualifier") or "none")
            poc = str(row.get("POC") or "")
            timestamp = timestamps.loc[index].to_pydatetime()
            value = float(measurements.loc[index])

            observations.append(
                NormalizedObservation(
                    source_name="US EPA AirData",
                    source_dataset=(
                        "Pre-generated hourly PM2.5 FRM/FEM Mass "
                        "(88101), 2025"
                    ),
                    source_record_id=(
                        f"{station_id}:88101:{poc}:"
                        f"{timestamp.isoformat()}"
                    ),
                    station_id=station_id,
                    latitude=float(latitudes.loc[index]),
                    longitude=float(longitudes.loc[index]),
                    country="US",
                    region=str(
                        row.get("State Name") or "California"
                    ),
                    city=None,
                    timestamp_utc=timestamp,
                    timestamp_local=None,
                    timezone="UTC",
                    variable="pm25",
                    value=value,
                    unit=unit,
                    measurement_type=MeasurementType.OBSERVED,
                    quality_flag=(
                        "sample_duration=1 HOUR;"
                        f"method_type={row.get('Method Type') or 'unknown'};"
                        f"method_code={row.get('Method Code') or 'unknown'};"
                        f"method_name={method_name};"
                        f"qualifier={qualifier};"
                        f"poc={poc};"
                        "source=EPA_AirData_hourly_bulk"
                    ),
                    data_status="available",
                    retrieved_at=retrieved_at,
                    license=(
                        "United States government data; retain EPA "
                        "method, qualifier, monitor, and source metadata"
                    ),
                    source_url=AIRDATA_URL,
                )
            )

    if not observations:
        raise ValueError(
            "No Alameda County PM2.5 observations were found in the "
            "official EPA hourly file"
        )

    observations.sort(
        key=lambda item: (
            item.timestamp_utc,
            item.station_id or "",
            item.source_record_id or "",
        )
    )
    report = {
        **metadata,
        "scanned_national_rows": scanned_rows,
        "matched_alameda_rows": geographic_rows,
        "normalized_observations": len(observations),
        "invalid_matched_rows_removed": invalid_rows,
        "unique_stations": len(
            {
                item.station_id
                for item in observations
                if item.station_id
            }
        ),
        "method_names": sorted(method_names),
        "units": sorted(units),
        "filter": {
            "state_code": "06",
            "county_code": "001",
            "parameter_code": "88101",
        },
        "data_advisory": (
            "EPA currently publishes a PM2.5 advisory for some "
            "pre-generated 88101 method records. Method names are "
            "preserved for later sensitivity analysis; no method is "
            "silently excluded in this first benchmark."
        ),
    }
    return observations, report


def run_bulk_experiment(
    config_path: str | Path,
    *,
    bulk_zip: str | Path,
    workspace: str | Path,
    repository_root: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    real_path = Path(config_path).resolve()
    real_config = _load_real_config(real_path)
    snapshot_config, snapshot_config_path = _load_snapshot_config(
        real_config,
        real_config_path=real_path,
    )

    output_root = Path(workspace)
    _prepare_workspace(output_root, overwrite=overwrite)
    plan_path = write_real_experiment_plan(
        real_path,
        output_root / "execution-plan.json",
    )

    observations, bulk_report = load_alameda_pm25_observations(
        bulk_zip
    )
    raw_root = output_root / "raw-source"
    raw_root.mkdir(parents=True, exist_ok=True)
    bulk_report_path = raw_root / "bulk-source-report.json"
    bulk_report_path.write_text(
        json.dumps(bulk_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    snapshot_release = freeze_official_snapshot(
        observations,
        config=snapshot_config,
        output_root=output_root / "official-snapshots",
        registry_root=output_root / "registry",
        repository_root=repository_root,
        acquisition_mode=AcquisitionMode.NORMALIZED_JSONL,
        overwrite=overwrite,
    )
    if not snapshot_release.quality_gate.passed:
        raise RuntimeError(
            "The official bulk snapshot quality gate did not pass: "
            + "; ".join(snapshot_release.quality_gate.reasons)
        )

    snapshot_directory = Path(snapshot_release.snapshot_directory)
    frozen_observations = load_observations(snapshot_directory)
    frame, selection_report = prepare_hourly_station_frame(
        frozen_observations,
        real_config.station_policy,
    )

    prepared_root = output_root / "prepared"
    prepared_root.mkdir(parents=True, exist_ok=True)
    prepared_csv = prepared_root / "selected-station-hourly.csv"
    frame.to_csv(prepared_csv, index=False)
    selection_path = prepared_root / "station-selection-report.json"
    selection_path.write_text(
        json.dumps(selection_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    selected_station = str(
        selection_report["selected_station"]["station_id"]
    )
    source_spec = ExperimentSpec(
        experiment_id=real_config.experiment_id + "-bulk",
        title=real_config.title + " — EPA AirData Bulk Route",
        description=(
            real_config.description
            + " The official pre-generated hourly AirData file "
            "was used because the synchronous AQS API endpoint was "
            "not reachable from the execution network."
        ),
        dataset=DatasetSpec(
            kind="csv",
            path="prepared/selected-station-hourly.csv",
            seed=real_config.random_state,
            variables=(real_config.station_policy.target_variable,),
            frequency="1h",
        ),
        nexus=NexusConfig(
            timestamp_column="timestamp",
            target_column=real_config.station_policy.target_variable,
            feature_columns=(),
            horizons=real_config.horizons,
            event_threshold=real_config.event_threshold,
            alpha=real_config.alpha,
            random_state=real_config.random_state,
            minimum_valid_rows=real_config.minimum_valid_rows,
            rolling_origin_step=real_config.rolling_origin_step,
            rolling_origin_max_origins=(
                real_config.rolling_origin_max_origins
            ),
            expected_frequency="1h",
        ),
        report=ReportSpec(
            title=real_config.title + " — Bulk AirData Route",
            subtitle=(
                "Official EPA pre-generated hourly PM2.5 "
                "forecasting experiment"
            ),
            author=real_config.created_by,
            organization="HeatSafe Research Lab",
            abstract=(
                "This report evaluates an hourly PM2.5 forecasting "
                "benchmark from the official US EPA AirData 2025 "
                "pre-generated file. Alameda County rows are filtered "
                "locally, normalized into an immutable snapshot, and "
                "a monitoring station is selected deterministically "
                "by temporal continuity."
            ),
            keywords=(
                "US EPA AirData",
                "PM2.5",
                "official bulk data",
                "Alameda County",
                "forecasting",
                "reproducibility",
            ),
        ),
        release=ReleaseSpec(
            version=real_config.release_version,
            status="candidate",
            create_zip=True,
            license="CC-BY-4.0",
        ),
        notes=(
            "Official source: US EPA AirData hourly 88101 file.",
            f"Bulk source SHA-256: {bulk_report['zip_sha256']}.",
            f"Selected monitoring station: {selected_station}.",
            "No API credential was used for the bulk route.",
            "No missing target values are imputed in the selected segment.",
            "EPA PM2.5 method metadata are retained for sensitivity review.",
        ),
        limitations=(
            *real_config.limitations,
            (
                "The national bulk file is updated periodically; "
                "the exact downloaded ZIP checksum defines this run."
            ),
            (
                "The current EPA PM2.5 pre-generated-file advisory "
                "requires method-level sensitivity review before "
                "publication claims."
            ),
        ),
        created_by=real_config.created_by,
    )
    experiment_spec_path = output_root / "real-experiment-spec.json"
    experiment_spec_path.write_text(
        source_spec.model_dump_json(indent=2),
        encoding="utf-8",
    )

    experiment_result = run_experiment(
        source_spec,
        spec_path=experiment_spec_path,
        output_directory=output_root / "experiment",
        repository_root=repository_root,
        overwrite=overwrite,
    )

    snapshot_manifest = snapshot_directory / "manifest.json"
    master = {
        "experiment_id": source_spec.experiment_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "created_by": real_config.created_by,
        "acquisition_route": "EPA AirData pre-generated bulk file",
        "source_url": AIRDATA_URL,
        "bulk_zip": str(Path(bulk_zip).resolve()),
        "bulk_zip_sha256": bulk_report["zip_sha256"],
        "bulk_report": str(bulk_report_path),
        "source_id": snapshot_config.source_id,
        "dataset_id": snapshot_config.dataset_id,
        "dataset_version": snapshot_config.version,
        "snapshot_config_path": str(snapshot_config_path),
        "execution_plan_path": str(plan_path),
        "execution_plan_sha256": sha256_file(plan_path),
        "snapshot_directory": str(snapshot_directory),
        "snapshot_manifest_sha256": sha256_file(snapshot_manifest),
        "snapshot_quality_gate": (
            snapshot_release.quality_gate.model_dump(mode="json")
        ),
        "snapshot_integrity": snapshot_release.snapshot_integrity,
        "registry_integrity": snapshot_release.registry_integrity,
        "selected_station": selection_report["selected_station"],
        "prepared_csv": str(prepared_csv),
        "prepared_csv_sha256": sha256_file(prepared_csv),
        "selection_report": str(selection_path),
        "selection_report_sha256": sha256_file(selection_path),
        "experiment_output": experiment_result.model_dump(mode="json"),
        "scientific_boundary": (
            "This is a reproducible station-level forecasting "
            "benchmark from an official EPA bulk data identity. "
            "It does not represent personal exposure, countywide "
            "conditions, causal effects, medical risk, or official "
            "warning authority."
        ),
    }
    manifest_path = output_root / "real-official-experiment-manifest.json"
    manifest_path.write_text(
        json.dumps(master, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_open_report_scripts(output_root)

    verification = verify_real_official_experiment(output_root)
    if not verification["valid"]:
        raise RuntimeError(
            "The bulk official experiment failed verification: "
            + "; ".join(verification["failures"])
        )

    return {
        "workspace": str(output_root),
        "manifest": str(manifest_path),
        "bulk_zip_sha256": bulk_report["zip_sha256"],
        "matched_alameda_rows": bulk_report[
            "matched_alameda_rows"
        ],
        "selected_station": selected_station,
        "selected_segment_rows": selection_report[
            "selected_segment_rows"
        ],
        "report_html": experiment_result.report_html,
        "candidate_release": experiment_result.release_archive,
        "verification": verification,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="heatsafe-epa-bulk-experiment",
        description=(
            "Run the first real EPA experiment from the official "
            "pre-generated hourly AirData ZIP"
        ),
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--zip", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repository-root")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_bulk_experiment(
        args.config,
        bulk_zip=args.zip,
        workspace=args.workspace,
        repository_root=args.repository_root,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
