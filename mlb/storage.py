"""
mlb.storage — write-up storage with optional color tag.

Disk-backed via persistence module. Reads /var/data/writeups_mlb.json on
import; writes on every save_writeup. Survives Render restarts.

Each write-up: {text, color, updated_at_utc}
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json


VALID_COLORS = {"green", "yellow", "orange", "red"}
_DISK_FILE = "writeups_mlb.json"

_MEMORY_STORE: dict[int, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read writeups from the persistent disk into the in-memory store.
    JSON keys are strings; convert back to int (game_pk) on load."""
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _MEMORY_STORE.clear()
        for k, v in raw.items():
            try:
                _MEMORY_STORE[int(k)] = v
            except (TypeError, ValueError):
                pass


def _persist() -> None:
    """Write the in-memory store to disk. Called after any mutation."""
    with _lock:
        snapshot = dict(_MEMORY_STORE)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


def get_writeup(game_pk: int) -> Optional[dict]:
    with _lock:
        return _MEMORY_STORE.get(int(game_pk))


def save_writeup(game_pk: int, text: str, color: Optional[str] = None) -> None:
    """Save (or replace) a write-up. Empty text = delete."""
    pk = int(game_pk)
    text = (text or "").strip()
    if color and color.lower() not in VALID_COLORS:
        color = None
    elif color:
        color = color.lower()
    with _lock:
        if not text:
            _MEMORY_STORE.pop(pk, None)
        else:
            _MEMORY_STORE[pk] = {
                "text":           text,
                "color":          color,
                "updated_at_utc": datetime.now(timezone.utc),
            }
    _persist()


def list_writeups(game_pks: list[int]) -> dict[int, dict]:
    out = {}
    with _lock:
        for pk in game_pks:
            entry = _MEMORY_STORE.get(int(pk))
            if entry:
                out[int(pk)] = entry
    return out


def attach_writeups_to_slate(slate: list[dict]) -> None:
    pks = [g["game_pk"] for g in slate if g.get("game_pk")]
    writeups = list_writeups(pks)
    for g in slate:
        g["writeup"] = writeups.get(int(g.get("game_pk", 0)))


def clear_all() -> None:
    with _lock:
        _MEMORY_STORE.clear()


# ── Delete + full listing (added 2026-08-30) ───────────────────────────
# Before this, the only way to remove a write-up was to select its game in
# the admin dropdown and save empty text. That breaks once the game rolls
# off the current slate: the dropdown only lists games on the viewed date,
# so older write-ups became unreachable — invisible in the UI and
# impossible to delete. These two functions back /admin/writeups, which
# lists EVERY stored write-up across all sports with a delete button.

def _key_candidates(raw):
    """Try the key as given, as int, and as str.

    Key types diverge by sport: MLB stores int game_pk, everything else
    stores str event_id. Rather than special-case each module, accept
    whichever form matches."""
    out = [raw]
    try:
        out.append(int(raw))
    except (TypeError, ValueError):
        pass
    out.append(str(raw))
    return out


def delete_writeup(event_id) -> bool:
    """Remove a write-up outright. Returns True if one existed."""
    removed = False
    with _lock:
        for candidate in _key_candidates(event_id):
            if candidate in _MEMORY_STORE:
                _MEMORY_STORE.pop(candidate, None)
                removed = True
                break
    if removed:
        _persist()
    return removed


def list_all_writeups() -> dict:
    """Every stored write-up, keyed by str(id) — including orphans whose
    game is no longer on any slate."""
    with _lock:
        return {str(k): dict(v) for k, v in _MEMORY_STORE.items()}


# ── Auto-expiry at 2am ET the day after the game (2026-08-30) ──────────
# Kevin's rule: a write-up lives through its game's calendar day, then
# clears. MLB games are all same-day so they all clear nightly; NFL
# spreads Thu-Mon so each clears on its own night. One rule, both shapes.
#
# The 2am ET grace period keeps late West-Coast games readable overnight
# instead of vanishing the moment the clock rolls past midnight Eastern.
#
# Expressed as: delete when game_date < (now_ET - 2h).date().
#   1:00am Fri -> cutoff is Thu -> Thursday games kept.
#   2:00am Fri -> cutoff is Fri -> Thursday games dropped.
#
# WHY NOT delete_orphaned: that removes anything absent from the live
# slate, so a partial upstream response (CFBD returning 40 of 89 games)
# would delete write-ups for games that haven't been played yet. Date
# comparison is deterministic and immune to API hiccups.
#
# Dates are stamped during attach_writeups_to_slate, which every warmer
# already calls — so this needed no cache or admin-route changes, and it
# backfills legacy write-ups automatically on the next cycle.

from datetime import timedelta as _wx_timedelta
from zoneinfo import ZoneInfo as _wx_ZoneInfo

_WX_ET = _wx_ZoneInfo("America/New_York")
WRITEUP_EXPIRE_HOUR_ET = 2


def _wx_game_id(game):
    for key in ("game_pk", "event_id", "id"):
        v = game.get(key)
        if v not in (None, ""):
            return str(v)
    return None


def _wx_game_date(game):
    """Eastern calendar date for a slate entry, as 'YYYY-MM-DD'.

    end_iso comes first so multi-day events (golf tournaments) expire
    after their FINAL round rather than their first."""
    for key in ("end_iso", "kickoff_date_eastern", "date_local", "date"):
        v = game.get(key)
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    for key in ("kickoff_eastern", "first_pitch_eastern", "start_eastern"):
        v = game.get(key)
        if hasattr(v, "date"):
            try:
                return v.date().isoformat()
            except Exception:
                pass
    return None


def _wx_cutoff_date():
    from datetime import datetime as _dt
    return (_dt.now(_WX_ET) - _wx_timedelta(hours=WRITEUP_EXPIRE_HOUR_ET)).date().isoformat()


def purge_expired() -> int:
    """Delete write-ups whose game day has passed. Returns count removed.

    Entries with no stamped game_date are left alone — we never delete
    something we can't confidently date."""
    cutoff = _wx_cutoff_date()
    removed = 0
    with _lock:
        for k in list(_MEMORY_STORE.keys()):
            gd = (_MEMORY_STORE[k] or {}).get("game_date")
            if gd and str(gd) < cutoff:
                del _MEMORY_STORE[k]
                removed += 1
    if removed:
        _persist()
    return removed


def _wx_stamp_and_purge(slate) -> None:
    """Stamp game_date onto any write-up missing one, then purge expired."""
    changed = False
    with _lock:
        for game in (slate or []):
            gid = _wx_game_id(game)
            if not gid:
                continue
            for cand in _key_candidates(gid):
                entry = _MEMORY_STORE.get(cand)
                if entry is None:
                    continue
                if not entry.get("game_date"):
                    gd = _wx_game_date(game)
                    if gd:
                        entry["game_date"] = gd
                        changed = True
                break
    if changed:
        _persist()
    purge_expired()


# Wrap the original attach so every warmer cycle stamps + purges without
# any caller needing to change. Name rebinding happens at import time, so
# `from x.storage import attach_writeups_to_slate` picks up the wrapper.
_wx_orig_attach = attach_writeups_to_slate


def attach_writeups_to_slate(slate):
    _wx_orig_attach(slate)
    try:
        _wx_stamp_and_purge(slate)
    except Exception as _e:
        print(f"[{__name__}] stamp/purge skipped: {type(_e).__name__}: {_e}",
              flush=True)


# ── Datetime normalization on load (2026-08-30) ────────────────────────
# JSON has no datetime type, so updated_at_utc round-trips as an ISO
# STRING. Five admin templates call .strftime() on it, which raises
# AttributeError on a str and 500s the page.
#
# This was latent for a long time: write-ups rarely outlived a restart,
# so _MEMORY_STORE almost always held the real datetime objects written
# by save_writeup in the same process. Once persistence became reliable,
# every restart reloaded them as strings and the admin pages broke.
#
# Fix at the source — coerce back to datetime on load — so the contract
# templates rely on ("updated_at_utc is a datetime") actually holds.

def _wx_normalize_timestamps() -> int:
    """Coerce ISO-string timestamps in the store back into datetimes."""
    from persistence import parse_dt as _wx_parse_dt
    fixed = 0
    with _lock:
        for k, v in list(_MEMORY_STORE.items()):
            if not isinstance(v, dict):
                continue
            ts = v.get("updated_at_utc")
            if isinstance(ts, str):
                parsed = _wx_parse_dt(ts)
                if parsed is not None:
                    v["updated_at_utc"] = parsed
                    fixed += 1
                else:
                    # Unparseable — drop it rather than leave a landmine
                    # that blows up .strftime() in a template.
                    v["updated_at_utc"] = None
                    fixed += 1
    return fixed


# Repair whatever the import-time _load_from_disk() already put in memory.
try:
    _wx_fixed = _wx_normalize_timestamps()
    if _wx_fixed:
        print(f"[{__name__}] normalized {_wx_fixed} timestamp(s) on load",
              flush=True)
except Exception as _e:
    print(f"[{__name__}] timestamp normalize skipped: {type(_e).__name__}: {_e}",
          flush=True)


# Wrap _load_from_disk so any later reload normalizes too.
_wx_orig_load = _load_from_disk


def _load_from_disk():
    _wx_orig_load()
    try:
        _wx_normalize_timestamps()
    except Exception as _e:
        print(f"[{__name__}] normalize after reload skipped: {_e}", flush=True)
