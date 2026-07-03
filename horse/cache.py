"""horse.cache — in-process cache + warmer thread for the horse racing slate.

Pattern mirrors mls.cache / golf.cache:
  - In-memory cache: full slate of upcoming stakes days
  - Background warmer: 25-min refresh cycle
  - Self-healing: stale cache (>30 min) triggers synchronous rebuild
    on the next read.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from .slate import build_horse_slate
from . import forecast_freeze


REFRESH_SECONDS = 25 * 60
STALE_CACHE_THRESHOLD_SEC = 30 * 60


_slate_cache: dict = {"races": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def get_horse_slate(allow_build: bool = True) -> tuple[list, dict | None]:
    """Return (races_list, meta_or_None)."""
    with _cache_lock:
        entry = dict(_slate_cache) if _slate_cache.get("races") is not None else None

    needs_rebuild = entry is None
    if entry and entry.get("built_at_utc"):
        age = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age > STALE_CACHE_THRESHOLD_SEC:
            needs_rebuild = True

    if needs_rebuild and allow_build:
        rebuild_slate()
        with _cache_lock:
            entry = dict(_slate_cache) if _slate_cache.get("races") is not None else None

    if not entry or entry.get("races") is None:
        return [], {"build_err": entry.get("build_err") if entry else "no cache", "built_at_utc": None}
    return entry["races"], {"build_err": entry.get("build_err"), "built_at_utc": entry.get("built_at_utc")}


def rebuild_slate() -> None:
    """Synchronous rebuild. Safe to call from the warmer or from a read."""
    try:
        races = build_horse_slate()
        with _cache_lock:
            _slate_cache["races"] = races
            _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
            _slate_cache["build_err"] = None
        # Cleanup old freezes
        try:
            forecast_freeze.clear_old(days_after=3)
        except Exception:
            pass
    except Exception as e:
        traceback.print_exc()
        with _cache_lock:
            _slate_cache["build_err"] = str(e)
            _slate_cache["built_at_utc"] = datetime.now(timezone.utc)


def _warmer_loop() -> None:
    """Background thread: rebuild every REFRESH_SECONDS."""
    while not _warmer_stop.is_set():
        try:
            rebuild_slate()
        except Exception:
            traceback.print_exc()
        _warmer_stop.wait(REFRESH_SECONDS)


def start_warmer() -> None:
    """Start the background warmer thread. Idempotent."""
    global _warmer_thread
    if _warmer_thread is not None and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(target=_warmer_loop, name="horse-warmer", daemon=True)
    _warmer_thread.start()
    print("[horse.cache] warmer started (25-min cycle)", flush=True)


def stop_warmer() -> None:
    _warmer_stop.set()
