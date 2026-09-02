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
    """Atomic write of the hot store. Entries older than _KEEP_AFTER_HOURS
    are moved to the permanent archive — NOT deleted. See the archive
    section below for why the hot store stays bounded."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_KEEP_AFTER_HOURS)
    evicted = {}
    with _lock:
        for pk in list(_openings.keys()):
            ts = _openings[pk].get("first_seen_at")
            if ts and ts < cutoff:
                evicted[pk] = _openings[pk]
        snapshot = dict(_openings)

    # Archive BEFORE dropping from the hot store. If the archive write
    # raises, we keep the records in memory and retry next cycle rather
    # than losing them — the whole point of this change.
    if evicted and _archive_records(evicted):
        with _lock:
            for pk in evicted:
                _openings.pop(pk, None)
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

_ARCHIVE_FILE = "mlb_odds_archive.json"


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
            print(f"[mlb.odds_storage] archived {added} closing line(s); "
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
        print(f"[mlb.odds_storage] archive write FAILED (records retained, "
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
