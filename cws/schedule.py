"""
cws.schedule — pull college baseball games for a date and filter to the
ones held at Charles Schwab Field (Omaha). ESPN's college baseball
scoreboard handles the bracket as the tournament progresses.
"""

from __future__ import annotations

import re
import requests
from typing import Optional

from .venue import CHARLES_SCHWAB_FIELD


ESPN_CBASE_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard"
REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/json",
}


def get_cws_schedule(date_str: str) -> list[dict]:
    """Fetch college baseball games for a date, filter to Omaha."""
    date_compact = date_str.replace("-", "")
    try:
        resp = requests.get(
            ESPN_CBASE_SCOREBOARD_URL,
            params={"dates": date_compact, "limit": 100},
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json().get("events", [])
        # Filter to events at Charles Schwab Field / Omaha
        aliases = [CHARLES_SCHWAB_FIELD["name"].lower()] + [a.lower() for a in CHARLES_SCHWAB_FIELD["aliases"]]
        omaha_events = []
        for e in events:
            comp = (e.get("competitions") or [{}])[0]
            venue = (comp.get("venue") or {}).get("fullName", "").lower()
            if any(a in venue or venue in a for a in aliases):
                omaha_events.append(e)
        return omaha_events
    except Exception as e:
        print(f"[cws.schedule] ESPN error for {date_str}: {e}", flush=True)
        return []


def parse_cws_event(event: dict) -> Optional[dict]:
    """Normalize ESPN college baseball event."""
    try:
        comp = (event.get("competitions") or [{}])[0]
        status_name = (comp.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        home = away = None
        for c in comp.get("competitors", []):
            team = c.get("team", {}) or {}
            entry = {
                "name":         team.get("displayName", team.get("name", "")),
                "short_name":   team.get("shortDisplayName", team.get("name", "")),
                "abbreviation": team.get("abbreviation", ""),
                "logo":         team.get("logo", ""),
                "team_id":      team.get("id", ""),
                "score":        c.get("score", ""),
                "rank":         (team.get("rank") or {}).get("current") if isinstance(team.get("rank"), dict) else None,
            }
            if c.get("homeAway") == "home":
                home = entry
            else:
                away = entry

        if not home or not away:
            return None

        return {
            "event_id":   str(event.get("id", "")),
            "name":       event.get("name", f"{away['name']} vs {home['name']}"),
            "first_pitch_utc": event.get("date", ""),
            "home":       home,
            "away":       away,
            "status":     status_name,
            "round":      event.get("notes", [{}])[0].get("headline", "") if event.get("notes") else "",
        }
    except Exception as e:
        print(f"[cws.schedule] parse error: {e}", flush=True)
        return None


def game_slug(away_name: str, home_name: str) -> str:
    def clean(n):
        n = n.lower()
        n = re.sub(r"[^a-z0-9 ]+", "", n)
        return re.sub(r"\s+", "-", n).strip("-") or "team"
    return f"{clean(away_name)}-vs-{clean(home_name)}"
