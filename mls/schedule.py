"""mls.schedule — ESPN MLS scoreboard fetcher + normalizer.

ESPN MLS scoreboard:
    https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard?dates=YYYYMMDD

Each event is a match. Competitors[] has the two clubs. ESPN provides
kickoff time, venue, status, and team IDs (mapped to mls.venues).

Returns normalized match dicts:
    {
        "event_id": str, "slug": str,
        "home": {"team_id", "name", "short", "abbrev", "logo_url"},
        "away": {...},
        "venue": {...},  # from mls.venues.get_stadium(home_team_id)
        "kickoff_utc": datetime,
        "kickoff_eastern_str": str,
        "status": str,
        "date_local": str (YYYY-MM-DD in venue local time),
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from .venues import MLS_TEAMS, get_team, get_stadium

log = logging.getLogger(__name__)


ESPN_MLS_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard"
)

REQUEST_HEADERS = {
    # Chrome desktop UA — see nfl/schedule.py for the 2026-08-14 UA-switch context
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT_SEC = 15

EASTERN_TZ = ZoneInfo("America/New_York")


def get_mls_week_games(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """Pull MLS matches across a date window. Fetches each day separately
    (ESPN's MLS endpoint returns matches for a single date)."""
    out: list[dict] = []
    seen_event_ids: set[str] = set()

    for offset in range(days_ahead + 1):
        d = (start_date + timedelta(days=offset))
        date_str = d.strftime("%Y%m%d")
        try:
            resp = requests.get(
                ESPN_MLS_SCOREBOARD_URL,
                params={"dates": date_str},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                log.warning(f"[mls.schedule] ESPN returned {resp.status_code} for {date_str}")
                continue
            data = resp.json()
        except Exception as e:
            log.warning(f"[mls.schedule] ESPN fetch failed for {date_str}: {e}")
            continue

        for event in (data.get("events") or []):
            eid = str(event.get("id") or "")
            if not eid or eid in seen_event_ids:
                continue
            parsed = parse_mls_event(event)
            if parsed:
                seen_event_ids.add(eid)
                out.append(parsed)

    out.sort(key=lambda g: g.get("kickoff_utc") or datetime.max.replace(tzinfo=timezone.utc))
    log.info(f"[mls.schedule] window {start_date.date()} +{days_ahead}d: {len(out)} matches")
    return out


def parse_mls_event(event: dict) -> Optional[dict]:
    """Convert one ESPN event into our normalized match shape.
    Returns None if the event lacks the data we need (venue, kickoff, teams)."""
    eid = str(event.get("id") or "")
    if not eid:
        return None

    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    home = away = None
    for c in competitors:
        team_record = _build_team_record(c)
        if not team_record:
            continue
        if c.get("homeAway") == "home":
            home = team_record
        elif c.get("homeAway") == "away":
            away = team_record
    if not home or not away:
        return None

    # Venue from home team's stadium (MLS uses home-team venues — no
    # neutral-site regular season matches outside MLS Cup final)
    venue = get_stadium(home["team_id"])
    if not venue:
        # Unknown home team — skip rather than render with missing venue
        log.warning(f"[mls.schedule] no venue for home team_id={home['team_id']} ({home['name']})")
        return None

    # Kickoff time
    kickoff_iso = comp.get("date") or event.get("date") or ""
    try:
        kickoff_utc = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None

    # Date in venue's local timezone (used for /mls/<date>/<slug> URLs)
    tz = ZoneInfo(venue["timezone"])
    kickoff_local = kickoff_utc.astimezone(tz)
    kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)

    status_state = ((event.get("status") or {}).get("type") or {}).get("state") or ""

    return {
        "id":              eid,
        "event_id":        eid,
        "home":            home,
        "away":            away,
        "venue":           venue,
        "kickoff_utc":     kickoff_utc,
        "kickoff_local":   kickoff_local,
        "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
        "date_local":      kickoff_local.strftime("%Y-%m-%d"),
        "status":          status_state,
        "slug":            _make_slug(away["abbrev"], home["abbrev"]),
    }


def _build_team_record(competitor: dict) -> Optional[dict]:
    """Extract team info from an ESPN competitor entry."""
    team_block = competitor.get("team") or {}
    try:
        team_id = int(team_block.get("id") or 0)
    except (ValueError, TypeError):
        team_id = 0
    if not team_id:
        return None

    local = MLS_TEAMS.get(team_id)
    if local:
        return {
            "team_id":  team_id,
            "name":     local["name"],
            "short":    local["short"],
            "abbrev":   local["abbrev"],
            "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
        }
    # Unknown team — synthesize from ESPN payload (rare for MLS, but defensive)
    return {
        "team_id":  team_id,
        "name":     team_block.get("displayName") or team_block.get("name") or f"Team {team_id}",
        "short":    team_block.get("shortDisplayName") or team_block.get("abbreviation") or "?",
        "abbrev":   team_block.get("abbreviation") or "?",
        "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
    }


def _make_slug(away_abbrev: str, home_abbrev: str) -> str:
    """URL slug: 'rbny-at-phi' style. Lowercase, short."""
    a = (away_abbrev or "tbd").lower().replace(".", "")
    h = (home_abbrev or "tbd").lower().replace(".", "")
    return f"{a}-at-{h}"
