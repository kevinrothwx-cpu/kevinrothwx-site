"""
golf.cache — in-process cache + warmer for PGA tournament slate.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone

from .slate import build_pga_slate
from mlb.nws import clear_periods_cache as clear_nws_periods
from hrrr import clear_periods_cache as clear_hrrr_periods


REFRESH_SECONDS = 25 * 60

_pga_cache: dict = {"slate": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def get_pga_slate(allow_build: bool = True):
    """Return (slate, meta_or_None)."""
    with _cache_lock:
        entry = dict(_pga_cache) if _pga_cache.get("slate") is not None else None
    if entry is None and allow_build:
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


def warmer_loop():
    print("[golf.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild()
            with _cache_lock:
                n = len(_pga_cache.get("slate") or [])
                err = _pga_cache.get("build_err")
            print(f"[golf.cache] rebuilt: {n} tournaments (err={err})", flush=True)
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
