from __future__ import annotations

import threading
import time
from typing import Iterable


# Class tracks a lightweight load VALUE FOR EACH ORIGIN WHERE IT IS NOT CPU LOAD BUT RATHER HOW OFTEN HAS THIS SELECTOR RECENTLY CHOSEN THE SERVER
class LoadTracker:

    def __init__(self, origin_ids: Iterable[str], decay_per_second: float = 0.85) -> None:
        # How fast load fades over time
        self._decay_per_second = decay_per_second
        # Gives an increasing clock
        now = time.monotonic()
        # List of server IDS
        self._values = {origin_id: (0.0, now) for origin_id in origin_ids}
        self._lock = threading.Lock()

    # For whenever a server/origin is selected, we want to increase its load value so that it is less likely to be chosen in the near future
    def mark_selected(self, origin_id: str) -> None:
        # Lock the shared data with threads
        with self._lock:
            now = time.monotonic()
            # Compute current decayed load value
            current_value = self._current_value(origin_id, now)
            # Add 1 and save new value with current timestamp
            # Whole point is to make servers more busy and add the load
            self._values[origin_id] = (current_value + 1.0, now)

    # Returns current load value for all origins
    def snapshot(self) -> dict[str, float]:
        with self._lock:
            now = time.monotonic()
            result: dict[str, float] = {}
            # For each origin, compute decayed current load, update stored value to decayed amount, put rounded value into result
            for origin_id in self._values:
                current = self._current_value(origin_id, now)
                self._values[origin_id] = (current, now)
                result[origin_id] = round(current, 3)
            return result

    # Decayed load value
    # If a server had load 5.0 a while ago, value should GRADUALLY SHRINK OVER TIME AS SERVER SHOULDN'T BE PUNISHED FOREVER
    # Matters less and less overtime
    def _current_value(self, origin_id: str, now: float) -> float:
        value, timestamp = self._values.get(origin_id, (0.0, now))
        elapsed = max(0.0, now - timestamp)
        return value * (self._decay_per_second ** elapsed)
