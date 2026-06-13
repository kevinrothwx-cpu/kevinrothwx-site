"""
cws.forecast_freeze — lock a CWS game's forecast at first pitch.

Mirrors mlb.forecast_freeze but keyed by event_id (string) instead of
game_pk (int). Same disk-backed persistence pattern.

Why: NWS rolls hourly periods off as time passes. Once a CWS game starts,
NWS no longer has the early-game hours, so the hourly table empties out
unless we snapshot it before first pitch and re-read from the snapshot
afterward.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "cws_forecast_freeze.json"

# event_id -> {"forecast", "wind_info", "hourly", "frozen_at_utc"}
_frozen: dict[str, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _frozen.clear()
        for k, v in raw.items():
            if isinstance(v, dict) and "frozen_at_utc" in v and isinstance(v["frozen_at_utc"], str):
                v["frozen_at_utc"] = parse_dt(v["frozen_at_utc"])
            _frozen[str(k)] = v


def _persist() -> None:
    with _lock:
        snapshot = dict(_frozen)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


def has(event_id: str) -> bool:
    with _lock:
        return str(event_id) in _frozen


def get(event_id: str) -> Optional[dict]:
    with _lock:
        return _frozen.get(str(event_id))


def freeze(event_id: str, forecast: dict, wind_info: dict, hourly: list[dict]) -> None:
    """Save a game's forecast snapshot. Called by the slate builder while
    the game is still in the future. Subsequent rebuilds overwrite the
    snapshot so the locked value tracks NWS up to first pitch."""
    with _lock:
        _frozen[str(event_id)] = {
            "forecast":      forecast,
            "wind_info":     wind_info,
            "hourly":        hourly,
            "frozen_at_utc": datetime.now(timezone.utc),
        }
    _persist()


def clear_old(cutoff_utc: datetime) -> int:
    """Drop frozen games older than cutoff. Returns count removed."""
    removed = 0
    with _lock:
        for eid in list(_frozen.keys()):
            ts = _frozen[eid].get("frozen_at_utc")
            if ts and ts < cutoff_utc:
                del _frozen[eid]
                removed += 1
    if removed:
        _persist()
    return removed


def clear_all() -> None:
    with _lock:
        _frozen.clear()
    _persist()
