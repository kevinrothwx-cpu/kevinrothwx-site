"""
nascar.schedule — ESPN unofficial NASCAR Cup Series scoreboard.

Endpoint:
    https://site.api.espn.com/apis/site/v2/sports/racing/nascar-cup-series/scoreboard
"""

from __future__ import annotations

import requests
import re
from typing import Optional


ESPN_NASCAR_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-cup-series/scoreboard"
REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/json",
}


def get_nascar_scoreboard() -> list[dict]:
    """Fetch current/upcoming NASCAR Cup races."""
    try:
        resp = requests.get(
            ESPN_NASCAR_SCOREBOARD_URL,
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[nascar.schedule] ESPN error: {e}", flush=True)
        return []


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
