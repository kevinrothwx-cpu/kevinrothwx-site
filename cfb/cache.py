"""cfb.cache — in-process cache + warmer thread for the CFB slate.

Pattern matches golf/cache.py:
  - In-memory cache keyed by date_str (one entry per date window we serve)
  - Background warmer thread refreshes every 25 minutes
  - Self-healing: on read, if cache is older than 30 min, force synchronous
    rebuild. This is the safety net for the "warmer thread silently dies"
    failure mode we've hit before on other sports.

CFB-specific behavior:
  - We cache by "window start date" not "single day"; one cache entry holds
    a full week of games (Tue-Sun typically)
  - The warmer fetches a 7-day window centered on "now"
  - Off-season (no upcoming CFB games for weeks), the warmer still runs but
    each cycle just returns an empty list quickly (ESPN responds fast for
    empty days, ~no API quota cost)
"""

from __future__ import annotations

from persistence import load_json as _load_json, save_json as _save_json

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from .slate import build_cfb_slate
from . import forecast_freeze
from . import storage as cfb_storage


REFRESH_SECONDS = 25 * 60

# Kickoff freeze window — mirrors the MLB first-pitch freeze pattern.
# Once kickoff is within FREEZE_BEFORE_KICKOFF_HOURS, the displayed
# forecast values (the cheat-sheet on the slate card and the kickoff
# snapshot on the detail page) lock to whatever they were at the moment
# we entered the window. The hourly strip continues to update from the
# warmer so users can see how conditions evolve during the game; only
# the headline numbers freeze. This is what gives OVERcast its perceived
# stability and we want the same feel here.
#
# After kickoff + FREEZE_RELEASE_AFTER_KICKOFF_HOURS the frozen snapshot
# is released (game is over, no one's looking at the live cheat sheet).
FREEZE_BEFORE_KICKOFF_HOURS    = 1
FREEZE_RELEASE_AFTER_KICKOFF_HOURS = 6

# Same self-healing threshold as golf — 30 min (slightly more than the
# 25-min warmer cycle so a healthy warmer never trips this). If the
# warmer dies and the cache goes stale, the first user request after
# 30 min triggers a synchronous rebuild and self-heals.
STALE_CACHE_THRESHOLD_SEC = 30 * 60

# Default forward-looking window: 7 days covers Tue MAC night through
# the following Sunday. Most weeks only have Thu-Sat games but the wider
# window costs nothing if those days are empty.
DEFAULT_WINDOW_DAYS = 7


_slate_cache: dict = {"games": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()

# Separate lock that serializes actual _rebuild() calls. Without this, a
# cold-cache burst (fresh deploy + Twitter link) causes every gunicorn
# worker thread to start its own 40s slate build in parallel, saturating
# the pool and blocking /health long enough to trip Render's 5s health-
# check alert. With this lock: only ONE build runs at a time; any other
# thread that arrives during a build immediately returns whatever's in
# cache (even empty) instead of stampeding. See 2026-08-25 incident.
_build_lock = threading.Lock()

# Frozen kickoff snapshots are now handled by cfb.forecast_freeze (disk-backed
# via persistence module — survives Render restarts). The in-memory dict here
# was replaced 2026-07-04 to match every other kickoff-sensitive sport.


def get_cfb_slate(allow_build: bool = True) -> tuple[list, dict | None]:
    """Return (games_list, meta_or_None).

    Auto-rebuilds if the cache is missing or older than the stale threshold.
    The stale-rebuild path is the recovery mechanism for the "warmer thread
    silently stopped updating" failure mode.

    Args:
        allow_build: If False, never trigger a synchronous build (used by
                     sitemap generation to avoid blocking on missing data).
    """
    with _cache_lock:
        entry = dict(_slate_cache) if _slate_cache.get("games") is not None else None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[cfb.cache] cache is {age_sec/60:.1f}min old (>30min) "
                  f"— forcing synchronous rebuild (warmer may be stuck)",
                  flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        # Non-blocking acquire — if another thread is already rebuilding,
        # skip and return whatever's in cache. Prevents the "N threads
        # all doing the same 40s build" stampede that saturates gunicorn
        # and blocks /health.
        acquired = _build_lock.acquire(blocking=False)
        if acquired:
            try:
                _rebuild()
            finally:
                _build_lock.release()
            with _cache_lock:
                entry = dict(_slate_cache) if _slate_cache.get("games") is not None else None
        else:
            print("[cfb.cache] rebuild already in progress in another thread — "
                  "serving current cache (may be empty)", flush=True)

    if entry is None:
        return [], None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["games"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild() -> None:
    """Pull the next 7 days of games and attach weather. Mutates the cache.

    After the slate is built, applies kickoff-freeze logic: any game whose
    kickoff is within the freeze window gets its forecast snapshot locked
    so the cheat-sheet doesn't oscillate as we approach game time.
    """
    err = None
    games = []
    try:
        games = build_cfb_slate(days_ahead=DEFAULT_WINDOW_DAYS)
        _apply_freeze(games)
        # Attach writeups + clean up orphaned notes for games that
        # rolled off the slate (finished + aged out).
        cfb_storage.attach_writeups_to_slate(games)
        live_ids = [g.get("event_id") for g in games if g.get("event_id")]
        try:
            cfb_storage.delete_orphaned(live_ids)
        except Exception as _e:
            print(f"[cfb.cache] writeup cleanup skipped: {_e}", flush=True)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["games"] = games
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def _apply_freeze(games: list[dict]) -> None:
    """Walk the slate and freeze kickoff-window games in place.

    Now DISK-BACKED via cfb.forecast_freeze so snapshots survive Render
    restarts. Also freezes hourly + hrrr_hourly, not just the headline
    forecast dict — that way both the cheat card AND the detail-page
    hourly strip stay stable through the game window.

    Cleanup: drop frozen entries whose release time has passed so the
    persistent JSON doesn't grow unbounded across the season.
    """
    now = datetime.now(timezone.utc)
    freeze_window_start = timedelta(hours=FREEZE_BEFORE_KICKOFF_HOURS)
    freeze_window_end = timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS)

    for g in games:
        gid = str(g.get("id") or "")
        kickoff = g.get("kickoff_utc")
        if not gid or not kickoff:
            g["is_frozen"] = False
            continue

        time_to_kickoff = kickoff - now
        in_freeze_window = (
            -freeze_window_end <= time_to_kickoff <= freeze_window_start
        )

        if not in_freeze_window:
            g["is_frozen"] = False
            continue

        cached = forecast_freeze.get(gid)
        if cached:
            # Restore the frozen snapshot in full — forecast + hourly + HRRR.
            g["forecast"]       = cached.get("forecast")
            g["hourly"]         = cached.get("hourly") or []
            g["hrrr_hourly"]    = cached.get("hrrr_hourly") or []
            g["weather_source"] = cached.get("weather_source") or g.get("weather_source")
            g["weather_error"]  = cached.get("weather_error")  or g.get("weather_error")
            g["is_frozen"] = True
        else:
            if g.get("forecast"):
                forecast_freeze.freeze(
                    gid,
                    forecast=g.get("forecast"),
                    hourly=g.get("hourly") or [],
                    hrrr_hourly=g.get("hrrr_hourly") or [],
                    weather_source=g.get("weather_source"),
                    weather_error=g.get("weather_error"),
                )
                g["is_frozen"] = True
            else:
                g["is_frozen"] = False

    # Persistent freeze cleanup: drop anything older than the release window
    # (frozen_at_utc + release hours would be well in the past).
    try:
        cutoff = now - timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS + 12)
        forecast_freeze.clear_old(cutoff)
    except Exception as _e:
        print(f"[cfb.cache] freeze cleanup skipped: {_e}", flush=True)


def find_game_in_slate(date_str: str, slug: str) -> dict | None:
    """Look up a single game from the current cache by date + slug."""
    games, _meta = get_cfb_slate(allow_build=False)
    for g in games:
        if g.get("date_local") == date_str and g.get("slug") == slug:
            return g
    return None


def frozen_count() -> int:
    """Number of currently-frozen game snapshots, for admin diagnostics."""
    try:
        return forecast_freeze.count()
    except Exception:
        return 0


def warmer_loop() -> None:
    """Background thread that rebuilds the cache every REFRESH_SECONDS."""
    print("[cfb.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            # Warmer blocks on _build_lock (unlike request threads which
            # skip). If a user-triggered rebuild is somehow in progress
            # when the warmer tick fires, warmer waits its turn instead
            # of duplicating the work. Bounded wait: the lock is only
            # ever held for one build.
            with _build_lock:
                _rebuild()
            with _cache_lock:
                n = len(_slate_cache.get("games") or [])
                err = _slate_cache.get("build_err")
            print(f"[cfb.cache] rebuilt: {n} games (err={err}, frozen={frozen_count()})", flush=True)
        except Exception:
            traceback.print_exc()
        for _ in range(REFRESH_SECONDS):
            if _warmer_stop.is_set():
                return
            time.sleep(1)


def start_warmer() -> None:
    """Boot the warmer thread. Idempotent — safe to call multiple times."""
    global _warmer_thread
    if _warmer_thread and _warmer_thread.is_alive():
        return
    _warmer_stop.clear()
    _warmer_thread = threading.Thread(
        target=warmer_loop,
        name="cfb-cache-warmer",
        daemon=True,
    )
    _warmer_thread.start()


def stop_warmer() -> None:
    _warmer_stop.set()


# EOF-CANARY 2026-07-04-cfb-recovery


# Alias so the warm-boot wrapper below has both entry points to wrap.
_rebuild_blocking = _rebuild


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
_WARM_KEY = "cfb_slate_warm.json"


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
