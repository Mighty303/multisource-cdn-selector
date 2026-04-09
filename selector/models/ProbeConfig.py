from __future__ import annotations

from dataclasses import dataclass


# Used for probing behaviour
@dataclass(frozen=True)
class ProbeConfig:
    # Path used for health checks
    health_path: str = '/health'
    # Path used to estimate throughput (Downloads part of a DASH segment to estimate speed)
    throughput_path: str = '/video/dash_content/clip1/360p_dashinit.mp4'
    # How long to wait before considering a probe attempt as failed
    timeout_seconds: float = 2.0
    # How long to cache metrics before re-probing
    ttl_seconds: float = 5.0
    # How many bytes to request for throughput sample
    sample_bytes: int = 262_144
