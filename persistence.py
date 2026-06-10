"""
persistence.py — disk-backed JSON storage for writeups and forecast snapshots.

WHY this exists:
    Render's free / Starter dynos are ephemeral — every restart wipes
    in-memory dicts. Sport writeups (typed by Kevin in the admin) and MLB
    forecast freezes (locked at first pitch) need to survive across
    restarts.

PATH:
    Uses /var/data when present (Render persistent disk, mounted on the
    Starter+ tier with a Disk add-on). Falls back to ./data/ in the repo
    folder for local development so the same code runs in both places.

ATOMIC WRITES:
    Write to file.tmp, then os.replace() to the real path. If the process
    crashes mid-write, the existing file is intact. Per-file locks
    prevent concurrent writes from corrupting JSON.

DATETIME HANDLING:
    Datetimes are serialized as ISO 8601 strings on save. Callers that
    need datetime objects back should call _parse_dt() at the boundary.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Optional


# Render mounts the persistent disk at /var/data on the Starter+ tier.
# Locally, fall back to ./data/ in the repo so dev work doesn't error.
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.join(_HERE, "data")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception as e:
    print(f"[persistence] could not create {DATA_DIR}: {e}", flush=True)

# Boot log — makes it visible in Render logs which path persistence resolved to.
print(f"[persistence] writing to {DATA_DIR}", flush=True)


# One lock per filename so two threads writing the SAME file serialize,
# but writes to DIFFERENT files don't block each other.
_file_locks: dict[str, threading.Lock] = {}
_locks_master = threading.Lock()


def _lock_for(filename: str) -> threading.Lock:
    with _locks_master:
        if filename not in _file_locks:
            _file_locks[filename] = threading.Lock()
        return _file_locks[filename]


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def load_json(filename: str, default: Any = None) -> Any:
    """
    Read JSON from disk. Returns `default` (or {} if not given) if the
    file doesn't exist, can't be parsed, or can't be read.
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with _lock_for(filename):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[persistence] failed to load {filename}: {e}", flush=True)
        return default if default is not None else {}


def save_json(filename: str, data: Any) -> None:
    """
    Atomically write JSON to disk. Uses tmp + rename so a crash mid-write
    leaves the previous version intact rather than corrupting the file.
    """
    path = os.path.join(DATA_DIR, filename)
    tmp = path + ".tmp"
    try:
        with _lock_for(filename):
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=_json_default)
            os.replace(tmp, path)
    except Exception as e:
        print(f"[persistence] failed to save {filename}: {e}", flush=True)


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    """
    Convert an ISO 8601 string back to a datetime. Used by callers that
    need datetime objects for comparisons (forecast freeze cleanup, etc.).
    Returns None if input is None, empty, or unparseable.
    """
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None
