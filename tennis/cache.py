"""tennis.cache — in-process cache + warmer for the active Slam.

Mirrors golf/cache.py including the self-healing stale-cache rebuild
that defends against the "warmer thread silently dies" failure mode.

Key difference from golf: there's only ever 0 or 1 active Slam, so the
cache holds just one slam_dict instead of a slate of N events. When no
Slam is active, the warmer goes idle (logs and sleeps) and the route
returns None — the homepage card and sport-nav both gate on
schedule.is_any_slam_active() to hide themselves.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone

from .schedule import active_slam, get_slam_by_id
from .slate import build_slam_slate
from mlb.nws import clear_periods_cache as clear_nws_periods


REFRESH_SECONDS = 25 * 60

_slam_cache: dict = {"slam": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


# Same self-healing threshold as golf — 30 min (slightly more than the
# 25-min warmer cycle so a healthy warmer never trips this). If the
# warmer dies and the cache goes stale, the first user request after
# 30 min triggers a synchronous rebuild and self-heals.
STALE_CACHE_THRESHOLD_SEC = 30 * 60


def get_active_slam_slate(allow_build: bool = True):
    """Return (slam_dict, meta_or_None).

    slam_dict is None when no Slam is currently active (caller should
    render an empty state — the /tennis route returns 404, the homepage
    card hides itself).

    Auto-rebuilds if the cache is missing or older than the stale threshold.
    """
    # If no Slam is active right now, there's nothing to return.
    current = active_slam()
    if current is None:
        return None, None

    with _cache_lock:
        entry = dict(_slam_cache) if _slam_cache.get("slam") is not None else None

    # If the cached slam doesn't match the current active one (could happen
    # right at the boundary between two Slams in the calendar), invalidate
    # and rebuild for the now-active Slam.
    if entry is not None and entry["slam"].get("slam_id") != current["slam_id"]:
        entry = None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[tennis.cache] cache is {age_sec/60:.1f}min old (>30min) "
                  f"— forcing synchronous rebuild (warmer may be stuck)", flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild(current["slam_id"])
        with _cache_lock:
            entry = dict(_slam_cache) if _slam_cache.get("slam") is not None else None

    if entry is None:
        return None, None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["slam"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def get_slam_slate_by_id(slam_id: str):
    """Lookup any Slam by ID (active or not). Used by /tennis/<slam-slug>
    if we ever want to expose past/upcoming Slam pages. For now only the
    active one will have a built slate; past/future return None.
    """
    slam = get_slam_by_id(slam_id)
    if slam is None:
        return None, None
    current = active_slam()
    if current is not None and current["slam_id"] == slam_id:
        return get_active_slam_slate()
    # Inactive Slam — return the slam meta with no days built. Template
    # can render "tournament has concluded" or "tournament starts <date>".
    return slam, None


def _rebuild(slam_id: str):
    err = None
    slam = None
    try:
        slam = get_slam_by_id(slam_id)
        if slam is None:
            err = f"unknown slam_id: {slam_id}"
        else:
            clear_nws_periods()
            slam = build_slam_slate(slam)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slam_cache["slam"] = slam
        _slam_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slam_cache["build_err"] = err


def warmer_loop():
    print("[tennis.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            current = active_slam()
            if current is not None:
                _rebuild(current["slam_id"])
                with _cache_lock:
                    s = _slam_cache.get("slam")
                    n = len(s.get("days") or []) if s else 0
                    err = _slam_cache.get("build_err")
                print(f"[tennis.cache] rebuilt {current['slam_id']}: "
                      f"{n} days (err={err})", flush=True)
            else:
                # No Slam active — skip the fetch, save the API calls.
                # Cache stays empty; route returns None.
                print("[tennis.cache] no active Slam — idle cycle", flush=True)
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
    _warmer_thread = threading.Thread(target=warmer_loop, name="tennis-cache-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer():
    _warmer_stop.set()
