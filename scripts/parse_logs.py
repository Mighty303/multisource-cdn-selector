#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

HAPROXY_LINE_RE = re.compile(
    r"(?P<ts>\S+)\s+backend=(?P<backend>\S+)\s+server=(?P<server>\S+)\s+"
    r"ttfb_ms=(?P<ttfb>\d+)\s+status=(?P<status>\d+)\s+camera=(?P<camera>\S+)"
)


def parse(path: str) -> list[dict[str, str | int | float | dict[str, object] | None]]:
    rows: list[dict[str, str | int | float | dict[str, object] | None]] = []
    with open(path, 'r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('{'):
                row = _parse_selector_line(line)
            else:
                row = _parse_haproxy_line(line)
            if row:
                rows.append(row)
    return rows


def summarize(
    rows: list[dict[str, str | int | float | dict[str, object] | None]]
) -> dict[str, object]:
    per_server_latency: dict[str, list[float]] = defaultdict(list)
    per_server_decision_ms: dict[str, list[float]] = defaultdict(list)
    per_server_score: dict[str, list[float]] = defaultdict(list)
    status_counts: dict[int, int] = defaultdict(int)
    mode_counts: dict[str, int] = defaultdict(int)
    server_counts: dict[str, int] = defaultdict(int)
    redirect_count = 0
    manifest_count = 0

    for row in rows:
        server = str(row['server'])
        server_counts[server] += 1
        status_counts[int(row['status'])] += 1
        if row.get('selector_mode'):
            mode_counts[str(row['selector_mode'])] += 1
        if row.get('action') == 'redirect':
            redirect_count += 1
        if row.get('action') == 'manifest':
            manifest_count += 1

        latency_value = row.get('latency_ms')
        if latency_value is not None:
            per_server_latency[server].append(float(latency_value))

        decision_value = row.get('decision_ms')
        if decision_value is not None:
            per_server_decision_ms[server].append(float(decision_value))

        score_value = row.get('score')
        if score_value is not None:
            per_server_score[server].append(float(score_value))

    avg_latency = {
        server: round(sum(values) / max(1, len(values)), 2)
        for server, values in per_server_latency.items()
    }
    avg_decision = {
        server: round(sum(values) / max(1, len(values)), 2)
        for server, values in per_server_decision_ms.items()
    }
    avg_score = {
        server: round(sum(values) / max(1, len(values)), 2)
        for server, values in per_server_score.items()
    }

    return {
        'records': len(rows),
        'selected_server_counts': dict(sorted(server_counts.items())),
        'mode_counts': dict(sorted(mode_counts.items())),
        'avg_latency_by_server_ms': avg_latency,
        'avg_decision_ms_by_server': avg_decision,
        'avg_score_by_server': avg_score,
        'status_counts': dict(sorted(status_counts.items())),
        'redirect_records': redirect_count,
        'manifest_records': manifest_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Parse selector or HAProxy routing logs')
    parser.add_argument('log_file', help='Path to routing log file')
    args = parser.parse_args()

    rows = parse(str(Path(args.log_file)))
    print(json.dumps(summarize(rows), indent=2))

def _parse_haproxy_line(line: str) -> dict[str, str | int] | None:
    match = HAPROXY_LINE_RE.search(line)
    if not match:
        return None
    return {
        'timestamp': match.group('ts'),
        'backend': match.group('backend'),
        'server': match.group('server'),
        'status': int(match.group('status')),
        'latency_ms': int(match.group('ttfb')),
    }


def _parse_selector_line(line: str) -> dict[str, str | int | float | dict[str, object]] | None:
    payload = json.loads(line)
    selected_server = payload.get('selected_server')
    status = payload.get('status')
    metrics = payload.get('metrics', {})
    selected_metrics = metrics.get(selected_server, {}) if isinstance(metrics, dict) else {}
    return {
        'timestamp': str(payload.get('timestamp', '')),
        'server': str(selected_server),
        'status': int(status),
        'selector_mode': str(payload.get('selector_mode', '')),
        'action': str(payload.get('action', '')),
        'decision_ms': float(payload['decision_ms']) if payload.get('decision_ms') is not None else None,
        'score': float(payload['score']) if payload.get('score') is not None else None,
        'latency_ms': (
            float(selected_metrics['latency_ms'])
            if isinstance(selected_metrics, dict) and selected_metrics.get('latency_ms') is not None
            else None
        ),
    }


if __name__ == '__main__':
    main()
