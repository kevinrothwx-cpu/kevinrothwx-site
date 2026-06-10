"""
golf.slate — build the tournament view with daily + hourly forecasts.

Each tournament's slate covers Round 1 through Round 4 (typical Thu-Sun
window, but we read from the API for exact dates). Per round we produce:
  - daily summary: high/low temp, max precip%, dominant sky
  - hourly forecast for play hours (default 6 AM - 8 PM local)

Course is looked up from courses.PGA_COURSES. Unknown courses produce
a slate entry with course_meta=None and forecast missing — page handles
gracefully.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from .courses import lookup_course
from .schedule import get_pga_scoreboard, parse_pga_event, tournament_slug

from mlb.nws import (
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
)
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from hrrr import get_hrrr_periods


EASTERN_TZ = ZoneInfo("America/New_York")

# Hours of the day we care about for play (local time)
PLAY_START_HOUR = 6
PLAY_END_HOUR   = 20   # 8 PM cushion


def _all_hourly_for_course(course_meta):
    """Fetch the full hourly-period list for a course (route NWS vs WeatherAPI)."""
    if course_meta.get("nws_unsupported"):
        try:
            periods = fetch_weatherapi_hourly(course_meta["lat"], course_meta["lon"])
            return periods, "weatherapi", None
        except Exception as e:
            return None, "weatherapi", str(e)
    try:
        url = get_nws_hourly_url(course_meta["lat"], course_meta["lon"])
        raw = get_nws_periods(url)
        return [extract_forecast(p) for p in raw], "nws", None
    except Exception as e:
        return None, "nws", str(e)


def _periods_for_round_day(periods, round_date, tz):
    """Pull periods that fall within play hours of round_date in the course's local tz."""
    if not periods:
        return []
    out = []
    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        local = start.astimezone(tz)
        if local.date() == round_date and PLAY_START_HOUR <= local.hour < PLAY_END_HOUR:
            p2 = dict(p)
            p2["hour_local"] = local.strftime("%-I %p").lstrip("0")
            p2["hour_local_dt"] = local
            out.append(p2)
    return out


def _summarize_day(round_periods):
    """Compute high/low temp, max precip%, dominant sky icon, avg wind for a day."""
    if not round_periods:
        return None
    temps = [p["temp"] for p in round_periods if p.get("temp") is not None]
    precips = [p.get("precip_pct", 0) or 0 for p in round_periods]
    winds = [p["wind_speed"] for p in round_periods if p.get("wind_speed") is not None]
    return {
        "high_temp": max(temps) if temps else None,
        "low_temp":  min(temps) if temps else None,
        "max_precip": max(precips) if precips else 0,
        "avg_wind":  round(sum(winds) / len(winds)) if winds else 0,
        "dominant_precip_pct": max(precips) if precips else 0,
    }


def build_tournament(event: dict) -> dict:
    """
    Build the full tournament dict ready for the template:
      - metadata (name, course, dates)
      - rounds: list of {round_num, round_label, date_local, daily_summary, hourly}
      - weather_source, weather_error
    """
    course = lookup_course(event["course"])
    rounds_out = []
    weather_source = None
    weather_err = None

    try:
        start = datetime.fromisoformat(event["start_iso"].replace("Z", "+00:00"))
        end   = datetime.fromisoformat(event["end_iso"].replace("Z", "+00:00")) if event["end_iso"] else start + timedelta(days=3)
    except Exception:
        start = end = None

    if course and start:
        tz = ZoneInfo(course["timezone"])
        first_round_local = start.astimezone(tz).date()
        # Defensive: cap window. Most events are 3-4 days. Monday finishes push to 5.
        # 7-day cap absorbs playoffs/weather delays without building a bogus tournament.
        if end:
            last_round_local = end.astimezone(tz).date()
        else:
            last_round_local = first_round_local + timedelta(days=3)
        max_round_date = first_round_local + timedelta(days=6)
        if last_round_local > max_round_date:
            last_round_local = max_round_date

        # Fetch full hourly periods once, then slice per round
        periods, source, err = _all_hourly_for_course(course)
        weather_source = source
        weather_err = err

        # Also fetch HRRR (CONUS only, ~48 h horizon). May be None for
        # international courses or on Open-Meteo failure. Failures are
        # silent and the toggle just won't render — never blocks NWS.
        hrrr_periods = None
        if not course.get("nws_unsupported"):
            try:
                hrrr_periods = get_hrrr_periods(course["lat"], course["lon"])
            except Exception as e:
                print(f"[golf.slate] HRRR fetch error for {course.get('name','?')}: {e}", flush=True)
                hrrr_periods = None

        num_rounds = (last_round_local - first_round_local).days + 1
        cur = first_round_local
        round_num = 1
        while cur <= last_round_local:
            day_periods = _periods_for_round_day(periods or [], cur, tz)
            # Slice HRRR with the exact same window logic so the two tables
            # are directly comparable hour-for-hour.
            day_hrrr = _periods_for_round_day(hrrr_periods or [], cur, tz) if hrrr_periods else []
            # Better round labels: 3-day events show "Final Round" not "Round 3"
            if round_num == num_rounds and num_rounds < 4:
                label = "Final Round"
            elif round_num == num_rounds:
                label = f"Final Round (R{round_num})"
            else:
                label = f"Round {round_num}"
            rounds_out.append({
                "round_num":   round_num,
                "round_label": label,
                "date_local":  cur,
                "date_label":  cur.strftime("%a %b %-d"),
                "summary":     _summarize_day(day_periods),
                "hourly":      day_periods,
                "hrrr_hourly": day_hrrr,
            })
            cur += timedelta(days=1)
            round_num += 1

    return {
        **event,
        "slug":         tournament_slug(event["short_name"] or event["name"]),
        "course_meta":  course,
        "rounds":       rounds_out,
        "weather_source": weather_source,
        "weather_error":  weather_err,
    }


def build_pga_slate() -> list[dict]:
    """
    Build the current PGA slate (typically 1-3 active/upcoming tournaments).
    """
    raw = get_pga_scoreboard()
    out = []
    for event in raw:
        parsed = parse_pga_event(event)
        if not parsed:
            continue
        tournament = build_tournament(parsed)
        out.append(tournament)

    # Sort by start date
    out.sort(key=lambda t: t.get("start_iso", ""))
    return out
