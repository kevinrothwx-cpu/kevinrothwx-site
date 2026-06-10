"""
mlb.forecast_freeze — lock a game's forecast at first pitch.

Why: NWS rolls hourly periods off as time passes. If a 6:35 PM game is
loaded at 9 PM, NWS has already discarded the 6-8 PM hours. Without
freezing, the hourly table would show only what NWS still has (1-2 hours).

Pattern (matches OVERcast): on every warmer rebuild, if a game has NOT
yet started, refresh its forecast from NWS and save it here. Once the
game has started (first_pitch <= now_utc), the warmer stops touching it
and the page reads from the frozen snapshot indefinitely.

Storage is in-process. Render Free tier wipes on restart, but the warmer
will re-freeze any unstarted games within its next 25-min cycle. Started
games lose their freeze on restart — acceptable tradeoff vs requiring a
persistent disk add-on. Phase 2 could persist to disk if needed.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


# game_pk → {"forecast", "wind_info", "hourly", "frozen_at_utc"}
_frozen: dict[int, dict] = {}
_lock = threading.Lock()


def has(game_pk: int) -> bool:
    with _lock:
        return int(game_pk) in _frozen


def get(game_pk: int) -> Optional[dict]:
    with _lock:
        return _frozen.get(int(game_pk))


def freeze(game_pk: int, forecast: dict, wind_info: dict, hourly: list[dict]) -> None:
    """Save a game's forecast snapshot. Called by slate builder while game is future."""
    with _lock:
        _frozen[int(game_pk)] = {
            "forecast":      forecast,
            "wind_info":     wind_info,
            "hourly":        hourly,
            "frozen_at_utc": datetime.now(timezone.utc),
        }


def clear_old(cutoff_utc: datetime) -> int:
    """Drop frozen games older than cutoff (e.g., yesterday). Returns count removed."""
    removed = 0
    with _lock:
        for pk in list(_frozen.keys()):
            ts = _frozen[pk].get("frozen_at_utc")
            if ts and ts < cutoff_utc:
                del _frozen[pk]
                removed += 1
    return removed


def clear_all() -> None:
    """Test helper."""
    with _lock:
        _frozen.clear()
