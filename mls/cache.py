"""mls.cache — in-process cache + warmer thread for the MLS slate.

Pattern mirrors cfb/cache.py:
  - In-memory cache: full week of matches in a single entry
  - Background warmer: 25-min refresh cycle
  - Self-healing: stale-cache (>30 min) triggers synchronous rebuild on
    next read. Protects against silent warmer-thread death.
  - Kickoff freeze: forecast snapshot locks 1h before kickoff so the
    cheat-card numbers don't oscillate during the build-up window.

Cleanup:
  - Frozen snapshots dropped 6h after kickoff (match is long over).
  - Writeups for matches no longer on the slate get cleaned via
    mls.storage.delete_orphaned (called at the end of each rebuild).
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from .slate import build_mls_slate
from . import storage as mls_storage


REFRESH_SECONDS = 25 * 60

FREEZE_BEFORE_KICKOFF_HOURS    = 1
FREEZE_RELEASE_AFTER_KICKOFF_HOURS = 6
STALE_CACHE_THRESHOLD_SEC = 30 * 60
DEFAULT_WINDOW_DAYS = 7


_slate_cache: dict = {"matches": None, "built_at_utc": None, "build_err": None}
_cache_lock = threading.Lock()
_warmer_thread = None
_warmer_stop = threading.Event()

_frozen_forecasts: dict[str, dict] = {}
_frozen_lock = threading.Lock()


def get_mls_slate(allow_build: bool = True) -> tuple[list, dict | None]:
    """Return (matches_list, meta_or_None)."""
    with _cache_lock:
        entry = dict(_slate_cache) if _slate_cache.get("matches") is not None else None

    needs_rebuild = entry is None
    if entry is not None and allow_build:
        age_sec = (datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds()
        if age_sec > STALE_CACHE_THRESHOLD_SEC:
            print(f"[mls.cache] cache is {age_sec/60:.1f}min old (>30min) — forcing rebuild",
                  flush=True)
            needs_rebuild = True

    if needs_rebuild and allow_build:
        _rebuild()
        with _cache_lock:
            entry = dict(_slate_cache) if _slate_cache.get("matches") is not None else None

    if entry is None:
        return [], None
    age = int((datetime.now(timezone.utc) - entry["built_at_utc"]).total_seconds())
    return entry["matches"], {
        "built_at_utc": entry["built_at_utc"],
        "age_seconds":  age,
        "build_err":    entry.get("build_err"),
    }


def _rebuild() -> None:
    err = None
    matches = []
    try:
        matches = build_mls_slate(days_ahead=DEFAULT_WINDOW_DAYS)
        _apply_freeze(matches)
        _cleanup_after_rebuild(matches)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    with _cache_lock:
        _slate_cache["matches"] = matches
        _slate_cache["built_at_utc"] = datetime.now(timezone.utc)
        _slate_cache["build_err"] = err


def _apply_freeze(matches: list[dict]) -> None:
    """Freeze each match's cheat-card forecast inside the kickoff window."""
    now = datetime.now(timezone.utc)
    freeze_window_start = timedelta(hours=FREEZE_BEFORE_KICKOFF_HOURS)
    freeze_window_end = timedelta(hours=FREEZE_RELEASE_AFTER_KICKOFF_HOURS)

    seen_ids: set[str] = set()
    with _frozen_lock:
        for m in matches:
            mid = str(m.get("event_id") or "")
            kickoff = m.get("kickoff_utc")
            if not mid or not kickoff:
                m["is_frozen"] = False
                continue
            seen_ids.add(mid)

            time_to_kickoff = kickoff - now
            in_freeze_window = (
                -freeze_window_end <= time_to_kickoff <= freeze_window_start
            )

            if not in_freeze_window:
                m["is_frozen"] = False
                continue

            cached = _frozen_forecasts.get(mid)
            if cached:
                m["forecast"] = dict(cached)
                m["is_frozen"] = True
            else:
                if m.get("forecast"):
                    _frozen_forecasts[mid] = dict(m["forecast"])
                    m["is_frozen"] = True
                else:
                    m["is_frozen"] = False

        stale = [k for k in _frozen_forecasts if k not in seen_ids]
        for k in stale:
            del _frozen_forecasts[k]


def _cleanup_after_rebuild(matches: list[dict]) -> None:
    """Auto-delete writeups for matches no longer on the slate."""
    live_ids = [m.get("event_id") for m in matches if m.get("event_id")]
    try:
        removed = mls_storage.delete_orphaned(live_ids)
        if removed:
            print(f"[mls.cache] cleaned up {removed} orphaned writeup(s)", flush=True)
    except Exception as e:
        print(f"[mls.cache] writeup cleanup failed: {e}", flush=True)


def find_match_in_slate(date_str: str, slug: str) -> dict | None:
    """Look up a single match from the cache by date + slug."""
    matches, _meta = get_mls_slate(allow_build=False)
    for m in matches:
        if m.get("date_local") == date_str and m.get("slug") == slug:
            return m
    return None


def frozen_count() -> int:
    return len(_frozen_forecasts)


def warmer_loop() -> None:
    print("[mls.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            _rebuild()
            with _cache_lock:
                n = len(_slate_cache.get("matches") or [])
                err = _slate_cache.get("build_err")
            print(f"[mls.cache] rebuilt: {n} matches (err={err}, frozen={frozen_count()})",
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
        target=warmer_loop, name="mls-cache-warmer", daemon=True,
    )
    _warmer_thread.start()


def stop_warmer() -> None:
    _warmer_stop.set()
