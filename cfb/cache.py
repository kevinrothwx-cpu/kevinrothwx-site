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
from datetime import datetime, timedelta, timezone

from .slate import build_cfb_slate


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

# Frozen kickoff snapshots, keyed by ESPN game id.
# Value is the forecast dict captured at the moment we entered the freeze
# window. Released once the game is well past kickoff so the dict doesn't
# grow without bound across the season.
_frozen_forecasts: dict[str, dict] = {}
_frozen_lock = threading.Lock()


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
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["games"] = games
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def _apply_freeze(games: list[dict]) -> None:
    """Walk the slate and freeze kickoff-window games in place.

    For each game:
      - If kickoff is within FREEZE_BEFORE_KICKOFF_HOURS or already passed
        (but within the release window), we want to use a frozen snapshot.
      - If we already have a frozen snapshot for this game ID, swap it in.
      - If not, capture the current forecast as the freeze snapshot.
      - Either way, set game["is_frozen"] = True for template use.

    Cleanup: drop frozen entries for games whose release time has passed
    so the dict doesn't grow unbounded.
    """
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


def find_game_in_slate(date_str: str, slug: str) -> dict | None:
    """Look up a single game from the current cache by date + slug."""
    games, _meta = get_cfb_slate(allow_build=False)
    for g in games:
        if g.get("date_local") == date_str and g.get("slug") == slug:
            return g
    return None


def frozen_count() -> int:
    """Number of currently-frozen game snapshots, for admin diagnostics."""
    return len(_frozen_forecasts)


def warmer_loop() -> None:
    """Background thread that rebuilds the cache every REFRESH_SECONDS."""
    print("[cfb.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
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
