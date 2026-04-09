from __future__ import annotations

from dataclasses import dataclass

from .Origin import Origin


# Final decision that the selector makes after evaluating all origins and metrics
@dataclass(frozen=True)
class Decision:
    # Chosen Origin server
    origin: Origin
    mode: str
    reason: str
    score: float | None
    # All calculated scores
    scores: dict[str, float | None]
    # All metrics
    metrics: dict[str, dict[str, float | bool | str | None]]

    # Same as before converts all the fields into a dictionary for logging
    def as_dict(self) -> dict[str, object]:
        return {
            'origin_id': self.origin.origin_id,
            'origin_base_url': self.origin.base_url,
            'mode': self.mode,
            'reason': self.reason,
            'score': self.score,
            'scores': self.scores,
            'metrics': self.metrics,
        }
