"""
cfb.cfbd_client — CollegeFootballData.com API client for the CFB schedule.

Why this exists:
    ESPN's CFB scoreboard started 403-blocking our requests on 2026-08-14.
    CollegeFootballData.com (CFBD) is a free, purpose-built CFB data source
    used by most CFB analysts. Register at https://collegefootballdata.com/key,
    add CFBD_API_KEY to Render env vars.

Data source:
    https://api.collegefootballdata.com
    Auth: `Authorization: Bearer <CFBD_API_KEY>`
    Games endpoint: /games?year=YYYY&week=N&seasonType=regular

Design:
    - Fetches games and transforms them into the SAME dict shape that
      cfb/schedule.py's parse_cfb_event produces from ESPN. That way the
      downstream slate builder, templates, and admin pages don't care
      which source populated the game.
    - Team name → ESPN team_id lookup via the local FBS_TEAMS dict
      (keyed by ESPN team ID). If CFBD returns a team name we don't
      recognize (e.g. FCS opponent), we skip the game rather than
      guessing.
    - Never raises. Any fetch/parse failure logs and returns [] so the
      caller (cfb/schedule.py) can fall back to ESPN cleanly.
"""

from __future__ import annotations

import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .venues import FBS_TEAMS
from persistence import load_json, save_json, parse_dt

log = logging.getLogger(__name__)


CFBD_BASE_URL = "https://api.collegefootballdata.com"
REQUEST_TIMEOUT_SEC = 15

EASTERN_TZ = ZoneInfo("America/New_York")


# ── Team name lookup ────────────────────────────────────────────────────

def _build_team_name_index() -> dict[str, int]:
    """Build case-insensitive team-name → ESPN team_id map from FBS_TEAMS.
    Handles both `name` (full: "Alabama Crimson Tide") and `short` ("Alabama").
    CFBD returns short names like "Alabama", "Ohio State" — that's the primary
    match key."""
    idx: dict[str, int] = {}
    for team_id, team in FBS_TEAMS.items():
        for key in ("name", "short"):
            v = team.get(key)
            if v:
                idx[v.lower().strip()] = team_id
    return idx


_TEAM_NAME_INDEX: dict[str, int] = _build_team_name_index()


# Manual overrides for known CFBD name mismatches. CFBD uses school names
# that occasionally differ from what FBS_TEAMS has stored. Add entries as
# they come up.
_CFBD_NAME_OVERRIDES: dict[str, str] = {
    # cfbd_school_lower: local_short_or_name_lower
    "app state":            "appalachian state",
    "louisiana monroe":     "ul monroe",
    "ul monroe":            "ul monroe",
    "louisiana lafayette":  "louisiana",
    "san jose state":       "san jose state",
    "california":           "cal",
    "connecticut":          "uconn",
    "florida international":"fiu",
    "hawai'i":              "hawaii",
    "hawaii":               "hawaii",
    "louisiana":            "louisiana",
    "massachusetts":        "umass",
    "mississippi":          "ole miss",
    "san diego state":      "san diego state",
    "southern california":  "usc",
    "southern methodist":   "smu",
    "texas christian":      "tcu",
    "texas san antonio":    "utsa",
    "texas el paso":        "utep",
    # Add more as CFBD returns names we don't recognize
}


def _lookup_team_id(cfbd_school: str) -> Optional[int]:
    """Given CFBD's team name, return the ESPN team_id from FBS_TEAMS or None."""
    if not cfbd_school:
        return None
    key = cfbd_school.lower().strip()
    if key in _TEAM_NAME_INDEX:
        return _TEAM_NAME_INDEX[key]
    override = _CFBD_NAME_OVERRIDES.get(key)
    if override and override in _TEAM_NAME_INDEX:
        return _TEAM_NAME_INDEX[override]
    return None


# ── Fetch + parse ────────────────────────────────────────────────────────

def _headers() -> Optional[dict]:
    """Build auth headers or return None if key is unset."""
    key = os.environ.get("CFBD_API_KEY", "").strip()
    if not key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "Accept":        "application/json",
    }


# Module-level cache: {(year, season_type): (fetched_at_utc, games_list)}.
# Also persisted to disk via `persistence.save_json` so it survives Render
# deploys — otherwise every push resets the cache and forces a fresh
# CFBD call on the next warmer cycle, blowing quota on deploy churn.
#
# TTL is 1 hour on Patreon Tier 1 ($1/mo, 5K calls/mo). Math: 1 fetch/hour
# × 24h × ~30 days = ~720 calls/month regular season, up to ~1440/month
# in bowl season (Dec-Feb includes postseason). Under 30% of the 5K cap
# even if OVERcast CFB is also hitting CFBD from a separate process.
_YEAR_CACHE: dict[tuple, tuple[datetime, list[dict]]] = {}
_CACHE_TTL_HOURS   = 1
BACKOFF_ON_429_HOURS = 1   # on Tier 1 (5K/mo), retry hourly after 429; worst-case
                            # 720 wasted calls/mo if quota stays exhausted, still
                            # well under cap. On free tier this was 6h.

_DISK_CACHE_FILE = "cfbd_year_cache.json"


def _load_cache_from_disk() -> None:
    """Populate _YEAR_CACHE from disk on module import so we don't lose
    everything across Render deploys. Silently returns if the file is
    missing or malformed — cold cache just means the first fetch after
    boot hits CFBD, same as before."""
    raw = load_json(_DISK_CACHE_FILE, default={})
    if not isinstance(raw, dict):
        return
    for key_str, entry in raw.items():
        try:
            # Key was serialized as "year|season_type" since JSON can't have tuple keys
            year_str, season_type = key_str.split("|", 1)
            key = (int(year_str), season_type)
            if not isinstance(entry, dict):
                continue
            fetched_at_str = entry.get("fetched_at")
            games = entry.get("games") or []
            fetched_at = parse_dt(fetched_at_str)
            if fetched_at and isinstance(games, list):
                _YEAR_CACHE[key] = (fetched_at, games)
        except Exception:
            continue
    if _YEAR_CACHE:
        print(f"[cfb.cfbd] loaded disk cache: {len(_YEAR_CACHE)} entries", flush=True)


def _persist_cache_to_disk() -> None:
    """Serialize _YEAR_CACHE and write atomically. Tuple keys become
    "year|season_type" strings; datetimes become ISO strings via
    persistence._json_default."""
    try:
        out = {}
        for (year, season_type), (fetched_at, games) in _YEAR_CACHE.items():
            key_str = f"{year}|{season_type}"
            out[key_str] = {
                "fetched_at": fetched_at.isoformat() if isinstance(fetched_at, datetime) else fetched_at,
                "games":      games,
            }
        save_json(_DISK_CACHE_FILE, out)
    except Exception as e:
        print(f"[cfb.cfbd] disk cache save failed: {type(e).__name__}: {e}", flush=True)


# Load on import
_load_cache_from_disk()


def fetch_cfbd_games_for_year(year: int, season_type: str = "regular") -> list[dict]:
    """Pull the full CFBD games list for a season. One API call per season
    per (up to) 6 hours — module cache prevents warmer cycles from hammering
    CFBD and blowing the monthly quota. Returns raw CFBD game dicts (unparsed).
    Empty list on failure — but if we have STALE cached data available, we
    return the stale data instead so the slate doesn't go empty on transient
    errors (particularly 429 quota-exceeded)."""
    now = datetime.now(timezone.utc)
    key = (year, season_type)

    # Serve from cache if fresh
    cached = _YEAR_CACHE.get(key)
    if cached is not None:
        fetched_at, games = cached
        age_hours = (now - fetched_at).total_seconds() / 3600
        if age_hours < _CACHE_TTL_HOURS:
            # Cache is fresh — no network call needed
            return games

    headers = _headers()
    if not headers:
        print("[cfb.cfbd] CFBD_API_KEY not set; skipping CFBD fetch", flush=True)
        return cached[1] if cached else []

    try:
        resp = requests.get(
            f"{CFBD_BASE_URL}/games",
            params={"year": year, "seasonType": season_type},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if resp.status_code == 429:
            # Monthly quota / rate limit hit. Extend cache TTL so we stop
            # hammering CFBD. If we have any cached data (even stale),
            # return it so the slate stays populated.
            print(f"[cfb.cfbd] 429 quota/rate exceeded — backing off {BACKOFF_ON_429_HOURS}h. "
                  f"Serving cached data if available.", flush=True)
            if cached:
                # Bump the cached timestamp forward so we don't retry for a while
                _YEAR_CACHE[key] = (now - timedelta(hours=_CACHE_TTL_HOURS - BACKOFF_ON_429_HOURS), cached[1])
                _persist_cache_to_disk()
                return cached[1]
            # Cold cache and 429 — store empty result with backoff TTL so
            # we don't slam the endpoint on every request
            _YEAR_CACHE[key] = (now - timedelta(hours=_CACHE_TTL_HOURS - BACKOFF_ON_429_HOURS), [])
            _persist_cache_to_disk()
            return []
        if resp.status_code != 200:
            print(f"[cfb.cfbd] returned {resp.status_code}: {resp.text[:200]}", flush=True)
            # Serve stale cache on other errors too
            return cached[1] if cached else []
        data = resp.json()
        if not isinstance(data, list):
            print(f"[cfb.cfbd] unexpected response type: {type(data).__name__}", flush=True)
            return cached[1] if cached else []
        # Cache success
        _YEAR_CACHE[key] = (now, data)
        _persist_cache_to_disk()
        print(f"[cfb.cfbd] fetched year={year} {season_type}: {len(data)} raw games (cached {_CACHE_TTL_HOURS}h, persisted)",
              flush=True)
        return data
    except Exception as e:
        print(f"[cfb.cfbd] fetch failed: {type(e).__name__}: {e}", flush=True)
        return cached[1] if cached else []


def get_cfbd_games_in_window(start_utc: datetime, days_ahead: int = 7,
                              cache_by_year: Optional[dict] = None) -> list[dict]:
    """Return parsed game dicts (matching our internal shape) for games
    kicking off within [start_utc, start_utc + days_ahead].

    The `cache_by_year` param is deprecated (kept for signature compatibility)
    — the module-level _YEAR_CACHE now handles cross-cycle caching with
    a 6-hour TTL. This function stays stateless from the caller's POV.
    """
    end_utc = start_utc + timedelta(days=days_ahead + 1)
    years_needed = {start_utc.year, end_utc.year}

    # Always fetch both season types. Removed the month-based gate on
    # 2026-08-23: extra 720 calls/month is <15% of the 5K Tier 1 cap and
    # guarantees late-announced bowls/CFP games can't slip through.
    all_raw: list[dict] = []
    for year in years_needed:
        for season_type in ("regular", "postseason"):
            all_raw.extend(fetch_cfbd_games_for_year(year, season_type))

    # Diagnostic: on 2026-08-23 we saw CFBD return 3610 raw games while our
    # parser produced 0 — v2 API likely changed field names. Dump the first
    # raw game's keys + values so we can see what CFBD is actually sending.
    if all_raw:
        first = all_raw[0]
        keys_sample = sorted(first.keys())[:20]
        print(f"[cfb.cfbd] raw sample keys: {keys_sample}", flush=True)
        # Show a small taste of common fields
        for probe in ("id", "start_date", "startDate", "home_team", "homeTeam",
                      "away_team", "awayTeam", "home_classification",
                      "homeClassification", "start_time_tbd", "startTimeTBD",
                      "venue", "neutral_site", "neutralSite", "season", "week"):
            if probe in first:
                v = first[probe]
                v_str = repr(v)[:60]
                print(f"[cfb.cfbd]   {probe}={v_str}", flush=True)

    out: list[dict] = []
    parse_reject_reasons: dict[str, int] = {}
    for raw in all_raw:
        parsed = parse_cfbd_game(raw, reject_stats=parse_reject_reasons)
        if not parsed:
            continue
        kickoff = parsed.get("kickoff_utc")
        if not kickoff:
            continue
        if kickoff < start_utc or kickoff > end_utc:
            parse_reject_reasons["out_of_window"] = parse_reject_reasons.get("out_of_window", 0) + 1
            continue
        out.append(parsed)

    if parse_reject_reasons:
        print(f"[cfb.cfbd] parse reject reasons: {parse_reject_reasons}", flush=True)

    # Sort chronologically to match ESPN fetcher's contract
    out.sort(key=lambda g: g["kickoff_utc"])
    print(f"[cfb.cfbd] window {start_utc.date()} +{days_ahead}d: {len(out)} games", flush=True)
    return out


def parse_cfbd_game(raw: dict, reject_stats: Optional[dict] = None) -> Optional[dict]:
    """Convert one CFBD game into our normalized shape (matching what
    cfb/schedule.py's parse_cfb_event produces from ESPN). Returns None
    if we can't map required fields (unknown teams, missing kickoff, etc.).

    CFBD v1 fields: id, start_date, home_team, home_id, home_classification,
                    away_team, away_id, away_classification, venue,
                    start_time_tbd, neutral_site
    CFBD v2 (camelCase): startDate, homeTeam, homeClassification, etc.
    """
    def _bump(reason: str):
        if reject_stats is not None:
            reject_stats[reason] = reject_stats.get(reason, 0) + 1

    try:
        cfbd_id    = raw.get("id")
        start_date = raw.get("start_date") or raw.get("startDate")
        home_school = raw.get("home_team") or raw.get("homeTeam") or ""
        away_school = raw.get("away_team") or raw.get("awayTeam") or ""
        if not (cfbd_id and start_date and home_school and away_school):
            _bump("missing_core_fields")
            return None

        # Skip TBD-time games — they'll get a real time when scheduled.
        if raw.get("start_time_tbd") or raw.get("startTimeTBD"):
            _bump("time_tbd")
            return None

        # Parse kickoff (CFBD uses ISO with trailing Z or explicit offset)
        try:
            kickoff_utc = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            _bump("bad_start_date")
            return None
        if kickoff_utc.tzinfo is None:
            kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)

        # Only include games where the HOME team is FBS. Skip games where
        # home is non-FBS (FCS host); away can be FCS (cupcake games at FBS
        # venue, still have real weather).
        home_class = (raw.get("home_classification") or raw.get("homeClassification") or "").lower()
        if home_class and home_class != "fbs":
            _bump(f"home_class_{home_class}")
            return None

        # Team lookups
        home_team_id = _lookup_team_id(home_school)
        away_team_id = _lookup_team_id(away_school)
        if home_team_id is None:
            _bump("unknown_home_team")
            # Only spam the log once per unique unknown team to avoid noise
            return None

        home_team = FBS_TEAMS.get(home_team_id, {})
        # away team may be None for FCS opponents — build a minimal record
        if away_team_id is not None:
            away_team = FBS_TEAMS.get(away_team_id, {})
            away_abbrev = away_team.get("abbrev") or away_school[:4].upper()
            away_full = away_team.get("name") or away_school
            away_short = away_team.get("short") or away_school
            away_logo = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{away_team_id}.png"
            away_color = away_team.get("color") or "#111111"
        else:
            # FCS opponent — display with the CFBD school name, generic logo
            away_abbrev = away_school[:4].upper()
            away_full = away_school
            away_short = away_school
            away_logo = ""
            away_color = "#888888"

        home_abbrev = home_team.get("abbrev") or home_school[:4].upper()
        home_full = home_team.get("name") or home_school
        home_short = home_team.get("short") or home_school
        home_logo = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{home_team_id}.png"
        home_color = home_team.get("color") or "#111111"

        # Venue: use home stadium unless neutral site
        is_neutral = bool(raw.get("neutral_site") or raw.get("neutralSite"))
        if is_neutral:
            # CFBD tells us the neutral venue name; we don't have coords for
            # every neutral venue. Try to look up by name in FBS_TEAMS's
            # stadiums; else fall back to home stadium (imperfect but at
            # least gives us weather somewhere plausible).
            neutral_name = raw.get("venue") or ""
            venue_dict = _find_stadium_by_name(neutral_name) or dict(home_team.get("stadium") or {})
            venue_dict = dict(venue_dict)
            venue_dict["is_neutral"] = True
        else:
            venue_dict = dict(home_team.get("stadium") or {})
            venue_dict["is_neutral"] = False

        if not venue_dict:
            _bump("no_venue")
            return None

        # Kickoff strings + date buckets
        kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)
        kickoff_eastern_str = kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0")
        kickoff_date_eastern = kickoff_eastern.strftime("%Y-%m-%d")

        # Slug + URL path
        slug = _make_slug(away_abbrev, home_abbrev, is_neutral)
        url_path = f"/ncaaf/{kickoff_date_eastern}/{slug}"

        season_type_raw = (raw.get("season_type") or raw.get("seasonType") or "regular").lower()
        season_type_label = {
            "regular":    "Regular Season",
            "postseason": "Bowl/Postseason",
            "spring_regular": "Spring",
        }.get(season_type_raw, season_type_raw.title())

        return {
            "event_id":             str(cfbd_id),
            "espn_url":             None,  # not from ESPN
            "cfbd_id":              cfbd_id,
            "home": {
                "team_id":   home_team_id,
                "name":      home_full,
                "short":     home_short,
                "abbrev":    home_abbrev,
                "logo_url":  home_logo,
                "color":     home_color,
                "rank":      None,  # CFBD doesn't include current rank on /games — separate endpoint
                "_in_local_db": True,
            },
            "away": {
                "team_id":   away_team_id or 0,
                "name":      away_full,
                "short":     away_short,
                "abbrev":    away_abbrev,
                "logo_url":  away_logo,
                "color":     away_color,
                "rank":      None,
                "_in_local_db": away_team_id is not None,
            },
            "venue":                venue_dict,
            "kickoff_utc":          kickoff_utc,
            "kickoff_eastern":      kickoff_eastern,
            "kickoff_eastern_str":  kickoff_eastern_str,
            "kickoff_date_eastern": kickoff_date_eastern,
            "date_local":           kickoff_eastern.strftime("%Y-%m-%d"),
            "season_type":          season_type_raw.replace("regular-season", "regular"),
            "season_type_label":    season_type_label,
            "week":                 raw.get("week"),
            "status":               "scheduled",  # CFBD has this, we can refine later
            "slug":                 slug,
            "url_path":             url_path,
            "source":               "cfbd",
        }
    except Exception as e:
        _bump(f"exception_{type(e).__name__}")
        print(f"[cfb.cfbd] parse failed: {type(e).__name__}: {e}", flush=True)
        return None


def _find_stadium_by_name(venue_name: str) -> Optional[dict]:
    """Search FBS_TEAMS for a stadium with a matching name. Handles the
    common neutral-site case where the venue is another FBS school's home
    stadium (e.g. AT&T Stadium hosts Texas vs OU annually)."""
    if not venue_name:
        return None
    vn = venue_name.lower().strip()
    for team in FBS_TEAMS.values():
        st = team.get("stadium") or {}
        st_name = (st.get("name") or "").lower().strip()
        if st_name == vn or vn in st_name or st_name in vn:
            return dict(st)
    return None


def _make_slug(away_abbrev: str, home_abbrev: str, is_neutral: bool) -> str:
    """URL-friendly slug. Mirrors cfb/schedule.py's _make_slug behavior."""
    a = (away_abbrev or "").lower().replace(" ", "-").replace("&", "and")
    h = (home_abbrev or "").lower().replace(" ", "-").replace("&", "and")
    if is_neutral:
        return f"{a}-vs-{h}"
    return f"{a}-{h}"
