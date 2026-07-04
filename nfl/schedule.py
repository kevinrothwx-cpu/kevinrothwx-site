"""nfl.schedule — ESPN NFL scoreboard fetcher + normalizer.

ESPN NFL scoreboard:
    https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=YYYYMMDD

Per Kevin's call: include preseason + regular + playoffs. ESPN tags
season type via season.type: 1=preseason, 2=regular, 3=postseason, 4=Pro Bowl.
We filter OUT type 4 (Pro Bowl) but accept 1/2/3.

Returns normalized game dicts sorted by kickoff time:
    {
        "id", "event_id",
        "home": {team_id, name, short, abbrev, logo_url, color},
        "away": {...},
        "venue": stadium dict from nfl.venues.get_stadium(home_team_id),
        "kickoff_utc": datetime,
        "kickoff_eastern_str": str,
        "kickoff_eastern": datetime (Eastern),
        "kickoff_date_eastern": YYYY-MM-DD str (Eastern),
        "date_local": YYYY-MM-DD (venue local),
        "season_type": int (1/2/3),
        "season_type_label": "Preseason" | "Regular Season" | "Postseason",
        "week": int or None,
        "status": str,
        "slug": str (away_abbrev-at-home_abbrev),
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from .venues import NFL_TEAMS, get_team, get_stadium, lookup_international_venue

log = logging.getLogger(__name__)


ESPN_NFL_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
)

REQUEST_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 nfl (kevinrothwx@gmail.com)",
}
REQUEST_TIMEOUT_SEC = 15

EASTERN_TZ = ZoneInfo("America/New_York")


_SEASON_TYPE_LABELS = {
    1: "Preseason",
    2: "Regular Season",
    3: "Postseason",
    4: "Pro Bowl",  # filtered out
}


def get_nfl_week_games(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """Pull NFL games across a date window. ESPN's NFL scoreboard returns
    one week of games when no date is passed, or a specific date when
    `dates=YYYYMMDD` is set. We walk each day individually to cover
    Sunday + Monday + Thursday + Saturday spread."""
    out: list[dict] = []
    seen_event_ids: set[str] = set()

    for offset in range(days_ahead + 1):
        d = start_date + timedelta(days=offset)
        date_str = d.strftime("%Y%m%d")
        try:
            resp = requests.get(
                ESPN_NFL_SCOREBOARD_URL,
                params={"dates": date_str},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            if resp.status_code != 200:
                log.warning(f"[nfl.schedule] ESPN returned {resp.status_code} for {date_str}")
                continue
            data = resp.json()
        except Exception as e:
            log.warning(f"[nfl.schedule] ESPN fetch failed for {date_str}: {e}")
            continue

        season_block = data.get("season") or {}
        season_type = ((data.get("season") or {}).get("type")
                       or ((data.get("leagues") or [{}])[0].get("season") or {}).get("type")
                       or 0)
        week = ((data.get("week") or {}).get("number")) or None

        for event in (data.get("events") or []):
            eid = str(event.get("id") or "")
            if not eid or eid in seen_event_ids:
                continue
            # Per-event season type lives under event.season.type, more reliable
            ev_season_type = ((event.get("season") or {}).get("type")) or season_type or 2
            if ev_season_type == 4:
                # Skip Pro Bowl
                continue
            parsed = parse_nfl_event(event, season_type=ev_season_type, week=week)
            if parsed:
                seen_event_ids.add(eid)
                out.append(parsed)

    out.sort(key=lambda g: g.get("kickoff_utc") or datetime.max.replace(tzinfo=timezone.utc))
    log.info(f"[nfl.schedule] window {start_date.date()} +{days_ahead}d: {len(out)} games")
    return out


def parse_nfl_event(event: dict, season_type: int = 2, week: Optional[int] = None) -> Optional[dict]:
    """Convert one ESPN event into our normalized game shape.

    International games (London, Munich, Madrid, Mexico City, etc.) get
    their venue overridden with an entry from INTERNATIONAL_VENUES
    (flagged nws_unsupported so the slate builder routes them through
    WeatherAPI instead of NWS). If ESPN reports a non-US country but
    we can't match the venue, we skip the game rather than fall through
    to the home team's US stadium.
    """
    eid = str(event.get("id") or "")
    if not eid:
        return None

    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    # International-game handling: override the venue with an entry from
    # our international directory. If country is non-US but we can't
    # match a known site, skip (better than showing US-stadium weather).
    espn_venue = comp.get("venue") or {}
    espn_venue_addr = espn_venue.get("address") or {}
    espn_country = (espn_venue_addr.get("country") or "").strip()
    espn_fullname = espn_venue.get("fullName") or ""
    espn_city = espn_venue_addr.get("city") or ""
    international_venue = None
    if espn_country and espn_country.upper() not in ("US", "USA", "UNITED STATES"):
        international_venue = lookup_international_venue(
            espn_fullname, espn_city, espn_country
        )
        if not international_venue:
            log.info(
                f"[nfl.schedule] skipping unmapped international game {eid} at "
                f"{espn_fullname!r} in {espn_city!r} ({espn_country}) — "
                f"add to nfl.venues.INTERNATIONAL_VENUES to enable forecast"
            )
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

    # International override — the ESPN-reported non-US venue wins.
    # Otherwise we use the home team's normal US stadium.
    if international_venue:
        venue = international_venue
    else:
        venue = get_stadium(home["team_id"])
    if not venue:
        log.warning(f"[nfl.schedule] no venue for team_id={home['team_id']} ({home['name']})")
        return None

    kickoff_iso = comp.get("date") or event.get("date") or ""
    try:
        kickoff_utc = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None

    tz = ZoneInfo(venue["timezone"])
    kickoff_local = kickoff_utc.astimezone(tz)
    kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)

    status_state = ((event.get("status") or {}).get("type") or {}).get("state") or ""

    return {
        "id":                eid,
        "event_id":          eid,
        "home":              home,
        "away":              away,
        "venue":             venue,
        "kickoff_utc":       kickoff_utc,
        "kickoff_local":     kickoff_local,
        "kickoff_eastern":   kickoff_eastern,
        "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
        "kickoff_date_eastern": kickoff_eastern.strftime("%Y-%m-%d"),
        "date_local":        kickoff_local.strftime("%Y-%m-%d"),
        "season_type":       season_type,
        "season_type_label": _SEASON_TYPE_LABELS.get(season_type, ""),
        "week":              week,
        "status":            status_state,
        "slug":              _make_slug(away["abbrev"], home["abbrev"]),
    }


def _build_team_record(competitor: dict) -> Optional[dict]:
    team_block = competitor.get("team") or {}
    try:
        team_id = int(team_block.get("id") or 0)
    except (ValueError, TypeError):
        team_id = 0
    if not team_id:
        return None
    local = NFL_TEAMS.get(team_id)
    if local:
        return {
            "team_id": team_id,
            "name":    local["name"],
            "short":   local["short"],
            "abbrev":  local["abbrev"],
            "conf":    local["conf"],
            "div":     local["div"],
            "color":   local["color"],
            "logo_url": team_block.get("logo") or "",
        }
    # Fallback if ESPN reports a team ID we don't recognize (rare)
    disp = team_block.get("displayName") or team_block.get("name") or f"Team {team_id}"
    abbr = team_block.get("abbreviation") or team_block.get("shortDisplayName") or "?"
    return {
        "team_id": team_id,
        "name":    disp,
        "short":   team_block.get("shortDisplayName") or disp,
        "abbrev":  abbr,
        "conf":    "",
        "div":     "",
        "color":   "#666666",
        "logo_url": team_block.get("logo") or "",
    }


def _make_slug(away_abbrev: str, home_abbrev: str) -> str:
    aw = (away_abbrev or "??").lower()
    hm = (home_abbrev or "??").lower()
    return f"{aw}-at-{hm}"


# EOF-CANARY 2026-07-04-cfb-recovery
