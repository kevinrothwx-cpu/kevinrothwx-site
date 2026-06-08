"""
worldcup.schedule — ESPN's unofficial scoreboard API for the 2026 World Cup.

Endpoint pattern (no auth required):
    https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=YYYYMMDD

Returns a list of events (matches) with:
    - id, name, date (ISO UTC)
    - competitions[0].venue.fullName
    - competitions[0].competitors (home/away with team metadata, logos)
    - status (scheduled/in-progress/final/postponed)

If ESPN returns no events (preseason window, rate limit, API change), we
fall back to a minimal hand-curated schedule so the page is never empty.
"""

from __future__ import annotations

import requests
from datetime import datetime
from typing import Optional


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept": "application/json",
}


def get_worldcup_schedule(date_str: str) -> list[dict]:
    """
    Fetch World Cup matches for a date (YYYY-MM-DD).
    Returns a list of raw event dicts from ESPN.
    """
    date_compact = date_str.replace("-", "")  # ESPN wants YYYYMMDD
    try:
        resp = requests.get(
            ESPN_SCOREBOARD_URL,
            params={"dates": date_compact, "limit": 50},
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as e:
        print(f"[worldcup.schedule] ESPN error for {date_str}: {e}", flush=True)
        return []


def parse_worldcup_event(event: dict) -> Optional[dict]:
    """
    Normalize one ESPN event into our internal shape. Returns None if event
    is missing critical fields or has been cancelled.
    """
    try:
        competition = (event.get("competitions") or [{}])[0]
        if not competition:
            return None

        status_name = (competition.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        # Teams — find home + away
        home = away = None
        for c in competition.get("competitors", []):
            team = c.get("team", {}) or {}
            entry = {
                "name":         team.get("displayName", team.get("name", "")),
                "short_name":   team.get("shortDisplayName", team.get("abbreviation", "")),
                "abbreviation": team.get("abbreviation", ""),
                "logo":         team.get("logo", ""),  # often a remote URL
                "team_id":      team.get("id", ""),
                "score":        c.get("score", ""),
            }
            if c.get("homeAway") == "home":
                home = entry
            else:
                away = entry

        if not home or not away:
            return None

        venue = (competition.get("venue") or {}).get("fullName", "")
        date_iso = event.get("date", "")
        if not date_iso:
            return None

        return {
            "event_id":   str(event.get("id", "")),
            "name":       event.get("name", f"{away['name']} vs {home['name']}"),
            "venue":      venue,
            "kickoff_utc": date_iso,
            "home":       home,
            "away":       away,
            "status":     status_name,
            "round":      event.get("season", {}).get("type", ""),
        }
    except Exception as e:
        print(f"[worldcup.schedule] parse error: {e}", flush=True)
        return None


def match_slug(away_name: str, home_name: str) -> str:
    """Slug for URL: 'mexico-vs-cameroon' style."""
    import re
    def clean(n: str) -> str:
        n = n.lower()
        n = re.sub(r"[^a-z0-9 ]+", "", n)
        return re.sub(r"\s+", "-", n).strip("-") or "team"
    return f"{clean(away_name)}-vs-{clean(home_name)}"
