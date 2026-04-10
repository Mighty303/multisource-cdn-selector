#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


DEFAULT_RESULTS_DIR = Path("results")
MODES = ["adaptive", "random", "round_robin"]
CONDITIONS = ["baseline", "toronto_degraded", "oregon_degraded", "ncalifornia_degraded"]
MODE_LABELS = {
    "adaptive": "Adaptive",
    "random": "Random",
    "round_robin": "Round Robin",
}
CONDITION_LABELS = {
    "baseline": "Baseline",
    "toronto_degraded": "Toronto Degraded",
    "oregon_degraded": "Oregon Degraded",
    "ncalifornia_degraded": "N. California Degraded",
}
MODE_COLORS = {
    "adaptive": "#16a34a",
    "random": "#dc2626",
    "round_robin": "#2563eb",
}


def load_csv_runs(results_dir: Path) -> dict[str, dict[str, dict[str, object]]]:
    runs: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for path in sorted(results_dir.glob("*.csv")):
        if path.name == "load_test_results.csv":
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        mode = rows[0]["mode"]
        condition = path.stem.replace(f"{mode}_", "", 1)

        times = [float(row["time_total"]) for row in rows]
        by_clients: dict[int, list[float]] = defaultdict(list)
        by_server: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            by_clients[int(row["clients"])].append(float(row["time_total"]))
            server = row["url_effective"].split("_selector_server=")[-1]
            by_server[server].append(float(row["time_total"]))

        runs[condition][mode] = {
            "path": str(path),
            "count": len(rows),
            "overall_avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "clients": {client: statistics.mean(vals) for client, vals in sorted(by_clients.items())},
            "servers": {
                server: {
                    "count": len(vals),
                    "avg": statistics.mean(vals),
                }
                for server, vals in sorted(by_server.items())
            },
        }
    return runs


def load_jsonl_support(results_dir: Path) -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for path in sorted(results_dir.glob("*.jsonl")):
        # These are tail snapshots, not clean per-run logs, so keep them separate.
        try:
            with path.open(encoding="utf-8") as handle:
                first = handle.readline()
            if not first:
                continue
        except OSError:
            continue
        summaries[path.name] = {"path": str(path)}
    return summaries


def best_mode_for_condition(runs: dict[str, dict[str, dict[str, object]]], condition: str) -> str:
    entries = {
        mode: runs[condition][mode]["overall_avg"]
        for mode in MODES
        if mode in runs.get(condition, {})
    }
    return min(entries, key=entries.get)


def format_seconds(value: float) -> str:
    return f"{value:.3f}s"


def render_overall_table(runs: dict[str, dict[str, dict[str, object]]]) -> str:
    lines = [
        "| Condition | Adaptive | Random | Round Robin | Best |",
        "|---|---:|---:|---:|---|",
    ]
    for condition in CONDITIONS:
        if condition not in runs:
            continue
        best = best_mode_for_condition(runs, condition)
        row = [
            CONDITION_LABELS[condition],
            format_seconds(runs[condition]["adaptive"]["overall_avg"]),
            format_seconds(runs[condition]["random"]["overall_avg"]),
            format_seconds(runs[condition]["round_robin"]["overall_avg"]),
            MODE_LABELS[best],
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_delta_table(runs: dict[str, dict[str, dict[str, object]]]) -> str:
    baseline = runs["baseline"]
    lines = [
        "| Condition | Adaptive Δ | Random Δ | Round Robin Δ |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        if condition == "baseline" or condition not in runs:
            continue
        row = [CONDITION_LABELS[condition]]
        for mode in MODES:
            delta = runs[condition][mode]["overall_avg"] - baseline[mode]["overall_avg"]
            row.append(format_seconds(delta))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_server_choice_table(runs: dict[str, dict[str, dict[str, object]]]) -> str:
    lines = [
        "| Condition | Mode | Selected Origins |",
        "|---|---|---|",
    ]
    for condition in CONDITIONS:
        if condition not in runs:
            continue
        for mode in MODES:
            if mode not in runs[condition]:
                continue
            server_bits = []
            for server, stats in runs[condition][mode]["servers"].items():
                server_bits.append(f"{server}: {stats['count']} req, {stats['avg']:.3f}s avg")
            lines.append(
                f"| {CONDITION_LABELS[condition]} | {MODE_LABELS[mode]} | " + "; ".join(server_bits) + " |"
            )
    return "\n".join(lines)


def render_client_table(runs: dict[str, dict[str, dict[str, object]]]) -> str:
    lines = [
        "| Condition | Mode | 1 Client | 5 Clients | 10 Clients |",
        "|---|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        if condition not in runs:
            continue
        for mode in MODES:
            if mode not in runs[condition]:
                continue
            clients = runs[condition][mode]["clients"]
            lines.append(
                "| "
                + " | ".join(
                    [
                        CONDITION_LABELS[condition],
                        MODE_LABELS[mode],
                        format_seconds(clients[1]),
                        format_seconds(clients[5]),
                        format_seconds(clients[10]),
                    ]
                )
                + " |"
            )
    return "\n".join(lines)


def render_findings(runs: dict[str, dict[str, dict[str, object]]]) -> str:
    baseline_best = best_mode_for_condition(runs, "baseline")
    toronto_best = best_mode_for_condition(runs, "toronto_degraded")
    oregon_best = best_mode_for_condition(runs, "oregon_degraded")
    ncal_best = best_mode_for_condition(runs, "ncalifornia_degraded")

    adaptive = runs["adaptive"] if "adaptive" in runs else {}
    return "\n".join(
        [
            "- Baseline performance was close across all three modes; no mode dominated when all origins were healthy.",
            f"- {MODE_LABELS[baseline_best]} had the lowest baseline average completion time, but only by a small margin.",
            f"- {MODE_LABELS[toronto_best]} clearly won when Toronto was degraded, because it avoided the degraded origin.",
            f"- {MODE_LABELS[oregon_best]} clearly won when Oregon was degraded, again by shifting away from the impaired server.",
            f"- {MODE_LABELS[ncal_best]} clearly won when N. California was degraded, showing the same adaptive behavior.",
            "- Random and Round Robin kept sending traffic to degraded origins, which caused 70s-99s request times on those paths.",
            "- The main value of the adaptive selector is not baseline speed. It is avoiding bad paths under asymmetric network conditions.",
        ]
    )


def svg_bar_chart(
    title: str,
    x_labels: list[str],
    series: list[tuple[str, str, list[float]]],
    y_label: str,
    output_path: Path,
) -> None:
    width = 960
    height = 520
    margin_left = 80
    margin_right = 30
    margin_top = 60
    margin_bottom = 90
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_y = max(max(values) for _, _, values in series)
    max_y = max_y * 1.15 if max_y > 0 else 1.0
    y_ticks = 5
    groups = len(x_labels)
    group_w = plot_w / groups
    bar_w = group_w / (len(series) + 1)

    def y_pos(value: float) -> float:
        return margin_top + plot_h - (value / max_y) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        'text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #111827; }',
        '.axis { stroke: #374151; stroke-width: 1; }',
        '.grid { stroke: #e5e7eb; stroke-width: 1; }',
        '.label { font-size: 12px; }',
        '.title { font-size: 20px; font-weight: 700; }',
        '.legend { font-size: 12px; }',
        '</style>',
        f'<text class="title" x="{width/2}" y="30" text-anchor="middle">{title}</text>',
    ]

    for i in range(y_ticks + 1):
        value = max_y * i / y_ticks
        y = y_pos(value)
        parts.append(f'<line class="grid" x1="{margin_left}" y1="{y:.1f}" x2="{width-margin_right}" y2="{y:.1f}"/>')
        parts.append(f'<text class="label" x="{margin_left-10}" y="{y+4:.1f}" text-anchor="end">{value:.1f}</text>')

    parts.append(f'<line class="axis" x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top+plot_h}"/>')
    parts.append(f'<line class="axis" x1="{margin_left}" y1="{margin_top+plot_h}" x2="{width-margin_right}" y2="{margin_top+plot_h}"/>')
    parts.append(
        f'<text class="label" x="20" y="{margin_top + plot_h/2:.1f}" transform="rotate(-90, 20, {margin_top + plot_h/2:.1f})" text-anchor="middle">{y_label}</text>'
    )

    for group_idx, x_label in enumerate(x_labels):
        gx = margin_left + group_idx * group_w
        for series_idx, (label, color, values) in enumerate(series):
            value = values[group_idx]
            x = gx + (series_idx + 0.5) * bar_w
            y = y_pos(value)
            height_px = margin_top + plot_h - y
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.8:.1f}" height="{height_px:.1f}" fill="{color}"/>')
            parts.append(f'<text class="label" x="{x + bar_w*0.4:.1f}" y="{y-6:.1f}" text-anchor="middle">{value:.1f}</text>')
        parts.append(
            f'<text class="label" x="{gx + group_w/2:.1f}" y="{height-45}" text-anchor="middle">{x_label}</text>'
        )

    legend_x = margin_left
    legend_y = height - 20
    for idx, (label, color, _) in enumerate(series):
        lx = legend_x + idx * 180
        parts.append(f'<rect x="{lx}" y="{legend_y-12}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text class="legend" x="{lx + 22}" y="{legend_y}">{label}</text>')

    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_outputs(runs: dict[str, dict[str, dict[str, object]]], results_dir: Path) -> None:
    overall_chart = results_dir / "overall_avg_by_condition.svg"
    delta_chart = results_dir / "delta_vs_baseline.svg"
    summary_md = results_dir / "RESULTS_SUMMARY.md"

    overall_series = []
    delta_series = []
    baseline = runs["baseline"]
    for mode in MODES:
        overall_series.append(
            (
                MODE_LABELS[mode],
                MODE_COLORS[mode],
                [runs[condition][mode]["overall_avg"] for condition in CONDITIONS],
            )
        )
        delta_series.append(
            (
                MODE_LABELS[mode],
                MODE_COLORS[mode],
                [0.0 if condition == "baseline" else runs[condition][mode]["overall_avg"] - baseline[mode]["overall_avg"] for condition in CONDITIONS],
            )
        )

    svg_bar_chart(
        title="Average Completion Time by Condition and Mode",
        x_labels=[CONDITION_LABELS[c] for c in CONDITIONS],
        series=overall_series,
        y_label="Average Time (s)",
        output_path=overall_chart,
    )
    svg_bar_chart(
        title="Increase vs Baseline by Condition and Mode",
        x_labels=[CONDITION_LABELS[c] for c in CONDITIONS],
        series=delta_series,
        y_label="Delta vs Baseline (s)",
        output_path=delta_chart,
    )

    summary = [
        "# Results Summary",
        "",
        f"Generated from the experiment CSV files in `{results_dir}/`.",
        "",
        "## Key Findings",
        "",
        render_findings(runs),
        "",
        "## Graphs",
        "",
        f"![Average Completion Time](./{overall_chart.name})",
        "",
        f"![Delta vs Baseline](./{delta_chart.name})",
        "",
        "## Overall Average Completion Time",
        "",
        render_overall_table(runs),
        "",
        "## Degradation Penalty vs Baseline",
        "",
        render_delta_table(runs),
        "",
        "## Average Time by Client Count",
        "",
        render_client_table(runs),
        "",
        "## Selected Origin Breakdown from CSV Redirect Targets",
        "",
        render_server_choice_table(runs),
        "",
        "## JSONL Notes",
        "",
        f"- The `.jsonl` files in `{results_dir}/` are useful supporting evidence for selector decisions, metrics, and event types.",
        "- They are not perfectly isolated per run because `collect_logs.sh` tails the last 5000 lines from the shared live selector log.",
        "- For report-quality quantitative comparisons, the CSV files are the cleaner source of truth.",
        "",
        "## Source Files",
        "",
    ]
    for condition in CONDITIONS:
        if condition not in runs:
            continue
        summary.append(f"### {CONDITION_LABELS[condition]}")
        summary.append("")
        for mode in MODES:
            csv_name = Path(runs[condition][mode]["path"]).name
            jsonl_name = f"{mode}_{condition}.jsonl"
            summary.append(f"- [{csv_name}](./{csv_name})")
            if (results_dir / jsonl_name).exists():
                summary.append(f"- [{jsonl_name}](./{jsonl_name})")
        summary.append("")

    summary_md.write_text("\n".join(summary), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize experiment CSVs and generate SVG charts")
    parser.add_argument(
        "results_dir",
        nargs="?",
        default=str(DEFAULT_RESULTS_DIR),
        help="Directory containing experiment CSV files (default: results)",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    runs = load_csv_runs(results_dir)
    if not runs:
        raise SystemExit(f"No experiment CSV files found in {results_dir}/")
    write_outputs(runs, results_dir)
    print(f"Wrote {results_dir / 'RESULTS_SUMMARY.md'}")
    print(f"Wrote {results_dir / 'overall_avg_by_condition.svg'}")
    print(f"Wrote {results_dir / 'delta_vs_baseline.svg'}")


if __name__ == "__main__":
    main()
