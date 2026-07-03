"""horse.slate — attach WeatherAPI hourly + HRRR to each upcoming stakes day.

Strategy (Kevin's call):
  Primary source  = WeatherAPI (paid tier, clean hourly grid, works for
                    Canadian venues too so it aligns with all tracks in
                    horse.venues).
  HRRR toggle     = Open-Meteo HRRR overlay for CONUS tracks. Skipped
                    automatically for Woodbine (outside CONUS).

Freeze pattern:
  - Post-time freeze: once a stakes race passes its scheduled post time,
    snapshot the hourly forecast so post-race review keeps the actual
    at-post-time numbers even after WeatherAPI has moved on.
  - Read the freeze on subsequent renders and serve it instead of live
    data for races that have already gone off.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date, time as dtime
from zoneinfo import ZoneInfo
from typing import Optional

from .venues import lookup_track
from .schedule import upcoming_stakes, get_stakes_race
from . import forecast_freeze

from mlb.weatherapi import fetch_weatherapi_hourly
from hrrr import get_hrrr_periods


PLAY_START_HOUR = 6
PLAY_END_HOUR   = 22


def _periods_for_race_day(periods, race_date, tz):
    """Trim to the race-day play window in venue local time."""
    if not periods:
        return []
    out = []
    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        local = start.astimezone(tz)
        if local.date() == race_date and PLAY_START_HOUR <= local.hour < PLAY_END_HOUR:
            p2 = dict(p)
            p2["hour_local"] = local.strftime("%-I %p").lstrip("0")
            p2["hour_local_dt"] = local
            out.append(p2)
    return out


def _summarize_day(day_periods):
    """Compute high/low temp, max precip%, avg wind for a race day."""
    if not day_periods:
        return None
    temps = [p["temp"] for p in day_periods if p.get("temp") is not None]
    precips = [p.get("precip_pct", 0) or 0 for p in day_periods]
    winds = [p["wind_speed"] for p in day_periods if p.get("wind_speed") is not None]
    return {
        "high_temp": max(temps) if temps else None,
        "low_temp":  min(temps) if temps else None,
        "max_precip": max(precips) if precips else 0,
        "avg_wind":  round(sum(winds) / len(winds)) if winds else 0,
    }


def _find_post_time_period(day_periods, post_time_local, tz):
    """Locate the hourly period nearest the race post time.

    post_time_local is HH:MM string in venue local time. Returns the
    period dict or None if no post time known or no matching period.
    """
    if not post_time_local or not day_periods:
        return None
    try:
        hh, mm = post_time_local.split(":")
        target_h = int(hh)
    except (ValueError, AttributeError):
        return None
    # Closest hour match
    best = None
    best_diff = 99
    for p in day_periods:
        dt = p.get("hour_local_dt")
        if not dt:
            continue
        diff = abs(dt.hour - target_h)
        if diff < best_diff:
            best_diff = diff
            best = p
    return best


def build_stakes_day(race: dict) -> dict:
    """Build a single stakes-day dict with attached forecast."""
    track = lookup_track(race["track"])
    if not track:
        return {**race, "track_meta": None, "forecast": None, "build_err": f"track slug {race['track']} not found in HORSE_TRACKS"}

    try:
        race_date = datetime.strptime(race["date_local"], "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        return {**race, "track_meta": track, "forecast": None, "build_err": f"bad date_local: {e}"}

    tz = ZoneInfo(track["timezone"])
    now_local = datetime.now(tz)
    today_local = now_local.date()

    # Check freeze first — races that already went off serve frozen data
    race_is_past = race_date < today_local
    frozen = forecast_freeze.get(race["race_id"])

    if race_is_past and frozen:
        return {
            **race,
            "track_meta": track,
            "race_date": race_date,
            "forecast_source": "frozen",
            "day_summary": frozen.get("summary"),
            "day_hourly": frozen.get("hourly") or [],
            "day_hrrr":   frozen.get("hrrr_hourly") or [],
            "post_time_period": None,
            "build_err": None,
        }

    # Live fetch
    forecast_source = None
    build_err = None
    all_periods = None
    hrrr_periods = None

    try:
        all_periods = fetch_weatherapi_hourly(track["lat"], track["lon"])
        forecast_source = "weatherapi"
    except Exception as e:
        build_err = f"WeatherAPI error: {e}"
        forecast_source = "unavailable"

    if not track.get("nws_unsupported"):
        try:
            hrrr_periods = get_hrrr_periods(track["lat"], track["lon"])
        except Exception as e:
            print(f"[horse.slate] HRRR fetch failed for {track['name']}: {e}", flush=True)
            hrrr_periods = None

    day_periods = _periods_for_race_day(all_periods or [], race_date, tz)
    day_hrrr = _periods_for_race_day(hrrr_periods or [], race_date, tz) if hrrr_periods else []
    day_summary = _summarize_day(day_periods)
    post_time_period = _find_post_time_period(day_periods, race.get("post_time_local"), tz)

    # If race day is today or past AND has data, freeze it. The post-time
    # snapshot ensures post-race review shows what the forecast actually
    # was as the horses loaded into the gate.
    if race_date <= today_local and day_periods:
        # Only freeze if we don't already have a snapshot — do not
        # overwrite a prior freeze.
        if not forecast_freeze.has(race["race_id"]):
            forecast_freeze.freeze(
                race["race_id"],
                summary=day_summary,
                hourly=day_periods,
                hrrr_hourly=day_hrrr,
            )

    return {
        **race,
        "track_meta": track,
        "race_date": race_date,
        "forecast_source": forecast_source,
        "day_summary": day_summary,
        "day_hourly": day_periods,
        "day_hrrr":   day_hrrr,
        "post_time_period": post_time_period,
        "build_err": build_err,
    }


def build_horse_slate(within_days: int = 90) -> list[dict]:
    """Build the current slate of upcoming (+ recently-run) stakes days."""
    upcoming = upcoming_stakes(within_days=within_days)
    out = []
    for race in upcoming:
        # Strip the internal _parsed_date helper before rendering
        race_clean = {k: v for k, v in race.items() if not k.startswith("_")}
        try:
            out.append(build_stakes_day(race_clean))
        except Exception as e:
            print(f"[horse.slate] build failed for {race.get('race_id')}: {e}", flush=True)
            out.append({**race_clean, "track_meta": None, "forecast_source": "unavailable", "build_err": str(e)})
    return out
