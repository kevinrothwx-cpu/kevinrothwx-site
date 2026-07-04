"""cfb.storage — CFB writeup storage with color tag.

Mirrors mls.storage exactly. Disk-backed via persistence module so
Kevin's notes survive Render restarts.

Kevin's stated intent: "we might as well wire in that capability in
case we decide to do some" — this module makes the /admin/cfb route
possible without committing to actually posting weekly writeups.

Key: ESPN event_id (string).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from persistence import load_json, save_json


VALID_COLORS = {"green", "yellow", "orange", "red"}
_DISK_FILE = "writeups_cfb.json"

_MEMORY_STORE: dict[str, dict] = {}
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


def list_writeups(event_ids):
    out = {}
    with _lock:
        for eid in event_ids:
            entry = _MEMORY_STORE.get(str(eid))
            if entry:
                out[str(eid)] = entry
    return out


def attach_writeups_to_slate(slate):
    eids = [g.get("event_id") for g in slate if g.get("event_id")]
    writeups = list_writeups(eids)
    for g in slate:
        g["writeup"] = writeups.get(str(g.get("event_id", "")))


def clear_all():
    with _lock:
        _MEMORY_STORE.clear()


def delete_orphaned(live_event_ids) -> int:
    """Delete writeups whose event_id is no longer in the live slate."""
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


# EOF-CANARY 2026-07-04-cfb-recovery
