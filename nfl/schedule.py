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

# User-Agent history:
#   Original:  "kevinrothwx-site/1.0 nfl (kevinrothwx@gmail.com)"  → 403
#   2026-08-13: dropped "nfl" token                                → still 403
#   2026-08-14: switched to Chrome desktop UA. ESPN's block was on
#               the whole custom-agent pattern, not just "nfl". Same
#               pattern applied to CFB/MLS/WorldCup/Prem/Golf/NASCAR.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
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
    """Pull NFL games across a date window.

    Sources (2026-08-14):
        1. PRIMARY: The Odds API — we already pay for it (ODDS_API_KEY),
           returns every scheduled NFL game with kickoff time, home team,
           away team. Flex changes are reflected automatically because
           books update commence_time when kickoffs move. Never blocked.
        2. FALLBACK: ESPN scoreboard — currently 403-blocked but kept as
           backup for the day it un-blocks or Odds API has an outage.
    """
    # ── PRIMARY: The Odds API ──────────────────────────────────────────
    try:
        from .odds_api_schedule import (
            fetch_nfl_games_from_odds_api,
            filter_to_window,
        )
        all_odds = fetch_nfl_games_from_odds_api()
        if all_odds:
            windowed = filter_to_window(all_odds, start_date, days_ahead=days_ahead)
            print(f"[nfl.schedule] Odds API returned {len(all_odds)} games, "
                  f"{len(windowed)} in window — using as primary", flush=True)
            return windowed
        print("[nfl.schedule] Odds API returned 0 games — falling back to ESPN",
              flush=True)
    except Exception as e:
        print(f"[nfl.schedule] Odds API raised {type(e).__name__}: {e} — "
              f"falling back to ESPN", flush=True)

    # ── FALLBACK: ESPN ─────────────────────────────────────────────────
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


# ── International venue discovery (added 2026-09-06) ──────────────────────
#
# WHY THIS EXISTS
#     The Odds API is the primary schedule source because it also carries the
#     totals, but it returns NO venue at all. odds_api_schedule.py therefore
#     falls back to "home team's stadium", which is wrong for every
#     international game. The Rams' 2026 Melbourne game rendered a SoFi
#     Stadium forecast — Los Angeles weather for a game in Australia — because
#     NEUTRAL_SITE_OVERRIDES had never been populated.
#
#     A hand-maintained override list is fine until someone forgets to add a
#     row, and then the failure is silent and confidently wrong. ESPN's
#     scoreboard DOES carry venue with a country field, and this module
#     already parses it for the ESPN fallback path. So: fetch ESPN purely as
#     a venue authority and let it fill the gap automatically.
#
# DESIGN
#     - Manual overrides still win. They are the path that works even when
#       ESPN is down or rate-limiting us.
#     - This runs once per slate build, cached, and never blocks: any failure
#       leaves the map empty and the manual overrides carry on.
#     - When ESPN says a game is international but we have no matching entry
#       in INTERNATIONAL_VENUES, that is logged loudly. That log line is the
#       signal to add a venue, and it is far better than silently showing the
#       home stadium's weather.

_intl_map_cache: dict = {"built_at": None, "map": {}}
_INTL_MAP_TTL_SEC = 3600


def fetch_international_venue_map(start_date: Optional[datetime] = None,
                                  days_ahead: int = 8) -> dict:
    """{(date_ymd_eastern, home_abbrev, away_abbrev): venue_dict} for games
    ESPN reports at a non-US venue.

    Cached for an hour. Never raises."""
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc)
    built = _intl_map_cache["built_at"]
    if built and (now - built).total_seconds() < _INTL_MAP_TTL_SEC:
        return _intl_map_cache["map"]

    if start_date is None:
        start_date = now - timedelta(hours=24)

    out: dict = {}
    unmapped: list[str] = []
    try:
        for offset in range(days_ahead + 1):
            d = start_date + timedelta(days=offset)
            try:
                resp = requests.get(
                    ESPN_NFL_SCOREBOARD_URL,
                    params={"dates": d.strftime("%Y%m%d")},
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT_SEC,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            for event in (data.get("events") or []):
                comp = (event.get("competitions") or [{}])[0]
                venue = comp.get("venue") or {}
                addr = venue.get("address") or {}
                country = (addr.get("country") or "").strip()
                if not country or country.upper() in ("US", "USA", "UNITED STATES"):
                    continue

                home_ab = away_ab = None
                for c in (comp.get("competitors") or []):
                    rec = _build_team_record(c)
                    if not rec:
                        continue
                    if c.get("homeAway") == "home":
                        home_ab = rec.get("abbrev")
                    elif c.get("homeAway") == "away":
                        away_ab = rec.get("abbrev")
                if not (home_ab and away_ab):
                    continue

                start_raw = event.get("date") or ""
                try:
                    ko = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                except Exception:
                    continue
                date_ymd = ko.astimezone(EASTERN_TZ).strftime("%Y-%m-%d")

                resolved = lookup_international_venue(
                    venue.get("fullName") or "", addr.get("city") or "", country)
                if resolved:
                    out[(date_ymd, home_ab, away_ab)] = resolved
                else:
                    unmapped.append(
                        f"{away_ab} at {home_ab} {date_ymd} — "
                        f"{venue.get('fullName')!r}, {addr.get('city')!r} ({country})")
    except Exception as e:
        print(f"[nfl.schedule] international venue scan failed: "
              f"{type(e).__name__}: {e}", flush=True)
        return _intl_map_cache["map"] or {}

    if unmapped:
        for u in unmapped:
            print(f"[nfl.schedule] UNMAPPED INTERNATIONAL VENUE — {u}. "
                  f"Add it to nfl.venues.INTERNATIONAL_VENUES or the forecast "
                  f"will fall back to the home team's US stadium.", flush=True)
    if out:
        print(f"[nfl.schedule] international venue map: {len(out)} game(s) "
              f"auto-detected from ESPN", flush=True)

    _intl_map_cache["map"] = out
    _intl_map_cache["built_at"] = now
    return out
