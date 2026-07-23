"""
mlb.odds_storage — persistent record of the first-seen total per game.

Why this exists:
    The Odds API returns the CURRENT total but not the OPENING total.
    Querying the historical endpoint costs 10x credits per request and
    is expensive to poll continuously. Instead, we snapshot the very
    first total we see for each game_pk and treat that as the "opening"
    line. Comparing current - opening gives us the line movement delta
    that users see on the per-game section.

Storage:
    JSON file at /var/data/mlb_odds_openings.json (Render persistent
    disk). Falls back to ./data/ locally. Survives restarts and deploys.
    Same infrastructure as mlb.forecast_freeze uses.

Schema:
    { "<game_pk>": {
          "total":         8.5,
          "book_display":  "DraftKings",
          "first_seen_at": "2026-07-22T13:00:00+00:00"
      }, ... }

    Keyed by game_pk (int, but JSON stringifies keys).

Cleanup:
    Openings for games older than 48 hours are removed on next save
    (games are done, no reason to keep them).
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


_DISK_FILE = "mlb_odds_openings.json"
_KEEP_AFTER_HOURS = 48  # drop entries older than 48h on next save

# game_pk (int) -> {"total": float, "book_display": str, "first_seen_at": datetime}
_openings: dict[int, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read openings from disk. JSON int-keys come back as strings; convert
    to int. Convert first_seen_at ISO string back to datetime."""
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _openings.clear()
        for k, v in raw.items():
            try:
                pk = int(k)
            except (TypeError, ValueError):
                continue
            if not isinstance(v, dict) or "total" not in v:
                continue
            if "first_seen_at" in v and isinstance(v["first_seen_at"], str):
                v["first_seen_at"] = parse_dt(v["first_seen_at"])
            _openings[pk] = v


def _persist() -> None:
    """Atomic write to disk. Also prunes old entries older than _KEEP_AFTER_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_KEEP_AFTER_HOURS)
    with _lock:
        # Prune stale entries in place
        for pk in list(_openings.keys()):
            ts = _openings[pk].get("first_seen_at")
            if ts and ts < cutoff:
                del _openings[pk]
        snapshot = dict(_openings)
    save_json(_DISK_FILE, snapshot)


# Load on module import so callers can immediately query
_load_from_disk()


def record_opening_if_new(game_pk: int, total: float, book_display: str) -> None:
    """Save the first-seen total for this game_pk. If we already have an
    entry for this game_pk, do nothing — the opening line is IMMUTABLE
    once recorded."""
    if game_pk is None or total is None:
        return
    pk = int(game_pk)
    with _lock:
        if pk in _openings:
            return
        _openings[pk] = {
            "total":         float(total),
            "book_display":  book_display or "",
            "first_seen_at": datetime.now(timezone.utc),
        }
    _persist()


def get_opening(game_pk: int) -> Optional[dict]:
    """Return {'total': float, 'book_display': str, 'first_seen_at': datetime}
    or None if we haven't seen this game_pk yet."""
    if game_pk is None:
        return None
    with _lock:
        entry = _openings.get(int(game_pk))
    return dict(entry) if entry else None


def clear_all() -> None:
    """Test helper — wipe all openings from memory AND disk."""
    with _lock:
        _openings.clear()
    save_json(_DISK_FILE, {})
