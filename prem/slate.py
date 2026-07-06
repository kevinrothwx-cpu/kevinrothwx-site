"""prem.slate — build the Premier League weather slate for a date window.

All EPL venues are in the UK, so WeatherAPI is the only weather source
(no NWS since NWS is US-only, no HRRR since HRRR is CONUS-only). Every
venue is flagged nws_unsupported=True in prem.venues.

Match shape extends schedule.py output with:
  - "forecast":       kickoff snapshot dict
  - "hourly":         list of period dicts around kickoff
  - "weather_source": "weatherapi-uk" | "all-failed"
  - "weather_error":  None | str
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from .schedule import get_epl_week_matches
from .venues import get_stadium

from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")


HOURS_BEFORE_KICKOFF = 1
HOURS_MATCH_WINDOW   = 3   # 90 min match + halftime + injury time + buffer


def build_epl_slate(start_date: Optional[datetime] = None,
                    days_ahead: int = 7) -> list[dict]:
    """Build weather-attached Premier League slate for a date window."""
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    matches = get_epl_week_matches(start_date, days_ahead=days_ahead)
    if not matches:
        return []

    venue_cache: dict[tuple[float, float], tuple[list[dict], str, Optional[str]]] = {}

    for m in matches:
        _attach_weather_to_match(m, venue_cache)

    print(
        f"[prem.slate] built slate: {len(matches)} matches, "
        f"{len(venue_cache)} unique venues fetched",
        flush=True,
    )
    return matches


def _attach_weather_to_match(match: dict, venue_cache: dict) -> None:
    """Mutate match dict in place: forecast, hourly, weather_source, weather_error."""
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

    snapshot = find_weatherapi_period(periods, kickoff_utc)
    hourly = _hourly_window(periods, kickoff_utc)

    match["forecast"] = snapshot
    match["hourly"] = hourly
    match["weather_source"] = source
    match["weather_error"] = err


def _fetch_weatherapi(lat: float, lon: float) -> tuple[list[dict], str, Optional[str]]:
    """WeatherAPI-only path — no NWS fallback because NWS doesn't cover UK."""
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        if periods:
            return periods, "weatherapi-uk", None
        return [], "all-failed", "WeatherAPI returned empty"
    except Exception as e:
        return [], "all-failed", f"WeatherAPI: {e}"


def _hourly_window(periods: list[dict], kickoff_utc: datetime) -> list[dict]:
    """Extract 1h before kickoff through 3h after. Kickoff hour flagged."""
    if not periods:
        return []
    kickoff = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    start = kickoff - timedelta(hours=HOURS_BEFORE_KICKOFF)
    end = kickoff + timedelta(hours=HOURS_MATCH_WINDOW)
    out = []
    for p in periods:
        try:
            st_raw = p.get("start_time") or ""
            st = datetime.fromisoformat(st_raw.replace("Z", "+00:00"))
            if st.tzinfo is None:
                st = st.replace(tzinfo=timezone.utc)
            if start <= st < end:
                p2 = dict(p)
                p2["is_game_hour"] = (kickoff <= st < kickoff + timedelta(hours=HOURS_MATCH_WINDOW))
                # Venue-local (UK) hour label for template display
                try:
                    p2["hour_local"] = st.astimezone(UK_TZ).strftime("%-I%p").lower()
                except (ValueError, AttributeError):
                    p2["hour_local"] = ""
                out.append(p2)
        except (ValueError, AttributeError):
            continue
    return out


# EOF-CANARY 2026-07-06-prem-build
