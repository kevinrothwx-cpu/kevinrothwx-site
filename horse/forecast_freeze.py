"""horse.forecast_freeze — lock the race-day forecast at post time.

Same pattern as golf.forecast_freeze and mlb.forecast_freeze: once a
stakes race goes off, we snapshot the current hourly + HRRR into disk.
The page can then serve the frozen snapshot for post-race review even
after the actual weather sensors have moved on.

Key: race_id (unique across track + date + race).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone, date
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "horse_forecast_freeze.json"

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


def has(race_id: str) -> bool:
    with _lock:
        return race_id in _frozen


def get(race_id: str) -> Optional[dict]:
    with _lock:
        return _frozen.get(race_id)


def freeze(race_id: str, summary, hourly, hrrr_hourly) -> None:
    with _lock:
        _frozen[race_id] = {
            "summary": summary,
            "hourly": hourly,
            "hrrr_hourly": hrrr_hourly,
            "frozen_at_utc": datetime.now(timezone.utc),
        }
    _persist()


def clear(race_id: str) -> None:
    with _lock:
        _frozen.pop(race_id, None)
    _persist()


def clear_old(days_after: int = 3) -> None:
    """Drop frozen snapshots more than `days_after` days past their race day."""
    now = datetime.now(timezone.utc)
    with _lock:
        to_drop = []
        for k, v in _frozen.items():
            fa = v.get("frozen_at_utc")
            if fa and (now - fa).days > days_after:
                to_drop.append(k)
        for k in to_drop:
            _frozen.pop(k, None)
    if to_drop:
        _persist()
