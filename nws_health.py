"""NWS API health tracker — rolling counters + threshold alerting.

Modules that call NWS report each outcome here (ok, rate_limit, server_error,
timeout, other_error). The tracker keeps a rolling 1-hour window of events
in memory and triggers an email alert via alerts.send_alert() when the
rate-limit count crosses a threshold within the recent window.

Design choices:
    - In-memory only (no disk persistence). Restarts reset counters — fine,
      because alerts are tied to live conditions, not historical analysis.
    - Single global tracker (NWS rate-limits per outbound IP, not per sport).
    - Threshold is intentionally conservative: 5 rate-limit events in 5 min
      triggers an alert. Anything below that is normal jitter (one venue
      occasionally times out, etc.).
    - The /admin/nws-health page reads from this same in-memory state, so
      what Kevin sees on the dashboard matches what triggered (or didn't
      trigger) the alert.

Usage (from any NWS caller):
    from nws_health import record, snapshot

    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 429:
            record("rate_limit", url)
        elif resp.status_code >= 500:
            record("server_error", url, code=resp.status_code)
        else:
            record("ok", url)
    except requests.Timeout:
        record("timeout", url)
    except Exception as e:
        record("other_error", url, msg=str(e))

The record() call is fire-and-forget — it never raises.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Optional

from alerts import send_alert

log = logging.getLogger(__name__)


# ── Tuning ────────────────────────────────────────────────────────────────

WINDOW_SEC = 60 * 60        # keep events for 1 hour
ALERT_WINDOW_SEC = 5 * 60   # threshold evaluated over this short window
ALERT_THRESHOLD = 5         # >= N rate-limit events in ALERT_WINDOW_SEC = alert


# ── State ─────────────────────────────────────────────────────────────────
# Each entry: (epoch_seconds, outcome_str, extra_str)
_events: deque[tuple[float, str, str]] = deque()
_lock = threading.Lock()


def record(outcome: str, url: str = "", code: Optional[int] = None,
           msg: str = "") -> None:
    """Record a single NWS API call outcome. Never raises.

    outcome: one of "ok", "rate_limit", "server_error", "timeout", "other_error"
    url:     the URL hit (truncated in storage to save memory)
    code:    HTTP status code if applicable
    msg:     short error message if applicable
    """
    try:
        now = time.time()
        # Compact extra info into one short string
        extra_parts = []
        if code is not None:
            extra_parts.append(f"code={code}")
        if msg:
            extra_parts.append(msg[:80])
        if url:
            # Just the path, not full query, to save memory
            short_url = url.split("?", 1)[0][-60:]
            extra_parts.append(short_url)
        extra = " | ".join(extra_parts)

        with _lock:
            _events.append((now, outcome, extra))
            _prune_locked(now)

        # Threshold check on rate_limit only — server_error/timeout don't
        # always mean we're being throttled.
        if outcome == "rate_limit":
            _maybe_alert(now)
    except Exception as e:
        # Health tracking must never break the calling code. Log and move on.
        log.warning(f"nws_health.record failed: {e}")


def snapshot() -> dict:
    """Return current rolling stats for the admin dashboard.

    Returns a dict with:
        window_minutes: how long the rolling window is (minutes)
        counts: dict of outcome -> count in last hour
        recent_alerts_5min: count of rate_limit events in the alert window
        last_event_epoch: timestamp of most recent event (or None)
        last_rate_limit_epoch: timestamp of most recent rate_limit (or None)
        sample_recent: last 20 events (epoch, outcome, extra)
    """
    now = time.time()
    with _lock:
        _prune_locked(now)
        events = list(_events)

    counts: dict[str, int] = {}
    last_event = None
    last_rate_limit = None
    recent_5min = 0
    for ts, outcome, _extra in events:
        counts[outcome] = counts.get(outcome, 0) + 1
        if last_event is None or ts > last_event:
            last_event = ts
        if outcome == "rate_limit":
            if last_rate_limit is None or ts > last_rate_limit:
                last_rate_limit = ts
            if now - ts <= ALERT_WINDOW_SEC:
                recent_5min += 1

    return {
        "window_minutes": WINDOW_SEC // 60,
        "counts": counts,
        "total_events": len(events),
        "recent_rate_limits_5min": recent_5min,
        "alert_threshold": ALERT_THRESHOLD,
        "last_event_epoch": last_event,
        "last_rate_limit_epoch": last_rate_limit,
        "sample_recent": [
            {"epoch": ts, "outcome": outcome, "info": extra}
            for ts, outcome, extra in events[-20:]
        ],
    }


# ── Internals ─────────────────────────────────────────────────────────────

def _prune_locked(now: float) -> None:
    """Drop events older than WINDOW_SEC. Caller holds _lock."""
    cutoff = now - WINDOW_SEC
    while _events and _events[0][0] < cutoff:
        _events.popleft()


def _maybe_alert(now: float) -> None:
    """If rate-limit count in the alert window crosses threshold, send email."""
    cutoff = now - ALERT_WINDOW_SEC
    with _lock:
        recent = sum(1 for ts, outcome, _ in _events
                     if ts >= cutoff and outcome == "rate_limit")
    if recent < ALERT_THRESHOLD:
        return

    # Threshold crossed — fire alert (cooldown is enforced inside alerts.py)
    body = (
        f"NWS API is rate-limiting mysportsweather.com.\n\n"
        f"Recent rate-limit count: {recent} in the last "
        f"{ALERT_WINDOW_SEC // 60} minutes.\n"
        f"Alert threshold: {ALERT_THRESHOLD}.\n\n"
        f"What's happening: NWS returned HTTP 429 enough times in a short "
        f"window that we tripped the alert threshold. Code is automatically "
        f"falling back to WeatherAPI for affected venues, so the site keeps "
        f"working. But this is worth checking — it could mean:\n\n"
        f"  - A traffic spike or warmer-thread bug burst NWS calls\n"
        f"  - OVERcast and mysportsweather.com share an outbound IP and the "
        f"combined load tripped the limit\n"
        f"  - NWS itself is having issues (check status.weather.gov)\n\n"
        f"Check the admin dashboard for full counts:\n"
        f"  https://mysportsweather.com/admin/nws-health\n"
    )
    send_alert(
        condition="nws_rate_limit",
        subject="NWS rate-limiting kevinrothwx-site",
        body=body,
    )
