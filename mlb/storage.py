"""
mlb.storage — write-up storage interface.

Phase 1 (NOW): in-memory dict, wiped on every Render restart.
  Kevin won't be using the write-up feature yet, so this is fine.

Phase 2 (when Kevin starts writing): swap _MEMORY_STORE for a SQLite
  backend. Requires upgrading kevinrothwx-site Render service to
  Starter ($7/mo) with persistent disk add-on. The interface here
  (get_writeup, save_writeup, list_writeups) stays identical.

A write-up is keyed by MLB game_pk (unique per game per day). Storing
by game_pk means doubleheaders are naturally distinct, and a write-up
written for "today's Cubs game" never bleeds into "tomorrow's Cubs game"
the way a (team, date) key could.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


# game_pk → {"text": str, "updated_at_utc": datetime}
_MEMORY_STORE: dict[int, dict] = {}
_lock = threading.Lock()


def get_writeup(game_pk: int) -> Optional[dict]:
    """Return {"text", "updated_at_utc"} or None if no write-up exists."""
    with _lock:
        return _MEMORY_STORE.get(int(game_pk))


def save_writeup(game_pk: int, text: str) -> None:
    """Save (or replace) a write-up for one game. Empty text = delete."""
    pk = int(game_pk)
    text = (text or "").strip()
    with _lock:
        if not text:
            _MEMORY_STORE.pop(pk, None)
            return
        _MEMORY_STORE[pk] = {
            "text":           text,
            "updated_at_utc": datetime.now(timezone.utc),
        }


def list_writeups(game_pks: list[int]) -> dict[int, dict]:
    """Return a {game_pk: writeup} dict, only including pks that have write-ups."""
    out = {}
    with _lock:
        for pk in game_pks:
            entry = _MEMORY_STORE.get(int(pk))
            if entry:
                out[int(pk)] = entry
    return out


def attach_writeups_to_slate(slate: list[dict]) -> None:
    """
    Mutates slate in place: adds `writeup` key to each game dict
    (either the writeup dict or None).
    """
    pks = [g["game_pk"] for g in slate if g.get("game_pk")]
    writeups = list_writeups(pks)
    for g in slate:
        g["writeup"] = writeups.get(int(g.get("game_pk", 0)))


def clear_all() -> None:
    """Test helper — clears the in-memory store."""
    with _lock:
        _MEMORY_STORE.clear()
