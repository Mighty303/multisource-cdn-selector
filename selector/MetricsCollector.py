from __future__ import annotations

import threading
import time
from urllib import error, request

from .models import Origin, OriginMetrics, ProbeConfig
from .LoadTracker import LoadTracker


# Main class for collecting metrics FROM ALL ORIGINS (Handles probing origins, caching results, merging in current load values)
class MetricsCollector:
    def __init__(self, origins: list[Origin], probe_config: ProbeConfig, load_tracker: LoadTracker) -> None:
        self._origins = origins
        # Probe settings
        self._probe_config = probe_config
        self._load_tracker = load_tracker
        # Cached probe results
        self._cache: dict[str, tuple[float, OriginMetrics]] = {}
        self._lock = threading.Lock()

    # Returns dictionary like {"oregon": OriginMetrics}
    def collect(self) -> dict[str, OriginMetrics]:
        now = time.monotonic()
        # Current load snapshot
        loads = self._load_tracker.snapshot()
        # Building this result dictionary
        metrics_by_origin: dict[str, OriginMetrics] = {}

        # Lock our code since we are accessing shared cache and origins list
        with self._lock:
            for origin in self._origins:
                cached = self._cache.get(origin.origin_id)
                # If there is a cached value and it is still valid (not too old), use it
                # Otherwise, probe the origin and update the cache with new metrics and timestamp
                # Prevents probing on every request
                if cached and now - cached[0] <= self._probe_config.ttl_seconds:
                    metrics = cached[1]
                else:
                    metrics = self._probe_origin(origin)
                    self._cache[origin.origin_id] = (now, metrics)

                # Creates a final OriginMetrics for the origin where we combine actual network measurements with recent selector load
                metrics_by_origin[origin.origin_id] = OriginMetrics(
                    healthy=metrics.healthy,
                    latency_ms=metrics.latency_ms,
                    throughput_mbps=metrics.throughput_mbps,
                    load=loads.get(origin.origin_id, 0.0),
                    error=metrics.error,
                )
        # Scoring algorithm can use these metrics
        return metrics_by_origin

    # Used to probe one server/origin by making HTTP requests to its health and throughput endpoints and measuring latency and throughput. Returns an OriginMetrics object with the results.
    def _probe_origin(self, origin: Origin) -> OriginMetrics:
        # First calls the health URL and measures latency where if it fails origin server is unhealthy and returns with error message
        try:
            latency_ms = self._measure_latency(origin.base_url + self._probe_config.health_path)
        except Exception as exc:
            return OriginMetrics(healthy=False, error=str(exc))

        # Can be a float or None but defaults as None
        throughput_mbps: float | None = None
        throughput_error: str | None = None
        # If measure throughput fails, server still remains healthy but store the error
        try:
            throughput_mbps = self._measure_throughput(
                origin.base_url + self._probe_config.throughput_path
            )
        except Exception as exc:
            throughput_error = str(exc)

        # If health probe succeeded, we return the metrics
        return OriginMetrics(
            healthy=True,
            latency_ms=round(latency_ms, 3),
            throughput_mbps=round(throughput_mbps, 3) if throughput_mbps is not None else None,
            error=throughput_error,
        )

    # Measures how long it takes to make a request to the Health URL and get a response.
    # Start timer, open URL, read first byte and once it does, stop timer and converts seconds to milliseconds
    def _measure_latency(self, url: str) -> float:
        start = time.perf_counter()
        with request.urlopen(url, timeout=self._probe_config.timeout_seconds) as response:
            response.read(1)
        return (time.perf_counter() - start) * 1000.0

    def _measure_throughput(self, url: str) -> float:
        # Create request where we ask only for a byte range instead of the whole file
        req = request.Request(url, headers={'Range': f'bytes=0-{self._probe_config.sample_bytes - 1}'})
        # Start timer, read/download sample bytes and measure elapsed time
        start = time.perf_counter()
        with request.urlopen(req, timeout=self._probe_config.timeout_seconds) as response:
            payload = response.read(self._probe_config.sample_bytes)
        # DON'T DIVIDE BY 0 here
        elapsed = max(time.perf_counter() - start, 0.001)
        if not payload:
            raise RuntimeError('empty throughput sample')
        bits = len(payload) * 8
        # Converts bytes->bits, divide by time to get bits per second and divide by 1,000,000 megabits per second
        return bits / elapsed / 1_000_000.0


# Fetches full content from a URL, returns bytes and converts URLError into RuntimeError
def open_url(url: str, timeout_seconds: float) -> bytes:
    try:
        with request.urlopen(url, timeout=timeout_seconds) as response:
            return response.read()
    except error.URLError as exc:
        raise RuntimeError(str(exc)) from exc
