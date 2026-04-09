from __future__ import annotations

from dataclasses import dataclass


# This class is used to REPRESENT ONE ORIGIN SERVER
# Frozen = True just makes the instance IMMUTABLE as the SERVER INFO SHOULD NOT CHANGE
@dataclass(frozen=True)
class Origin:
    # Short name for the server eg: oregon
    origin_id: str
    # Where the server lives
    base_url: str
    # region
    region: str = ''
