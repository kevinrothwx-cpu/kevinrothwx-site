"""
mlb.cache — disk-backed slate cache + background warmer thread.

Why this exists:
    Building a slate from scratch hits MLB Stats API once, then NWS twice
    per park (one /points/ + one /forecast/hourly), then Open-Meteo for
    Toronto. That's ~30+ external calls per build. We don't want every
    page load to trigger that.

Pattern:
    1. Cache the built slate keyed by date_str, both in-memory AND on disk
       (Render persistent disk at /var/data/mlb_slate_cache/).
    2. A background thread refreshes today/tomorrow every REFRESH_SECONDS.
       Each rebuild writes the slate atomically to disk.
    3. On every get_slate() call, we stat the disk file. If it's newer
       than our in-memory copy (i.e. another worker's warmer refreshed it),
       we load the disk copy into memory before returning.
    4. On cache miss with no disk copy either, build inline.

Why disk-backed (2026-07-22, task #17):
    Multi-worker gunicorn deploys had per-process in-memory caches that
    drifted. Worker A might have data from 12:00, worker B from 12:25,
    and users were served randomly by either — sometimes seeing stale
    data for hours. With shared disk, whichever worker's warmer succeeds
    first, all workers immediately see the fresh data on their next request.

Kill switch:
    Set env var MLB_DISK_CACHE_DISABLED=1 in Render to fall back to the
    pure in-memory behavior. Useful if disk-backing ever misbehaves.

Serialization:
    We use pickle instead of JSON because the slate contains datetimes,
    nested dicts, and mixed types that JSON round-trips badly (datetimes
    become strings and downstream code expects datetime objects). Pickle
    handles Python types natively. Files are per-process-atomic-rename
    written — no cross-worker locking needed because rename is atomic
    at the filesystem level.
"""

from __future__ import annotations

from persistence import load_json as _load_json, save_json as _save_json

import os
import pickle
import threading
import threading as _threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from persistence import DATA_DIR
from .slate import build_slate
from .nws import clear_periods_cache


EASTERN_TZ = ZoneInfo("America/New_York")

REFRESH_SECONDS = 25 * 60   # 25 min. Briefly tried 5 min (2026-06-17) to
                             # match OVERcast more tightly; reverted because
                             # OVERcast started failing intermittently and
                             # the timing matched our cycles strongly enough
                             # to suspect we were tripping a shared-egress
                             # NWS rate-limit on Render.

# ── Disk-backed cache config ────────────────────────────────────────
_DISK_CACHE_DIR = os.path.join(DATA_DIR, "mlb_slate_cache")


def _disk_cache_disabled() -> bool:
    """Env-var kill switch. Set MLB_DISK_CACHE_DISABLED=1 to bypass all
    disk operations and fall back to pure in-memory (pre-2026-07-22)
    behavior."""
    return os.environ.get("MLB_DISK_CACHE_DISABLED", "").strip() == "1"


def _disk_cache_path(date_str: str) -> str:
    return os.path.join(_DISK_CACHE_DIR, f"mlb_slate_{date_str}.pkl")


def _write_slate_to_disk(date_str: str, entry: dict) -> None:
    """Best-effort atomic write of a cache entry to disk.
    Logs on failure but never raises — disk write failure is not fatal;
    the in-memory cache still has the fresh data for this worker."""
    if _disk_cache_disabled():
        return
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
        path = _disk_cache_path(date_str)
        # Include PID in tmp name so two workers writing simultaneously
        # don't clobber each other's tmp file. os.replace is atomic.
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "wb") as f:
            pickle.dump(entry, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, path)
    except Exception as e:
        print(
            f"[mlb.cache] disk write failed for {date_str}: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )


def _read_slate_from_disk_if_fresher(date_str: str) -> None:
    """If the disk copy is newer than what's in memory (i.e. another
    worker rebuilt it more recently than we did), load it into memory.

    Silent on any error — a corrupted or missing disk file just means
    we fall through to whatever's in memory, which is same-as-current
    behavior. This is the primary safety net for the whole disk-cache
    change: any bug here degrades to "no worse than today"."""
    if _disk_cache_disabled():
        return
    try:
        path = _disk_cache_path(date_str)
        if not os.path.exists(path):
            return
        disk_mtime = os.path.getmtime(path)
        with _cache_lock:
            mem = _slate_cache.get(date_str)
            mem_mtime = mem.get("_disk_mtime") if mem else None
        if mem_mtime is not None and disk_mtime <= mem_mtime:
            # Our in-memory copy is at least as fresh as disk. Skip.
            return
        with open(path, "rb") as f:
            entry = pickle.load(f)
        # Sanity: entry must have the expected shape or we ignore it.
        if not isinstance(entry, dict):
            return
        if "slate" not in entry or "built_at_utc" not in entry:
            return
        entry["_disk_mtime"] = disk_mtime
        with _cache_lock:
            _slate_cache[date_str] = entry
    except Exception as e:
        print(
            f"[mlb.cache] disk read failed for {date_str}: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )


# date_str → {"slate": list[dict], "built_at_utc": datetime, "build_err": str|None,
#             "_disk_mtime": float (present only for entries loaded from disk)}
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

    Reads:
        1. Check disk for a fresher copy from another worker's warmer.
        2. If disk had one, it's now in memory. Return it.
        3. Otherwise return whatever's in memory.
        4. If nothing in memory and allow_build, build inline.
    """
    # Step 1: pick up any fresher disk copy before we look at memory.
    _read_slate_from_disk_if_fresher(date_str)

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


def _prune_old_slates() -> None:
    """Remove cached slates for dates older than today (Eastern) from
    both memory and disk. Without this, _slate_cache accumulates one
    entry per date any user or admin has ever browsed to — after a
    week you see 7+ dates in /admin/cache-health, all showing STALE,
    which hides the real staleness signal for today/tomorrow.

    Silent on disk delete failure — the memory cleanup already
    happened and a leftover pkl file is cosmetic."""
    today = _today_eastern_str()
    with _cache_lock:
        old = [d for d in list(_slate_cache) if d < today]
        for d in old:
            _slate_cache.pop(d, None)
    if _disk_cache_disabled():
        return
    try:
        if not os.path.exists(_DISK_CACHE_DIR):
            return
        for fn in os.listdir(_DISK_CACHE_DIR):
            # File format: mlb_slate_YYYY-MM-DD.pkl
            if not (fn.startswith("mlb_slate_") and fn.endswith(".pkl")):
                continue
            date_part = fn[len("mlb_slate_"):-len(".pkl")]
            # ISO YYYY-MM-DD sorts lexicographically, so string < today works
            if date_part < today:
                try:
                    os.remove(os.path.join(_DISK_CACHE_DIR, fn))
                except Exception:
                    pass
    except Exception as e:
        print(f"[mlb.cache] prune failed: {type(e).__name__}: {e}", flush=True)


def _rebuild(date_str: str) -> None:
    """Build (or rebuild) the slate for date_str, store in memory, and
    persist to disk so other workers see the fresh data on their next
    request."""
    err: str | None = None
    slate: list[dict] = []
    try:
        # Drop NWS periods cache so we get fresh forecasts on rebuild
        clear_periods_cache()
        slate = build_slate(date_str)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    entry = {
        "slate":         slate,
        "built_at_utc":  datetime.now(timezone.utc),
        "build_err":     err,
    }
    with _cache_lock:
        _slate_cache[date_str] = entry
    # Persist to disk. Best-effort — on any error we still have the
    # in-memory copy for this worker.
    _write_slate_to_disk(date_str, entry)


def warmer_loop() -> None:
    """Background thread: refresh today + tomorrow every REFRESH_SECONDS."""
    print("[mlb.cache] warmer thread started", flush=True)
    while not _warmer_stop.is_set():
        try:
            today    = _today_eastern_str()
            tomorrow = _tomorrow_eastern_str()
            # Drop yesterday-and-older entries first so cache-health only
            # shows dates that actually matter (today + tomorrow).
            _prune_old_slates()
            for d in (today, tomorrow):
                _rebuild_blocking(d)
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
# MLB previously survived restarts via pickle files on the Render disk.
# That disk is gone (it blocked zero-downtime deploys) and
# MLB_DISK_CACHE_DISABLED=1 now short-circuits those writes, so every
# restart forced a full rebuild from the MLB API plus per-park weather —
# the slow first load, and the thread starvation that tripped Render's
# health check on 2026-08-31.
#
# Same fix as CFB/NFL, but MLB's cache is keyed by date_str, so we
# snapshot the whole {date: entry} map rather than a single slate.
_WARM_KEY = "mlb_slate_warm.json"


def _save_warm_snapshot() -> None:
    """Mirror every cached date to Postgres. Best-effort; never raises."""
    try:
        with _cache_lock:
            snap = {d: {"slate": e.get("slate"),
                        "built_at_utc": e.get("built_at_utc")}
                    for d, e in _slate_cache.items() if e.get("slate")}
        if snap:
            _save_json(_WARM_KEY, snap)
    except Exception as e:
        print(f"[mlb.cache] warm snapshot save failed: {type(e).__name__}: {e}",
              flush=True)


def _load_warm_snapshot() -> None:
    """Restore cached dates from the last snapshot, for dates not already
    in memory. Never overwrites fresher in-memory data."""
    try:
        raw = _load_json(_WARM_KEY, default=None)
        if not raw:
            return
        restored = 0
        with _cache_lock:
            for d, e in raw.items():
                if d in _slate_cache or not e.get("slate"):
                    continue
                _slate_cache[d] = {
                    "slate":        e["slate"],
                    "built_at_utc": e.get("built_at_utc"),
                    "build_err":    None,
                }
                restored += 1
        if restored:
            print(f"[mlb.cache] warm boot: restored {restored} date(s) from snapshot",
                  flush=True)
    except Exception as e:
        print(f"[mlb.cache] warm boot skipped: {type(e).__name__}: {e}", flush=True)


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
