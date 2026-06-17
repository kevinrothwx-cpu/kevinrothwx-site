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


def _names_from_event_name(name: str) -> tuple[str, str]:
    """Parse ESPN's event.name field which uses 'Away at Home' format.

    Examples:
      'Oklahoma Sooners at Georgia Bulldogs' -> ('Oklahoma Sooners', 'Georgia Bulldogs')
      'North Carolina Tar Heels at West Virginia Mountaineers' -> ('North Carolina Tar Heels', 'West Virginia Mountaineers')

    This is the most reliable source of the matchup. ESPN's per-competitor
    displayName field sometimes lags behind and returns 'TBD' even after
    the bracket resolves; the event.name field updates first.
    """
    if not name or " at " not in name:
        return ("", "")
    parts = name.split(" at ", 1)
    if len(parts) != 2:
        return ("", "")
    return (parts[0].strip(), parts[1].strip())


def parse_cws_event(event: dict) -> Optional[dict]:
    """Normalize ESPN college baseball event.

    The matchup names come from event.name ('Away at Home' format) as the
    primary source — ESPN's competitor.displayName sometimes returns 'TBD'
    for bracket games even after the matchup is resolved, but event.name
    updates first. We still use competitor data for logos, ranks, IDs,
    abbreviations — anything other than the display name.
    """
    try:
        comp = (event.get("competitions") or [{}])[0]
        status_name = (comp.get("status") or {}).get("type", {}).get("name", "")
        if "CANCELED" in status_name.upper() or "CANCELLED" in status_name.upper():
            return None

        event_name = event.get("name", "")
        away_name_from_event, home_name_from_event = _names_from_event_name(event_name)

        home = away = None
        for c in comp.get("competitors", []):
            team = c.get("team", {}) or {}
            display_name = team.get("displayName") or team.get("name") or ""
            short_name = team.get("shortDisplayName") or team.get("name") or ""
            entry = {
                "name":         display_name,
                "short_name":   short_name,
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

        # If competitors are missing or have TBD names, fall back to event.name parsing.
        # This handles the bracket-pending → resolved transition where ESPN updates
        # event.name first and the competitor displayNames lag.
        def _is_tbd(n: str) -> bool:
            return not n or n.strip().upper() in ("TBD", "TBA", "")

        if home is None and home_name_from_event:
            home = {"name": home_name_from_event, "short_name": home_name_from_event,
                    "abbreviation": "", "logo": "", "team_id": "", "score": "", "rank": None}
        if away is None and away_name_from_event:
            away = {"name": away_name_from_event, "short_name": away_name_from_event,
                    "abbreviation": "", "logo": "", "team_id": "", "score": "", "rank": None}

        # Override TBD display names with event.name parsed values (keeps logos etc.)
        if home and _is_tbd(home.get("name")) and home_name_from_event:
            home["name"] = home_name_from_event
            if _is_tbd(home.get("short_name")):
                home["short_name"] = home_name_from_event
        if away and _is_tbd(away.get("name")) and away_name_from_event:
            away["name"] = away_name_from_event
            if _is_tbd(away.get("short_name")):
                away["short_name"] = away_name_from_event

        if not home or not away:
            return None

        # Final TBD check — if AFTER all fallbacks both are still TBD, the matchup
        # truly isn't set yet on ESPN's side. Render the game anyway with TBD so
        # the time/venue slot is visible; consumers will see it update later.
        return {
            "event_id":   str(event.get("id", "")),
            "name":       event_name or f"{away['name']} vs {home['name']}",
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
