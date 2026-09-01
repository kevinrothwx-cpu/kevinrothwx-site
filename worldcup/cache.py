"""
worldcup.cache — in-process cache + background warmer for World Cup matchdays.

Same pattern as mlb.cache. Refreshes today + 2 days ahead every 25 min.
Separate from mlb.cache so the two sport modules don't share state.
"""

from __future__ import annotations

import threading
import threading as _threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .slate import build_matchday
from mlb.nws import clear_periods_cache as clear_nws_periods


EASTERN_TZ = ZoneInfo("America/New_York")
REFRESH_SECONDS = 25 * 60

_matchday_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def _today_eastern_str():
    return datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")


def _date_offset(days):
    return (datetime.now(EASTERN_TZ) + timedelta(days=days)).strftime("%Y-%m-%d")


def get_matchday(date_str: str, allow_build: bool = True):
    """Return (slate, meta_or_None) for a date."""
    with _cache_lock:
        entry = _matchday_cache.get(date_str)
    if entry is None and allow_build:
        _rebuild(date_str)
        with _cache_lock:
            entry = _matchday_cache.get(date_str)
    if entry is None:
        return None, None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["slate"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild(date_str: str):
    err = None
    slate = []
    try:
        # NWS periods cache is shared via mlb.nws; clear it so both sports refresh
        clear_nws_periods()
        slate = build_matchday(date_str)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _matchday_cache[date_str] = {
            "slate": slate,
            "built_at_utc": datetime.now(timezone.utc),
            "build_err": err,
        }


def warmer_loop():
    print("[worldcup.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            # Refresh today + next 2 days (the matchday view window)
            for offset in (0, 1, 2):
                d = _date_offset(offset)
                _rebuild_blocking(d)
                with _cache_lock:
                    n = len(_matchday_cache[d]["slate"])
                    err = _matchday_cache[d].get("build_err")
                print(f"[worldcup.cache] rebuilt {d}: {n} matches (err={err})", flush=True)
        except Exception:
            traceback.print_exc()
        for _ in range(REFRESH_SECONDS):
            if _warmer_stop.is_set():
                return
            time.sleep(1)


def start_warmer():
    global _warmer_thread
    if _warmer_thread and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(target=warmer_loop, name="worldcup-cache-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer():
    _warmer_stop.set()


# ── Build lock (2026-08-31) ────────────────────────────────────────────
# Without this, a cold cache under concurrent load makes EVERY request
# thread start its own slate rebuild. Gunicorn runs -w 1 --threads 4, so
# four simultaneous visitors consume all four threads for the length of a
# full build (tens of seconds), and /health can't get a thread inside
# Render's 5-second timeout. That fired a "server failure detected" alert
# on 2026-08-31 right after the disk detach, because removing the MLB
# pickle cache made MLB rebuild from the API on every boot.
#
# Request threads: non-blocking acquire. If a build is already running,
# skip and serve whatever is cached (possibly empty) rather than piling
# on. The in-flight build is refreshing the same data anyway.
#
# Warmer thread: blocking acquire via _rebuild_blocking, so a scheduled
# refresh waits its turn instead of being silently dropped.
_build_lock = _threading.Lock()
_unlocked_rebuild = _rebuild


def _rebuild(*args, **kwargs):
    """Request-path rebuild. Skips if another build is already running."""
    if not _build_lock.acquire(blocking=False):
        print(f"[{__name__}] rebuild already in progress — serving current cache",
              flush=True)
        return
    try:
        return _unlocked_rebuild(*args, **kwargs)
    finally:
        _build_lock.release()


def _rebuild_blocking(*args, **kwargs):
    """Warmer-path rebuild. Waits for any in-flight build to finish."""
    with _build_lock:
        return _unlocked_rebuild(*args, **kwargs)
