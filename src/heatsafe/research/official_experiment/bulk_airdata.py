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
        "airdata_product_type": "official EPA hourly data file",
        "sample_duration_inference": (
            "1 HOUR inferred from the official hourly-file product "
            "identity; the hourly schema has no Sample Duration column"
        ),
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


def _numeric_code(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0+$", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def _format_code(value: object, width: int) -> str:
    converted = pd.to_numeric(
        pd.Series([value], dtype="object"),
        errors="coerce",
    ).iloc[0]
    if pd.notna(converted):
        return f"{int(converted):0{width}d}"

    cleaned = str(value).strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    return cleaned.zfill(width)


def _county_name_value(frame: pd.DataFrame) -> str:
    names = (
        frame["County Name"]
        .astype("string")
        .dropna()
        .str.strip()
    )
    names = names[names != ""]
    return str(names.iloc[0]) if not names.empty else "Unknown"


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

    requested_state_code = 6
    requested_county_code = 1
    parameter_code = 88101

    requested_chunks: list[pd.DataFrame] = []
    county_hourly_counts: dict[tuple[int, str], int] = {}
    scanned_rows = 0
    california_parameter_rows = 0
    california_hourly_rows = 0

    for chunk in _chunk_iterator(
        zip_path,
        member,
        chunksize=chunksize,
    ):
        scanned_rows += len(chunk)
        state = _numeric_code(chunk["State Code"])
        county = _numeric_code(chunk["County Code"])
        parameter = _numeric_code(chunk["Parameter Code"])
        california_parameter = (
            (state == requested_state_code)
            & (parameter == parameter_code)
        )
        california_parameter_rows += int(california_parameter.sum())

        eligible = california_parameter
        california_hourly_rows += int(eligible.sum())
        if not bool(eligible.any()):
            continue

        eligible_frame = chunk.loc[eligible].copy()
        eligible_county_codes = county.loc[eligible]

        for county_value in sorted(
            {
                int(value)
                for value in eligible_county_codes.dropna().tolist()
            }
        ):
            county_rows = eligible_frame.loc[
                eligible_county_codes == county_value
            ]
            county_name = _county_name_value(county_rows)
            key = (county_value, county_name)
            county_hourly_counts[key] = (
                county_hourly_counts.get(key, 0)
                + int(len(county_rows))
            )

        requested_mask = eligible & (county == requested_county_code)
        if bool(requested_mask.any()):
            requested_chunks.append(chunk.loc[requested_mask].copy())

    fallback_used = not requested_chunks
    if requested_chunks:
        selected_county_code = requested_county_code
        raw_selected = pd.concat(
            requested_chunks,
            ignore_index=True,
        )
        selected_county_name = _county_name_value(raw_selected)
        fallback_reason = None
    else:
        if not county_hourly_counts:
            raise ValueError(
                "The official EPA hourly 88101 file contains no "
                "California rows for parameter 88101. "
                "Scanned national rows: "
                f"{scanned_rows}; California 88101 rows: "
                f"{california_parameter_rows}."
            )

        ranked_counties = sorted(
            county_hourly_counts.items(),
            key=lambda item: (
                -item[1],
                item[0][0],
                item[0][1],
            ),
        )
        (
            selected_county_code,
            selected_county_name,
        ), _ = ranked_counties[0]
        fallback_reason = (
            "Alameda County had no 88101 rows in the downloaded "
            "official hourly file. The California county with the "
            "largest number of 88101 hourly-file rows was selected "
            "using a deterministic row-count rule."
        )

        fallback_chunks: list[pd.DataFrame] = []
        for chunk in _chunk_iterator(
            zip_path,
            member,
            chunksize=chunksize,
        ):
            state = _numeric_code(chunk["State Code"])
            county = _numeric_code(chunk["County Code"])
            parameter = _numeric_code(chunk["Parameter Code"])
            selected_mask = (
                (state == requested_state_code)
                & (county == selected_county_code)
                & (parameter == parameter_code)
            )
            if bool(selected_mask.any()):
                fallback_chunks.append(
                    chunk.loc[selected_mask].copy()
                )

        if not fallback_chunks:
            raise RuntimeError(
                "The fallback county was selected but its rows "
                "could not be loaded during the second pass"
            )
        raw_selected = pd.concat(
            fallback_chunks,
            ignore_index=True,
        )

    timestamps = pd.to_datetime(
        raw_selected["Date GMT"].astype(str)
        + " "
        + raw_selected["Time GMT"].astype(str),
        utc=True,
        errors="coerce",
    )
    measurements = pd.to_numeric(
        raw_selected["Sample Measurement"],
        errors="coerce",
    )
    latitudes = pd.to_numeric(
        raw_selected["Latitude"],
        errors="coerce",
    )
    longitudes = pd.to_numeric(
        raw_selected["Longitude"],
        errors="coerce",
    )

    valid = (
        timestamps.notna()
        & measurements.notna()
        & latitudes.notna()
        & longitudes.notna()
    )
    invalid_rows = int((~valid).sum())
    selected = raw_selected.loc[valid].copy()
    timestamps = timestamps.loc[valid]
    measurements = measurements.loc[valid]
    latitudes = latitudes.loc[valid]
    longitudes = longitudes.loc[valid]

    observations: list[NormalizedObservation] = []
    method_names: set[str] = set()
    units: set[str] = set()

    for index, row in selected.iterrows():
        station_id = (
            f"{_format_code(row['State Code'], 2)}-"
            f"{_format_code(row['County Code'], 3)}-"
            f"{_format_code(row['Site Num'], 4)}"
        )
        method_name = str(row.get("Method Name") or "unknown")
        method_names.add(method_name)
        unit = str(row.get("Units of Measure") or "source-unit")
        units.add(unit)
        qualifier = str(row.get("Qualifier") or "none")
        poc = _format_code(row.get("POC"), 1)
        timestamp = timestamps.loc[index].to_pydatetime()
        value = float(measurements.loc[index])
        sample_duration = "1 HOUR"
        sample_duration_source = (
            "inferred_from_official_epa_hourly_file_identity"
        )

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
                    f"sample_duration={sample_duration};"
                    f"sample_duration_source={sample_duration_source};"
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
            "The selected California county contained no valid "
            "hourly PM2.5 observations after timestamp, value, "
            "and coordinate validation"
        )

    observations.sort(
        key=lambda item: (
            item.timestamp_utc,
            item.station_id or "",
            item.source_record_id or "",
        )
    )

    ranked_counties_payload = [
        {
            "county_code": f"{code:03d}",
            "county_name": name,
            "hourly_rows": count,
        }
        for (code, name), count in sorted(
            county_hourly_counts.items(),
            key=lambda item: (
                -item[1],
                item[0][0],
                item[0][1],
            ),
        )[:25]
    ]

    report = {
        **metadata,
        "scanned_national_rows": scanned_rows,
        "california_88101_rows": california_parameter_rows,
        "california_hourly_88101_rows": california_hourly_rows,
        "requested_geography": {
            "state_code": "06",
            "state_name": "California",
            "county_code": "001",
            "county_name": "Alameda",
        },
        "selected_geography": {
            "state_code": "06",
            "state_name": "California",
            "county_code": f"{selected_county_code:03d}",
            "county_name": selected_county_name,
        },
        "geography_fallback_used": fallback_used,
        "geography_fallback_reason": fallback_reason,
        "matched_selected_county_rows": int(len(raw_selected)),
        "matched_alameda_rows": (
            int(len(raw_selected)) if not fallback_used else 0
        ),
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
        "top_california_counties_by_hourly_rows": (
            ranked_counties_payload
        ),
        "filter": {
            "state_code": "06",
            "county_code": f"{selected_county_code:03d}",
            "parameter_code": "88101",
            "sample_duration": "1 HOUR",
            "sample_duration_source": (
                "official EPA hourly-file identity"
            ),
        },
        "selection_policy": (
            "Use Alameda County when 88101 rows exist in the "
            "official hourly file. Otherwise choose the California "
            "county with the largest number of hourly-file 88101 rows, "
            "breaking "
            "ties by county code and county name."
        ),
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
    selected_geography = bulk_report["selected_geography"]
    selected_county_code = str(
        selected_geography["county_code"]
    )
    selected_county_name = str(
        selected_geography["county_name"]
    )
    geography_label = (
        f"{selected_county_name} County, California"
    )

    if bulk_report["geography_fallback_used"]:
        snapshot_config = snapshot_config.model_copy(
            update={
                "dataset_id": (
                    "epa-airdata-ca-"
                    f"{selected_county_code}-pm25-2025"
                ),
                "title": (
                    "EPA AirData "
                    f"{geography_label} hourly PM2.5 2025 snapshot"
                ),
                "description": (
                    "An immutable official-source snapshot of US EPA "
                    "AirData hourly PM2.5 measurements for "
                    f"{geography_label} during 2025. Alameda County "
                    "was requested first but had no explicit one-hour "
                    "88101 rows in the downloaded file."
                ),
            }
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
        title=(
            f"US EPA AirData {geography_label} PM2.5 "
            "Forecasting Benchmark — 2025"
        ),
        description=(
            "A reproducible official-source PM2.5 forecasting "
            f"experiment for {geography_label}. The official "
            "pre-generated hourly AirData file was used because the "
            "synchronous AQS API endpoint was not reachable from the "
            "execution network. Alameda County was requested first; "
            "a deterministic California coverage fallback is used "
            "only when Alameda has no explicit one-hour 88101 rows."
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
            title=(
                f"US EPA AirData {geography_label} PM2.5 "
                "Forecasting Benchmark — Bulk Route"
            ),
            subtitle=(
                "Official EPA pre-generated hourly PM2.5 "
                "forecasting experiment"
            ),
            author=real_config.created_by,
            organization="HeatSafe Research Lab",
            abstract=(
                "This report evaluates an hourly PM2.5 forecasting "
                "benchmark from the official US EPA AirData 2025 "
                "pre-generated file. Rows for "
                f"{geography_label} are filtered locally, normalized "
                "into an immutable snapshot, and "
                "a monitoring station is selected deterministically "
                "by temporal continuity."
            ),
            keywords=(
                "US EPA AirData",
                "PM2.5",
                "official bulk data",
                geography_label,
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
            f"Selected geography: {geography_label}.",
            (
                "Geography fallback used: "
                f"{bulk_report['geography_fallback_used']}."
            ),
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
        "requested_geography": bulk_report["requested_geography"],
        "selected_geography": bulk_report["selected_geography"],
        "geography_fallback_used": (
            bulk_report["geography_fallback_used"]
        ),
        "geography_fallback_reason": (
            bulk_report["geography_fallback_reason"]
        ),
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
        "selected_geography": bulk_report["selected_geography"],
        "geography_fallback_used": (
            bulk_report["geography_fallback_used"]
        ),
        "matched_selected_county_rows": bulk_report[
            "matched_selected_county_rows"
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
