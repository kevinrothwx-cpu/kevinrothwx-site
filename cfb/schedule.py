"""
cfb.schedule — ESPN college football scoreboard fetcher.

Endpoint:
    https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard

Free, no key, ESPN's primary college football data feed (powers their apps).
CFB scoreboard is reliable enough that we do NOT need a hand-curated fallback
like we do for PGA — CFB is ESPN's flagship sport and the endpoint is heavily
maintained.

This module fetches raw events for a date window, normalizes each game to
our internal shape (matching cfb.venues team lookups), and returns a clean
list of game dicts ready for slate.py to attach weather to.

Key normalization decisions:
- Slug format: "<away-abbrev>-<home-abbrev>" lowercased, e.g. "bama-aub"
- Rankings: AP Top 25 from ESPN's curatedRank field
- Neutral sites: ESPN's neutralSite flag is the source of truth
- Venue: home team's stadium from cfb/venues.py FBS_TEAMS dict, unless
  neutral, in which case we use ESPN's venue payload
- Unknown teams (not yet in FBS_TEAMS, i.e. G5 teams pending population):
  the game is STILL included but with a degraded team record — the slate
  will fall back to ESPN's venue data for weather lookup
"""

from __future__ import annotations

import requests
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .venues import FBS_TEAMS


ESPN_CFB_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/"
    "college-football/scoreboard"
)
REQUEST_HEADERS = {
    # Switched from custom "kevinrothwx-site/1.0 ..." UA to Chrome desktop
    # on 2026-08-14 after ESPN started 403-ing every scoreboard request.
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
EASTERN_TZ = ZoneInfo("America/New_York")

# ESPN group code 80 = FBS (filters out FCS and Division II/III noise).
# Without this filter the scoreboard can include 100+ FCS games per Saturday
# which we don't cover.
FBS_GROUP_ID = "80"


# ── Public API ────────────────────────────────────────────────────────────

def get_cfb_scoreboard(date_str: Optional[str] = None) -> list[dict]:
    """Fetch ESPN's FBS scoreboard for a specific date.

    Args:
        date_str: "YYYYMMDD" format (e.g. "20260905"). If None, fetches
                  today's games using ESPN's default date logic.

    Returns:
        List of raw event dicts. Empty list on failure (never raises).
    """
    params = {"groups": FBS_GROUP_ID, "limit": 300}
    if date_str:
        params["dates"] = date_str
    try:
        resp = requests.get(
            ESPN_CFB_SCOREBOARD_URL,
            headers=REQUEST_HEADERS,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json().get("events", []) or []
        return events
    except Exception as e:
        print(f"[cfb.schedule] ESPN fetch failed for date {date_str!r}: {e}", flush=True)
        return []


def get_cfb_week_games(start_date: datetime, days_ahead: int = 7) -> list[dict]:
    """Fetch and normalize games for a window starting from start_date.

    Args:
        start_date: First day of the window (datetime; date portion used).
        days_ahead: How many days forward to fetch. Default 7 covers the
                    typical CFB week (Tue MAC night through Sun ACC game).

    Returns:
        List of normalized game dicts sorted by kickoff time.
        Games that fail to parse are skipped, not raised.
    """
    all_games: list[dict] = []
    for offset in range(days_ahead):
        d = (start_date + timedelta(days=offset)).strftime("%Y%m%d")
        raw_events = get_cfb_scoreboard(date_str=d)
        for event in raw_events:
            game = parse_cfb_event(event)
            if game is not None:
                all_games.append(game)

    # De-dup by event_id since ESPN sometimes returns the same game on
    # consecutive day queries (e.g. a Friday night game might appear in
    # both Thu and Fri queries if it's at a timezone boundary).
    seen_ids = set()
    deduped: list[dict] = []
    for g in all_games:
        if g["event_id"] not in seen_ids:
            seen_ids.add(g["event_id"])
            deduped.append(g)

    deduped.sort(key=lambda g: g["kickoff_utc"])
    print(
        f"[cfb.schedule] window {start_date.date()} +{days_ahead}d: "
        f"{len(deduped)} unique games "
        f"(of {len(all_games)} raw events fetched)",
        flush=True,
    )
    return deduped


# ── Per-event parsing ─────────────────────────────────────────────────────

def parse_cfb_event(event: dict) -> Optional[dict]:
    """Normalize a single ESPN event to our internal game shape.

    Returns None if the event is unparseable (missing required fields, not
    a 2-team competition, etc.). Caller should treat None as "skip silently".
    """
    try:
        event_id = str(event.get("id") or "")
        if not event_id:
            return None

        competitions = event.get("competitions") or []
        if not competitions:
            return None
        comp = competitions[0]

        # Status
        status_block = (comp.get("status") or {}).get("type") or {}
        status_state = (status_block.get("state") or "").lower()
        status_name = (status_block.get("name") or "").upper()
        status_detail = status_block.get("detail") or ""

        if status_state == "post" or "FINAL" in status_name or "POST" in status_name:
            status = "final"
        elif status_state == "in":
            status = "in_progress"
        else:
            status = "scheduled"

        # Kickoff time (UTC, ISO format from ESPN)
        kickoff_str = comp.get("date") or event.get("date") or ""
        try:
            kickoff_utc = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
        kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)
        kickoff_eastern_str = kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0")

        # Competitors (away/home)
        competitors = comp.get("competitors") or []
        if len(competitors) != 2:
            return None
        away_competitor = next((c for c in competitors if c.get("homeAway") == "away"), None)
        home_competitor = next((c for c in competitors if c.get("homeAway") == "home"), None)
        if not away_competitor or not home_competitor:
            return None

        away = _build_team_record(away_competitor)
        home = _build_team_record(home_competitor)
        if away is None or home is None:
            return None

        # Venue (with neutral-site handling)
        is_neutral = bool(comp.get("neutralSite", False))
        venue = _build_venue_record(comp.get("venue") or {}, home, is_neutral)

        # Game characteristics
        is_conference_game = bool(comp.get("conferenceCompetition", False))
        is_top25_matchup = (away["rank"] is not None and home["rank"] is not None
                            and away["rank"] <= 25 and home["rank"] <= 25)

        # Broadcast
        broadcasts = comp.get("broadcasts") or []
        broadcast = ""
        if broadcasts:
            names = broadcasts[0].get("names") or []
            broadcast = ", ".join(names) if names else ""

        # Season info
        season = event.get("season") or {}
        week = (event.get("week") or {}).get("number")

        # URL slug
        slug = _make_slug(away["abbrev"], home["abbrev"], is_neutral)
        date_part = kickoff_eastern.strftime("%Y-%m-%d")
        url_path = f"/ncaaf/{date_part}/{slug}"

        return {
            "event_id":             event_id,
            "espn_url":             f"https://www.espn.com/college-football/game/_/gameId/{event_id}",
            "name":                 event.get("name") or "",
            "short_name":           event.get("shortName") or "",
            "away":                 away,
            "home":                 home,
            "kickoff_utc":          kickoff_utc,
            "kickoff_utc_str":      kickoff_utc.isoformat(),
            "kickoff_eastern":      kickoff_eastern,
            "kickoff_eastern_str":  kickoff_eastern_str,
            "kickoff_date_eastern": date_part,
            "status":               status,
            "status_detail":        status_detail,
            "week":                 week,
            "season_year":          season.get("year"),
            "season_type":          (season.get("slug") or "").replace("regular-season", "regular"),
            "venue":                venue,
            "is_conference_game":   is_conference_game,
            "is_top25_matchup":     is_top25_matchup,
            "broadcast":            broadcast,
            "slug":                 slug,
            "url_path":             url_path,
        }
    except Exception as e:
        # Defensive: never let one bad event break the whole slate build.
        print(f"[cfb.schedule] parse error on event {event.get('id', '?')}: {e}", flush=True)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_team_record(competitor: dict) -> Optional[dict]:
    """Build our internal team record from an ESPN competitor block.

    Looks up the team in FBS_TEAMS by ESPN team ID. If not found (e.g. G5
    team not yet populated in venues.py), falls back to ESPN's team data
    so the game still renders, just with degraded info.
    """
    team_block = competitor.get("team") or {}
    try:
        team_id = int(team_block.get("id") or 0)
    except (ValueError, TypeError):
        team_id = 0
    if not team_id:
        return None

    # Rank (None for unranked, 1-25 for AP Top 25)
    rank = None
    curated_rank = competitor.get("curatedRank") or {}
    if curated_rank:
        try:
            r = int(curated_rank.get("current", 99))
            if 1 <= r <= 25:
                rank = r
        except (ValueError, TypeError):
            pass

    # Score (live/final games only)
    try:
        score = int(competitor.get("score") or 0) if competitor.get("score") else None
    except (ValueError, TypeError):
        score = None

    # Look up in our local DB first (preferred, has stadium info)
    local = FBS_TEAMS.get(team_id)
    if local is not None:
        return {
            "team_id":     team_id,
            "name":        local["name"],
            "short":       local["short"],
            "abbrev":      local["abbrev"],
            "conf":        local["conf"],
            "color":       local["color"],
            "rank":        rank,
            "score":       score,
            "logo_url":    f"https://a.espncdn.com/i/teamlogos/ncaa/500/{team_id}.png",
            "_in_local_db": True,
        }

    # Fallback: ESPN-only data (degraded). Used for G5 teams we haven't
    # populated yet. The slate will still work, just with less branding.
    return {
        "team_id":     team_id,
        "name":        team_block.get("displayName") or team_block.get("name") or f"Team {team_id}",
        "short":       team_block.get("shortDisplayName") or team_block.get("name") or "?",
        "abbrev":      team_block.get("abbreviation") or "?",
        "conf":        "?",
        "color":       f"#{team_block.get('color') or '666666'}",
        "rank":        rank,
        "score":       score,
        "logo_url":    f"https://a.espncdn.com/i/teamlogos/ncaa/500/{team_id}.png",
        "_in_local_db": False,
    }


def _build_venue_record(espn_venue: dict, home_team: dict,
                       is_neutral: bool) -> dict:
    """Build venue record. Prefer home team's local DB stadium for non-neutral
    games (it has lat/lon for weather). For neutral games, use ESPN's venue
    payload with city defaults."""
    if not is_neutral and home_team.get("_in_local_db"):
        # Home team's stadium from our DB (has weather-ready lat/lon/tz)
        local_team = FBS_TEAMS[home_team["team_id"]]
        s = local_team["stadium"]
        return {
            "name":       s["name"],
            "city":       s["city"],
            "lat":        s["lat"],
            "lon":        s["lon"],
            "tz":         s["tz"],
            "roof":       s["roof"],
            "cap":        s.get("cap"),
            "is_neutral": False,
        }

    # Neutral site OR team not in local DB. Use ESPN's venue data.
    addr = espn_venue.get("address") or {}
    city_str = addr.get("city") or ""
    state = addr.get("state") or ""
    city = f"{city_str}, {state}".strip(", ")
    return {
        "name":       espn_venue.get("fullName") or "Unknown venue",
        "city":       city or "Unknown",
        "lat":        None,  # No lat/lon — slate must look it up or skip weather
        "lon":        None,
        "tz":         "America/New_York",  # safe default
        "roof":       "open",
        "cap":        espn_venue.get("capacity"),
        "is_neutral": is_neutral,
    }


def _make_slug(away_abbrev: str, home_abbrev: str, is_neutral: bool) -> str:
    """URL-friendly slug. e.g. "bama-aub" or for neutral games "tex-vs-ou"."""
    def clean(s: str) -> str:
        s = (s or "").lower()
        s = re.sub(r"[^a-z0-9]+", "", s)
        return s or "team"
    joiner = "-vs-" if is_neutral else "-at-"
    return f"{clean(away_abbrev)}{joiner}{clean(home_abbrev)}"
