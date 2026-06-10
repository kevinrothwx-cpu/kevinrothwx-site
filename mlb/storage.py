"""
mlb.storage — write-up storage with optional color tag.

Disk-backed via persistence module. Reads /var/data/writeups_mlb.json on
import; writes on every save_writeup. Survives Render restarts.

Each write-up: {text, color, updated_at_utc}
  color ∈ {"green", "yellow", "orange", "red", None}
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


# Populate from disk on module import
_load_from_disk()


def get_writeup(game_pk: int) -> Optional[dict]:
    with _lock:
        return _MEMORY_STORE.get(int(game_pk))


def save_writeup(game_pk: int, text: str, color: Optional[str] = None) -> None:
    """
    Save (or replace) a write-up. Empty text = delete.
    Color must be one of VALID_COLORS or None.
    """
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
