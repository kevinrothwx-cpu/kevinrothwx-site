"""
worldcup.cache — in-process cache + background warmer for World Cup matchdays.

Same pattern as mlb.cache. Refreshes today + 2 days ahead every 25 min.
Separate from mlb.cache so the two sport modules don't share state.
"""

from __future__ import annotations

import threading
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
                _rebuild(d)
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
