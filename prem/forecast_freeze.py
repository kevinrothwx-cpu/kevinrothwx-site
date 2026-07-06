"""prem.forecast_freeze — lock a match's hourly forecast at kickoff.

Mirrors mls.forecast_freeze exactly. Disk-backed via persistence so the
freeze survives Render restarts.

Key: ESPN event_id (string).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "prem_forecast_freeze.json"

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


def freeze(event_id, forecast, hourly, weather_source, weather_error) -> None:
    """Save a match's pre-kickoff snapshot."""
    with _lock:
        _frozen[str(event_id)] = {
            "forecast":       forecast,
            "hourly":         hourly,
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


# EOF-CANARY 2026-07-06-prem-build
