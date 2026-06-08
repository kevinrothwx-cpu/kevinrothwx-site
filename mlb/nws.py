"""
mlb.nws — NOAA NWS + MLB Stats API helpers for kevinrothwx.com

Vendored from OVERcast/score_today.py, but stripped of the OVERcast engine,
odds API, pandas, and snapshot logger. This module is self-contained and
only depends on `requests`.

NWS coverage:
    US (contiguous + Alaska + Hawaii) only. For Rogers Centre (Toronto)
    we fall back to Open-Meteo — see mlb/open_meteo.py.

User-Agent:
    NWS requires a User-Agent string with contact info. We use a distinct
    UA from OVERcast so the two services are tracked separately by NWS.
"""

from __future__ import annotations

import re
import requests
from datetime import datetime, timedelta
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
NWS_POINTS_URL   = "https://api.weather.gov/points/{lat},{lon}"

# Distinct UA so NWS rate-limit / abuse tracking treats this as its own service
NWS_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/geo+json",
}

# Compass direction → meteorological degrees (wind FROM)
COMPASS_TO_DEG = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
    "CALM": 0, "VRB": 0, "VAR": 0,
}


# ── MLB Schedule ──────────────────────────────────────────────────────────────

def get_mlb_schedule(date_str: str) -> list[dict]:
    """
    Fetch all MLB games for a given date (YYYY-MM-DD).
    Returns a list of raw game dicts from the MLB Stats API.
    """
    resp = requests.get(
        MLB_SCHEDULE_URL,
        params={"sportId": 1, "date": date_str, "hydrate": "team,venue"},
        timeout=15,
    )
    resp.raise_for_status()
    games = []
    for date_data in resp.json().get("dates", []):
        games.extend(date_data.get("games", []))
    return games


def parse_mlb_game(game: dict) -> Optional[dict]:
    """
    Extract the fields we need from a raw Stats API game object.
    Returns None if the game is postponed, cancelled, or suspended.
    """
    state = game.get("status", {}).get("abstractGameState", "")
    if state in ("Postponed", "Cancelled", "Suspended"):
        return None

    venue_name = game.get("venue", {}).get("name", "")
    game_date  = game.get("gameDate", "")   # ISO 8601 UTC string
    away_team  = game.get("teams", {}).get("away", {}).get("team", {})
    home_team  = game.get("teams", {}).get("home", {}).get("team", {})

    return {
        "venue":         venue_name,
        "game_date":     game_date,
        "game_pk":       game.get("gamePk", 0),
        "away_abbr":     away_team.get("abbreviation", away_team.get("teamCode", "???")),
        "home_abbr":     home_team.get("abbreviation", home_team.get("teamCode", "???")),
        "away_name":     away_team.get("name", ""),
        "home_name":     home_team.get("name", ""),
        "away_team_id":  away_team.get("id", ""),
        "home_team_id":  home_team.get("id", ""),
        "double_header": game.get("doubleHeader", "N"),
        "game_num":      game.get("gameNumber", 1),
        "status":        state,
    }


# ── NWS Forecast (in-process cache) ──────────────────────────────────────────

# lat/lon → hourly forecast URL (cached indefinitely; URLs are stable)
_nws_hourly_url_cache: dict[str, str] = {}
# hourly URL → list of forecast periods (cleared by background warmer every 25 min)
_nws_periods_cache: dict[str, list] = {}


def clear_periods_cache() -> None:
    """Called by the background warmer to force fresh forecasts."""
    _nws_periods_cache.clear()


def get_nws_hourly_url(lat: float, lon: float) -> str:
    """
    Two-step NWS lookup. /points/{lat},{lon} returns metadata including
    the hourly forecast URL for that grid cell. Cached per lat/lon
    indefinitely (NWS URLs are stable).
    """
    key = f"{lat:.4f},{lon:.4f}"
    if key not in _nws_hourly_url_cache:
        resp = requests.get(
            NWS_POINTS_URL.format(lat=lat, lon=lon),
            headers=NWS_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        _nws_hourly_url_cache[key] = resp.json()["properties"]["forecastHourly"]
    return _nws_hourly_url_cache[key]


def get_nws_periods(hourly_url: str) -> list:
    """
    Fetch and cache the list of hourly forecast periods for a URL.
    Each call returns ~156 hourly periods (next ~6.5 days).
    """
    if hourly_url not in _nws_periods_cache:
        resp = requests.get(hourly_url, headers=NWS_HEADERS, timeout=15)
        resp.raise_for_status()
        _nws_periods_cache[hourly_url] = resp.json()["properties"]["periods"]
    return _nws_periods_cache[hourly_url]


def find_period_for_time(periods: list, target_utc: datetime) -> dict:
    """
    Return the hourly forecast period that covers the rounded target time.

    NWS periods are hourly buckets (e.g. 6 PM–7 PM). A game at 6:40 PM
    technically falls in the 6 PM bucket but is mostly played during 7, 8,
    9 PM hours. Rounding to nearest hour gives a more representative pick.

    Falls back to nearest future period, then the first period.
    """
    rounded_utc = target_utc.replace(second=0, microsecond=0)
    if rounded_utc.minute >= 30:
        rounded_utc = rounded_utc.replace(minute=0) + timedelta(hours=1)
    else:
        rounded_utc = rounded_utc.replace(minute=0)

    for period in periods:
        start = datetime.fromisoformat(period["startTime"])
        end   = datetime.fromisoformat(period["endTime"])
        if start <= rounded_utc.astimezone(start.tzinfo) < end:
            return period

    future = [
        p for p in periods
        if datetime.fromisoformat(p["startTime"]) >= rounded_utc.astimezone(
            datetime.fromisoformat(periods[0]["startTime"]).tzinfo
        )
    ]
    return future[0] if future else periods[0]


# ── Forecast field parsers ────────────────────────────────────────────────────

def parse_wind_direction(wind_dir) -> float:
    """Convert NWS windDirection (string compass or numeric degrees) to met deg."""
    if wind_dir is None:
        return 0.0
    try:
        return float(wind_dir)
    except (ValueError, TypeError):
        return COMPASS_TO_DEG.get(str(wind_dir).strip().upper(), 0.0)


def parse_wind_speed(wind_str) -> float:
    """
    Parse NWS windSpeed string to mph float.
    Handles "10 mph", "10 to 15 mph" (averages range), "0" or None.
    """
    if not wind_str:
        return 0.0
    nums = re.findall(r"\d+(?:\.\d+)?", str(wind_str))
    if not nums:
        return 0.0
    return sum(float(n) for n in nums) / len(nums)


def extract_forecast(period: dict) -> dict:
    """
    Pull temp (°F), dew (°F), wind_speed (mph), wind_deg (met degrees),
    precip probability (%), humidity (%), and short_forecast from one
    NWS hourly period.
    """
    # Temperature
    temp = period.get("temperature", 70)
    if period.get("temperatureUnit") == "C":
        temp = temp * 9 / 5 + 32
    temp = round(float(temp))

    # Dewpoint — NWS returns °C inside a unit object
    dew_obj = period.get("dewpoint") or period.get("dewPoint")
    if isinstance(dew_obj, dict):
        dew_c = dew_obj.get("value")
        dew = round(dew_c * 9 / 5 + 32) if dew_c is not None else None
    else:
        dew = round(float(dew_obj) * 9 / 5 + 32) if dew_obj is not None else None

    # Wind
    wind_speed = round(parse_wind_speed(period.get("windSpeed", "0")))
    wind_deg   = parse_wind_direction(period.get("windDirection"))

    # Precip probability (kevinrothwx-site shows this; OVERcast didn't)
    pop_obj = period.get("probabilityOfPrecipitation")
    if isinstance(pop_obj, dict):
        pop = pop_obj.get("value")
    else:
        pop = pop_obj
    precip_pct = int(pop) if pop is not None else 0

    # Relative humidity (also fan-friendly)
    rh_obj = period.get("relativeHumidity")
    if isinstance(rh_obj, dict):
        rh = rh_obj.get("value")
    else:
        rh = rh_obj
    humidity_pct = int(rh) if rh is not None else None

    return {
        "temp":           temp,
        "dew":            dew,
        "wind_speed":     wind_speed,
        "wind_deg":       wind_deg,
        "precip_pct":     precip_pct,
        "humidity_pct":   humidity_pct,
        "short_forecast": period.get("shortForecast", ""),
        "start_time":     period.get("startTime"),
        "end_time":       period.get("endTime"),
    }
