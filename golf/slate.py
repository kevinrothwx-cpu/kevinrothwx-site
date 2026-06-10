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
from .holes import get_course_holes, prepare_course_map
from .schedule import get_pga_scoreboard, parse_pga_event, tournament_slug
from .wind_impact import attach_wind_impact, circular_mean_deg

from mlb.nws import (
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
)
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period


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
    wind_dirs = [p["wind_deg"] for p in round_periods if p.get("wind_deg") is not None]
    return {
        "high_temp": max(temps) if temps else None,
        "low_temp":  min(temps) if temps else None,
        "max_precip": max(precips) if precips else 0,
        "avg_wind":  round(sum(winds) / len(winds)) if winds else 0,
        "avg_wind_deg": circular_mean_deg(wind_dirs),
        "dominant_precip_pct": max(precips) if precips else 0,
    }


def build_tournament(event: dict) -> dict:
    """
    Build the full tournament dict ready for the template:
      - metadata (name, course, dates)
      - rounds: list of {round_num, date_local, daily_summary, hourly}
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
        # If end < start_iso + 3 days, default to a 4-day tournament window
        last_round_local = end.astimezone(tz).date() if end else first_round_local + timedelta(days=3)

        # Fetch full hourly periods once, then slice per round
        periods, source, err = _all_hourly_for_course(course)
        weather_source = source
        weather_err = err

        cur = first_round_local
        round_num = 1
        while cur <= last_round_local and round_num <= 4:
            day_periods = _periods_for_round_day(periods or [], cur, tz)
            rounds_out.append({
                "round_num": round_num,
                "date_local": cur,
                "date_label": cur.strftime("%a %b %-d"),
                "summary": _summarize_day(day_periods),
                "hourly":  day_periods,
            })
            cur += timedelta(days=1)
            round_num += 1

    return {
        **event,
        "slug":         tournament_slug(event["short_name"] or event["name"]),
        "course_meta":  course,
        "rounds":       rounds_out,
        "course_map":   _build_course_map(course, rounds_out),
        "weather_source": weather_source,
        "weather_error":  weather_err,
    }


def _build_course_map(course, rounds_out) -> Optional[dict]:
    """
    Fetch (or read cached) OSM hole geometry and classify each hole against
    the first round with a usable wind forecast. Returns None when the
    course is unmapped or geometry is unavailable — page degrades to no map.
    """
    if not course:
        return None
    try:
        holes = get_course_holes(course)
        course_map = prepare_course_map(holes) if holes else None
    except Exception as e:
        print(f"[golf.slate] course map build failed: {e}", flush=True)
        return None
    if not course_map:
        return None

    wind_round = next(
        (r for r in rounds_out
         if r.get("summary") and r["summary"].get("avg_wind_deg") is not None),
        None,
    )
    if wind_round:
        s = wind_round["summary"]
        attach_wind_impact(course_map, s["avg_wind_deg"])
        course_map["wind_deg"] = s["avg_wind_deg"]
        course_map["wind_speed"] = s["avg_wind"]
        course_map["round_label"] = (
            f"Round {wind_round['round_num']} · {wind_round['date_label']}"
        )
    else:
        attach_wind_impact(course_map, None)
    return course_map


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
