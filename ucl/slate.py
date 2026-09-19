"""
ucl.slate — weather-attached Champions League slate.

Adapted from prem/slate.py. One material difference: EPL is entirely in
one timezone, so prem hardcodes UK_TZ for hour labels. The Champions
League spans Europe/Lisbon through Asia/Baku, five hours apart, so every
hour label here is rendered in the MATCH VENUE's own timezone.

All grounds are nws_unsupported, so weather is WeatherAPI only. No NWS
attempt is made, which also means UCL adds zero load to the NWS budget
the other sports share.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .schedule import get_ucl_week_matches
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from game_precip import apply_game_window_precip

HOURS_BEFORE_KICKOFF = 1
HOURS_MATCH_WINDOW   = 3   # 90 min + halftime + stoppage + buffer


def build_ucl_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 7) -> list[dict]:
    """Build the weather-attached UCL slate for a date window."""
    if start_date is None:
        # Back up 4h so a match already in progress stays on the slate.
        start_date = datetime.now(timezone.utc) - timedelta(hours=4)

    matches = get_ucl_week_matches(start_date, days_ahead=days_ahead)
    if not matches:
        return []

    matches = [m for m in matches if not _is_match_stale(m)]

    venue_cache: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}
    for m in matches:
        _attach_weather_to_match(m, venue_cache)

    print(f"[ucl.slate] built slate: {len(matches)} matches, "
          f"{len(venue_cache)} unique venues fetched", flush=True)
    return matches


def _is_match_stale(match: dict) -> bool:
    """Stale once the venue's local calendar date has rolled past kickoff."""
    venue = match.get("venue") or {}
    kickoff_utc = match.get("kickoff_utc")
    tz_name = venue.get("tz") or venue.get("timezone")
    if not kickoff_utc or not tz_name:
        return False
    try:
        tz = ZoneInfo(tz_name)
        return kickoff_utc.astimezone(tz).date() < datetime.now(tz).date()
    except Exception:
        return False


def _attach_weather_to_match(match: dict, venue_cache: dict) -> None:
    """Mutate match in place: forecast, hourly, weather_source, weather_error."""
    venue = match.get("venue") or {}
    lat = venue.get("lat")
    lon = venue.get("lon")
    kickoff_utc = match.get("kickoff_utc")

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
        periods, source, err = _fetch_weatherapi(lat, lon)
        venue_cache[key] = (periods, source, err)

    if not periods:
        match["forecast"] = None
        match["hourly"] = []
        match["weather_source"] = source or "all-failed"
        match["weather_error"] = err
        return

    match["hourly"] = _hourly_window(periods, kickoff_utc, venue.get("tz"))
    # Rain chance across the match, not just the kickoff hour. See game_precip.
    match["forecast"] = apply_game_window_precip(
        find_weatherapi_period(periods, kickoff_utc), match["hourly"])
    match["weather_source"] = source
    match["weather_error"] = err


def _fetch_weatherapi(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """WeatherAPI only. NWS does not cover Europe, so there is nothing to
    fall back to and no NWS request is ever made."""
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            return periods, "weatherapi-eu", None
        return [], "all-failed", "WeatherAPI returned empty"
    except Exception as e:
        return [], "all-failed", f"WeatherAPI: {e}"


def _hourly_window(periods: list[dict], kickoff_utc: datetime,
                   tz_name: Optional[str]) -> list[dict]:
    """1h before kickoff through 3h after, labelled in venue-local time."""
    if not periods:
        return []
    try:
        venue_tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    except Exception:
        venue_tz = timezone.utc

    kickoff = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    start = kickoff - timedelta(hours=HOURS_BEFORE_KICKOFF)
    end = kickoff + timedelta(hours=HOURS_MATCH_WINDOW)

    out = []
    for p in periods:
        try:
            st = datetime.fromisoformat((p.get("start_time") or "").replace("Z", "+00:00"))
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            if not (start <= st < end):
                continue
            p2 = dict(p)
            p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_MATCH_WINDOW))
            try:
                p2["hour_local"] = st.astimezone(venue_tz).strftime("%-I%p").lower()
            except (ValueError, AttributeError):
                p2["hour_local"] = ""
            out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out


# EOF-CANARY 2026-09-08-ucl-build
