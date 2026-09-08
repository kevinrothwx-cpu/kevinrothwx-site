"""prem.schedule — Premier League fixtures.

PRIMARY SOURCE: The Odds API, via prem/odds_api_schedule.py.

    ESPN's eng.1 scoreboard 403-blocks our Render IP. It hit NFL on
    2026-08-14 and MLS on 2026-08-24; both were migrated to The Odds API
    then. prem/ was missed, so from that point /prem rendered "No Premier
    League matches scheduled in the next 7 days" on every request while
    ESPN returned fixtures normally to any other network. Found and fixed
    2026-09-08 while building ucl/.

    The ESPN parser below is kept for reference, exactly as mls/schedule.py
    keeps its own. It is NOT called by production code. Do not restore it
    as a fallback: a fallback that always 403s just hides the real failure
    behind a second empty result.

Original ESPN notes follow.

ESPN EPL scoreboard endpoint:
    https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates=YYYYMMDD

Same pattern as mls/schedule.py, adapted for EPL. All venues are in
England, so kickoff_local is always Europe/London time.

Returns normalized match dicts:
    {
        "id", "event_id",
        "home": {team_id, name, short, abbrev, color, logo_url},
        "away": {...},
        "venue": stadium dict from prem.venues.get_stadium(home_team_id),
        "kickoff_utc": datetime,
        "kickoff_local": datetime (Europe/London),
        "kickoff_local_str": str (e.g. "3:00 PM BST"),
        "kickoff_eastern_str": str (e.g. "10:00 AM ET"),
        "date_local": YYYY-MM-DD (Europe/London),
        "status": str,
        "slug": str (home-vs-away),
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from .venues import EPL_TEAMS, get_team, get_stadium

log = logging.getLogger(__name__)

ESPN_EPL_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
)

REQUEST_HEADERS = {
    # Chrome desktop UA — see nfl/schedule.py for the 2026-08-14 UA-switch context
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT_SEC = 15

UK_TZ = ZoneInfo("Europe/London")
EASTERN_TZ = ZoneInfo("America/New_York")


def get_epl_week_matches(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """EPL fixtures kicking off within the window. Empty list on failure.

    Delegates to The Odds API. See the module docstring for why ESPN is no
    longer used."""
    from .odds_api_schedule import (
        fetch_epl_matches_from_odds_api,
        filter_to_window,
    )
    all_matches = fetch_epl_matches_from_odds_api()
    if not all_matches:
        print("[prem.schedule] no fixtures returned from Odds API", flush=True)
        return []
    windowed = filter_to_window(all_matches, start_date, days_ahead=days_ahead)
    print(f"[prem.schedule] {len(all_matches)} fixtures upcoming, "
          f"{len(windowed)} in {days_ahead}d window", flush=True)
    return windowed


def _get_epl_week_matches_espn(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """LEGACY ESPN path — kept for reference. Not called by production code.

    ESPN's soccer/eng.1/scoreboard endpoint 403s from Render."""
    out: list[dict] = []
    seen: set[str] = set()

    for offset in range(days_ahead + 1):
        d = start_date + timedelta(days=offset)
        date_str = d.strftime("%Y%m%d")
        try:
            resp = requests.get(
                ESPN_EPL_URL,
                params={"dates": date_str},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                log.warning(f"[prem.schedule] ESPN returned {resp.status_code} for {date_str}")
                continue
            data = resp.json()
        except Exception as e:
            log.warning(f"[prem.schedule] ESPN fetch failed for {date_str}: {e}")
            continue

        for event in (data.get("events") or []):
            eid = str(event.get("id") or "")
            if not eid or eid in seen:
                continue
            parsed = parse_epl_event(event)
            if parsed:
                seen.add(eid)
                out.append(parsed)

    out.sort(key=lambda m: m.get("kickoff_utc") or datetime.max.replace(tzinfo=timezone.utc))
    return out


def parse_epl_event(event: dict) -> Optional[dict]:
    """Convert one ESPN event into our normalized match shape."""
    eid = str(event.get("id") or "")
    if not eid:
        return None

    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    home = away = None
    for c in competitors:
        rec = _build_team_record(c)
        if not rec:
            continue
        if c.get("homeAway") == "home":
            home = rec
        elif c.get("homeAway") == "away":
            away = rec
    if not home or not away:
        return None

    # Venue = home team's stadium (Premier League doesn't do neutral-site
    # regular season games; we can revisit for the occasional US pre-season).
    venue = get_stadium(home["team_id"])
    if not venue:
        log.info(f"[prem.schedule] no venue for home team_id={home['team_id']} — skipping event {eid}")
        return None

    kickoff_iso = comp.get("date") or event.get("date") or ""
    try:
        kickoff_utc = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None

    kickoff_local = kickoff_utc.astimezone(UK_TZ)
    kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)

    # Format helpers — %Z gives "BST" / "GMT" per season, "ET" is hardcoded.
    kickoff_local_str = kickoff_local.strftime("%-I:%M %p %Z").lstrip("0")
    kickoff_eastern_str = kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0")

    status = ((event.get("status") or {}).get("type") or {}).get("state") or ""

    return {
        "id":                    eid,
        "event_id":              eid,
        "home":                  home,
        "away":                  away,
        "venue":                 venue,
        "kickoff_utc":           kickoff_utc,
        "kickoff_local":         kickoff_local,
        "kickoff_eastern":       kickoff_eastern,
        "kickoff_local_str":     kickoff_local_str,
        "kickoff_eastern_str":   kickoff_eastern_str,
        "date_local":            kickoff_local.strftime("%Y-%m-%d"),
        "date_local_pretty":     kickoff_local.strftime("%A, %B %-d"),
        "status":                status,
        "slug":                  _slug(home["abbrev"], away["abbrev"]),
    }


def _build_team_record(competitor: dict) -> Optional[dict]:
    team_block = competitor.get("team") or {}
    try:
        team_id = int(team_block.get("id") or 0)
    except (ValueError, TypeError):
        team_id = 0
    if not team_id:
        return None

    local = EPL_TEAMS.get(team_id)
    if local:
        return {
            "team_id": team_id,
            "name":    local["name"],
            "short":   local["short"],
            "abbrev":  local["abbrev"],
            "color":   local["color"],
            "logo_url": team_block.get("logo") or "",
        }
    # Fallback: ESPN team id not in our list (Champions League intruder,
    # exhibition, or a team we haven't mapped). Return a stub so the match
    # still parses but the venue lookup will fail upstream and drop it.
    disp = team_block.get("displayName") or team_block.get("name") or f"Team {team_id}"
    return {
        "team_id": team_id,
        "name":    disp,
        "short":   team_block.get("shortDisplayName") or disp,
        "abbrev":  team_block.get("abbreviation") or "?",
        "color":   "#666666",
        "logo_url": team_block.get("logo") or "",
    }


def _slug(home_abbrev: str, away_abbrev: str) -> str:
    """URL slug: home-vs-away (Premier League convention: home team first)."""
    h = (home_abbrev or "??").lower()
    a = (away_abbrev or "??").lower()
    return f"{h}-vs-{a}"


# EOF-CANARY 2026-07-06-prem-build
