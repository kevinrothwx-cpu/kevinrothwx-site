"""
mlb.nws — NOAA NWS + MLB Stats API helpers for kevinrothwx.com

Vendored from OVERcast/score_today.py, but stripped of the OVERcast engine,
odds API, pandas, and snapshot logger. This module is self-contained and
only depends on `requests`.

NWS coverage:
    US (contiguous + Alaska + Hawaii) only. For Rogers Centre (Toronto)
    we fall back to Open-Meteo, see mlb/open_meteo.py.

NWS endpoints used:
    1. /points/{lat},{lon} — returns forecastHourly + forecastGridData URLs
    2. forecastHourly URL — list of hourly periods with temp/wind/precip
    3. forecastGridData URL — raw model grid with windGust series

The forecastHourly endpoint does NOT include gust data; gusts live only on
the gridpoint endpoint. We fetch both and merge gust values into the
normalized period dicts so templates can display them.
"""

from __future__ import annotations

import re
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional


MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
NWS_POINTS_URL   = "https://api.weather.gov/points/{lat},{lon}"

NWS_HEADERS = {
    "User-Agent": "kevinrothwx-site/1.0 (kevinrothwx@gmail.com)",
    "Accept":     "application/geo+json",
}

COMPASS_TO_DEG = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
    "CALM": 0, "VRB": 0, "VAR": 0,
}

# km/h to mph
_KMH_TO_MPH = 0.621371


def get_mlb_schedule(date_str: str) -> list[dict]:
    """Fetch all MLB games for a given date (YYYY-MM-DD)."""
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
    """Extract the fields we need from a raw Stats API game object."""
    state = game.get("status", {}).get("abstractGameState", "")
    if state in ("Postponed", "Cancelled", "Suspended"):
        return None

    venue_name = game.get("venue", {}).get("name", "")
    game_date  = game.get("gameDate", "")
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


# ── Caches ──────────────────────────────────────────────────────────────
# _nws_point_cache holds both URLs from a single /points fetch — the points
# endpoint returns both forecastHourly and forecastGridData URLs in one
# response, so we cache both together to avoid duplicate calls.
_nws_point_cache: dict[str, dict] = {}
_nws_periods_cache: dict[str, list] = {}
_nws_gusts_cache: dict[str, dict] = {}

# Long-lived "last successful fetch" cache. Survives warmer cache clears so
# that brief NWS outages don't blank out a page — we keep serving the most
# recent good response for up to 24 hours while NWS recovers. Keyed by
# hourly_url, value is (periods, datetime_utc). After 24h, callers (e.g.
# golf.slate._all_hourly_for_course) should fall back to WeatherAPI.
_nws_last_good_cache: dict[str, tuple[list, datetime]] = {}
_NWS_LAST_GOOD_MAX_AGE = timedelta(hours=24)


def clear_periods_cache() -> None:
    """Called by background warmers to force fresh forecasts.
    Clears both hourly period and gust caches so we get fresh data each cycle.
    The /points endpoint cache is preserved — those URLs are stable per location.
    The last-good cache is also preserved — it's the safety net for NWS outages."""
    _nws_periods_cache.clear()
    _nws_gusts_cache.clear()


def _get_nws_point_data(lat: float, lon: float) -> dict:
    """Fetch (and cache) the /points response, returning both forecast URLs."""
    key = f"{lat:.4f},{lon:.4f}"
    if key not in _nws_point_cache:
        resp = requests.get(
            NWS_POINTS_URL.format(lat=lat, lon=lon),
            headers=NWS_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        props = resp.json().get("properties", {})
        _nws_point_cache[key] = {
            "hourly_url": props.get("forecastHourly", ""),
            "grid_url":   props.get("forecastGridData", ""),
        }
    return _nws_point_cache[key]


def get_nws_hourly_url(lat: float, lon: float) -> str:
    """Two-step NWS lookup. Returns the forecastHourly URL."""
    return _get_nws_point_data(lat, lon)["hourly_url"]


def get_nws_gridpoint_url(lat: float, lon: float) -> str:
    """Return the forecastGridData URL (raw model grid, has windGust series)."""
    return _get_nws_point_data(lat, lon)["grid_url"]


def get_nws_periods(hourly_url: str) -> list:
    """Fetch and cache hourly forecast periods for a URL.

    On fetch failure (NWS 5xx, network blip, timeout), falls back to the
    last-good cached periods if they're less than 24h old. After 24h with
    no fresh data, re-raises so the caller can route to a backup source
    (e.g. WeatherAPI).
    """
    if hourly_url in _nws_periods_cache:
        return _nws_periods_cache[hourly_url]

    short = hourly_url.split("/gridpoints/")[-1] if "/gridpoints/" in hourly_url else hourly_url[-40:]
    try:
        resp = requests.get(hourly_url, headers=NWS_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()["properties"]
        periods = data["periods"]
        # Record success in BOTH caches: short-term (warmer-cleared) and
        # long-term last-good (preserved across warmer cycles).
        _nws_periods_cache[hourly_url] = periods
        _nws_last_good_cache[hourly_url] = (periods, datetime.now(timezone.utc))
        print(f"[mlb.nws] fetched {short} updateTime={data.get('updateTime')}", flush=True)
        return periods
    except Exception as e:
        last_good = _nws_last_good_cache.get(hourly_url)
        if last_good is not None:
            periods, ts = last_good
            age = datetime.now(timezone.utc) - ts
            age_hr = age.total_seconds() / 3600
            if age < _NWS_LAST_GOOD_MAX_AGE:
                print(f"[mlb.nws] fetch failed for {short}: {e} — serving stale cache (age={age_hr:.1f}h)", flush=True)
                # Populate short-term cache too so we don't hammer NWS every
                # request within this warmer cycle. Next cycle clears + retries.
                _nws_periods_cache[hourly_url] = periods
                return periods
            print(f"[mlb.nws] fetch failed for {short}: {e} — last-good is {age_hr:.1f}h old (>24h), re-raising for caller fallback", flush=True)
        else:
            print(f"[mlb.nws] fetch failed for {short}: {e} — no last-good cache, re-raising", flush=True)
        raise


def _parse_iso_duration_hours(dur: str) -> int:
    """Parse an ISO 8601 duration like 'PT3H' or 'PT1H' to integer hours.
    NWS gridpoints uses these to declare how long a value is valid for."""
    m = re.match(r"PT(\d+)H", dur or "")
    return int(m.group(1)) if m else 1


def get_nws_gusts(lat: float, lon: float) -> dict[str, int]:
    """
    Fetch NWS gridpoint windGust series for a location. Returns a dict
    mapping ISO-formatted UTC hour timestamps to gust mph (rounded int).

    The gridpoint endpoint reports gusts in km/h with ISO-8601 duration
    spans (e.g. one value valid for PT3H). We expand each span into the
    per-hour entries it covers so callers can look up by exact hour.

    Cached per location. Empty dict on fetch failure so callers can fall
    back gracefully without blowing up the page.
    """
    key = f"{lat:.4f},{lon:.4f}"
    if key in _nws_gusts_cache:
        return _nws_gusts_cache[key]

    try:
        grid_url = get_nws_gridpoint_url(lat, lon)
        if not grid_url:
            _nws_gusts_cache[key] = {}
            return {}
        resp = requests.get(grid_url, headers=NWS_HEADERS, timeout=15)
        resp.raise_for_status()
        gust_obj = resp.json().get("properties", {}).get("windGust", {}) or {}
        values = gust_obj.get("values") or []
        unit = gust_obj.get("uom", "")
        # NWS reports km/h by default; convert if needed.
        is_kmh = "km_h-1" in unit

        out: dict[str, int] = {}
        for entry in values:
            valid_time = entry.get("validTime", "")
            val = entry.get("value")
            if val is None or "/" not in valid_time:
                continue
            time_str, duration_str = valid_time.split("/", 1)
            try:
                start = datetime.fromisoformat(time_str)
            except ValueError:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            start_utc = start.astimezone(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            )
            hours = _parse_iso_duration_hours(duration_str)
            mph = float(val) * _KMH_TO_MPH if is_kmh else float(val)
            mph_int = round(mph)
            for h in range(hours):
                t = start_utc + timedelta(hours=h)
                out[t.isoformat()] = mph_int

        _nws_gusts_cache[key] = out
        print(f"[mlb.nws] fetched {len(out)} hourly gust entries for {lat},{lon}", flush=True)
        return out
    except Exception as e:
        print(f"[mlb.nws] gust fetch failed for {lat},{lon}: {e}", flush=True)
        _nws_gusts_cache[key] = {}
        return {}


def attach_nws_gusts(periods: list, lat: float, lon: float) -> list:
    """
    Mutate a list of normalized period dicts in place to attach gust mph
    looked up from the NWS gridpoint windGust series. Only fills periods
    whose 'gust' field is None — preserves values populated by HRRR or
    another source. Returns the same list for chaining convenience.
    """
    if not periods:
        return periods
    gusts = get_nws_gusts(lat, lon)
    if not gusts:
        return periods
    for p in periods:
        if p.get("gust") is not None:
            continue
        st_raw = p.get("start_time")
        if not st_raw:
            continue
        try:
            st = datetime.fromisoformat(st_raw)
        except ValueError:
            continue
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        st_utc = st.astimezone(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        p["gust"] = gusts.get(st_utc.isoformat())
    return periods


def find_period_for_time(periods: list, target_utc: datetime) -> dict:
    """Return the hourly forecast period that covers the rounded target time."""
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


def parse_wind_direction(wind_dir) -> float:
    """Convert NWS windDirection (string compass or numeric degrees) to met deg."""
    if wind_dir is None:
        return 0.0
    try:
        return float(wind_dir)
    except (ValueError, TypeError):
        return COMPASS_TO_DEG.get(str(wind_dir).strip().upper(), 0.0)


def parse_wind_speed(wind_str) -> float:
    """Parse NWS windSpeed string to mph float."""
    if not wind_str:
        return 0.0
    nums = re.findall(r"\d+(?:\.\d+)?", str(wind_str))
    if not nums:
        return 0.0
    return sum(float(n) for n in nums) / len(nums)


def extract_forecast(period: dict) -> dict:
    """Pull temp, dew, wind, precip, humidity from one NWS hourly period.
    The 'gust' field is left as None — gusts come from a separate gridpoint
    fetch and get merged in by attach_nws_gusts()."""
    temp = period.get("temperature", 70)
    if period.get("temperatureUnit") == "C":
        temp = temp * 9 / 5 + 32
    temp = round(float(temp))

    dew_obj = period.get("dewpoint") or period.get("dewPoint")
    if isinstance(dew_obj, dict):
        dew_c = dew_obj.get("value")
        dew = round(dew_c * 9 / 5 + 32) if dew_c is not None else None
    else:
        dew = round(float(dew_obj) * 9 / 5 + 32) if dew_obj is not None else None

    wind_speed = round(parse_wind_speed(period.get("windSpeed", "0")))
    wind_deg   = parse_wind_direction(period.get("windDirection"))

    pop_obj = period.get("probabilityOfPrecipitation")
    if isinstance(pop_obj, dict):
        pop = pop_obj.get("value")
    else:
        pop = pop_obj
    precip_pct = int(pop) if pop is not None else 0

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
        "gust":           None,
        "precip_pct":     precip_pct,
        "humidity_pct":   humidity_pct,
        "short_forecast": period.get("shortForecast", ""),
        "start_time":     period.get("startTime"),
        "end_time":       period.get("endTime"),
    }
