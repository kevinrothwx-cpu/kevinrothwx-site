"""tennis.slate — build the day-by-day forecast for an active Slam.

Mirrors golf/slate.py's per-round-day pattern but adapted for Slams:
  - Slams run ~14 days instead of golf's 4 rounds
  - The "play window" is ~11 AM – 10 PM venue-local
  - Three of four venues are international (NWS doesn't cover them),
    so the WeatherAPI fallback layer is the primary path for those

Output is a list of day dicts ready for the template:
  {
      "day_num":    1,
      "day_label":  "Day 1",
      "date_local": date(2026, 6, 29),
      "date_label": "Mon Jun 29",
      "summary":    {"high_temp", "low_temp", "max_precip", "avg_wind"},
      "hourly":     [period dicts with hour_local strings],
  }

Caller (cache.py) wraps this in a slam dict with the venue meta etc.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from mlb.nws import (
    get_nws_hourly_url, get_nws_periods, extract_forecast,
    attach_nws_gusts,
)
from mlb.weatherapi import fetch_weatherapi_hourly


# Tennis play hours at all 4 Slams. Start ~11 AM local (first matches on
# show courts typically begin around then), end at 22:00 to cover evening
# matches and US Open night sessions. Past 10 PM most outer courts are
# done; the major show courts can run until midnight under lights but
# we'd rather not bloat the hourly strip beyond what's useful.
PLAY_START_HOUR = 11
PLAY_END_HOUR   = 22


def _all_hourly_for_venue(venue_meta: dict):
    """Fetch the full hourly-period list for a Slam venue.

    Fallback strategy (same as golf):
      1. NWS — for US Open (US venue). 24h stale-cache safety net inside
         get_nws_periods means brief NWS outages don't blank the page.
      2. WeatherAPI — used as the PRIMARY layer for the three international
         venues (flagged nws_unsupported=True in venues.py) and as the
         backup for US Open when NWS is unrecoverable.

    Returns (periods, source_label, err) — same shape as golf._all_hourly_for_course.
    """
    lat = venue_meta["lat"]
    lon = venue_meta["lon"]
    venue_name = venue_meta.get("name", "?")

    # International venues skip NWS entirely (it doesn't cover them).
    if venue_meta.get("nws_unsupported"):
        try:
            periods = fetch_weatherapi_hourly(lat, lon)
            return periods, "weatherapi", None
        except Exception as e:
            return None, "weatherapi", str(e)

    # US Open: NWS first
    try:
        url = get_nws_hourly_url(lat, lon)
        raw = get_nws_periods(url)
        periods = [extract_forecast(p) for p in raw]
        attach_nws_gusts(periods, lat, lon)
        return periods, "nws", None
    except Exception as nws_err:
        print(f"[tennis.slate] NWS failed for {venue_name}: {nws_err} "
              f"— falling back to WeatherAPI", flush=True)

    # WeatherAPI fallback
    try:
        periods = fetch_weatherapi_hourly(lat, lon)
        print(f"[tennis.slate] WeatherAPI fallback ok for {venue_name}", flush=True)
        return periods, "weatherapi-fallback", None
    except Exception as wa_err:
        return None, "all-sources-failed", f"NWS unrecoverable; WeatherAPI: {wa_err}"


def _periods_for_day(periods, day_date, tz):
    """Pull periods that fall within tennis play hours of day_date in the
    venue's local timezone."""
    if not periods:
        return []
    out = []
    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        local = start.astimezone(tz)
        if local.date() == day_date and PLAY_START_HOUR <= local.hour < PLAY_END_HOUR:
            p2 = dict(p)
            p2["hour_local"] = local.strftime("%-I %p").lstrip("0")
            p2["hour_local_dt"] = local
            out.append(p2)
    return out


def _summarize_day(day_periods):
    """High/low temp, max precip%, avg wind for a tournament day's play hours."""
    if not day_periods:
        return None
    temps = [p["temp"] for p in day_periods if p.get("temp") is not None]
    precips = [p.get("precip_pct", 0) or 0 for p in day_periods]
    winds = [p["wind_speed"] for p in day_periods if p.get("wind_speed") is not None]
    return {
        "high_temp":           max(temps) if temps else None,
        "low_temp":            min(temps) if temps else None,
        "max_precip":          max(precips) if precips else 0,
        "avg_wind":            round(sum(winds) / len(winds)) if winds else 0,
        "dominant_precip_pct": max(precips) if precips else 0,
    }


def build_slam_slate(slam: dict) -> dict:
    """Build a complete slam dict ready for the template.

    Input is the Slam meta from schedule.active_slam() or get_slam_by_id():
        {"slam_id", "display_name", "start_date", "end_date", "venue"}

    Output adds:
        {"days":          [...],
         "weather_source": "weatherapi" | "nws" | "weatherapi-fallback" | "all-sources-failed",
         "weather_error":  None | str}

    The days list spans from start_date through end_date inclusive. Past
    days (before today in venue-local time) are still included here; the
    route-level filter strips them at request time (mirrors golf's
    drop-past-rounds pattern from app.py).
    """
    venue = slam["venue"]
    tz = ZoneInfo(venue["timezone"])
    start_date = slam["start_date"]
    end_date = slam["end_date"]

    periods, source, err = _all_hourly_for_venue(venue)

    days_out = []
    cur = start_date
    day_num = 1
    while cur <= end_date:
        day_periods = _periods_for_day(periods or [], cur, tz)
        days_out.append({
            "day_num":     day_num,
            "day_label":   f"Day {day_num}",
            "date_local":  cur,
            "date_label":  cur.strftime("%a %b %-d"),
            "summary":     _summarize_day(day_periods),
            "hourly":      day_periods,
        })
        cur += timedelta(days=1)
        day_num += 1

    return {
        **slam,
        "days":           days_out,
        "weather_source": source,
        "weather_error":  err,
    }
