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
    """Atomic write of the hot store. Entries older than _KEEP_AFTER_HOURS
    are moved to the permanent archive — NOT deleted. See the archive
    section below for why the hot store stays bounded."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_KEEP_AFTER_HOURS)
    evicted = {}
    with _lock:
        for event_id in list(_openings.keys()):
            ts = _openings[event_id].get("first_seen_at")
            if ts and ts < cutoff:
                evicted[event_id] = _openings[event_id]
        snapshot = dict(_openings)

    # Archive BEFORE dropping from the hot store. If the archive write
    # raises, we keep the records in memory and retry next cycle rather
    # than losing them — the whole point of this change.
    if evicted and _archive_records(evicted):
        with _lock:
            for event_id in evicted:
                _openings.pop(event_id, None)
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


def record_kickoff_line(event_id: str, total: float, book_display: str) -> None:
    """Snapshot the CURRENT (most-recent-seen) total on the opening dict.

    Called every warmer cycle while the game is pre-kickoff. Overwrites
    the previous value each time — the last write before kickoff is
    what we want to display for the frozen O/U through the game window.

    Once the game has started, cfb.slate stops calling this so the
    kickoff-line value stops advancing. See _build_odds_for_game for
    the gate logic.
    """
    if not event_id or total is None:
        return
    key = str(event_id)
    with _lock:
        entry = _openings.get(key)
        if entry is None:
            # No opening recorded yet — shouldn't happen if
            # record_opening_if_new is called first, but be defensive.
            _openings[key] = {
                "total":            float(total),
                "book_display":     book_display or "",
                "first_seen_at":    datetime.now(timezone.utc),
                "kickoff_total":    float(total),
                "kickoff_book":     book_display or "",
                "kickoff_snapshot_at": datetime.now(timezone.utc),
            }
        else:
            entry["kickoff_total"]        = float(total)
            entry["kickoff_book"]         = book_display or ""
            entry["kickoff_snapshot_at"]  = datetime.now(timezone.utc)
    _persist()


def get_kickoff_line(event_id: str) -> Optional[dict]:
    """Return {'total', 'book_display', 'snapshot_at'} for the frozen
    kickoff-line O/U, or None if not yet recorded."""
    if not event_id:
        return None
    with _lock:
        entry = _openings.get(str(event_id))
    if not entry or "kickoff_total" not in entry:
        return None
    return {
        "total":         entry["kickoff_total"],
        "book_display":  entry.get("kickoff_book", ""),
        "snapshot_at":   entry.get("kickoff_snapshot_at"),
    }


def clear_all() -> None:
    """Test helper — wipe all openings from memory AND disk."""
    with _lock:
        _openings.clear()
    save_json(_DISK_FILE, {})


# ── Closing-line archive ──────────────────────────────────────────────────
#
# WHY THIS EXISTS (2026-09-01):
#     _persist() used to DELETE entries older than _KEEP_AFTER_HOURS. That
#     silently destroyed the opening/closing-line history — the exact
#     dataset OVERcast wants for CLV work, and the one thing here that
#     cannot be backfilled. Once a game's line is gone, it is gone.
#
# WHY WE STILL EVICT FROM THE HOT STORE:
#     _openings is fully resident in memory and rewritten whole on every
#     save, and _persist() fires once per game per warmer cycle. Letting
#     it grow unbounded would turn a ~30KB write into a multi-MB one every
#     cycle, forever. So the hot store stays bounded — but evicted records
#     are APPENDED to an archive instead of dropped.
#
#     Net effect: per-cycle write cost is unchanged, history is permanent.
#     The archive is only touched when a game ages out (rare, and small).

_ARCHIVE_FILE = "cfb_odds_archive.json"


def _archive_records(evicted: dict) -> bool:
    """Append aged-out records to the permanent archive. Never overwrites
    an existing archived entry — the first write for a game wins, same
    immutability rule as the opening line itself.

    Returns True if the records are safely archived (caller may now drop
    them from the hot store), False if the write failed (caller must keep
    them). Never raises."""
    if not evicted:
        return True
    try:
        archive = load_json(_ARCHIVE_FILE, default={}) or {}
        added = 0
        for key, rec in evicted.items():
            k = str(key)
            if k in archive:
                continue
            out = dict(rec)
            out["archived_at"] = datetime.now(timezone.utc)
            archive[k] = out
            added += 1
        if added:
            save_json(_ARCHIVE_FILE, archive)
            print(f"[cfb.odds_storage] archived {added} closing line(s); "
                  f"archive now {len(archive)} games", flush=True)
    except Exception as e:
        # Archiving must never break the live odds path — odds are additive,
        # and _persist() runs inside the slate build. Raising here would turn
        # a failed archive write into a blank slate.
        #
        # So: log loudly and return False. The caller keeps the records in
        # the hot store and retries next cycle. Nothing is lost, nothing
        # breaks. A sustained failure shows up as this line repeating every
        # warmer cycle, which is the alert.
        print(f"[cfb.odds_storage] archive write FAILED (records retained, "
              f"will retry): {type(e).__name__}: {e}", flush=True)
        return False
    return True


def get_archived(event_key) -> Optional[dict]:
    """Look up a game's archived record. Returns None if not archived."""
    if event_key is None:
        return None
    archive = load_json(_ARCHIVE_FILE, default={}) or {}
    rec = archive.get(str(event_key))
    return dict(rec) if rec else None


def all_records() -> dict:
    """Every record we hold — archive plus the hot store. Hot entries win
    on key collision since they are the more recent state. This is the
    full closing-line dataset for export/analysis."""
    out = dict(load_json(_ARCHIVE_FILE, default={}) or {})
    with _lock:
        for k, v in _openings.items():
            out[str(k)] = dict(v)
    return out


def archive_stats() -> dict:
    """Counts for the admin page — how much history we are holding."""
    archive = load_json(_ARCHIVE_FILE, default={}) or {}
    with _lock:
        hot = len(_openings)
    return {"hot": hot, "archived": len(archive), "total": hot + len(archive)}
