"""
mlb.cache — in-process slate cache + background warmer thread.

Why this exists:
    Building a slate from scratch hits MLB Stats API once, then NWS twice
    per park (one /points/ + one /forecast/hourly), then Open-Meteo for
    Toronto. That's ~30+ external calls per build. We don't want every
    page load to trigger that.

Pattern (matches OVERcast's approach):
    1. Cache the built slate keyed by date_str
    2. A background thread refreshes today/tomorrow every REFRESH_SECONDS
    3. On cache miss, build inline and cache (used for date archives)

Cache scope: per-process. Each Render worker has its own copy. With one
worker on Starter, this is fine. With multiple workers, each builds its
own; not ideal but not broken. Future improvement: shared Redis.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .slate import build_slate
from .nws import clear_periods_cache


EASTERN_TZ = ZoneInfo("America/New_York")

REFRESH_SECONDS = 25 * 60   # 25 min — matches OVERcast cadence

# date_str → {"slate": list[dict], "built_at_utc": datetime, "build_err": str|None}
_slate_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()

_warmer_thread: threading.Thread | None = None
_warmer_stop = threading.Event()


def _today_eastern_str() -> str:
    return datetime.now(EASTERN_TZ).strftime("%Y-%m-%d")


def _tomorrow_eastern_str() -> str:
    return (datetime.now(EASTERN_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")


def get_slate(date_str: str, allow_build: bool = True) -> tuple[list[dict] | None, dict | None]:
    """
    Return (slate, meta_dict_or_None). meta has:
        built_at_utc:  datetime
        age_seconds:   int (how long since build)
        build_err:     str | None (last build error if any)

    If date is not in cache and allow_build, builds it inline.
    """
    with _cache_lock:
        entry = _slate_cache.get(date_str)

    if entry is None and allow_build:
        _rebuild(date_str)
        with _cache_lock:
            entry = _slate_cache.get(date_str)

    if entry is None:
        return None, None

    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["slate"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild(date_str: str) -> None:
    """Build (or rebuild) the slate for date_str and store in the cache."""
    err: str | None = None
    slate: list[dict] = []
    try:
        # Drop NWS periods cache so we get fresh forecasts on rebuild
        clear_periods_cache()
        slate = build_slate(date_str)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    with _cache_lock:
        _slate_cache[date_str] = {
            "slate":         slate,
            "built_at_utc":  datetime.now(timezone.utc),
            "build_err":     err,
        }


def warmer_loop() -> None:
    """Background thread: refresh today + tomorrow every REFRESH_SECONDS."""
    print("[mlb.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            today    = _today_eastern_str()
            tomorrow = _tomorrow_eastern_str()
            for d in (today, tomorrow):
                _rebuild(d)
                with _cache_lock:
                    n_games = len(_slate_cache[d]["slate"])
                    err     = _slate_cache[d].get("build_err")
                print(f"[mlb.cache] rebuilt {d}: {n_games} games (err={err})", flush=True)
        except Exception:
            traceback.print_exc()
        # Sleep in 1-second slices so we can stop quickly on shutdown
        for _ in range(REFRESH_SECONDS):
            if _warmer_stop.is_set():
                return
            time.sleep(1)


def start_warmer() -> None:
    """Start the background warmer thread. Idempotent."""
    global _warmer_thread
    if _warmer_thread and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(target=warmer_loop, name="mlb-cache-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer() -> None:
    """Stop the warmer (used in tests or graceful shutdown)."""
    _warmer_stop.set()
