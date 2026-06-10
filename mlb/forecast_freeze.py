"""
mlb.forecast_freeze — lock a game's forecast at first pitch.

Why: NWS rolls hourly periods off as time passes. If a 6:35 PM game is
loaded at 9 PM, NWS has already discarded the 6-8 PM hours. Without
freezing, the hourly table would show only what NWS still has (1-2 hours).

Pattern (matches OVERcast): on every warmer rebuild, if a game has NOT
yet started, refresh its forecast from NWS and save it here. Once the
game has started (first_pitch <= now_utc), the warmer stops touching it
and the page reads from the frozen snapshot indefinitely.

Storage is disk-backed via the persistence module, survives Render
restarts. Frozen snapshots for finished games are cleaned up by
clear_old() (called by the daily roll-over).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "mlb_forecast_freeze.json"

# game_pk -> {"forecast", "wind_info", "hourly", "frozen_at_utc"}
_frozen: dict[int, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read frozen snapshots from disk. JSON int-keys come back as strings;
    convert back to int (game_pk). Convert ISO-string frozen_at_utc back to
    datetime so clear_old() can compare timestamps correctly."""
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _frozen.clear()
        for k, v in raw.items():
            try:
                pk = int(k)
            except (TypeError, ValueError):
                continue
            if isinstance(v, dict) and "frozen_at_utc" in v:
                v["frozen_at_utc"] = parse_dt(v["frozen_at_utc"])
            _frozen[pk] = v


def _persist() -> None:
    """Atomic write of the in-memory store to disk."""
    with _lock:
        snapshot = dict(_frozen)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


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
    _persist()


def clear_old(cutoff_utc: datetime) -> int:
    """Drop frozen games older than cutoff (e.g., yesterday). Returns count removed."""
    removed = 0
    with _lock:
        for pk in list(_frozen.keys()):
            ts = _frozen[pk].get("frozen_at_utc")
            if ts and ts < cutoff_utc:
                del _frozen[pk]
                removed += 1
    if removed:
        _persist()
    return removed


def clear_all() -> None:
    """Test helper."""
    with _lock:
        _frozen.clear()
    _persist()
