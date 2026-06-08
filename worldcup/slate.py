"""
worldcup.slate — builds the matchday view for the World Cup.

Pattern matches mlb.slate: for each match on a date, look up venue, fetch
weather (NWS for US, WeatherAPI for Mexico/Canada), trim hourly window
to ±1 hour around kickoff, return ready-to-render dicts.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from .venues import WORLD_CUP_VENUES, lookup_venue
from .schedule import get_worldcup_schedule, parse_worldcup_event, match_slug

# Reuse weather provider code from the MLB module
from mlb.nws import (
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
)
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period


EASTERN_TZ = ZoneInfo("America/New_York")

HOURS_BEFORE = 1
HOURS_GAME   = 2   # soccer matches run ~2 hours including stoppage
HOURS_AFTER  = 1


def _forecast_for_venue(venue: dict, target_utc: datetime):
    """Pick NWS or WeatherAPI based on the venue's nws_unsupported flag."""
    if venue.get("nws_unsupported"):
        try:
            periods = fetch_weatherapi_hourly(venue["lat"], venue["lon"])
            chosen = find_weatherapi_period(periods, target_utc)
            return chosen, periods, "weatherapi", None
        except Exception as e:
            return None, None, "weatherapi", str(e)

    try:
        url = get_nws_hourly_url(venue["lat"], venue["lon"])
        raw = get_nws_periods(url)
        chosen_raw = find_period_for_time(raw, target_utc)
        chosen = extract_forecast(chosen_raw)
        normalized = [extract_forecast(p) for p in raw]
        return chosen, normalized, "nws", None
    except Exception as e:
        return None, None, "nws", str(e)


def _hourly_window(periods, kickoff_utc, venue_tz):
    """Trim periods to [kickoff - HOURS_BEFORE, kickoff + GAME + AFTER]."""
    if not periods:
        return []
    fp = kickoff_utc.replace(minute=0, second=0, microsecond=0)
    window_start = fp - timedelta(hours=HOURS_BEFORE)
    window_end   = fp + timedelta(hours=HOURS_GAME + HOURS_AFTER)
    selected = []
    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        start_utc = start.astimezone(timezone.utc)
        if window_start <= start_utc < window_end:
            start_eastern = start_utc.astimezone(EASTERN_TZ)
            p2 = dict(p)
            p2["hour_eastern"]    = start_eastern.strftime("%-I %p").lstrip("0")
            p2["hour_eastern_dt"] = start_eastern
            p2["is_game_hour"]    = fp <= start_utc < fp + timedelta(hours=HOURS_GAME)
            selected.append(p2)
    return selected


def build_matchday(date_str: str) -> list[dict]:
    """
    Build the matchday slate for a date. Returns matches in chronological
    order by kickoff. Matches without a known venue are dropped.
    """
    raw = get_worldcup_schedule(date_str)
    out = []
    for event in raw:
        parsed = parse_worldcup_event(event)
        if not parsed:
            continue
        venue = lookup_venue(parsed["venue"])
        if not venue:
            # Unknown / unmapped venue — log for visibility but skip
            print(f"[worldcup.slate] unknown venue: {parsed['venue']!r}", flush=True)
            continue

        try:
            ko_utc = datetime.fromisoformat(parsed["kickoff_utc"].replace("Z", "+00:00"))
        except Exception:
            continue

        venue_tz = ZoneInfo(venue["timezone"])
        ko_local   = ko_utc.astimezone(venue_tz)
        ko_eastern = ko_utc.astimezone(EASTERN_TZ)

        forecast, all_periods, source, err = _forecast_for_venue(venue, ko_utc)

        hourly = _hourly_window(all_periods or [], ko_utc, venue_tz)
        slug = match_slug(parsed["away"]["name"], parsed["home"]["name"])

        out.append({
            **parsed,
            "venue_meta":    venue,
            "kickoff_utc_dt":     ko_utc,
            "kickoff_local":      ko_local,
            "kickoff_eastern":    ko_eastern,
            "kickoff_eastern_str": ko_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "forecast":      forecast,
            "hourly":        hourly,
            "slug":          slug,
            "weather_source": source,
            "weather_error":  err,
        })

    out.sort(key=lambda m: m["kickoff_utc_dt"])
    return out


def build_matchday_window(start_date_str: str, days: int = 3) -> dict[str, list[dict]]:
    """
    Build matchday slates for `days` consecutive days starting from start_date_str.
    Returns a dict mapping each date_str to its slate.
    Used for the default `/worldcup` view which shows today + next 2 days.
    """
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    out = {}
    for i in range(days):
        d = start + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        out[ds] = build_matchday(ds)
    return out
