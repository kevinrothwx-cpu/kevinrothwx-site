"""
worldcup.storage — write-up storage with optional color tag.
Mirror of mlb.storage but keyed by ESPN event_id (string).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


VALID_COLORS = {"green", "yellow", "orange", "red"}

_MEMORY_STORE: dict[str, dict] = {}
_lock = threading.Lock()


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
            return
        _MEMORY_STORE[eid] = {
            "text":           text,
            "color":          color,
            "updated_at_utc": datetime.now(timezone.utc),
        }


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
