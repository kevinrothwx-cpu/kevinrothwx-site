"""
prem.odds_api_schedule — Premier League schedule from The Odds API.

Why this exists (2026-09-08):
    /prem was serving "No Premier League matches scheduled in the next 7
    days" while ESPN's eng.1 scoreboard happily returned ten fixtures for
    the same window from any unblocked network. ESPN 403-blocks our Render
    IP — it hit NFL on 2026-08-14 and MLS on 2026-08-24, both of which were
    migrated to The Odds API at the time. prem/ was missed, so the failure
    sat silently behind the empty-state message for two weeks.

    This module is the same migration MLS got, and it mirrors
    ucl/odds_api_schedule.py.

Data source:
    https://api.the-odds-api.com/v4/sports/soccer_epl/odds
    Auth: apiKey query param (ODDS_API_KEY, shared with MLB/NFL/CFB/MLS/UCL)

API BUDGET
    /prem shows a goals total but nothing that moves minute to minute, so
    this module is effectively a FIXTURE feed with a slow-moving line
    attached. Fixtures move on a scale of days (TV reschedules) and a
    Premier League goals total barely moves at all. Refresh is therefore
    3 hours when a match is inside 72h and 12 hours otherwise, which is
    roughly 8 credits/day in season instead of the ~58 a 25-minute warmer
    would cost. prem/slate.py keeps its own 25-minute WEATHER cycle on top,
    so forecasts stay as fresh as every other sport.
"""

from __future__ import annotations

import os
import threading
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from .venues import EPL_TEAMS, get_stadium

ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
REQUEST_TIMEOUT_SEC = 12
UK_TZ = ZoneInfo("Europe/London")
EASTERN_TZ = ZoneInfo("America/New_York")

TTL_NEAR_SECONDS = 3 * 60 * 60       # a match inside 72h
TTL_FAR_SECONDS  = 12 * 60 * 60      # nothing soon (international breaks, summer)
NEAR_WINDOW_HOURS = 72

_raw_cache: dict[str, object] = {"at": 0.0, "data": [], "ttl": TTL_FAR_SECONDS}
_raw_lock = threading.Lock()
_warned_names: set[str] = set()


# The Odds API's club names don't always match ours. Same approach as
# mls/ and ucl/: index name + short + abbrev, then layer aliases on top.
ALIASES: dict[str, int] = {
    "afc bournemouth": 349, "bournemouth": 349,
    "arsenal": 359, "arsenal fc": 359,
    "aston villa": 362,
    "brentford": 337, "brentford fc": 337,
    "brighton and hove albion": 331, "brighton & hove albion": 331, "brighton": 331,
    "chelsea": 363, "chelsea fc": 363,
    "coventry city": 388, "coventry": 388,
    "crystal palace": 384,
    "everton": 368, "everton fc": 368,
    "fulham": 370, "fulham fc": 370,
    "hull city": 306, "hull": 306,
    "ipswich town": 373, "ipswich": 373,
    "leeds united": 357, "leeds": 357,
    "liverpool": 364, "liverpool fc": 364,
    "manchester city": 382, "man city": 382,
    "manchester united": 360, "man united": 360, "man utd": 360,
    "newcastle united": 361, "newcastle": 361,
    "nottingham forest": 393, "nott'm forest": 393, "notts forest": 393,
    "sunderland": 366, "sunderland afc": 366,
    "tottenham hotspur": 367, "tottenham": 367, "spurs": 367,
}


def _build_name_index() -> dict[str, int]:
    idx: dict[str, int] = {}
    for tid, t in EPL_TEAMS.items():
        for key in (t.get("name"), t.get("short"), t.get("abbrev")):
            if key:
                idx[key.lower().strip()] = tid
    idx.update(ALIASES)
    return idx


NAME_INDEX = _build_name_index()


def lookup_team_id(name: str) -> Optional[int]:
    if not name:
        return None
    return NAME_INDEX.get(name.lower().strip())


def _next_kickoff_within(raw_games: list[dict], hours: int) -> bool:
    if not raw_games:
        return False
    cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
    now = datetime.now(timezone.utc) - timedelta(hours=4)
    for g in raw_games:
        try:
            ko = datetime.fromisoformat((g.get("commence_time") or "").replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        if now <= ko <= cutoff:
            return True
    return False


def _fetch_raw(api_key: str) -> list[dict]:
    """One HTTP call. Empty list on any failure — never raises."""
    try:
        resp = requests.get(
            ODDS_API_URL,
            params={
                "apiKey":     api_key,
                "regions":    "uk,us",
                "markets":    "totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if resp.status_code != 200:
            print(f"[prem.odds_api] returned {resp.status_code}: {resp.text[:200]}",
                  flush=True)
            return []
        raw = resp.json()
        if not isinstance(raw, list):
            print(f"[prem.odds_api] unexpected response type: {type(raw).__name__}",
                  flush=True)
            return []
        remaining = resp.headers.get("x-requests-remaining")
        if remaining is not None:
            print(f"[prem.odds_api] {len(raw)} fixtures | credits remaining: {remaining}",
                  flush=True)
        return raw
    except Exception as e:
        print(f"[prem.odds_api] fetch failed: {type(e).__name__}: {e}", flush=True)
        return []


def fetch_raw_epl_payload(api_key: str) -> list[dict]:
    with _raw_lock:
        age = _time.time() - float(_raw_cache["at"])
        if _raw_cache["data"] and age < float(_raw_cache["ttl"]):
            return list(_raw_cache["data"])  # type: ignore[arg-type]

    data = _fetch_raw(api_key)

    with _raw_lock:
        if not data and _raw_cache["data"]:
            # A failed refresh must not blank a good slate.
            _raw_cache["at"] = _time.time() - float(_raw_cache["ttl"]) + 300
            return list(_raw_cache["data"])  # type: ignore[arg-type]
        ttl = (TTL_NEAR_SECONDS if _next_kickoff_within(data, NEAR_WINDOW_HOURS)
               else TTL_FAR_SECONDS)
        _raw_cache["at"] = _time.time()
        _raw_cache["data"] = data
        _raw_cache["ttl"] = ttl
        print(f"[prem.odds_api] cached {len(data)} fixtures, next refresh in "
              f"{int(ttl/60)} min", flush=True)
    return list(data)


def fetch_epl_matches_from_odds_api() -> list[dict]:
    """Upcoming EPL fixtures in prem/schedule.py's match shape. [] on failure."""
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        print("[prem.odds_api] ODDS_API_KEY not set; skipping", flush=True)
        return []

    raw_games = fetch_raw_epl_payload(api_key)
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

    new = [n for n in set(unresolved) if n not in _warned_names]
    if new:
        _warned_names.update(new)
        print(f"[prem.odds_api] UNMAPPED CLUB NAMES (add to ALIASES): "
              f"{sorted(new)}", flush=True)

    out.sort(key=lambda m: m["kickoff_utc"])
    print(f"[prem.odds_api] parsed {len(out)} fixtures", flush=True)
    return out


def _parse_match(raw: dict, unresolved: list[str]) -> Optional[dict]:
    """One Odds API fixture -> prem's match shape. None if unusable.

    Shape must stay identical to prem/schedule.py's _parse_event output —
    templates/prem/slate.html and the /prem routes read these keys."""
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

        home = _team_record(home_id)
        away = _team_record(away_id)

        venue = get_stadium(home_id)
        if not venue:
            print(f"[prem.odds_api] skipping {event_id}: no venue for "
                  f"team_id={home_id} ({home_name})", flush=True)
            return None

        kickoff_local = kickoff_utc.astimezone(UK_TZ)
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
            "kickoff_local_str":   kickoff_local.strftime("%-I:%M %p %Z").lstrip("0"),
            "kickoff_eastern_str": kickoff_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "date_local":          kickoff_local.strftime("%Y-%m-%d"),
            "date_local_pretty":   kickoff_local.strftime("%A, %B %-d"),
            "status":              "pre",
            "slug":                _slug(home["abbrev"], away["abbrev"]),
            "total":               _extract_total(raw),
            "source":              "odds_api",
        }
    except Exception as e:
        print(f"[prem.odds_api] parse failed for {raw.get('id')}: "
              f"{type(e).__name__}: {e}", flush=True)
        return None


def _extract_total(raw: dict) -> Optional[float]:
    """Consensus goals total, if any book posted one. None otherwise.

    We were already paying for the totals market on every request (see the
    markets param above) and then throwing the result away, so /prem showed
    no O/U while /ucl did. Same median-across-books approach as ucl/."""
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


def _team_record(team_id: int) -> dict:
    t = EPL_TEAMS[team_id]
    return {
        "team_id":  team_id,
        "name":     t["name"],
        "short":    t["short"],
        "abbrev":   t["abbrev"],
        "color":    t.get("color", ""),
        "logo_url": f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
    }


def _slug(home_abbrev: str, away_abbrev: str) -> str:
    """Must match prem/schedule.py's _slug: home-vs-away."""
    return f"{(home_abbrev or '??').lower()}-vs-{(away_abbrev or '??').lower()}"


def filter_to_window(matches: list[dict], start_utc: datetime,
                     days_ahead: int = 7) -> list[dict]:
    end_utc = start_utc + timedelta(days=days_ahead + 1)
    return [m for m in matches if start_utc <= m["kickoff_utc"] <= end_utc]
