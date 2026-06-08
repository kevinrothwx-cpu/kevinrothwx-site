"""nascar.cache — in-process cache + warmer."""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone

from .slate import build_nascar_slate
from mlb.nws import clear_periods_cache as clear_nws_periods


REFRESH_SECONDS = 25 * 60

_nascar_cache = {"slate": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def get_nascar_slate(allow_build: bool = True):
    with _cache_lock:
        entry = dict(_nascar_cache) if _nascar_cache.get("slate") is not None else None
    if entry is None and allow_build:
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
        slate = build_nascar_slate()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _nascar_cache["slate"] = slate
        _nascar_cache["built_at_utc"] = datetime.now(timezone.utc)
        _nascar_cache["build_err"] = err


def warmer_loop():
    print("[nascar.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild()
            with _cache_lock:
                n = len(_nascar_cache.get("slate") or [])
                err = _nascar_cache.get("build_err")
            print(f"[nascar.cache] rebuilt: {n} races (err={err})", flush=True)
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
