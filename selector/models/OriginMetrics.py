from __future__ import annotations

from dataclasses import dataclass


# Measured metrics for AN ORIGIN SERVER
@dataclass
class OriginMetrics:
    # Current server status
    healthy: bool
    latency_ms: float | None = None
    throughput_mbps: float | None = None
    # How busy current server seems
    load: float = 0.0
    # Optional error message
    error: str | None = None

    # Converts metrics object into a PLAIN DICTIONARY
    # Return type means we are returning a dictionary of string keys and values that can be float, bool, string or None
    def as_dict(self) -> dict[str, float | bool | str | None]:
        return {
            'healthy': self.healthy,
            'latency_ms': self.latency_ms,
            'throughput_mbps': self.throughput_mbps,
            'load': self.load,
            'error': self.error,
        }
