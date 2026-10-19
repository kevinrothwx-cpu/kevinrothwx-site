"""embed_stats — who is showing our iframe cards, and how often (2026-10-19).

Kevin's view: /admin/embed (app.py, behind ADMIN_PASSWORD).

WHAT GETS COUNTED
    One count per card load that reaches the server, keyed by:
      - day (Eastern)
      - referring site (the page the iframe sits on, from the Referer
        header; browsers send at least the site's domain for iframes)
      - card (sport/date/slug)
    Loads from mysportsweather.com itself (the picker's Preview button) are
    skipped so Kevin's own checks don't pad the numbers. No Referer at all
    (bots, privacy settings) is counted as "(no referrer)".

    Cloudflare is not caching these HTML responses today (cf-cache-status:
    DYNAMIC), so the counts are close to real views. If edge caching of
    HTML is ever turned on, counts become "cache misses" and undercount.

STORAGE
    New counts collect in memory and a background thread adds them to the
    saved copy ("embed_stats.json", via persistence) every FLUSH_SECONDS.
    Each flush re-reads the saved copy and adds to it, so a bad read can't
    wipe history. A restart can lose up to one window of counts; fine for
    a usage gauge. Keeps KEEP_DAYS days. Single gunicorn worker
    (Procfile -w 1), so one in-memory copy.

SAFETY
    record() never raises and never blocks on storage: a stats bug can't
    break a card.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FILENAME = "embed_stats.json"
FLUSH_SECONDS = 300
KEEP_DAYS = 60
MAX_REFS_PER_DAY = 500
MAX_CARDS_PER_DAY = 3000
NO_REF = "(no referrer)"
OWN_DOMAINS = ("mysportsweather.com", "kevinrothwx.com")

_EASTERN = ZoneInfo("America/New_York")
_lock = threading.Lock()
# Counts not yet saved: {day: {"refs": {ref: n}, "cards": {card: {ref: n}}}}.
# Deltas, not a full copy: every flush re-reads what's stored and ADDS these,
# so a failed or empty read can't wipe saved history (see flush()).
_pending: dict = {}
_seen_stored_days = 0     # how many days the last good read returned
_started = False


def _today() -> str:
    return datetime.now(_EASTERN).strftime("%Y-%m-%d")


def _read_stored():
    """Saved history, or None when the read failed / looks wrong."""
    try:
        from persistence import load_json
        d = load_json(FILENAME, {"days": {}})
        if isinstance(d, dict) and isinstance(d.get("days"), dict):
            return d
    except Exception as e:
        print(f"[embed_stats] load failed: {type(e).__name__}: {e}", flush=True)
    return None


def _merge(into: dict, delta: dict) -> None:
    for day, v in delta.items():
        d = into.setdefault(day, {"refs": {}, "cards": {}})
        d.setdefault("refs", {})
        d.setdefault("cards", {})
        for ref, n in v["refs"].items():
            d["refs"][ref] = d["refs"].get(ref, 0) + n
        for ck, by_ref in v["cards"].items():
            c = d["cards"].setdefault(ck, {})
            for ref, n in by_ref.items():
                c[ref] = c.get(ref, 0) + n


def _clean_ref(host: str) -> str | None:
    """'www.covers.com' -> 'covers.com'. None = our own site (not counted)."""
    h = (host or "").strip().lower().split(":", 1)[0]
    if not h:
        return NO_REF
    if h.startswith("www."):
        h = h[4:]
    if any(h == d or h.endswith("." + d) for d in OWN_DOMAINS):
        return None
    return h[:120]


def record(card_key: str, referer_host: str) -> None:
    try:
        ref = _clean_ref(referer_host)
        if ref is None:
            return
        day = _today()
        with _lock:
            d = _pending.setdefault(day, {"refs": {}, "cards": {}})
            refs, cards = d["refs"], d["cards"]
            if ref in refs or len(refs) < MAX_REFS_PER_DAY:
                refs[ref] = refs.get(ref, 0) + 1
            if card_key in cards or len(cards) < MAX_CARDS_PER_DAY:
                c = cards.setdefault(card_key, {})
                c[ref] = c.get(ref, 0) + 1
    except Exception as e:
        print(f"[embed_stats] record failed: {type(e).__name__}: {e}", flush=True)


def flush() -> None:
    """Add pending counts to saved history, prune old days, save.

    If the read fails, or comes back empty when the last good read had
    history, skip this round and keep the pending counts for next time.
    That's what stops a storage hiccup from overwriting real data."""
    global _pending, _seen_stored_days
    try:
        with _lock:
            if not _pending:
                return
            delta, _pending = _pending, {}
        stored = _read_stored()
        if stored is None or (not stored["days"] and _seen_stored_days > 0):
            print("[embed_stats] read looked wrong; keeping counts for next flush", flush=True)
            with _lock:
                _merge(_pending, delta)
            return
        _merge(stored["days"], delta)
        cutoff = (datetime.now(_EASTERN) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
        for day in [k for k in stored["days"] if k < cutoff]:
            del stored["days"][day]
        from persistence import save_json
        save_json(FILENAME, stored)
        _seen_stored_days = len(stored["days"])
    except Exception as e:
        print(f"[embed_stats] flush failed: {type(e).__name__}: {e}", flush=True)


def _flusher() -> None:
    while True:
        time.sleep(FLUSH_SECONDS)
        flush()


def start() -> None:
    global _started, _seen_stored_days
    if _started:
        return
    _started = True
    stored = _read_stored()
    if stored:
        _seen_stored_days = len(stored["days"])
    threading.Thread(target=_flusher, daemon=True, name="embed-stats-flush").start()


def summary(today: str | None = None) -> dict:
    """Numbers for /admin/embed."""
    today = today or _today()
    t = datetime.strptime(today, "%Y-%m-%d")
    d7 = (t - timedelta(days=6)).strftime("%Y-%m-%d")
    d30 = (t - timedelta(days=29)).strftime("%Y-%m-%d")
    stored = _read_stored() or {"days": {}}
    days = stored["days"]
    with _lock:
        _merge(days, _pending)          # include counts not saved yet
    sites: dict[str, dict] = {}
    cards: dict[str, dict] = {}
    daily = []
    for day in sorted(days):
        v = days[day]
        total = 0
        for ref, n in v.get("refs", {}).items():
            total += n
            s = sites.setdefault(ref, {"site": ref, "today": 0, "d7": 0, "d30": 0,
                                       "all": 0, "first": day, "last": day})
            s["all"] += n
            s["last"] = day
            if day == today:
                s["today"] += n
            if day >= d7:
                s["d7"] += n
            if day >= d30:
                s["d30"] += n
        if day >= d30:
            daily.append({"day": day, "views": total})
        if day >= d7:
            for ck, by_ref in v.get("cards", {}).items():
                c = cards.setdefault(ck, {"card": ck, "views": 0, "sites": {}})
                for ref, n in by_ref.items():
                    c["views"] += n
                    c["sites"][ref] = c["sites"].get(ref, 0) + n
    site_rows = sorted(sites.values(), key=lambda s: (-s["d30"], -s["all"]))
    card_rows = sorted(cards.values(), key=lambda c: -c["views"])[:100]
    for c in card_rows:
        c["site_list"] = ", ".join(f"{k} ({n})" for k, n in
                                   sorted(c["sites"].items(), key=lambda kv: -kv[1]))
    return {"today": today, "sites": site_rows, "cards": card_rows,
            "daily": list(reversed(daily)), "keep_days": KEEP_DAYS}


# EOF-CANARY 2026-10-19-embed-stats
