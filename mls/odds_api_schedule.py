"""
mls.odds_api_schedule — MLS schedule sourced from The Odds API.

Why this exists:
    ESPN's MLS scoreboard started 403-blocking our Render IP on 2026-08-24
    (same block that hit NFL on 2026-08-14). We already pay for The Odds
    API — their `soccer_usa_mls` endpoint returns every scheduled match
    with kickoff time, home team, away team, and totals odds.

    Cost: 1 API credit per fetch. Warmer runs every 25 min → 96 calls/day
    → well under monthly quota (5000 in current plan).

Data source:
    https://api.the-odds-api.com/v4/sports/soccer_usa_mls/odds
    Auth: apiKey query param (same key MLB + NFL use — ODDS_API_KEY env)

Team name matching:
    The Odds API returns full team names ("Seattle Sounders FC", "LAFC",
    "D.C. United"). We build a case-insensitive lookup against both
    MLS_TEAMS["name"] and MLS_TEAMS["short"], plus a small alias table
    for known naming differences (e.g., "LAFC" vs "Los Angeles FC",
    "St Louis City SC" vs "St. Louis City SC").

    When a name doesn't match, we log it so we can add it to the alias
    table on the next deploy. No games get silently dropped.

Caveats:
    - Games without posted odds don't appear. In practice not an issue
      for MLS regular season — books post odds days in advance.
    - Leagues Cup / US Open Cup / Concacaf Champions Cup matches are NOT
      returned by this slug. Those need a separate integration if we
      ever want them.
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .venues import MLS_TEAMS, get_stadium


ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_usa_mls/odds"
REQUEST_TIMEOUT_SEC = 12
EASTERN_TZ = ZoneInfo("America/New_York")

# Module-level TTL cache. MLS matches happen Wed + Sat/Sun and kickoff
# times are set days in advance, so re-fetching every 25 min (the warmer
# cadence) just burns Odds API credits. Cap actual fetches to once every
# 6h — 4/day = ~120/mo instead of ~2900/mo.
#
# In-memory only. Deploys wipe it, but a redeploy costs at most 1 credit
# to warm back up.
CACHE_TTL_SECONDS = 6 * 3600
_CACHE: dict = {"games": None, "fetched_at": None}


# ── Team name → team_id lookup ─────────────────────────────────────────────

# Manual aliases for names The Odds API uses that don't exactly match our
# MLS_TEAMS[team_id]["name"] or ["short"]. The base lookup already covers
# both "name" and "short" for every team (case-insensitive), so this
# table only needs to catch KNOWN divergences — punctuation drops,
# alternate accent spellings, dropped suffixes, etc.
#
# Extend this table when the log shows a name in "unresolved team names".
# All team_ids MUST exist in MLS_TEAMS or the alias is silently discarded
# by _build_team_name_index below.
_NAME_ALIASES: dict[str, int] = {
    # Punctuation / period drops
    "dc united":               193,
    "st louis city sc":        21812,
    "saint louis city sc":     21812,
    # Accent variants
    "cf montréal":             9720,
    # Historical / colloquial names some feeds still use
    "montreal impact":         9720,
    # "FC" suffix dropped
    "atlanta united":          18418,
    "seattle sounders":        9726,
    "houston dynamo":          6077,
    "vancouver whitecaps":     9727,
    "minnesota united":        17362,
    "austin":                  20906,
    "san diego":               22529,
    # "SC" / "FC" suffix added
    "columbus crew sc":        183,
    # Common short-form variants
    "orlando city":            12011,
    "chicago fire":            182,
    "philadelphia":            10739,
    "kansas city":             186,
    "red bulls":               190,
    "ny city":                 17606,
    "ny city fc":              17606,
    "la":                      187,   # LA Galaxy in some short forms
}


def _build_team_name_index() -> dict[str, int]:
    """Case-insensitive lookup: team name → MLS team_id. Merges the
    canonical MLS_TEAMS entries with the manual alias table."""
    idx: dict[str, int] = {}
    for team_id, team in MLS_TEAMS.items():
        for key in ("name", "short"):
            v = team.get(key)
            if v:
                idx[v.lower().strip()] = team_id
    # Manual aliases override — only add if they resolve to a real team.
    for alias, team_id in _NAME_ALIASES.items():
        if team_id in MLS_TEAMS:
            idx[alias] = team_id
    return idx


_TEAM_NAME_INDEX: dict[str, int] = _build_team_name_index()


def _lookup_team_id(name: str) -> Optional[int]:
    """Return the MLS team_id for a given team name from The Odds API.
    Returns None if unresolvable (caller logs + skips the game)."""
    if not name:
        return None
    return _TEAM_NAME_INDEX.get(name.lower().strip())


# ── Fetch + parse ──────────────────────────────────────────────────────────

def fetch_mls_games_from_odds_api() -> list[dict]:
    """Pull upcoming MLS matches from The Odds API. Transforms into the
    same internal match shape mls/schedule.py produced from ESPN.

    Cached for CACHE_TTL_SECONDS (6h). The warmer calls this every 25
    min; the cache absorbs 14 of every 15 warmer ticks so we spend ~4
    credits/day instead of 96.

    Empty list on failure — caller (get_mls_week_games) then returns
    empty and the slate page shows the "no matches" empty state instead
    of a 500."""
    now = datetime.now(timezone.utc)
    cached = _CACHE.get("games")
    fetched_at = _CACHE.get("fetched_at")
    if cached is not None and fetched_at is not None:
        age = (now - fetched_at).total_seconds()
        if age < CACHE_TTL_SECONDS:
            # Silent hit — no log spam. The warmer prints its own tick line.
            return cached

    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[mls.odds_api] ODDS_API_KEY not set; skipping", flush=True)
        return []

    try:
        resp = requests.get(
            ODDS_API_URL,
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
            print(f"[mls.odds_api] returned {resp.status_code}: {resp.text[:200]}",
                  flush=True)
            return []
        raw_games = resp.json()
        if not isinstance(raw_games, list):
            print(f"[mls.odds_api] unexpected response type: {type(raw_games).__name__}",
                  flush=True)
            return []
    except Exception as e:
        print(f"[mls.odds_api] fetch failed: {type(e).__name__}: {e}", flush=True)
        return []

    print(f"[mls.odds_api] fetched {len(raw_games)} raw games", flush=True)

    out: list[dict] = []
    seen: set[str] = set()
    unresolved: list[str] = []
    for g in raw_games:
        gid = str(g.get("id") or "")
        if gid and gid in seen:
            continue
        seen.add(gid)
        parsed = _parse_odds_api_game(g, unresolved)
        if parsed is not None:
            out.append(parsed)

    if unresolved:
        # Print a compact summary so we can add aliases without spamming logs.
        uniq = sorted(set(unresolved))
        print(f"[mls.odds_api] {len(uniq)} unresolved team names (add to _NAME_ALIASES): "
              f"{uniq[:20]}", flush=True)

    out.sort(key=lambda g: g.get("kickoff_utc") or datetime.max.replace(tzinfo=timezone.utc))
    print(f"[mls.odds_api] parsed {len(out)} games (deduped, teams resolved) — "
          f"cached for {CACHE_TTL_SECONDS // 3600}h", flush=True)

    # Store in cache. Only cache non-empty results — if a fetch returned 0
    # games (e.g., transient API glitch), let the next warmer tick retry
    # instead of serving nothing for 6 hours.
    if out:
        _CACHE["games"] = out
        _CACHE["fetched_at"] = now
    return out


def _parse_odds_api_game(raw: dict, unresolved: list[str]) -> Optional[dict]:
    """Transform one Odds-API game dict into our internal MLS match shape.
    Returns None if teams don't resolve or kickoff is missing.

    Appends unresolvable team names to `unresolved` so the caller can
    log them for us to add to _NAME_ALIASES."""
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
            if home_id is None:
                unresolved.append(home_name)
            if away_id is None:
                unresolved.append(away_name)
            return None

        try:
            kickoff_utc = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        if kickoff_utc.tzinfo is None:
            kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)

        # Team records — match mls/schedule.py's _build_team_record shape
        home_team = MLS_TEAMS[home_id]
        away_team = MLS_TEAMS[away_id]
        home_rec = {
            "team_id":  home_id,
            "name":     home_team["name"],
            "short":    home_team["short"],
            "abbrev":   home_team["abbrev"],
            "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{home_id}.png",
        }
        away_rec = {
            "team_id":  away_id,
            "name":     away_team["name"],
            "short":    away_team["short"],
            "abbrev":   away_team["abbrev"],
            "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{away_id}.png",
        }

        # Venue is home team's stadium (MLS regular season = no neutral sites
        # outside MLS Cup final, which The Odds API doesn't cover anyway)
        venue = get_stadium(home_id)
        if not venue:
            print(f"[mls.odds_api] skipping {event_id}: no venue for home team_id={home_id}",
                  flush=True)
            return None

        tz = ZoneInfo(venue["timezone"])
        kickoff_local = kickoff_utc.astimezone(tz)
        kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)

        return {
            "id":              str(event_id),
            "event_id":        str(event_id),
            "home":            home_rec,
            "away":            away_rec,
            "venue":           venue,
            "kickoff_utc":     kickoff_utc,
            "kickoff_local":   kickoff_local,
            "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "date_local":      kickoff_local.strftime("%Y-%m-%d"),
            "status":          "pre",
            "slug":            _make_slug(away_rec["abbrev"], home_rec["abbrev"]),
            "source":          "odds_api",
        }
    except Exception as e:
        print(f"[mls.odds_api] parse failed: {type(e).__name__}: {e}", flush=True)
        return None


def _make_slug(away_abbrev: str, home_abbrev: str) -> str:
    """Mirror mls/schedule.py's slug format: 'rbny-at-phi'."""
    a = (away_abbrev or "tbd").lower().replace(".", "")
    h = (home_abbrev or "tbd").lower().replace(".", "")
    return f"{a}-at-{h}"


def filter_to_window(games: list[dict], start_utc: datetime,
                     days_ahead: int = 7) -> list[dict]:
    """Trim to matches whose kickoff falls in [start_utc, start_utc+days_ahead].
    The Odds API returns everything upcoming; we cap to the slate window."""
    end_utc = start_utc + timedelta(days=days_ahead + 1)
    return [g for g in games if start_utc <= g["kickoff_utc"] <= end_utc]
