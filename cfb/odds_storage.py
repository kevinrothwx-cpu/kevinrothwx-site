"""
cfb.odds_storage — persistent record of the first-seen total per game.

Mirrors mlb/odds_storage.py exactly. See that module for the full rationale.

Storage:
    JSON file at /var/data/cfb_odds_openings.json (Render persistent disk).
    Falls back to ./data/ locally.

Schema:
    { "<event_id>": {
          "total":         52.5,
          "book_display":  "DraftKings",
          "first_seen_at": "2026-08-06T13:00:00+00:00"
      }, ... }

    Keyed by ESPN event_id (str), which is what cfb/schedule.py returns
    as the unique game identifier. Note: MLB uses int game_pk; CFB uses
    str event_id. Same shape, different key type — do not cross-import.

Cleanup:
    Openings for games older than 168 hours (1 week) are removed on next
    save. CFB has a much longer window than MLB (bowl games, missed
    Saturdays, etc.) — a week's buffer keeps the closing line queryable
    after the game while still bounding disk growth.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "cfb_odds_openings.json"
_KEEP_AFTER_HOURS = 168  # drop entries older than 1 week

# event_id (str) -> {"total": float, "book_display": str, "first_seen_at": datetime}
_openings: dict[str, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read openings from disk. Convert first_seen_at ISO string back to
    datetime. Keys stay as strings (ESPN event IDs)."""
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _openings.clear()
        for k, v in raw.items():
            if not isinstance(v, dict) or "total" not in v:
                continue
            if "first_seen_at" in v and isinstance(v["first_seen_at"], str):
                v["first_seen_at"] = parse_dt(v["first_seen_at"])
            _openings[str(k)] = v


def _persist() -> None:
    """Atomic write to disk. Prunes entries older than _KEEP_AFTER_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_KEEP_AFTER_HOURS)
    with _lock:
        for event_id in list(_openings.keys()):
            ts = _openings[event_id].get("first_seen_at")
            if ts and ts < cutoff:
                del _openings[event_id]
        snapshot = dict(_openings)
    save_json(_DISK_FILE, snapshot)


# Load on module import so callers can immediately query
_load_from_disk()


def record_opening_if_new(event_id: str, total: float, book_display: str) -> None:
    """Save the first-seen total for this event_id. IMMUTABLE — if we
    already have an entry, do nothing."""
    if not event_id or total is None:
        return
    key = str(event_id)
    with _lock:
        if key in _openings:
            return
        _openings[key] = {
            "total":         float(total),
            "book_display":  book_display or "",
            "first_seen_at": datetime.now(timezone.utc),
        }
    _persist()


def get_opening(event_id: str) -> Optional[dict]:
    """Return the stored opening dict, or None if not yet seen."""
    if not event_id:
        return None
    with _lock:
        entry = _openings.get(str(event_id))
    return dict(entry) if entry else None


def clear_all() -> None:
    """Test helper — wipe all openings from memory AND disk."""
    with _lock:
        _openings.clear()
    save_json(_DISK_FILE, {})
