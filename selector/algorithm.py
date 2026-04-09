"""
This script implements the main logic to our selector where its job is to
1) Store info about each server 2) Store measured metrics for each server 3) Implement a score 4) Choose which server to use based on the mode adaptive, random, round robin
"""
from __future__ import annotations

import math
import random
from typing import Mapping, Sequence

from .models import Decision, Origin, OriginMetrics, SelectorWeights

# Tuple of the 3 allowed modes where our selector only accepts these 3 choices
VALID_MODES = ('adaptive', 'random', 'round_robin')


def normalize_mode(value: str | None) -> str:
    # If value is none use adaptive as default
    mode = (value or 'adaptive').strip().lower()
    if mode not in VALID_MODES:
        raise ValueError(
            f'Unsupported selector mode: {value}. Expected one of {", ".join(VALID_MODES)}'
        )
    return mode

# Takes metrics from one origin and scoring weights and RETURNS ONE NUMERIC SCORE
# LOWER SCORE = BETTER
def score_origin(metrics: OriginMetrics, weights: SelectorWeights) -> float:
    # Base case if server is unhealthy we return infinity so that it is never chosen
    if not metrics.healthy:
        return math.inf

    # Given theres missing latency, TREAT THIS SERVER AS BAD
    latency_ms = metrics.latency_ms if metrics.latency_ms is not None else 10_000.0
    # If throughput is missing use 0
    throughput_mbps = (
        metrics.throughput_mbps if metrics.throughput_mbps is not None else 0.0
    )
    load = metrics.load
    # MOST IMPORTANT SCORE FORMULA (LOWER SCORE = BETTER)
    # Essentially, we add the latency and load and subtract the throughput
    # This makes it so a server with low latency, low load and high throughput GETS THE SMALLEST SCORE AND WINS
    return (
        weights.latency * latency_ms
        + weights.load * load
        - weights.throughput * throughput_mbps
    )

# Main function that takes in all the origins, their metrics, the mode we want to use, the weights for scoring, and the current round robin index (if needed) and RETURNS THE DECISION AND THE UPDATED ROUND ROBIN INDEX
# AS NAME SUGGESTS, ROUND ROBIN INDEX IS ONLY FOR ROUND ROBIN MODE AND KEEPS TRACK OF WHICH SERVER TO CHOOSE NEXT
def choose_origin(
    # List of all origin servers
    origins: Sequence[Origin],
    # Dictionary mapping origin_id to their metrics
    metrics_by_origin: Mapping[str, OriginMetrics],
    mode: str,
    weights: SelectorWeights,
    round_robin_index: int,
    random_source: random.Random | None = None,
) -> tuple[Decision, int]:
    # Make sure mode is valid and cleaned
    normalized_mode = normalize_mode(mode)
    rng = random_source or random.Random()
    # Builds list of only health origin servers where if metrics dict doesnt contain that origin, it pretends its unhealthy
    healthy_origins = [
        origin for origin in origins if metrics_by_origin.get(origin.origin_id, OriginMetrics(False)).healthy
    ]
    if not healthy_origins:
        raise RuntimeError('No healthy origins available for selection')

    # Calculate score for every origin and store it in a dictionary
    # metrics_by_origin[origin.origin_id] could be a problem if a key is missing so maybe switch to metrics_by_origin.get(origin.origin_id, OriginMetrics(False))
    scores = {
        origin.origin_id: _coerce_score(score_origin(metrics_by_origin[origin.origin_id], weights))
        for origin in origins
    }
    # Build a dictionary of all metrics for each origin
    metrics = {
        origin.origin_id: metrics_by_origin.get(origin.origin_id, OriginMetrics(False)).as_dict()
        for origin in origins
    }

    # Check the 3 modes
    # 1) Pick a random server
    if normalized_mode == 'random':
        selected = rng.choice(healthy_origins)
        # Return decision where round robin index is unchanged since we are not using round robin mode
        return Decision(
            origin=selected,
            mode=normalized_mode,
            reason='random_choice',
            score=scores[selected.origin_id],
            scores=scores,
            metrics=metrics,
        ), round_robin_index

    if normalized_mode == 'round_robin':
        next_index = round_robin_index
        # Loop through origins
        for offset in range(len(origins)):
            candidate = origins[(round_robin_index + offset) % len(origins)]
            # If candidate is healthy, choose it
            candidate_metrics = metrics_by_origin.get(candidate.origin_id, OriginMetrics(False))
            if candidate_metrics.healthy:
                # Moves pointer to next origin for next call
                next_index = (round_robin_index + offset + 1) % len(origins)
                return Decision(
                    origin=candidate,
                    mode=normalized_mode,
                    reason='round_robin_next_healthy',
                    score=scores[candidate.origin_id],
                    scores=scores,
                    metrics=metrics,
                ), next_index
        raise RuntimeError('Round-robin selection failed because all origins are unhealthy')
    # 3) Adaptive mode where we pick origin with SMALLEST SCORE
    selected = min(
        healthy_origins,
        key=lambda origin: score_origin(metrics_by_origin[origin.origin_id], weights),
    )
    return Decision(
        origin=selected,
        mode=normalized_mode,
        reason='adaptive_min_score',
        score=scores[selected.origin_id],
        scores=scores,
        metrics=metrics,
    ), round_robin_index

# Cleans up a score before we log it by rounding it to 3 decimal places and converting inf and nan to None
def _coerce_score(value: float) -> float | None:
    if math.isinf(value) or math.isnan(value):
        return None
    return round(value, 3)
