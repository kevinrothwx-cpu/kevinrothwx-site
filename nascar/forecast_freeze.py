"""nascar.forecast_freeze — lock a race's hourly forecast at green flag.

Why: NWS rolls hourly periods off as time passes. Once a race is underway
the hourly table would otherwise shrink because NWS has discarded the
early pre-race hours. Without freezing the slate displays a sliding,
abridged window centered on whatever NWS still has, which makes the
page look like the forecast "changed" after the race started.

Pattern (matches mlb.forecast_freeze): on every warmer rebuild, if the
race has NOT yet had its green flag, refresh forecast + hourly from NWS
and snapshot here. Once the race has started (green_flag <= now_utc),
the warmer stops touching it and the page reads from the frozen
snapshot indefinitely.

Storage is disk-backed via persistence module, survives Render restarts.
Frozen snapshots for finished races are cleaned by clear_old() (called
from the warmer once per cycle).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "nascar_forecast_freeze.json"

# event_id (string) -> {"forecast", "hourly", "hrrr_hourly",
#                        "weather_source", "weather_error", "frozen_at_utc"}
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


def freeze(event_id, forecast, hourly, hrrr_hourly,
           weather_source, weather_error) -> None:
    """Save a race's pre-green-flag snapshot."""
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
    """Test helper."""
    with _lock:
        _frozen.clear()
    _persist()
