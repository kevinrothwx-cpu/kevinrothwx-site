"""cws.cache — in-process cache + warmer."""

from __future__ import annotations

import threading, time, traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .slate import build_cws_slate
from .venue import CWS_2026_START, CWS_2026_END
from mlb.nws import clear_periods_cache as clear_nws_periods


EASTERN_TZ = ZoneInfo("America/New_York")
REFRESH_SECONDS = 25 * 60

_cws_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def is_in_window():
    """Returns True if today is within the CWS 2026 window."""
    today = datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")
    return CWS_2026_START <= today <= CWS_2026_END


def get_cws_slate(date_str: str, allow_build: bool = True):
    with _cache_lock:
        entry = _cws_cache.get(date_str)
    if entry is None and allow_build:
        _rebuild(date_str)
        with _cache_lock:
            entry = _cws_cache.get(date_str)
    if entry is None:
        return None, None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["slate"], {
        "built_at_utc": entry["built_at_utc"], "age_seconds": age, "build_err": entry.get("build_err"),
    }


def _rebuild(date_str):
    err = None
    slate = []
    try:
        clear_nws_periods()
        slate = build_cws_slate(date_str)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _cws_cache[date_str] = {"slate": slate, "built_at_utc": datetime.now(timezone.utc), "build_err": err}


def warmer_loop():
    print("[cws.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            # Only refresh during the tournament window
            if is_in_window():
                today = datetime.now(EASTERN_TZ)
                for offset in (0, 1, 2):
                    d = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
                    _rebuild(d)
                    with _cache_lock:
                        n = len(_cws_cache[d]["slate"])
                        err = _cws_cache[d].get("build_err")
                    print(f"[cws.cache] rebuilt {d}: {n} games (err={err})", flush=True)
            else:
                print("[cws.cache] outside CWS window — skipping refresh", flush=True)
        except Exception:
            traceback.print_exc()
        for _ in range(REFRESH_SECONDS):
            if _warmer_stop.is_set():
                return
            time.sleep(1)


def start_warmer():
    global _warmer_thread
    if _warmer_thread and _warmer_thread.is_alive(): return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(target=warmer_loop, name="cws-cache-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer():
    _warmer_stop.set()
