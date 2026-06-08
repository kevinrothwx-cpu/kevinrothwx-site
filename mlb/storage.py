"""
mlb.storage — write-up storage with optional color tag.

Phase 1: in-memory dict, wiped on Render restart. Upgrade to SQLite when
Kevin starts using the feature regularly (requires Render Starter plan).

Each write-up: {text, color, updated_at_utc}
  color ∈ {"green", "yellow", "orange", "red", None}
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


VALID_COLORS = {"green", "yellow", "orange", "red"}

_MEMORY_STORE: dict[int, dict] = {}
_lock = threading.Lock()


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
            return
        _MEMORY_STORE[pk] = {
            "text":           text,
            "color":          color,
            "updated_at_utc": datetime.now(timezone.utc),
        }


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
