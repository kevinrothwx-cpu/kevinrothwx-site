"""golf.storage — write-up storage for PGA tournaments (mirror of MLB).
Disk-backed via persistence module, survives Render restarts."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


VALID_COLORS = {"green", "yellow", "orange", "red"}
_DISK_FILE = "writeups_golf.json"

_MEMORY_STORE: dict[str, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read writeups from disk JSON.

    JSON serialization turns datetime objects into ISO strings, so on load
    we rehydrate updated_at_utc back into a datetime. The admin template
    calls .strftime() on it — strings don't have strftime, so without this
    rehydration the admin page 500s after any Render restart that drops
    the in-memory store but preserves the disk file. Mirrors the pattern
    in worldcup/storage.py and cws/storage.py.
    """
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _MEMORY_STORE.clear()
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(v.get("updated_at_utc"), str):
                v["updated_at_utc"] = parse_dt(v["updated_at_utc"])
            _MEMORY_STORE[str(k)] = v


def _persist() -> None:
    with _lock:
        snapshot = dict(_MEMORY_STORE)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


def get_writeup(event_id: str) -> Optional[dict]:
    with _lock:
        return _MEMORY_STORE.get(str(event_id))


def save_writeup(event_id: str, text: str, color: Optional[str] = None) -> None:
    eid = str(event_id)
    text = (text or "").strip()
    if color and color.lower() not in VALID_COLORS:
        color = None
    elif color:
        color = color.lower()
    with _lock:
        if not text:
            _MEMORY_STORE.pop(eid, None)
        else:
            _MEMORY_STORE[eid] = {
                "text":           text,
                "color":          color,
                "updated_at_utc": datetime.now(timezone.utc),
            }
    _persist()


def list_writeups(event_ids):
    out = {}
    with _lock:
        for eid in event_ids:
            entry = _MEMORY_STORE.get(str(eid))
            if entry:
                out[str(eid)] = entry
    return out


def attach_writeups_to_slate(slate):
    eids = [t.get("event_id") for t in slate if t.get("event_id")]
    writeups = list_writeups(eids)
    for t in slate:
        t["writeup"] = writeups.get(str(t.get("event_id", "")))


def clear_all():
    with _lock:
        _MEMORY_STORE.clear()


def delete_orphaned(live_event_ids) -> int:
    """Delete writeups whose event_id is no longer in the live slate.

    Called from the warmer cycle after a healthy rebuild. If the supplied
    set is empty (slate likely failed to build), skips cleanup so a
    transient ESPN outage can't wipe Kevin's notes.
    """
    live = {str(eid) for eid in (live_event_ids or [])}
    if not live:
        return 0
    removed = 0
    with _lock:
        for k in list(_MEMORY_STORE.keys()):
            if k not in live:
                del _MEMORY_STORE[k]
                removed += 1
    if removed:
        _persist()
    return removed
ersist()
    return removed
