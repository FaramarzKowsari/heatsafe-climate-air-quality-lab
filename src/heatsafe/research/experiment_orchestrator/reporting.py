from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from heatsafe.research.experiment_orchestrator.contracts import ExperimentSpec
from heatsafe.research.nexus.contracts import ForecastMetric, NexusReport


def _metric_mapping(metric: ForecastMetric) -> dict[str, object]:
    return metric.model_dump(mode="json")


def _best_metrics(report: NexusReport) -> list[ForecastMetric]:
    best: list[ForecastMetric] = []
    for horizon in report.horizons:
        model_name = report.best_by_horizon[horizon]
        match = next(
            metric
            for metric in report.metrics
            if metric.horizon_hours == horizon and metric.model == model_name
        )
        best.append(match)
    return best


def write_paper_tables(
    report: NexusReport,
    output_directory: str | Path,
) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)

    metrics_path = root / "all-model-metrics.csv"
    rolling_path = root / "rolling-origin-metrics.csv"
    best_path = root / "best-by-horizon.csv"
    summary_path = root / "results-summary.json"

    metric_rows = [_metric_mapping(metric) for metric in report.metrics]
    if metric_rows:
        with metrics_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(metric_rows[0]))
            writer.writeheader()
            writer.writerows(metric_rows)

    rolling_rows = [
        metric.model_dump(mode="json")
        for metric in report.rolling_origin_metrics
    ]
    with rolling_path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = [
            "model",
            "horizon_hours",
            "origins",
            "mae",
            "rmse",
            "mean_bias",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rolling_rows)

    best_rows = [
        {
            "horizon_hours": metric.horizon_hours,
            "model": metric.model,
            "mae": metric.mae,
            "rmse": metric.rmse,
            "event_f1": metric.event_f1,
            "prediction_interval_coverage": metric.prediction_interval_coverage,
            "mean_interval_width": metric.mean_interval_width,
        }
        for metric in _best_metrics(report)
    ]
    with best_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(best_rows[0]))
        writer.writeheader()
        writer.writerows(best_rows)

    summary = {
        "benchmark_name": report.benchmark_name,
        "benchmark_version": report.benchmark_version,
        "target": report.target,
        "horizons": report.horizons,
        "best_by_horizon": report.best_by_horizon,
        "dataset_summary": report.dataset_summary,
        "split_description": report.split_description,
        "leakage_controls": report.leakage_controls,
        "limitations": report.limitations,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "all_model_metrics": str(metrics_path),
        "rolling_origin_metrics": str(rolling_path),
        "best_by_horizon": str(best_path),
        "results_summary": str(summary_path),
    }


def _svg_bar_chart(
    *,
    title: str,
    labels: Iterable[str],
    values: Iterable[float],
    output: Path,
    value_suffix: str = "",
    maximum: float | None = None,
) -> Path:
    label_list = list(labels)
    value_list = [float(value) for value in values]
    if not label_list or len(label_list) != len(value_list):
        raise ValueError("Chart labels and values must be non-empty and aligned")

    width = 960
    left = 170
    right = 60
    top = 78
    row_height = 54
    height = top + row_height * len(label_list) + 60
    chart_width = width - left - right
    upper = maximum if maximum is not None else max(value_list)
    upper = upper if upper > 0 else 1.0

    rows: list[str] = []
    for index, (label, value) in enumerate(zip(label_list, value_list, strict=True)):
        y = top + index * row_height
        bar_width = max(1.0, chart_width * min(max(value / upper, 0.0), 1.0))
        rows.append(
            f'<text x="{left - 12}" y="{y + 22}" text-anchor="end">'
            f"{html.escape(label)}</text>"
        )
        rows.append(
            f'<rect x="{left}" y="{y}" width="{bar_width:.2f}" height="28" rx="5"/>'
        )
        rows.append(
            f'<text x="{left + bar_width + 10:.2f}" y="{y + 21}">'
            f"{value:.3f}{html.escape(value_suffix)}</text>"
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{html.escape(title)}</title>\n'
        '<desc id="desc">Horizontal bar chart generated from the experiment results.</desc>\n'
        '<style>text{font:15px system-ui,sans-serif;fill:currentColor}'
        'rect{fill:currentColor;opacity:.72}</style>\n'
        '<text x="28" y="42" style="font-size:24px;font-weight:700">'
        f"{html.escape(title)}</text>\n"
        + "\n".join(rows)
        + "\n</svg>\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    return output


def write_paper_figures(
    report: NexusReport,
    output_directory: str | Path,
) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    best = _best_metrics(report)
    labels = [f"{metric.horizon_hours}h · {metric.model}" for metric in best]

    mae = _svg_bar_chart(
        title="Best-model MAE by forecast horizon",
        labels=labels,
        values=[metric.mae for metric in best],
        output=root / "best-mae-by-horizon.svg",
    )
    coverage = _svg_bar_chart(
        title="Prediction-interval coverage for the best model",
        labels=labels,
        values=[metric.prediction_interval_coverage for metric in best],
        output=root / "coverage-by-horizon.svg",
        maximum=1.0,
    )
    event_f1 = _svg_bar_chart(
        title="Event F1 for the best model",
        labels=labels,
        values=[metric.event_f1 for metric in best],
        output=root / "event-f1-by-horizon.svg",
        maximum=1.0,
    )
    return {
        "best_mae": str(mae),
        "coverage": str(coverage),
        "event_f1": str(event_f1),
    }


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    head = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(clean(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([head, separator, *body])


def _html_table(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "\n".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def write_paper_reports(
    *,
    spec: ExperimentSpec,
    report: NexusReport,
    dataset_descriptor: Mapping[str, Any],
    output_directory: str | Path,
) -> dict[str, str]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    markdown_path = root / "report.md"
    html_path = root / "report.html"

    best = _best_metrics(report)
    best_rows = [
        [
            metric.horizon_hours,
            metric.model,
            metric.mae,
            metric.rmse,
            metric.event_f1,
            metric.prediction_interval_coverage,
            metric.mean_interval_width,
        ]
        for metric in best
    ]
    all_rows = [
        [
            metric.horizon_hours,
            metric.model,
            metric.mae,
            metric.rmse,
            metric.mean_bias,
            metric.r2,
            metric.event_f1,
            metric.prediction_interval_coverage,
            metric.mean_interval_width,
        ]
        for metric in report.metrics
    ]
    best_headers = [
        "Horizon (h)",
        "Best model",
        "MAE",
        "RMSE",
        "Event F1",
        "Coverage",
        "Interval width",
    ]
    all_headers = [
        "Horizon (h)",
        "Model",
        "MAE",
        "RMSE",
        "Bias",
        "R²",
        "Event F1",
        "Coverage",
        "Interval width",
    ]

    limitations = tuple(dict.fromkeys((*spec.limitations, *report.limitations)))
    notes = tuple(dict.fromkeys((*spec.notes, *report.leakage_controls)))

    markdown = f"""# {spec.report.title}

**{spec.report.subtitle}**

- **Experiment ID:** `{spec.experiment_id}`
- **Author:** {spec.report.author}
- **Organization:** {spec.report.organization}
- **Release:** {spec.release.version} ({spec.release.status})
- **Target:** `{report.target}`
- **Forecast horizons:** {", ".join(f"{value}h" for value in report.horizons)}
- **Data kind:** `{dataset_descriptor.get("kind")}`
- **Canonical input SHA-256:** `{dataset_descriptor.get("canonical_sha256")}`

## Abstract

{spec.report.abstract}

## Experimental design

{spec.description}

The benchmark uses {report.split_description.lower()} The complete configuration is stored in
`../experiment-spec.json`, and the canonical input table is stored in `../data/input.csv`.

## Dataset identity

- Rows: {dataset_descriptor.get("rows")}
- Columns: {", ".join(str(value) for value in dataset_descriptor.get("columns", []))}
- Source path: {dataset_descriptor.get("source_path") or "generated deterministically"}
- Synthetic seed: {dataset_descriptor.get("synthetic_seed")}

## Best model by horizon

{_markdown_table(best_headers, best_rows)}

## Complete results

{_markdown_table(all_headers, all_rows)}

## Figures

- [Best-model MAE](../figures/best-mae-by-horizon.svg)
- [Prediction-interval coverage](../figures/coverage-by-horizon.svg)
- [Event F1](../figures/event-f1-by-horizon.svg)

## Leakage controls and notes

{chr(10).join(f"- {value}" for value in notes)}

## Limitations

{chr(10).join(f"- {value}" for value in limitations)}

## Reproduction

Linux or macOS:

```bash
bash ../reproduce.sh
```

Windows:

```bat
..\\reproduce.cmd
```

Verify checksums:

```bash
heatsafe-experiment verify ..
```

The candidate release archive is generated without minting or claiming a DOI.
"""
    markdown_path.write_text(markdown, encoding="utf-8")

    limitation_html = "".join(f"<li>{html.escape(value)}</li>" for value in limitations)
    note_html = "".join(f"<li>{html.escape(value)}</li>" for value in notes)
    keyword_text = ", ".join(spec.report.keywords)
    html_report = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(spec.report.title)}</title>
<meta name="author" content="{html.escape(spec.report.author)}">
<meta name="description" content="{html.escape(spec.report.abstract)}">
<style>
body{{font-family:system-ui,sans-serif;line-height:1.62;margin:0;color:#17252b;background:#f7fafb}}
main{{max-width:1120px;margin:auto;padding:42px 24px 70px}}
header,section{{background:#fff;border:1px solid #dce7ea;border-radius:18px;padding:26px;margin:0 0 22px}}
h1{{font-size:2rem;margin:.2rem 0}}h2{{margin-top:0}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}}
.meta div{{padding:12px;border-radius:12px;background:#f4f8f9}}
table{{width:100%;border-collapse:collapse;font-size:.88rem}}th,td{{padding:9px;border-bottom:1px solid #dce7ea;text-align:left}}
.table-wrap{{overflow:auto}}img{{display:block;width:100%;height:auto;border:1px solid #dce7ea;border-radius:14px;margin:14px 0}}
code{{background:#eef4f5;padding:.12rem .3rem;border-radius:5px}}pre{{overflow:auto;background:#17252b;color:#fff;padding:16px;border-radius:12px}}
.small{{color:#60757c;font-size:.9rem}}
</style>
</head>
<body><main>
<header>
<p class="small">{html.escape(spec.report.organization)} · Reproducible experiment report</p>
<h1>{html.escape(spec.report.title)}</h1>
<p>{html.escape(spec.report.subtitle)}</p>
<div class="meta">
<div><strong>Experiment</strong><br><code>{html.escape(spec.experiment_id)}</code></div>
<div><strong>Author</strong><br>{html.escape(spec.report.author)}</div>
<div><strong>Release</strong><br>{html.escape(spec.release.version)} · {html.escape(spec.release.status)}</div>
<div><strong>Target</strong><br><code>{html.escape(report.target)}</code></div>
<div><strong>Rows</strong><br>{html.escape(str(dataset_descriptor.get("rows")))}</div>
<div><strong>Keywords</strong><br>{html.escape(keyword_text)}</div>
</div>
</header>
<section><h2>Abstract</h2><p>{html.escape(spec.report.abstract)}</p></section>
<section><h2>Experimental design</h2><p>{html.escape(spec.description)}</p>
<p>{html.escape(report.split_description)}</p></section>
<section><h2>Best model by horizon</h2><div class="table-wrap">{_html_table(best_headers, best_rows)}</div></section>
<section><h2>Complete results</h2><div class="table-wrap">{_html_table(all_headers, all_rows)}</div></section>
<section><h2>Figures</h2>
<img src="../figures/best-mae-by-horizon.svg" alt="Best-model MAE by forecast horizon">
<img src="../figures/coverage-by-horizon.svg" alt="Prediction interval coverage by horizon">
<img src="../figures/event-f1-by-horizon.svg" alt="Event F1 by horizon">
</section>
<section><h2>Leakage controls and notes</h2><ul>{note_html}</ul></section>
<section><h2>Limitations</h2><ul>{limitation_html}</ul></section>
<section><h2>Reproduction</h2>
<p>Use the self-contained canonical input and normalized experiment specification.</p>
<pre><code>heatsafe-experiment run --spec experiment-spec.json --output reproduced-run --repository-root . --overwrite
heatsafe-experiment verify reproduced-run</code></pre>
<p class="small">This candidate bundle does not mint or claim a DOI.</p>
</section>
</main></body></html>
"""
    html_path.write_text(html_report, encoding="utf-8")
    return {"markdown": str(markdown_path), "html": str(html_path)}
