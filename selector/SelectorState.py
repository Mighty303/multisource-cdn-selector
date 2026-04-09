from __future__ import annotations

from collections import deque
import json
import random
import re
import threading
import time
from pathlib import Path
from urllib import parse, request

from .algorithm import choose_origin, normalize_mode
from .models import Origin, OriginMetrics, ProbeConfig, SelectorWeights
from .LoadTracker import LoadTracker
from .MetricsCollector import MetricsCollector

# Capture each BaseURL value so it can be rewritten relative to the requested manifest path.
BASE_URL_RE = re.compile(r'(<BaseURL>)(.*?)(</BaseURL>)', flags=re.IGNORECASE | re.DOTALL)


# Class stores shared runtime state of the selector
class SelectorState:
    def __init__(self, config: dict[str, object], log_file: Path) -> None:
        self._config = config
        self._log_file = log_file
        # Creates all your origin servers from the config JSON
        # This is so selector knows all available servers
        self._origins = [
            Origin(
                origin_id=str(origin['id']),
                base_url=str(origin['base_url']).rstrip('/'),
                region=str(origin.get('region', '')),
            )
            for origin in config.get('origins', [])
        ]

        # If no servers, raise error
        if not self._origins:
            raise ValueError('Selector config must include at least one origin')

        weights_config = config.get('weights', {})
        probe_config = config.get('probe', {})
        # Load the weights
        self._weights = SelectorWeights(
            latency=float(weights_config.get('latency', 0.65)),
            load=float(weights_config.get('load', 0.25)),
            throughput=float(weights_config.get('throughput', 0.10)),
        )
        self._public_base_url = str(config.get('public_base_url', '')).rstrip('/')
        self._manifest_path = str(
            probe_config.get('manifest_path', '/video/dash_content/clip1/manifest.mpd')
        )
        self._probe_config = ProbeConfig(
            health_path=str(probe_config.get('health_path', '/health')),
            throughput_path=str(
                probe_config.get('throughput_path', '/video/dash_content/clip1/360p_dashinit.mp4')
            ),
            timeout_seconds=float(probe_config.get('timeout_seconds', 2.0)),
            ttl_seconds=float(probe_config.get('ttl_seconds', 5.0)),
            sample_bytes=int(probe_config.get('sample_bytes', 262_144)),
        )
        self._mode = normalize_mode(str(config.get('mode', 'adaptive')))
        self._round_robin_index = 0
        self._lock = threading.Lock()
        self._random = random.Random()
        self._next_event_id = 1
        self._recent_events: deque[dict[str, object]] = deque(maxlen=200)
        self._last_decision: dict[str, object] | None = None
        self._forced_offline: dict[str, float] = {}  # origin_id → expiry UNIX timestamp
        self._load_tracker = LoadTracker([origin.origin_id for origin in self._origins])
        # Probes all origins
        self._collector = MetricsCollector(self._origins, self._probe_config, self._load_tracker)

    @property
    def manifest_path(self) -> str:
        return self._manifest_path

    @property
    def origins(self):
        return self._origins

    def force_offline(self, origin_id: str, duration: float) -> None:
        with self._lock:
            self._forced_offline[origin_id] = time.time() + duration

    def _apply_forced_offline(self, metrics: dict) -> dict:
        now = time.time()
        result = {}
        for oid, m in metrics.items():
            if self._forced_offline.get(oid, 0) > now:
                result[oid] = OriginMetrics(
                    healthy=False,
                    latency_ms=m.latency_ms,
                    throughput_mbps=m.throughput_mbps,
                    load=m.load,
                    error='forced offline',
                )
            else:
                result[oid] = m
        return result

    # Builds JSON response for status / current state
    def status(self) -> dict[str, object]:
        metrics_by_origin = self._apply_forced_offline(self._collector.collect())
        with self._lock:
            mode = self._mode
            last_decision = dict(self._last_decision) if self._last_decision else None
        return {
            'mode': mode,
            'public_base_url': self._public_base_url,
            'weights': {
                'latency': self._weights.latency,
                'load': self._weights.load,
                'throughput': self._weights.throughput,
            },
            'origins': [
                {
                    'id': origin.origin_id,
                    'base_url': origin.base_url,
                    'region': origin.region,
                }
                for origin in self._origins
            ],
            'probe': {
                'health_path': self._probe_config.health_path,
                'throughput_path': self._probe_config.throughput_path,
                'ttl_seconds': self._probe_config.ttl_seconds,
            },
            'last_decision': last_decision,
            'metrics': {
                origin_id: metrics.as_dict()
                for origin_id, metrics in metrics_by_origin.items()
            },
        }

    # Changes the selector mode which lets you switch modes live without restarting
    # We need to lock the thread here as mode is shared
    def set_mode(self, value: str) -> dict[str, object]:
        normalized = normalize_mode(value)
        with self._lock:
            previous_mode = self._mode
            self._mode = normalized
        return {'mode': self._mode, 'previous_mode': previous_mode}

    # Decision pipeline
    def choose(self):
        metrics_by_origin = self._apply_forced_offline(self._collector.collect())
        with self._lock:
            # Choose the origin
            decision, next_round_robin_index = choose_origin(
                origins=self._origins,
                metrics_by_origin=metrics_by_origin,
                mode=self._mode,
                weights=self._weights,
                round_robin_index=self._round_robin_index,
                random_source=self._random,
            )
            self._round_robin_index = next_round_robin_index
        # Increase load score for current server
        self._load_tracker.mark_selected(decision.origin.origin_id)
        return decision

    def is_manifest_request(self, path: str) -> bool:
        return path == self._manifest_path or path.lower().endswith('.mpd')

    # We rewrite it to selector server as we don't want the player to bypass selector for segments
    def rewrite_manifest(self, manifest_text: str, request_path: str) -> str:
        # If no public selector URL is configured
        if not self._public_base_url:
            return manifest_text

        selector_manifest_url = parse.urljoin(
            f'{self._public_base_url}/',
            request_path.lstrip('/'),
        )

        def replace(match: re.Match[str]) -> str:
            base_url = match.group(2).strip()
            rewritten = parse.urljoin(selector_manifest_url, base_url)
            return f'{match.group(1)}{rewritten}{match.group(3)}'

        return BASE_URL_RE.sub(replace, manifest_text)

    # Downloads MPD from chosen origin then rewrites it
    # Builds the selected origin's MPD URL, Download the manifest, Decodes bytes to text, Rewrites base URL and returns the rewritten manifest text
    def fetch_manifest(self, decision, manifest_path: str) -> str:
        manifest_url = parse.urljoin(decision.origin.base_url + '/', manifest_path.lstrip('/'))
        with request.urlopen(manifest_url, timeout=self._probe_config.timeout_seconds) as response:
            payload = response.read().decode('utf-8')
        return self.rewrite_manifest(payload, manifest_path)

    # Build the redirect target for non manifest requests
    def build_redirect_url(self, decision, path: str, query: str) -> str:
        target = parse.urljoin(decision.origin.base_url + '/', path.lstrip('/'))
        target_parts = list(parse.urlparse(target))
        query_pairs = parse.parse_qsl(query, keep_blank_values=True)
        query_pairs.append(('_selector_server', decision.origin.origin_id))
        target_parts[4] = parse.urlencode(query_pairs, doseq=True)
        return parse.urlunparse(target_parts)

    # Ensures the log directory exists, then appends one JSON object per line to the log file
    def log_event(self, event: dict[str, object]) -> None:
        enriched = dict(event)
        enriched.setdefault('ts', round(time.time(), 3))
        with self._lock:
            enriched.setdefault('event_id', self._next_event_id)
            self._next_event_id += 1
            self._recent_events.append(dict(enriched))

        if enriched.get('selected_server'):
            with self._lock:
                self._last_decision = {
                    'timestamp': str(enriched.get('timestamp', '')),
                    'action': str(enriched.get('action', '')),
                    'path': str(enriched.get('path', '')),
                    'status': int(enriched.get('status', 0)),
                    'selected_server': str(enriched.get('selected_server', '')),
                    'selector_mode': str(enriched.get('selector_mode', '')),
                    'decision_ms': float(enriched['decision_ms']) if enriched.get('decision_ms') is not None else None,
                    'score': float(enriched['score']) if enriched.get('score') is not None else None,
                    'target': str(enriched.get('target', '')),
                    'event_id': int(enriched['event_id']),
                    'event_type': str(enriched.get('event_type', '')),
                    'request_kind': str(enriched.get('request_kind', '')),
                    'reason': str(enriched.get('reason', '')),
                }
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with self._log_file.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(enriched, sort_keys=True) + '\n')

    def recent_events(self, limit: int = 100, since_id: int | None = None) -> list[dict[str, object]]:
        with self._lock:
            events = list(self._recent_events)
        if since_id is not None:
            events = [event for event in events if int(event.get('event_id', 0)) > since_id]
        if limit > 0:
            events = events[-limit:]
        return [dict(event) for event in events]

    def latest_event_id(self) -> int:
        with self._lock:
            return self._next_event_id - 1
