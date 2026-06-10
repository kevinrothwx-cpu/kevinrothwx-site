"""
mlb.slate — the slate builder for kevinrothwx.com.

Given a date string (YYYY-MM-DD), produces a list of game dicts ready to
hand to a template. Each game dict has:

    {
      "game_pk":      int,
      "away_abbr":    "BAL",
      "home_abbr":    "NYY",
      "away_name":    "Baltimore Orioles",
      "home_name":    "New York Yankees",
      "venue":        "Yankee Stadium",
      "park":         <PARK_METADATA dict for canonical park>,
      "first_pitch_utc":     datetime,
      "first_pitch_local":   datetime (ballpark tz),
      "first_pitch_eastern": datetime (America/New_York, for display per Kevin),
      "forecast":     {temp, dew, wind_speed, wind_deg, precip_pct, ...},
      "wind_info":    {bucket, label, arrow, wind_speed},
      "hourly":       [ {hour_local_eastern, temp, precip_pct, ...}, ... ]  (±1 hr around game time + 3 in-game hours)
      "slug":         "orioles-vs-yankees",     # used in URLs
      "weather_source": "nws" | "weatherapi" | None,
      "weather_error":  None | str,
    }

Build is best-effort: a single park's NWS failure does not break the slate.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from .park_metadata import PARK_METADATA, PARK_NAME_TO_CANONICAL, EXCLUDED_VENUES
from .wind import get_wind_info
from .nws import (
    get_mlb_schedule, parse_mlb_game,
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
)
from .weatherapi import fetch_weatherapi_hourly, find_weatherapi_period


EASTERN_TZ = ZoneInfo("America/New_York")

# Hourly window per game: 1 hour before first pitch + 3 in-game hours + 1 after
HOURS_BEFORE = 1
HOURS_GAME   = 3
HOURS_AFTER  = 1


def slugify_team(name: str) -> str:
    """Brewers → brewers, Red Sox → red-sox, Diamondbacks → diamondbacks."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]+", "", name)
    name = re.sub(r"\s+", "-", name).strip("-")
    return name


def game_slug(away_name: str, home_name: str) -> str:
    """
    Build the URL slug for a game.
    "Baltimore Orioles" @ "New York Yankees" → "orioles-vs-yankees"
    Uses the last word of each team name (the nickname) for shorter URLs.
    """
    def last_word(team_name: str) -> str:
        words = team_name.split()
        if len(words) >= 2 and words[-2].lower() in ("red", "blue", "white"):
            # "Red Sox", "Blue Jays", "White Sox"
            return slugify_team(" ".join(words[-2:]))
        return slugify_team(words[-1]) if words else "team"
    return f"{last_word(away_name)}-vs-{last_word(home_name)}"


def lookup_park(venue_name: str) -> Optional[dict]:
    """Resolve any venue name (incl. aliases) to its PARK_METADATA entry."""
    if not venue_name:
        return None
    if venue_name in EXCLUDED_VENUES:
        return None
    canonical = PARK_NAME_TO_CANONICAL.get(venue_name.lower())
    if canonical:
        return {**PARK_METADATA[canonical], "_canonical_name": canonical}
    return None


def _forecast_for_park(park: dict, target_utc: datetime) -> tuple[Optional[dict], Optional[list[dict]], str, Optional[str]]:
    """
    Fetch forecast + raw hourly periods for one park.
    Returns (forecast_at_first_pitch, all_hourly_periods_normalized, source, error).

    `all_hourly_periods_normalized` is a list of dicts each in the same shape
    as `extract_forecast` returns — so downstream code does not need to know
    which provider it came from.
    """
    if park.get("nws_unsupported"):
        # Open-Meteo path (Toronto)
        try:
            periods = fetch_weatherapi_hourly(park["lat"], park["lon"])
            chosen  = find_weatherapi_period(periods, target_utc)
            return chosen, periods, "weatherapi", None
        except Exception as e:
            return None, None, "weatherapi", str(e)

    # NWS path (US)
    try:
        url = get_nws_hourly_url(park["lat"], park["lon"])
        raw_periods = get_nws_periods(url)
        chosen_raw  = find_period_for_time(raw_periods, target_utc)
        chosen      = extract_forecast(chosen_raw)
        normalized  = [extract_forecast(p) for p in raw_periods]
        return chosen, normalized, "nws", None
    except Exception as e:
        return None, None, "nws", str(e)


def _hourly_window(periods: list[dict], first_pitch_utc: datetime, tz: ZoneInfo) -> list[dict]:
    """
    Pick the hourly periods covering [first_pitch - HOURS_BEFORE,
    first_pitch + HOURS_GAME + HOURS_AFTER]. Annotates each with
    `hour_eastern` (str like "7 PM") for display per Kevin's spec
    (Eastern time across the board).
    """
    if not periods:
        return []

    # Round first pitch to its hour
    fp = first_pitch_utc.replace(minute=0, second=0, microsecond=0)
    window_start = fp - timedelta(hours=HOURS_BEFORE)
    window_end   = fp + timedelta(hours=HOURS_GAME + HOURS_AFTER)

    selected = []
    for p in periods:
        # All providers serialize start_time to ISO; parse and compare in UTC
        start = datetime.fromisoformat(p["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        start_utc = start.astimezone(timezone.utc)

        if window_start <= start_utc < window_end:
            # Annotate with Eastern time for display
            start_eastern = start_utc.astimezone(EASTERN_TZ)
            p2 = dict(p)
            p2["hour_eastern"]      = start_eastern.strftime("%-I %p").lstrip("0")
            p2["hour_eastern_dt"]   = start_eastern
            p2["is_game_hour"]      = fp <= start_utc < fp + timedelta(hours=HOURS_GAME)
            selected.append(p2)
    return selected


def build_slate(date_str: str) -> list[dict]:
    """
    Build the slate for a given date. Returns games in chronological order
    by first pitch. Games with no park match are dropped silently.
    """
    raw_games = get_mlb_schedule(date_str)
    out = []

    for g in raw_games:
        parsed = parse_mlb_game(g)
        if not parsed:
            continue
        park = lookup_park(parsed["venue"])
        if not park:
            # Unknown / excluded venue (international series, spring training)
            continue

        # Parse game time (UTC) and convert to ballpark local + Eastern
        try:
            fp_utc = datetime.fromisoformat(parsed["game_date"].replace("Z", "+00:00"))
        except Exception:
            continue
        park_tz = ZoneInfo(park["timezone"])
        fp_local   = fp_utc.astimezone(park_tz)
        fp_eastern = fp_utc.astimezone(EASTERN_TZ)

        # Fetch forecast + full hourly band
        forecast, all_periods, source, err = _forecast_for_park(park, fp_utc)

        # Compute wind info (only if we have a forecast)
        wind_info = None
        if forecast:
            wind_info = get_wind_info(
                wind_deg=forecast["wind_deg"],
                cf_bearing=park["cf_bearing_degrees"],
                wind_speed=forecast["wind_speed"],
            )

        # Trim to the ±game window
        hourly = _hourly_window(all_periods or [], fp_utc, park_tz)

        slug = game_slug(parsed["away_name"], parsed["home_name"])
        # Doubleheaders: append game_num
        if parsed.get("double_header") in ("Y", "S") and parsed.get("game_num", 1) > 1:
            slug = f"{slug}-g{parsed['game_num']}"

        out.append({
            **parsed,
            "park":                park,
            "first_pitch_utc":     fp_utc,
            "first_pitch_local":   fp_local,
            "first_pitch_eastern": fp_eastern,
            "first_pitch_eastern_str": fp_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "forecast":            forecast,
            "wind_info":           wind_info,
            "hourly":              hourly,
            "slug":                slug,
            "weather_source":      source,
            "weather_error":       err,
        })

    out.sort(key=lambda g: g["first_pitch_utc"])
    return out


# ── Precip color helper for templates ─────────────────────────────────────────

def precip_color(pct: int) -> str:
    """
    Color-bucket for precipitation %. Used by the hourly table to make rain
    chances pop visually. Returns a CSS class name.

    Thresholds:
        0-15%   green    (low / dry)
        16-40%  yellow   (moderate)
        41-65%  orange   (likely)
        66+%    red      (high)
    """
    if pct is None:
        return "precip-none"
    if pct <= 19:
        return "precip-green"
    if pct <= 39:
        return "precip-yellow"
    if pct <= 65:
        return "precip-orange"
    return "precip-red"


def precip_icon(pct) -> str:
    """
    Maps a precip % to a sky-icon class name. Same four buckets as
    precip_color. Templates render the matching SVG via a macro.

    Buckets:
        sun                 (0-15%)
        partly-cloudy       (16-40%)
        rain                (41-65%)
        storm               (66+%)
    """
    if pct is None:
        return "icon-sun"
    pct = int(pct)
    if pct <= 19:
        return "icon-sun"
    if pct <= 39:
        return "icon-partly-cloudy"
    if pct <= 65:
        return "icon-rain"
    return "icon-storm"
