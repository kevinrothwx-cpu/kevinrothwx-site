"""nascar.cache — in-process cache + warmer.

Self-healing pattern (added 2026-06-29 after Sonoma stayed visible day
after race): on read, if cache age exceeds STALE_CACHE_THRESHOLD_SEC,
force a synchronous rebuild. This is the safety net for the
"warmer-thread silently died" failure mode we've hit on other sports.
Without it, a dead warmer means the page serves stale data indefinitely
until a Render redeploy.

Warmer cycle also:
  - Cleans orphaned writeups (events no longer in live slate, e.g. last
    Sunday's race after auto-advance dropped it)
  - Cleans stale freeze entries (>7 days old)
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone, timedelta

from .slate import build_nascar_slate
from .storage import delete_orphaned as delete_orphaned_writeups
from . import forecast_freeze
from mlb.nws import clear_periods_cache as clear_nws_periods
from hrrr import clear_periods_cache as clear_hrrr_periods


REFRESH_SECONDS = 25 * 60

# Same self-healing threshold as golf and CFB (~30 min — slightly more
# than the 25-min warmer cycle so a healthy warmer never trips this).
# If the warmer dies and cache goes stale, the first user request after
# 30 min triggers a synchronous rebuild and self-heals.
STALE_CACHE_THRESHOLD_SEC = 30 * 60

# Freeze cleanup: drop snapshots older than this. Races finish and roll
# off the slate within ~12 hours; 7 days is a generous cushion.
FREEZE_RETENTION_DAYS = 7


_nascar_cache = {"slate": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def get_nascar_slate(allow_build: bool = True):
    """Return (slate, meta). Auto-rebuilds if missing OR older than the
    stale threshold (and allow_build=True). The stale-rebuild path is the
    recovery mechanism for warmer-died failure mode."""
    with _cache_lock:
        entry = dict(_nascar_cache) if _nascar_cache.get("slate") is not None else None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[nascar.cache] cache is {age_sec/60:.1f}min old (>30min) "
                  f"— forcing synchronous rebuild (warmer may be stuck)",
                  flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild()
        with _cache_lock:
            entry = dict(_nascar_cache) if _nascar_cache.get("slate") is not None else None

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
        slate = build_nascar_slate()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _nascar_cache["slate"] = slate
        _nascar_cache["built_at_utc"] = datetime.now(timezone.utc)
        _nascar_cache["build_err"] = err


def _cleanup_after_rebuild():
    """Orphaned-writeup + stale-freeze cleanup. Runs from the warmer thread
    after a successful rebuild. Safe-guarded so any failure here never breaks
    the warmer cycle."""
    try:
        with _cache_lock:
            slate = list(_nascar_cache.get("slate") or [])
        live_ids = {str(r.get("event_id") or r.get("id") or "")
                    for r in slate if (r.get("event_id") or r.get("id"))}
        live_ids.discard("")
        n = delete_orphaned_writeups(live_ids)
        if n:
            print(f"[nascar.cache] cleaned up {n} orphaned writeups", flush=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=FREEZE_RETENTION_DAYS)
        m = forecast_freeze.clear_old(cutoff)
        if m:
            print(f"[nascar.cache] cleaned up {m} stale freeze entries", flush=True)
    except Exception as e:
        print(f"[nascar.cache] cleanup error (ignored): {e}", flush=True)


def warmer_loop():
    print("[nascar.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild()
            with _cache_lock:
                n = len(_nascar_cache.get("slate") or [])
                err = _nascar_cache.get("build_err")
            print(f"[nascar.cache] rebuilt: {n} races (err={err})", flush=True)
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
    _warmer_thread = threading.Thread(target=warmer_loop, name="nascar-cache-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer():
    _warmer_stop.set()
