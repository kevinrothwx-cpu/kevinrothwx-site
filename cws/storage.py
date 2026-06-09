"""cws.storage — write-up storage with color tag."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


VALID_COLORS = {"green", "yellow", "orange", "red"}
_MEMORY_STORE = {}
_lock = threading.Lock()


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
            return
        _MEMORY_STORE[eid] = {"text": text, "color": color,
                              "updated_at_utc": datetime.now(timezone.utc)}


def attach_writeups_to_slate(slate):
    eids = [g.get("event_id") for g in slate if g.get("event_id")]
    with _lock:
        for g in slate:
            g["writeup"] = _MEMORY_STORE.get(str(g.get("event_id", "")))


def clear_all():
    with _lock:
        _MEMORY_STORE.clear()
