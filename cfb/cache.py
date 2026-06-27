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

import threading
import time
import traceback
from datetime import datetime, timezone

from .slate import build_cfb_slate


REFRESH_SECONDS = 25 * 60

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
    """Pull the next 7 days of games and attach weather. Mutates the cache."""
    err = None
    games = []
    try:
        games = build_cfb_slate(days_ahead=DEFAULT_WINDOW_DAYS)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["games"] = games
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def warmer_loop() -> None:
    """Background thread that rebuilds the cache every REFRESH_SECONDS."""
    print("[cfb.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild()
            with _cache_lock:
                n = len(_slate_cache.get("games") or [])
                err = _slate_cache.get("build_err")
            print(f"[cfb.cache] rebuilt: {n} games (err={err})", flush=True)
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
