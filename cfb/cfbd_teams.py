"""
cfb.cfbd_teams — CollegeFootballData.com /teams endpoint client.

Purpose:
    Get a logo URL for EVERY college football team we might display,
    including FCS opponents that aren't in our FBS_TEAMS dict.

    CFBD's /teams endpoint returns each team's `logos` array (usually
    ESPN CDN URLs). We fetch once per year, cache to disk, and expose
    get_logo_for_school(name) which parse_cfbd_game calls as a fallback
    when the internal FBS_TEAMS lookup misses.

Cost:
    1 CFBD credit per year per day (24h TTL). ~30 credits/month for
    the regular season year, ~60 in December when we may straddle two
    years. Negligible against the 5K/mo Tier 1 cap.

Never raises. Any failure logs and returns "" so the caller can render
the team name without a logo image (same as before this module existed).
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

from persistence import load_json, save_json, parse_dt


CFBD_BASE_URL = "https://api.collegefootballdata.com"
REQUEST_TIMEOUT_SEC = 15

# Module-level cache: {year: (fetched_at_utc, {normalized_school: logo_url})}.
# Persisted so Render deploys don't wipe it.
_CACHE: dict[int, tuple[datetime, dict[str, str]]] = {}
_CACHE_TTL_HOURS = 24
_DISK_CACHE_FILE = "cfbd_teams_cache.json"


def _headers() -> Optional[dict]:
    key = os.environ.get("CFBD_API_KEY", "").strip()
    if not key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "Accept":        "application/json",
    }


def _normalize(school: str) -> str:
    """Case-insensitive + strip trailing whitespace for lookups. Match
    keys the same way cfbd_client._lookup_team_id does."""
    return (school or "").lower().strip()


def _load_cache_from_disk() -> None:
    """Populate _CACHE from disk on module import."""
    raw = load_json(_DISK_CACHE_FILE, default={})
    if not isinstance(raw, dict):
        return
    for year_str, entry in raw.items():
        try:
            year = int(year_str)
            if not isinstance(entry, dict):
                continue
            fetched_at = parse_dt(entry.get("fetched_at"))
            logos = entry.get("logos") or {}
            if fetched_at and isinstance(logos, dict):
                _CACHE[year] = (fetched_at, dict(logos))
        except Exception:
            continue
    if _CACHE:
        total_teams = sum(len(v[1]) for v in _CACHE.values())
        print(f"[cfb.cfbd_teams] loaded disk cache: {len(_CACHE)} years, "
              f"{total_teams} teams total", flush=True)


def _persist_cache_to_disk() -> None:
    try:
        out = {}
        for year, (fetched_at, logos) in _CACHE.items():
            out[str(year)] = {
                "fetched_at": fetched_at.isoformat() if isinstance(fetched_at, datetime) else fetched_at,
                "logos":      logos,
            }
        save_json(_DISK_CACHE_FILE, out)
    except Exception as e:
        print(f"[cfb.cfbd_teams] disk persist failed: {type(e).__name__}: {e}",
              flush=True)


def _fetch_teams_for_year(year: int) -> dict[str, str]:
    """Hit CFBD /teams?year=YYYY and return {normalized_school: logo_url}.
    Returns cached copy if fresh, empty dict on hard failure."""
    now = datetime.now(timezone.utc)
    cached = _CACHE.get(year)
    if cached is not None:
        fetched_at, logos = cached
        age_hours = (now - fetched_at).total_seconds() / 3600
        if age_hours < _CACHE_TTL_HOURS:
            return logos

    headers = _headers()
    if not headers:
        print("[cfb.cfbd_teams] CFBD_API_KEY not set; skipping teams fetch",
              flush=True)
        return cached[1] if cached else {}

    try:
        resp = requests.get(
            f"{CFBD_BASE_URL}/teams",
            params={"year": year},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if resp.status_code == 429:
            print(f"[cfb.cfbd_teams] 429 quota; serving stale cache if any",
                  flush=True)
            return cached[1] if cached else {}
        if resp.status_code != 200:
            print(f"[cfb.cfbd_teams] returned {resp.status_code}: "
                  f"{resp.text[:200]}", flush=True)
            return cached[1] if cached else {}
        data = resp.json()
        if not isinstance(data, list):
            print(f"[cfb.cfbd_teams] unexpected response type: "
                  f"{type(data).__name__}", flush=True)
            return cached[1] if cached else {}
    except Exception as e:
        print(f"[cfb.cfbd_teams] fetch failed: {type(e).__name__}: {e}",
              flush=True)
        return cached[1] if cached else {}

    # Build the lookup. CFBD /teams returns:
    #   {"id": 333, "school": "Alabama", "mascot": "Crimson Tide",
    #    "abbreviation": "ALA", "alt_name_1": "...", "alt_name_2": "...",
    #    "alt_name_3": "...", "classification": "fbs",
    #    "conference": "SEC", "color": "#9E1B32",
    #    "logos": ["https://a.espncdn.com/i/teamlogos/ncaa/500/333.png", ...]}
    # We key on `school` + any non-null `alt_name_*` variants so lookups
    # match whatever name CFBD returns in its /games payload.
    logos: dict[str, str] = {}
    for team in data:
        if not isinstance(team, dict):
            continue
        logo_list = team.get("logos")
        if not logo_list or not isinstance(logo_list, list):
            continue
        logo_url = logo_list[0]
        if not logo_url or not isinstance(logo_url, str):
            continue
        # Register under every name variant CFBD publishes.
        for key in ("school", "alt_name_1", "alt_name_2", "alt_name_3"):
            v = team.get(key)
            if v and isinstance(v, str):
                logos[_normalize(v)] = logo_url

    _CACHE[year] = (now, logos)
    _persist_cache_to_disk()
    print(f"[cfb.cfbd_teams] year={year}: {len(data)} teams, "
          f"{len(logos)} name-keyed logos (cached {_CACHE_TTL_HOURS}h, persisted)",
          flush=True)
    return logos


def get_logo_for_school(school: str, year: Optional[int] = None) -> str:
    """Return the CFBD-supplied logo URL for a team (FBS OR FCS OR lower).

    Called from cfbd_client.parse_cfbd_game as a fallback when the
    internal FBS_TEAMS lookup misses (typically FCS opponents on cupcake
    games). Returns "" if we can't resolve — caller renders team name
    without a logo image.

    `year` defaults to the current UTC year. We also try the previous
    year on miss to handle December games that straddle the year boundary."""
    if not school:
        return ""
    key = _normalize(school)
    if year is None:
        year = datetime.now(timezone.utc).year

    for y in (year, year - 1):
        logos = _fetch_teams_for_year(y)
        if key in logos:
            return logos[key]
    return ""


# Load persistent cache on import so we don't need a fresh CFBD call
# on the first slate build after a Render deploy.
_load_cache_from_disk()
