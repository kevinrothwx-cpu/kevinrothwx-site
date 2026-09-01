"""
nfl.odds_api_schedule — NFL schedule sourced from The Odds API.

Why this exists:
    ESPN's NFL scoreboard started 403-blocking our requests on 2026-08-14.
    We already pay for The Odds API (ODDS_API_KEY env var, used by MLB).
    Their NFL endpoint returns every scheduled game with kickoff time,
    home team, away team — everything we need to build a schedule. Bonus:
    when the NFL flexes a game to a different broadcast window, bettors
    care about accurate kickoff times, so The Odds API updates them
    automatically. That's a better feed than ESPN even without the block.

Data source:
    https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds
    Auth: apiKey query param (same key MLB uses)

Caveats:
    - International Series games (London/Munich/Madrid/Mexico City/São
      Paulo) are returned with the US "home" team. The Odds API doesn't
      flag them as neutral-site. We handle a small manual override list
      below; add rows as international games are announced each spring.
    - Games without posted odds don't appear. In practice this is
      never a problem for regular-season or preseason NFL — books post
      odds days in advance for every game. Playoffs same.
    - Preseason "TBD" games (rare, mostly Hall of Fame slot) may be
      posted late — we accept whatever The Odds API has and don't complain.
"""

from __future__ import annotations

import os
import threading
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .venues import NFL_TEAMS, get_stadium, lookup_international_venue


# The Odds API has SEPARATE sport slugs for NFL regular season and
# preseason. Miss either one and you get an empty slate for that window.
# Both are 1 credit per fetch (2 credits total per warmer cycle).
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
NFL_SPORT_SLUGS = [
    "americanfootball_nfl",             # regular season + playoffs
    "americanfootball_nfl_preseason",   # August preseason only
]
REQUEST_TIMEOUT_SEC = 12

EASTERN_TZ = ZoneInfo("America/New_York")


# ── Team name → team_id lookup ─────────────────────────────────────────────
# The Odds API returns full team names like "Kansas City Chiefs".

def _build_team_name_index() -> dict[str, int]:
    """Build a case-insensitive lookup: team display name → NFL team_id.
    Supports both full name ("Kansas City Chiefs") and short ("Chiefs")."""
    idx: dict[str, int] = {}
    for team_id, team in NFL_TEAMS.items():
        for key in ("name", "short"):
            v = team.get(key)
            if v:
                idx[v.lower().strip()] = team_id
    return idx


_TEAM_NAME_INDEX: dict[str, int] = _build_team_name_index()


def _lookup_team_id(name: str) -> Optional[int]:
    """Return the NFL team_id for a given team name from The Odds API."""
    if not name:
        return None
    return _TEAM_NAME_INDEX.get(name.lower().strip())


# ── Neutral-site override list ─────────────────────────────────────────────
# The Odds API doesn't flag international games. Format each entry as:
#   (kickoff_date_ymd_str, home_team_abbrev, away_team_abbrev) → venue_key_from_INTERNATIONAL_VENUES
# Add new games here each year in preseason. If a game isn't in the list,
# it defaults to the home team's US stadium.
NEUTRAL_SITE_OVERRIDES: dict[tuple[str, str, str], str] = {
    # Example (leave commented until confirmed):
    # ("2026-10-05", "JAX", "MIN"): "wembley",
    # ("2026-11-09", "CAR", "NYG"): "allianz_munich",
}


# ── Fetch + parse ──────────────────────────────────────────────────────────

# Short-TTL cache of the RAW Odds API payload, shared with nfl/odds.py.
#
# The schedule and the totals come from the exact same request: this module
# fetches /americanfootball_nfl/odds?markets=totals to learn kickoff times
# and teams, and nfl/odds.py needs the bookmaker data in that SAME response
# to read the O/U. Without this cache a single slate build hit each slug
# twice — 4 credits per warmer cycle instead of 2, about 5,800 wasted
# calls a month.
#
# 120s is comfortably longer than one slate build (both consumers run
# seconds apart) and far shorter than the 25-minute warmer cycle, so the
# next cycle always fetches fresh.
_RAW_TTL_SECONDS = 120
_raw_cache: dict[str, tuple[float, list]] = {}
_raw_lock = threading.Lock()


def _fetch_one_sport(sport_slug: str, api_key: str) -> list[dict]:
    """Hit The Odds API for one sport slug and return the raw game list.
    Cached for _RAW_TTL_SECONDS so schedule + odds share one request.
    Empty list on any failure — never raises."""
    import time as _time
    with _raw_lock:
        hit = _raw_cache.get(sport_slug)
        if hit and (_time.time() - hit[0]) < _RAW_TTL_SECONDS:
            return hit[1]

    data = _fetch_one_sport_uncached(sport_slug, api_key)
    # Cache empty results too. The preseason slug is legitimately empty for
    # most of the year, and skipping the cache on empty meant it refetched
    # on every consumer — 3 credits per cycle instead of 2. A 120s window is
    # far shorter than the 25-minute warmer cycle, so pinning an empty
    # result briefly costs nothing in freshness.
    with _raw_lock:
        _raw_cache[sport_slug] = (_time.time(), data)
    return data


def fetch_raw_nfl_payload(api_key: str) -> list[dict]:
    """Raw Odds API games across both NFL slugs, de-duped by id.

    Public entry point for nfl/odds.py so both consumers share the cached
    fetch instead of each paying for its own."""
    out, seen = [], set()
    for slug in NFL_SPORT_SLUGS:
        for g in _fetch_one_sport(slug, api_key):
            gid = str(g.get("id") or "")
            if gid and gid in seen:
                continue
            if gid:
                seen.add(gid)
            out.append(g)
    return out


def _fetch_one_sport_uncached(sport_slug: str, api_key: str) -> list[dict]:
    """The actual HTTP call. Wrapped by _fetch_one_sport for caching."""
    try:
        resp = requests.get(
            f"{ODDS_API_BASE}/{sport_slug}/odds",
            params={
                "apiKey":     api_key,
                "regions":    "us",
                "markets":    "totals",
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if resp.status_code != 200:
            print(f"[nfl.odds_api] {sport_slug} returned {resp.status_code}: {resp.text[:200]}",
                  flush=True)
            return []
        raw = resp.json()
        if not isinstance(raw, list):
            print(f"[nfl.odds_api] {sport_slug} unexpected response type: {type(raw).__name__}",
                  flush=True)
            return []
        return raw
    except Exception as e:
        print(f"[nfl.odds_api] {sport_slug} fetch failed: {type(e).__name__}: {e}",
              flush=True)
        return []


def fetch_nfl_games_from_odds_api() -> list[dict]:
    """Pull upcoming NFL games from The Odds API across both regular-season
    and preseason sport slugs. Transforms into our internal NFL game shape.

    Costs 2 API credits per call (one per slug). Empty list on failure —
    caller (schedule.py) then falls back to ESPN."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[nfl.odds_api] ODDS_API_KEY not set; skipping", flush=True)
        return []

    raw_games: list[dict] = []
    for slug in NFL_SPORT_SLUGS:
        chunk = _fetch_one_sport(slug, api_key)
        if chunk:
            print(f"[nfl.odds_api] {slug}: {len(chunk)} raw games", flush=True)
        raw_games.extend(chunk)

    # De-dupe by game id in case both slugs return the same game (shouldn't
    # happen for NFL — preseason and regular season are disjoint — but
    # defensive).
    seen: set[str] = set()
    out: list[dict] = []
    for g in raw_games:
        gid = str(g.get("id") or "")
        if gid and gid in seen:
            continue
        seen.add(gid)
        parsed = _parse_odds_api_game(g)
        if parsed is not None:
            out.append(parsed)

    out.sort(key=lambda g: g.get("kickoff_utc") or datetime.max.replace(tzinfo=timezone.utc))
    print(f"[nfl.odds_api] fetched {len(out)} games total (both slugs, deduped)",
          flush=True)
    return out


def _parse_odds_api_game(raw: dict) -> Optional[dict]:
    """Transform one Odds-API game dict into our internal NFL game shape.
    Returns None if teams don't resolve or kickoff is missing."""
    try:
        event_id = raw.get("id")
        commence_iso = raw.get("commence_time", "")
        home_name = raw.get("home_team", "")
        away_name = raw.get("away_team", "")
        if not (event_id and commence_iso and home_name and away_name):
            return None

        home_id = _lookup_team_id(home_name)
        away_id = _lookup_team_id(away_name)
        if home_id is None or away_id is None:
            print(f"[nfl.odds_api] skipping {event_id}: unknown team "
                  f"({home_name!r} vs {away_name!r})", flush=True)
            return None

        # Kickoff
        try:
            kickoff_utc = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        if kickoff_utc.tzinfo is None:
            kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)

        # Team records — match nfl/schedule.py's _build_team_record shape
        home_team = NFL_TEAMS[home_id]
        away_team = NFL_TEAMS[away_id]
        home_rec = {
            "team_id": home_id,
            "name":    home_team["name"],
            "short":   home_team["short"],
            "abbrev":  home_team["abbrev"],
            "conf":    home_team["conf"],
            "div":     home_team["div"],
            "color":   home_team["color"],
            "logo_url": f"https://a.espncdn.com/i/teamlogos/nfl/500/{home_team['abbrev'].lower()}.png",
        }
        away_rec = {
            "team_id": away_id,
            "name":    away_team["name"],
            "short":   away_team["short"],
            "abbrev":  away_team["abbrev"],
            "conf":    away_team["conf"],
            "div":     away_team["div"],
            "color":   away_team["color"],
            "logo_url": f"https://a.espncdn.com/i/teamlogos/nfl/500/{away_team['abbrev'].lower()}.png",
        }

        # Venue lookup — check neutral override first, then home team's stadium
        kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)
        date_ymd = kickoff_eastern.strftime("%Y-%m-%d")
        override_key = (date_ymd, home_rec["abbrev"], away_rec["abbrev"])
        venue = None
        if override_key in NEUTRAL_SITE_OVERRIDES:
            venue_key = NEUTRAL_SITE_OVERRIDES[override_key]
            venue = lookup_international_venue(venue_key, "", "")
        if not venue:
            venue = get_stadium(home_id)
        if not venue:
            print(f"[nfl.odds_api] skipping {event_id}: no venue for home team_id={home_id}",
                  flush=True)
            return None

        # Local kickoff conversion
        tz = ZoneInfo(venue["timezone"])
        kickoff_local = kickoff_utc.astimezone(tz)

        # Guess season type from date (rough heuristic — good enough for
        # display). Preseason: Aug 1 – first Thursday of September.
        # Regular: through mid-January. Postseason: Jan-Feb.
        month = kickoff_eastern.month
        if month == 8 or (month == 9 and kickoff_eastern.day <= 8):
            season_type = 1  # Preseason
            season_type_label = "Preseason"
        elif month in (1, 2):
            season_type = 3  # Postseason
            season_type_label = "Postseason"
        else:
            season_type = 2  # Regular Season
            season_type_label = "Regular Season"

        return {
            "id":                str(event_id),
            "event_id":          str(event_id),
            "home":              home_rec,
            "away":              away_rec,
            "venue":             venue,
            "kickoff_utc":       kickoff_utc,
            "kickoff_local":     kickoff_local,
            "kickoff_eastern":   kickoff_eastern,
            "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "kickoff_date_eastern": kickoff_eastern.strftime("%Y-%m-%d"),
            "date_local":        kickoff_local.strftime("%Y-%m-%d"),
            "season_type":       season_type,
            "season_type_label": season_type_label,
            "week":              None,  # The Odds API doesn't tell us week #
            "status":            "pre",
            "slug":              _make_slug(away_rec["abbrev"], home_rec["abbrev"]),
            "source":            "odds_api",
        }
    except Exception as e:
        print(f"[nfl.odds_api] parse failed: {type(e).__name__}: {e}", flush=True)
        return None


def _make_slug(away_abbrev: str, home_abbrev: str) -> str:
    """Mirror nfl/schedule.py's slug format."""
    a = (away_abbrev or "").lower().replace(" ", "-")
    h = (home_abbrev or "").lower().replace(" ", "-")
    return f"{a}-{h}"


def filter_to_window(games: list[dict], start_utc: datetime,
                      days_ahead: int = 8) -> list[dict]:
    """Trim to games whose kickoff falls in [start_utc, start_utc+days_ahead].
    Odds API returns all upcoming games; we cap to our slate window."""
    end_utc = start_utc + timedelta(days=days_ahead + 1)
    return [g for g in games if start_utc <= g["kickoff_utc"] <= end_utc]
