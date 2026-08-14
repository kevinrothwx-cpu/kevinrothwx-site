"""
nascar.schedule — ESPN unofficial NASCAR Cup Series scoreboard.

ESPN's documented NASCAR Cup endpoint stopped returning data sometime
before June 2026 — every URL pattern tested returns 400 or empty events.
The community ESPN-API gist no longer lists a NASCAR endpoint.

We still try the original URL plus two plausible alternatives each
fetch in case ESPN restores access. If all three return nothing, we
fall back to the hand-curated 2026 schedule in schedule_fallback.py
so the /nascar page is never blank during the active season.
"""

from __future__ import annotations

import requests
import re
from datetime import datetime, timezone
from typing import Optional

from .schedule_fallback import get_fallback_events


# Patterns to try, in order. The first that returns events wins.
ESPN_NASCAR_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-cup-series/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/racing/nascar/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier-series/scoreboard",
]
REQUEST_HEADERS = {
    # Chrome desktop UA — see nfl/schedule.py for the 2026-08-14 UA-switch context
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_nascar_scoreboard() -> list[dict]:
    """
    Fetch current/upcoming NASCAR Cup races. Tries ESPN's known URL
    patterns first; if none return data, falls back to the embedded
    2026 schedule so the page stays useful while ESPN access is broken.
    """
    for url in ESPN_NASCAR_URLS:
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
            resp.raise_for_status()
            events = resp.json().get("events", []) or []
            if events:
                print(f"[nascar.schedule] ESPN returned {len(events)} events from {url}", flush=True)
                return events
        except Exception as e:
            print(f"[nascar.schedule] ESPN error at {url}: {e}", flush=True)
            continue

    # All ESPN attempts failed or returned empty — use the embedded schedule.
    fallback = get_fallback_events(datetime.now(timezone.utc))
    if fallback:
        print(f"[nascar.schedule] using fallback schedule, {len(fallback)} upcoming races", flush=True)
    return fallback


def parse_nascar_event(event: dict) -> Optional[dict]:
    """Normalize one ESPN NASCAR event."""
    try:
        status_name = (event.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        name = event.get("name") or event.get("shortName") or "NASCAR Cup Race"
        short_name = event.get("shortName") or name
        date_iso = event.get("date", "")

        comps = event.get("competitions") or []
        venue_obj = (comps[0].get("venue") if comps else {}) or {}
        track = venue_obj.get("fullName") or ""

        return {
            "event_id":   str(event.get("id", "")),
            "name":       name,
            "short_name": short_name,
            "track":      track,
            "green_flag_utc": date_iso,
            "status":     status_name,
            "url":        (event.get("links") or [{}])[0].get("href", ""),
        }
    except Exception as e:
        print(f"[nascar.schedule] parse error: {e}", flush=True)
        return None


def race_slug(name: str) -> str:
    """Slug for URL: 'coca-cola-600', 'daytona-500' style."""
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]+", "", n)
    n = re.sub(r"\s+", "-", n).strip("-")
    return n or "race"
