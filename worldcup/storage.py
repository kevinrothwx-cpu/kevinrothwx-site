"""
worldcup.storage — write-up storage with optional color tag.
Mirror of mlb.storage but keyed by ESPN event_id (string).
Disk-backed via persistence module, survives Render restarts.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


VALID_COLORS = {"green", "yellow", "orange", "red"}
_DISK_FILE = "writeups_worldcup.json"

_MEMORY_STORE: dict[str, dict] = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    """Read writeups from disk. JSON serializes datetimes to ISO strings,
    so rehydrate updated_at_utc back to datetime — the admin template calls
    .strftime() on it and would crash on a string."""
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


def list_writeups(event_ids: list[str]) -> dict[str, dict]:
    out = {}
    with _lock:
        for eid in event_ids:
            entry = _MEMORY_STORE.get(str(eid))
            if entry:
                out[str(eid)] = entry
    return out


def attach_writeups_to_slate(slate: list[dict]) -> None:
    eids = [m.get("event_id") for m in slate if m.get("event_id")]
    writeups = list_writeups(eids)
    for m in slate:
        m["writeup"] = writeups.get(str(m.get("event_id", "")))


def clear_all() -> None:
    with _lock:
        _MEMORY_STORE.clear()
