"""nfl.cache — in-process cache + warmer thread for the NFL slate."""

from __future__ import annotations

from persistence import load_json as _load_json, save_json as _save_json

import threading
import threading as _threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from .slate import build_nfl_slate
from . import storage as nfl_storage


REFRESH_SECONDS = 25 * 60

FREEZE_BEFORE_KICKOFF_HOURS    = 1
FREEZE_RELEASE_AFTER_KICKOFF_HOURS = 6
STALE_CACHE_THRESHOLD_SEC = 30 * 60
DEFAULT_WINDOW_DAYS = 8


_slate_cache: dict = {"games": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()

_frozen_forecasts: dict[str, dict] = {}
_frozen_lock = threading.Lock()


def get_nfl_slate(allow_build: bool = True) -> tuple[list, dict | None]:
    with _cache_lock:
        entry = dict(_slate_cache) if _slate_cache.get("games") is not None else None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[nfl.cache] cache is {age_sec/60:.1f}min old (>30min) — forcing rebuild",
                  flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild()
        with _cache_lock:
            entry = dict(_slate_cache) if _slate_cache.get("games") is not None else None

    if entry is None:
        return [], None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["games"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild() -> None:
    err = None
    games = []
    try:
        games = build_nfl_slate(days_ahead=DEFAULT_WINDOW_DAYS)
        _apply_freeze(games)
        _cleanup_after_rebuild(games)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["games"] = games
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def _apply_freeze(games: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    freeze_window_start = timedelta(hours=FREEZE_BEFORE_KICKOFF_HOURS)
    freeze_window_end = timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS)

    seen_ids: set[str] = set()
    with _frozen_lock:
        for g in games:
            gid = str(g.get("id") or "")
            kickoff = g.get("kickoff_utc")
            if not gid or not kickoff:
                g["is_frozen"] = False
                continue
            seen_ids.add(gid)

            time_to_kickoff = kickoff - now
            in_freeze_window = (
                -freeze_window_end <= time_to_kickoff <= freeze_window_start
            )

            if not in_freeze_window:
                g["is_frozen"] = False
                continue

            cached = _frozen_forecasts.get(gid)
            if cached:
                g["forecast"] = dict(cached)
                g["is_frozen"] = True
            else:
                if g.get("forecast"):
                    _frozen_forecasts[gid] = dict(g["forecast"])
                    g["is_frozen"] = True
                else:
                    g["is_frozen"] = False

        stale = [k for k in _frozen_forecasts if k not in seen_ids]
        for k in stale:
            del _frozen_forecasts[k]


def _cleanup_after_rebuild(games: list[dict]) -> None:
    live_ids = [g.get("event_id") for g in games if g.get("event_id")]
    try:
        removed = nfl_storage.delete_orphaned(live_ids)
        if removed:
            print(f"[nfl.cache] cleaned up {removed} orphaned writeup(s)", flush=True)
    except Exception as e:
        print(f"[nfl.cache] writeup cleanup failed: {e}", flush=True)


def find_game_in_slate(date_str: str, slug: str) -> dict | None:
    """Find by kickoff_date_eastern + slug (NFL games are typically
    addressed by Eastern date since national TV broadcasts standardize on it)."""
    games, _meta = get_nfl_slate(allow_build=False)
    for g in games:
        if g.get("kickoff_date_eastern") == date_str and g.get("slug") == slug:
            return g
    return None


def frozen_count() -> int:
    return len(_frozen_forecasts)


def warmer_loop() -> None:
    print("[nfl.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild_blocking()
            with _cache_lock:
                n = len(_slate_cache.get("games") or [])
                err = _slate_cache.get("build_err")
            print(f"[nfl.cache] rebuilt: {n} games (err={err}, frozen={frozen_count()})",
                  flush=True)
        except Exception:
            traceback.print_exc()
        for _ in range(REFRESH_SECONDS):
            if _warmer_stop.is_set():
                return
            time.sleep(1)


def start_warmer() -> None:
    global _warmer_thread
    if _warmer_thread and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(
        target=warmer_loop, name="nfl-cache-warmer", daemon=True,
    )
    _warmer_thread.start()


def stop_warmer() -> None:
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


# ── Warm boot (2026-08-31) ─────────────────────────────────────────────
# In-memory caches start empty on every process start, and /health returns
# 200 before any slate is built — so Render swaps traffic to a brand new
# instance while it's still cold. Visitors got either a slow page or, worse,
# "No games scheduled in this window", which reads as "the season is over".
#
# Fix: mirror the last good slate into Postgres after each rebuild, and
# load it on import. A booting instance serves real data immediately while
# the warmer refreshes behind it.
#
# Safe because persistence round-trips datetimes losslessly (see
# persistence._json_default / _revive) — slate dicts are full of them
# (kickoff_utc, hourly period timestamps), and a bare-string round-trip
# would break every template that formats a date.
_WARM_KEY = "nfl_slate_warm.json"


def _save_warm_snapshot() -> None:
    """Mirror the current slate to Postgres. Best-effort; never raises."""
    try:
        with _cache_lock:
            games = _slate_cache.get("games")
            built = _slate_cache.get("built_at_utc")
        if not games:
            return
        _save_json(_WARM_KEY, {"games": games, "built_at_utc": built})
    except Exception as e:
        print(f"[{__name__}] warm snapshot save failed: {type(e).__name__}: {e}",
              flush=True)


def _load_warm_snapshot() -> None:
    """Populate the in-memory cache from the last saved slate, if empty."""
    try:
        with _cache_lock:
            if _slate_cache.get("games"):
                return
        raw = _load_json(_WARM_KEY, default=None)
        if not raw or not raw.get("games"):
            return
        with _cache_lock:
            _slate_cache["games"] = raw["games"]
            _slate_cache["built_at_utc"] = raw.get("built_at_utc")
            _slate_cache["build_err"] = None
        n = len(raw["games"])
        print(f"[{__name__}] warm boot: restored {n} games from snapshot "
              f"(built {raw.get('built_at_utc')})", flush=True)
    except Exception as e:
        print(f"[{__name__}] warm boot skipped: {type(e).__name__}: {e}", flush=True)


# Persist a snapshot after every rebuild, wrapping whichever _rebuild is
# current (the build-lock wrapper installed above).
_prewarm_rebuild = _rebuild


def _rebuild(*args, **kwargs):
    r = _prewarm_rebuild(*args, **kwargs)
    _save_warm_snapshot()
    return r


_prewarm_rebuild_blocking = _rebuild_blocking


def _rebuild_blocking(*args, **kwargs):
    r = _prewarm_rebuild_blocking(*args, **kwargs)
    _save_warm_snapshot()
    return r


_load_warm_snapshot()
