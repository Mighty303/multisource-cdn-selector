from __future__ import annotations

from dataclasses import dataclass


# Stores the weights used in scoring (MIGHT NEED TO CHANGE LATER)
# Our default values treat latency as most important factor
@dataclass(frozen=True)
class SelectorWeights:
    latency: float = 0.65
    load: float = 0.25
    throughput: float = 0.10
