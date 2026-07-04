"""cfb.forecast_freeze — lock a game's hourly forecast at kickoff.

Mirrors mls.forecast_freeze and nfl.forecast_freeze. Once a CFB game
kicks off, the displayed hourly window stops updating from NWS (which
rolls past hours off) and serves the frozen snapshot. This keeps the
in-game user view stable and survives Render restarts (disk-backed).

Prior to this module, CFB freeze was in-memory-only inside cfb/cache.py.
That lost state on every deploy or Render restart. This module makes the
freeze persistent, matching every other kickoff-sensitive sport.

Key: ESPN event_id (string).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "cfb_forecast_freeze.json"

_frozen: dict[str, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _frozen.clear()
        for k, v in raw.items():
            if isinstance(v, dict) and "frozen_at_utc" in v:
                v["frozen_at_utc"] = parse_dt(v["frozen_at_utc"])
            _frozen[str(k)] = v


def _persist() -> None:
    with _lock:
        snapshot = dict(_frozen)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


def has(event_id) -> bool:
    with _lock:
        return str(event_id) in _frozen


def get(event_id) -> Optional[dict]:
    with _lock:
        return _frozen.get(str(event_id))


def freeze(event_id, forecast, hourly, hrrr_hourly, weather_source, weather_error) -> None:
    """Save a game's pre-kickoff snapshot (forecast + hourly + HRRR)."""
    with _lock:
        _frozen[str(event_id)] = {
            "forecast":       forecast,
            "hourly":         hourly,
            "hrrr_hourly":    hrrr_hourly,
            "weather_source": weather_source,
            "weather_error":  weather_error,
            "frozen_at_utc":  datetime.now(timezone.utc),
        }
    _persist()


def clear_old(cutoff_utc: datetime) -> int:
    """Drop frozen entries older than cutoff. Returns count removed."""
    removed = 0
    with _lock:
        for k in list(_frozen.keys()):
            ts = _frozen[k].get("frozen_at_utc")
            if ts and ts < cutoff_utc:
                del _frozen[k]
                removed += 1
    if removed:
        _persist()
    return removed


def clear_all() -> None:
    with _lock:
        _frozen.clear()
    _persist()


def count() -> int:
    with _lock:
        return len(_frozen)
