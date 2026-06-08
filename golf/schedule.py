"""
golf.schedule — ESPN's unofficial PGA Tour scoreboard.

Endpoint:
    https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard

Returns one or more active/upcoming tournaments with:
    - name, short name
    - course, location
    - start/end dates
    - status (scheduled, in-progress, final)

Free, no key, used by ESPN's apps. Same pattern as MLB Stats / soccer.
"""

from __future__ import annotations

import requests
import re
from datetime import datetime
from typing import Optional


ESPN_PGA_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/json",
}


def get_pga_scoreboard() -> list[dict]:
    """Fetch the current PGA scoreboard. Returns raw event dicts."""
    try:
        resp = requests.get(
            ESPN_PGA_SCOREBOARD_URL,
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[golf.schedule] ESPN error: {e}", flush=True)
        return []


def parse_pga_event(event: dict) -> Optional[dict]:
    """
    Normalize an ESPN PGA event. Returns None if cancelled or missing fields.
    """
    try:
        status_name = (event.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        name      = event.get("name") or event.get("shortName") or "PGA Tournament"
        short_name = event.get("shortName") or name
        start_iso = event.get("date") or ""
        end_date  = event.get("endDate") or ""

        # Course / venue — ESPN nests this in competitions[0].venue
        comps = event.get("competitions") or []
        venue_obj = (comps[0].get("venue") if comps else {}) or {}
        course = venue_obj.get("fullName") or ""
        address = venue_obj.get("address") or {}
        city = (address.get("city") or "").strip()
        state = (address.get("state") or "").strip()
        location = ", ".join([p for p in [city, state] if p])

        if not start_iso:
            return None

        return {
            "event_id":   str(event.get("id", "")),
            "name":       name,
            "short_name": short_name,
            "course":     course,
            "location":   location,
            "start_iso":  start_iso,
            "end_iso":    end_date,
            "status":     status_name,
            "url":        (event.get("links") or [{}])[0].get("href", ""),
        }
    except Exception as e:
        print(f"[golf.schedule] parse error: {e}", flush=True)
        return None


def tournament_slug(name: str) -> str:
    """Slug for URL: 'us-open', 'memorial-tournament' style."""
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]+", "", n)
    n = re.sub(r"\s+", "-", n).strip("-")
    return n or "tournament"
