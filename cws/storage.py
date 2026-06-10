"""cws.storage — write-up storage with color tag.
Disk-backed via persistence module, survives Render restarts."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json


VALID_COLORS = {"green", "yellow", "orange", "red"}
_DISK_FILE = "writeups_cws.json"

_MEMORY_STORE = {}
_lock = threading.Lock()


def _load_from_disk() -> None:
    raw = load_json(_DISK_FILE, default={})
    with _lock:
        _MEMORY_STORE.clear()
        for k, v in raw.items():
            _MEMORY_STORE[str(k)] = v


def _persist() -> None:
    with _lock:
        snapshot = dict(_MEMORY_STORE)
    save_json(_DISK_FILE, snapshot)


_load_from_disk()


def get_writeup(event_id):
    with _lock:
        return _MEMORY_STORE.get(str(event_id))


def save_writeup(event_id, text, color: Optional[str] = None):
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
            _MEMORY_STORE[eid] = {"text": text, "color": color,
                                  "updated_at_utc": datetime.now(timezone.utc)}
    _persist()


def attach_writeups_to_slate(slate):
    eids = [g.get("event_id") for g in slate if g.get("event_id")]
    with _lock:
        for g in slate:
            g["writeup"] = _MEMORY_STORE.get(str(g.get("event_id", "")))


def clear_all():
    with _lock:
        _MEMORY_STORE.clear()
