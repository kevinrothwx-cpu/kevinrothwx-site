"""indexnow_auto — submit NEW pages to IndexNow automatically (2026-10-12).

WHY: Bing Webmaster Tools flagged "Some of your recently published pages were
not submitted via IndexNow." Until now IndexNow only ran when Kevin pressed
the button at /admin/indexnow, so every new game page (MLB, NFL, NCAAF, MLS,
Prem: dozens a day) went unannounced.

WHAT: a background thread. Every 30 minutes it takes the site's full URL
list (_msw_all_url_paths in app.py: evergreen pages + current game pages,
already excluding pages hidden from search), finds the ones it has never
submitted, and sends just those to IndexNow in one batch. Bing, Yandex and
other IndexNow engines share submissions, so one ping covers them all.

RULES:
    - New URLs only. A URL is submitted once; we don't re-ping pages every
      cycle (that reads as spam to Bing).
    - The submitted list is persisted (persistence.py), so a deploy or
      restart doesn't re-submit the whole site.
    - Entries older than 45 days are pruned so the list stays small. A game
      page is long gone by then; an evergreen page re-submitted after 45
      days is harmless.
    - The very first run (empty list) submits every current URL once,
      which is harmless and gives Bing a clean full picture. After that,
      only new URLs go out.
    - Never raises; failures log and retry next cycle.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from persistence import load_json, save_json

_FILE = "indexnow_submitted.json"
INTERVAL_SEC = 30 * 60
FIRST_DELAY_SEC = 5 * 60
KEEP_DAYS = 45
MAX_BATCH = 2000

_started = False
_lock = threading.Lock()


def _load() -> dict:
    raw = load_json(_FILE, default={}) or {}
    return raw if isinstance(raw, dict) else {}


def _prune(d: dict) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    return {k: v for k, v in d.items() if isinstance(v, str) and v >= cutoff}


def run_once(get_paths, notify, base_url: str = "https://mysportsweather.com") -> int:
    """One cycle. Returns the number of URLs submitted (0 if none/failed)."""
    with _lock:
        submitted = _prune(_load())
        paths = [p for p in (get_paths() or []) if isinstance(p, str) and p.startswith("/")]
        new = [p for p in paths if p not in submitted][:MAX_BATCH]
        if not new:
            save_json(_FILE, submitted)
            return 0
        ok = notify([base_url + p for p in new], host="mysportsweather.com")
        if not ok:
            print(f"[indexnow_auto] push of {len(new)} new URL(s) failed; will retry", flush=True)
            return 0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for p in new:
            submitted[p] = today
        save_json(_FILE, submitted)
        print(f"[indexnow_auto] submitted {len(new)} new URL(s), e.g. {new[:3]}", flush=True)
        return len(new)


def start(get_paths, notify) -> None:
    """Start the background loop once per process. Safe to call repeatedly."""
    global _started
    if _started:
        return
    _started = True

    def loop():
        time.sleep(FIRST_DELAY_SEC)          # let the warmers build slates first
        while True:
            try:
                run_once(get_paths, notify)
            except Exception as e:
                print(f"[indexnow_auto] cycle error (ignored): {type(e).__name__}: {e}", flush=True)
            time.sleep(INTERVAL_SEC)

    threading.Thread(target=loop, daemon=True, name="indexnow-auto").start()
    print("[indexnow_auto] started (every 30 min, new URLs only)", flush=True)


# EOF-CANARY 2026-10-12-indexnow-auto
