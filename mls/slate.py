"""mls.slate — build the MLS weather slate for a date window.

Same NWS-primary, WeatherAPI-fallback pattern as cfb/slate.py. Reuses
cfb/nws_client because MLS adds maybe 100 venues × 1 fetch/match-day on
top of the existing CFB+MLB+golf+NASCAR NWS load — well under any
reasonable rate-limit budget, and the cfb_nws_client already has the
pacing + circuit breaker layer.

Canadian venues (Toronto FC, CF Montreal, Vancouver Whitecaps) have
nws_unsupported=True — these route straight to WeatherAPI since NWS
only covers US territory.

Match shape extends schedule.py output with:
  - "forecast":       kickoff snapshot dict
  - "hourly":         list of period dicts around kickoff
  - "weather_source": "nws" | "weatherapi-fallback" | "weatherapi-canadian" | "all-failed"
  - "weather_error":  None | str
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from .schedule import get_mls_week_games

from cfb.nws_client import fetch_cfb_hourly
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from mlb.nws import find_period_for_time


# MLS regular-season match window: 1h before through 3h after kickoff.
# Match is 90 minutes + halftime + injury time + Q&A → ~2.5h typical;
# 3h buffer covers extra-time playoff scenarios cleanly.
HOURS_BEFORE_KICKOFF = 1
HOURS_GAME_WINDOW    = 3


def build_mls_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 7) -> list[dict]:
    """Build the full weather-attached MLS slate for a date window.

    Args:
        start_date: First day to include. Defaults to today UTC.
        days_ahead: Forward days. Default 7 covers a typical MLS week
                    (Wed midweek + Sat marquee window).
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    matches = get_mls_week_games(start_date, days_ahead=days_ahead)
    if not matches:
        return []

    # Per-venue weather cache shared across the build.
    venue_weather: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}

    for m in matches:
        _attach_weather_to_match(m, venue_weather)

    print(
        f"[mls.slate] built slate: {len(matches)} matches, "
        f"{len(venue_weather)} unique venues fetched",
        flush=True,
    )
    return matches


def _attach_weather_to_match(match: dict, venue_cache: dict) -> None:
    """Mutate match dict in place: add forecast, hourly, weather_source, weather_error."""
    venue = match.get("venue") or {}
    lat = venue.get("lat")
    lon = venue.get("lon")
    kickoff_utc = match.get("kickoff_utc")
    nws_unsupported = bool(venue.get("nws_unsupported"))

    if lat is None or lon is None or kickoff_utc is None:
        match["forecast"] = None
        match["hourly"] = []
        match["weather_source"] = "no-venue-data"
        match["weather_error"] = "Stadium lat/lon not available for this match"
        return

    key = (round(lat, 4), round(lon, 4))
    if key in venue_cache:
        periods, source, err = venue_cache[key]
    else:
        if nws_unsupported:
            periods, source, err = _fetch_weatherapi_only(lat, lon)
        else:
            periods, source, err = _fetch_with_nws_fallback(lat, lon)
        venue_cache[key] = (periods, source, err)

    if not periods:
        match["forecast"] = None
        match["hourly"] = []
        match["weather_source"] = source or "all-failed"
        match["weather_error"] = err
        return

    if source == "nws":
        snapshot = find_period_for_time(periods, kickoff_utc)
    else:
        snapshot = find_weatherapi_period(periods, kickoff_utc)

    hourly = _hourly_window(periods, kickoff_utc)

    match["forecast"] = snapshot
    match["hourly"] = hourly
    match["weather_source"] = source
    match["weather_error"] = err


def _fetch_with_nws_fallback(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """NWS primary (via cfb client for shared pacing/circuit breaker),
    WeatherAPI fallback. US venues only — Canadian routes through
    _fetch_weatherapi_only."""
    try:
        periods = fetch_cfb_hourly(lat, lon)
        if periods:
            return periods, "nws", None
        nws_err = "NWS returned None (circuit open, rate-limited, or empty)"
    except Exception as e:
        nws_err = str(e)
        print(f"[mls.slate] NWS raised for {lat},{lon}: {e} — falling back to WeatherAPI",
              flush=True)

    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            print(f"[mls.slate] WeatherAPI fallback ok for {lat},{lon}", flush=True)
            return periods, "weatherapi-fallback", None
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI returned empty"
    except Exception as wa_err:
        return [], "all-failed", f"NWS: {nws_err}; WeatherAPI: {wa_err}"


def _fetch_weatherapi_only(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """Direct WeatherAPI path for Canadian venues — NWS only serves
    US territory, no point trying NWS first."""
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            return periods, "weatherapi-canadian", None
        return [], "all-failed", "WeatherAPI returned empty"
    except Exception as e:
        return [], "all-failed", f"WeatherAPI: {e}"


def _hourly_window(periods: list[dict], kickoff_utc: datetime) -> list[dict]:
    """Extract 1h before kickoff through 3h after. Game-time flagged for templates."""
    if not periods:
        return []
    kickoff = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    start = kickoff - timedelta(hours=HOURS_BEFORE_KICKOFF)
    end = kickoff + timedelta(hours=HOURS_GAME_WINDOW)
    out = []
    for p in periods:
        try:
            st_raw = p.get("start_time") or ""
            st = datetime.fromisoformat(st_raw.replace("Z", "+00:00"))
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            if start <= st < end:
                p2 = dict(p)
                p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_GAME_WINDOW))
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out
