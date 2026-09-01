"""
golf.cache — in-process cache + warmer for PGA tournament slate.
"""

from __future__ import annotations

import threading
import threading as _threading
import time
import traceback
from datetime import datetime, timezone

from datetime import timedelta

from .slate import build_pga_slate
from .storage import delete_orphaned as delete_orphaned_writeups
from . import forecast_freeze
from mlb.nws import clear_periods_cache as clear_nws_periods
from hrrr import clear_periods_cache as clear_hrrr_periods


REFRESH_SECONDS = 25 * 60

# Freeze cleanup: drop snapshots older than this. A typical tournament
# is Thursday-Sunday; 14 days is a generous cushion that survives bowl
# weeks and major championships with extra rounds.
FREEZE_RETENTION_DAYS = 14

_pga_cache: dict = {"slate": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


# Safety net for the "warmer thread silently dies" symptom Kevin keeps
# hitting. If the background warmer stops updating, the cache returns
# stale data indefinitely until a manual redeploy. By checking the cache
# age on every read, the first user request after the warmer stalls will
# force a synchronous rebuild and self-heal. Trade-off: that user gets a
# slow page load (5-15s for all the NWS/HRRR calls), but subsequent
# requests are fast again and the data is fresh.
STALE_CACHE_THRESHOLD_SEC = 30 * 60   # 30 min — slightly more than the
                                       # 25-min warmer cycle, so a healthy
                                       # warmer never trips this threshold.


def get_pga_slate(allow_build: bool = True):
    """Return (slate, meta_or_None).

    Auto-rebuilds if the cache is missing OR older than STALE_CACHE_THRESHOLD_SEC
    (and allow_build=True). The stale-rebuild path is the recovery mechanism
    for the "warmer thread silently stopped updating" failure mode.
    """
    with _cache_lock:
        entry = dict(_pga_cache) if _pga_cache.get("slate") is not None else None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[golf.cache] cache is {age_sec/60:.1f}min old (>30min) "
                  f"— forcing synchronous rebuild (warmer may be stuck)", flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild()
        with _cache_lock:
            entry = dict(_pga_cache) if _pga_cache.get("slate") is not None else None

    if entry is None:
        return None, None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["slate"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild():
    err = None
    slate = []
    try:
        clear_nws_periods()
        clear_hrrr_periods()
        slate = build_pga_slate()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _pga_cache["slate"] = slate
        _pga_cache["built_at_utc"] = datetime.now(timezone.utc)
        _pga_cache["build_err"] = err


def _cleanup_after_rebuild():
    """Orphaned-writeup + stale-freeze cleanup. Runs from the warmer thread
    after a successful rebuild. Safe-guarded so any failure here never
    breaks the warmer cycle."""
    try:
        with _cache_lock:
            slate = list(_pga_cache.get("slate") or [])
        live_ids = {str(t.get("event_id") or "") for t in slate if t.get("event_id")}
        live_ids.discard("")
        live_ids = {str(t.get("event_id") or "") for t in slate if t.get("event_id")}
        live_ids.discard("")
        n = delete_orphaned_writeups(live_ids)
        if n:
            print(f"[golf.cache] cleaned up {n} orphaned writeups", flush=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=FREEZE_RETENTION_DAYS)
        m = forecast_freeze.clear_old(cutoff)
        if m:
            print(f"[golf.cache] cleaned up {m} stale freeze entries", flush=True)
    except Exception as e:
        print(f"[golf.cache] cleanup error (ignored): {e}", flush=True)


def warmer_loop():
    print("[golf.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild_blocking()
            with _cache_lock:
                n = len(_pga_cache.get("slate") or [])
                err = _pga_cache.get("build_err")
            print(f"[golf.cache] rebuilt: {n} tournaments (err={err})", flush=True)
            _cleanup_after_rebuild()
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
    _warmer_thread = threading.Thread(target=warmer_loop, name="golf-cache-warmer", daemon=True)
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
