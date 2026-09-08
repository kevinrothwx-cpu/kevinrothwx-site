"""ucl.cache — in-process cache + warmer thread for the UCL slate.

Mirrors mls.cache: 25-min warmer cycle, 30-min stale-cache threshold for
self-healing rebuild, kickoff freeze applied per-match at build time.
"""

from __future__ import annotations

import threading
import threading as _threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from .slate import build_ucl_slate
from . import forecast_freeze
from . import storage as ucl_storage


REFRESH_SECONDS = 25 * 60            # matchday cadence, same as every other sport
IDLE_REFRESH_SECONDS = 6 * 60 * 60   # nothing scheduled soon
IDLE_AFTER_EMPTY_CYCLES = 2          # consecutive empty builds before backing off

FREEZE_BEFORE_KICKOFF_HOURS    = 1
FREEZE_RELEASE_AFTER_KICKOFF_HOURS = 4  # 90 min + injury + buffer
STALE_CACHE_THRESHOLD_SEC = 30 * 60
DEFAULT_WINDOW_DAYS = 7


_slate_cache: dict = {"matches": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()


def get_ucl_slate(allow_build: bool = True) -> tuple[list, dict | None]:
    """Return (matches_list, meta_or_None)."""
    with _cache_lock:
        entry = dict(_slate_cache) if _slate_cache.get("matches") is not None else None

    needs_rebuild = entry is None
    if entry and entry.get("built_at_utc"):
        age = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age > STALE_CACHE_THRESHOLD_SEC:
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild()
        with _cache_lock:
            entry = dict(_slate_cache) if _slate_cache.get("matches") is not None else None

    if not entry or entry.get("matches") is None:
        return [], {"build_err": entry.get("build_err") if entry else "no cache",
                    "built_at_utc": None}
    return entry["matches"], {
        "build_err":    entry.get("build_err"),
        "built_at_utc": entry.get("built_at_utc"),
    }


def _rebuild() -> None:
    """Synchronous rebuild — safe to call from warmer or from a read."""
    err = None
    matches = []
    try:
        matches = build_ucl_slate(days_ahead=DEFAULT_WINDOW_DAYS)
        _apply_freeze(matches)
        ucl_storage.attach_writeups_to_slate(matches)
        live_ids = [m.get("event_id") for m in matches if m.get("event_id")]
        try:
            ucl_storage.delete_orphaned(live_ids)
        except Exception as _e:
            print(f"[ucl.cache] writeup cleanup skipped: {_e}", flush=True)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["matches"] = matches
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def _apply_freeze(matches: list[dict]) -> None:
    """Freeze headline forecast in the kickoff window. Disk-backed."""
    now = datetime.now(timezone.utc)
    win_before = timedelta(hours=FREEZE_BEFORE_KICKOFF_HOURS)
    win_after  = timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS)

    for m in matches:
        eid = str(m.get("event_id") or "")
        kickoff = m.get("kickoff_utc")
        if not eid or not kickoff:
            m["is_frozen"] = False
            continue
        ttk = kickoff - now
        in_window = -win_after <= ttk <= win_before
        if not in_window:
            m["is_frozen"] = False
            continue

        cached = forecast_freeze.get(eid)
        if cached:
            m["forecast"]       = cached.get("forecast")
            m["hourly"]         = cached.get("hourly") or []
            m["weather_source"] = cached.get("weather_source") or m.get("weather_source")
            m["weather_error"]  = cached.get("weather_error")  or m.get("weather_error")
            m["is_frozen"] = True
        else:
            if m.get("forecast"):
                forecast_freeze.freeze(
                    eid,
                    forecast=m.get("forecast"),
                    hourly=m.get("hourly") or [],
                    weather_source=m.get("weather_source"),
                    weather_error=m.get("weather_error"),
                )
                m["is_frozen"] = True
            else:
                m["is_frozen"] = False

    try:
        cutoff = now - timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS + 12)
        forecast_freeze.clear_old(cutoff)
    except Exception as _e:
        print(f"[ucl.cache] freeze cleanup skipped: {_e}", flush=True)


def find_match_in_slate(date_str: str, slug: str):
    """Look up a match by date + slug from the current cache."""
    matches, _meta = get_ucl_slate(allow_build=False)
    for m in matches:
        if m.get("date_local") == date_str and m.get("slug") == slug:
            return m
    return None


def frozen_count() -> int:
    try:
        return forecast_freeze.count()
    except Exception:
        return 0


def _warmer_loop() -> None:
    """Adaptive warmer.

    The Champions League league phase plays eight Tuesdays and Wednesdays
    between September and January. Spinning a full rebuild every 25 minutes
    on the ~124 days with no fixtures would burn CPU on a 4-thread box and
    keep a paid API warm for nothing. So: run the normal 25-minute cycle
    whenever the slate has matches, and back off to 6 hours after two
    consecutive empty builds. The first non-empty build snaps straight back
    to the fast cycle, so a fixture appearing in the 7-day window is picked
    up within one idle interval at worst.
    """
    print("[ucl.cache] warmer started (25-min active / 6-hr idle)", flush=True)
    empty_streak = 0
    while not _warmer_stop.is_set():
        try:
            _rebuild_blocking()
            with _cache_lock:
                n = len(_slate_cache.get("matches") or [])
            empty_streak = empty_streak + 1 if n == 0 else 0
        except Exception:
            traceback.print_exc()
            empty_streak = 0

        idle = empty_streak >= IDLE_AFTER_EMPTY_CYCLES
        wait = IDLE_REFRESH_SECONDS if idle else REFRESH_SECONDS
        if idle and empty_streak == IDLE_AFTER_EMPTY_CYCLES:
            print("[ucl.cache] no fixtures in window; backing off to 6-hr cycle",
                  flush=True)
        _warmer_stop.wait(wait)


def start_warmer() -> None:
    """Boot the warmer thread. Idempotent."""
    global _warmer_thread
    if _warmer_thread is not None and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(target=_warmer_loop, name="ucl-warmer", daemon=True)
    _warmer_thread.start()


def stop_warmer() -> None:
    _warmer_stop.set()


# EOF-CANARY 2026-09-08-ucl-build


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
