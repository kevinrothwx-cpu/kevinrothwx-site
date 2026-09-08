"""
ucl.odds_api_schedule — Champions League schedule from The Odds API.

Why not ESPN:
    ESPN's soccer scoreboard 403-blocks our Render IP. It hit NFL on
    2026-08-14, MLS on 2026-08-24, and it is why /prem currently serves
    an empty slate while ESPN happily returns fixtures from any other
    network. Building UCL on ESPN would have shipped a page that tests
    clean locally and is permanently empty in production.

Data source:
    https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds
    Auth: apiKey query param (ODDS_API_KEY, same key MLB/NFL/CFB/MLS use)

API BUDGET — read before changing the TTLs
    Every other warmer on this box refreshes every 25 minutes. Doing that
    here would cost ~58 credits/day, ~1,750/month, against a plan the MLS
    module documents as 5,000/month. That is not worth it for a
    competition that plays eight Tuesdays and Wednesdays between
    September and January.

    The insight is that FIXTURES barely change (they're published months
    ahead) while WEATHER changes constantly. Weather comes from
    WeatherAPI, not from here. So this module refreshes on a two-tier
    schedule:

        next kickoff within 72h  -> TTL 1 hour   (odds still move)
        otherwise                -> TTL 6 hours  (nothing is happening)

    That lands around 150-250 credits/month. ucl/slate.py keeps its own
    25-minute weather cycle on top of this cache, so forecasts stay as
    fresh as every other sport while the paid API is barely touched.
"""

from __future__ import annotations

import os
import threading
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from .venues import UCL_TEAMS, lookup_team_id, get_stadium

ODDS_API_URL = ("https://api.the-odds-api.com/v4/sports/"
                "soccer_uefa_champs_league/odds")
REQUEST_TIMEOUT_SEC = 12
EASTERN_TZ = ZoneInfo("America/New_York")

# Two-tier cache. See API BUDGET above.
TTL_NEAR_SECONDS = 60 * 60          # a match inside 72h
TTL_FAR_SECONDS  = 6 * 60 * 60      # nothing soon
NEAR_WINDOW_HOURS = 72

_raw_cache: dict[str, object] = {"at": 0.0, "data": [], "ttl": TTL_FAR_SECONDS}
_raw_lock = threading.Lock()

# Loud-once memory so an unmappable club name doesn't spam the log every cycle.
_warned_names: set[str] = set()


def _next_kickoff_within(raw_games: list[dict], hours: int) -> bool:
    """True if any cached fixture kicks off inside `hours` from now."""
    if not raw_games:
        return False
    cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
    now = datetime.now(timezone.utc) - timedelta(hours=4)  # in-progress grace
    for g in raw_games:
        iso = g.get("commence_time") or ""
        try:
            ko = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        if now <= ko <= cutoff:
            return True
    return False


def _fetch_raw(api_key: str) -> list[dict]:
    """Hit The Odds API once. Empty list on any failure — never raises."""
    try:
        resp = requests.get(
            ODDS_API_URL,
            params={
                "apiKey":     api_key,
                "regions":    "us,uk,eu",
                "markets":    "totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if resp.status_code != 200:
            print(f"[ucl.odds_api] returned {resp.status_code}: {resp.text[:200]}",
                  flush=True)
            return []
        raw = resp.json()
        if not isinstance(raw, list):
            print(f"[ucl.odds_api] unexpected response type: {type(raw).__name__}",
                  flush=True)
            return []
        remaining = resp.headers.get("x-requests-remaining")
        if remaining is not None:
            print(f"[ucl.odds_api] {len(raw)} fixtures | credits remaining: {remaining}",
                  flush=True)
        return raw
    except Exception as e:
        print(f"[ucl.odds_api] fetch failed: {type(e).__name__}: {e}", flush=True)
        return []


def fetch_raw_ucl_payload(api_key: str) -> list[dict]:
    """Cached raw payload with the two-tier TTL described at module top."""
    with _raw_lock:
        age = _time.time() - float(_raw_cache["at"])
        if _raw_cache["data"] and age < float(_raw_cache["ttl"]):
            return list(_raw_cache["data"])  # type: ignore[arg-type]

    data = _fetch_raw(api_key)

    with _raw_lock:
        if not data and _raw_cache["data"]:
            # A failed refresh must not blank a good slate. Keep the old
            # payload and retry on the next near-tier interval.
            _raw_cache["at"] = _time.time() - float(_raw_cache["ttl"]) + 300
            return list(_raw_cache["data"])  # type: ignore[arg-type]
        ttl = (TTL_NEAR_SECONDS if _next_kickoff_within(data, NEAR_WINDOW_HOURS)
               else TTL_FAR_SECONDS)
        _raw_cache["at"] = _time.time()
        _raw_cache["data"] = data
        _raw_cache["ttl"] = ttl
        print(f"[ucl.odds_api] cached {len(data)} fixtures, next refresh in "
              f"{int(ttl/60)} min", flush=True)
    return list(data)


def fetch_ucl_matches_from_odds_api() -> list[dict]:
    """Upcoming UCL fixtures in our internal match shape. [] on failure."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[ucl.odds_api] ODDS_API_KEY not set; skipping", flush=True)
        return []

    raw_games = fetch_raw_ucl_payload(api_key)
    unresolved: list[str] = []
    out: list[dict] = []
    seen: set[str] = set()

    for g in raw_games:
        gid = str(g.get("id") or "")
        if gid and gid in seen:
            continue
        if gid:
            seen.add(gid)
        parsed = _parse_match(g, unresolved)
        if parsed is not None:
            out.append(parsed)

    # Log unknown clubs ONCE each. A club we can't resolve is a match with
    # no venue and therefore no forecast, so this must never be silent.
    new = [n for n in set(unresolved) if n not in _warned_names]
    if new:
        _warned_names.update(new)
        print(f"[ucl.odds_api] UNMAPPED CLUB NAMES (add to venues.ALIASES): "
              f"{sorted(new)}", flush=True)

    out.sort(key=lambda m: m["kickoff_utc"])
    print(f"[ucl.odds_api] parsed {len(out)} fixtures", flush=True)
    return out


def _parse_match(raw: dict, unresolved: list[str]) -> Optional[dict]:
    """One Odds API fixture -> our internal match shape. None if unusable."""
    try:
        event_id = raw.get("id")
        commence_iso = raw.get("commence_time") or ""
        home_name = raw.get("home_team") or ""
        away_name = raw.get("away_team") or ""
        if not (event_id and commence_iso and home_name and away_name):
            return None

        home_id = lookup_team_id(home_name)
        away_id = lookup_team_id(away_name)
        if home_id is None:
            unresolved.append(home_name)
        if away_id is None:
            unresolved.append(away_name)
        if home_id is None or away_id is None:
            return None

        try:
            kickoff_utc = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        if kickoff_utc.tzinfo is None:
            kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)

        home_t, away_t = UCL_TEAMS[home_id], UCL_TEAMS[away_id]
        home = _team_record(home_id, home_t)
        away = _team_record(away_id, away_t)

        venue = get_stadium(home_id)
        if not venue:
            print(f"[ucl.odds_api] skipping {event_id}: no venue for "
                  f"team_id={home_id} ({home_name})", flush=True)
            return None

        tz = ZoneInfo(venue["tz"])
        kickoff_local = kickoff_utc.astimezone(tz)
        kickoff_eastern = kickoff_utc.astimezone(EASTERN_TZ)

        return {
            "id":                  str(event_id),
            "event_id":            str(event_id),
            "home":                home,
            "away":                away,
            "venue":               venue,
            "kickoff_utc":         kickoff_utc,
            "kickoff_local":       kickoff_local,
            "kickoff_eastern":     kickoff_eastern,
            "kickoff_local_str":   kickoff_local.strftime("%H:%M"),
            "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "date_local":          kickoff_local.strftime("%Y-%m-%d"),
            "date_local_pretty":   kickoff_local.strftime("%A, %B %-d"),
            "date_eastern":        kickoff_eastern.strftime("%Y-%m-%d"),
            "status":              "pre",
            "slug":                make_slug(home["abbrev"], away["abbrev"]),
            "total":               _extract_total(raw),
            "source":              "odds_api",
        }
    except Exception as e:
        print(f"[ucl.odds_api] parse failed for {raw.get('id')}: "
              f"{type(e).__name__}: {e}", flush=True)
        return None


def _team_record(team_id: int, t: dict) -> dict:
    return {
        "team_id":  team_id,
        "name":     t["name"],
        "short":    t["short"],
        "abbrev":   t["abbrev"],
        "color":    t["color"],
        "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
    }


def _extract_total(raw: dict) -> Optional[float]:
    """Consensus goals total, if any book posted one. None otherwise."""
    try:
        points = []
        for bk in (raw.get("bookmakers") or []):
            for mk in (bk.get("markets") or []):
                if mk.get("key") != "totals":
                    continue
                for oc in (mk.get("outcomes") or []):
                    p = oc.get("point")
                    if isinstance(p, (int, float)):
                        points.append(float(p))
        if not points:
            return None
        points.sort()
        return points[len(points) // 2]
    except Exception:
        return None


def make_slug(home_abbrev: str, away_abbrev: str) -> str:
    """URL slug: home-vs-away. Matches the prem convention."""
    return f"{(home_abbrev or '??').lower()}-vs-{(away_abbrev or '??').lower()}"


def filter_to_window(matches: list[dict], start_utc: datetime,
                     days_ahead: int = 7) -> list[dict]:
    end_utc = start_utc + timedelta(days=days_ahead + 1)
    return [m for m in matches if start_utc <= m["kickoff_utc"] <= end_utc]
