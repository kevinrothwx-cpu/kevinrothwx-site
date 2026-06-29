"""golf.forecast_freeze — lock per-round hourly forecast at round start.

Why: NWS rolls hourly periods off as time passes. A 4-day PGA tournament
loaded mid-week sees Round 1 (Thursday) disappear from NWS on Friday,
Round 2 disappear on Saturday, etc. Without freezing, the Round 1 hourly
table empties as soon as Thursday ends — even though many readers want to
look back at "what did Thursday end up being?"

Pattern (matches mlb.forecast_freeze and nascar.forecast_freeze):
on every warmer rebuild, for each round whose play day has NOT yet
passed, snapshot the hourly + summary + HRRR. Once a round day is in
the past, the warmer stops touching it and the page reads from the
frozen snapshot.

Storage is disk-backed via persistence module, survives Render restarts.
Frozen snapshots for finished rounds clear via clear_old() called by
the warmer once per cycle.

Key shape: f"{event_id}_{round_date_iso}" — composite so each round of
each tournament is its own freeze entry. Same tournament's Round 1
and Round 4 freeze independently.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone, date
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "golf_forecast_freeze.json"

# composite_key -> {"summary", "hourly", "hrrr_hourly", "frozen_at_utc"}
_frozen: dict[str, dict] = {}
_lock = threading.Lock()


def _key(event_id, round_date) -> str:
    """Build composite key. round_date may be a date or ISO string."""
    if isinstance(round_date, date):
        d = round_date.isoformat()
    else:
        d = str(round_date)
    return f"{event_id}_{d}"


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


def has(event_id, round_date) -> bool:
    with _lock:
        return _key(event_id, round_date) in _frozen


def get(event_id, round_date) -> Optional[dict]:
    with _lock:
        return _frozen.get(_key(event_id, round_date))


def freeze(event_id, round_date, summary, hourly, hrrr_hourly) -> None:
    """Save a round's pre-play-day snapshot."""
    with _lock:
        _frozen[_key(event_id, round_date)] = {
            "summary":       summary,
            "hourly":        hourly,
            "hrrr_hourly":   hrrr_hourly,
            "frozen_at_utc": datetime.now(timezone.utc),
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
