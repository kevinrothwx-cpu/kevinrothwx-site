"""
nascar.slate — build the race day view (hourly forecast around green flag).

Each race entry includes:
  - track metadata
  - green flag time (UTC + track-local + Eastern)
  - hourly forecast for ±2 hours around green flag
  - summary forecast at green flag
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .tracks import lookup_track
from .schedule import get_nascar_scoreboard, parse_nascar_event, race_slug

from mlb.nws import (
    get_nws_hourly_url, get_nws_periods,
    find_period_for_time, extract_forecast,
)
from mlb.weatherapi import fetch_weatherapi_hourly, find_weatherapi_period
from hrrr import get_hrrr_periods


EASTERN_TZ = ZoneInfo("America/New_York")

HOURS_BEFORE = 2   # pre-race buildup
HOURS_RACE   = 3   # most Cup races are ~3 hours
HOURS_AFTER  = 1


def _forecast_for_track(track, target_utc):
    if track.get("nws_unsupported"):
        try:
            periods = fetch_weatherapi_hourly(track["lat"], track["lon"])
            chosen = find_weatherapi_period(periods, target_utc)
            return chosen, periods, "weatherapi", None
        except Exception as e:
            return None, None, "weatherapi", str(e)
    try:
        url = get_nws_hourly_url(track["lat"], track["lon"])
        raw = get_nws_periods(url)
        chosen_raw = find_period_for_time(raw, target_utc)
        chosen = extract_forecast(chosen_raw)
        normalized = [extract_forecast(p) for p in raw]
        return chosen, normalized, "nws", None
    except Exception as e:
        return None, None, "nws", str(e)


def _hourly_window(periods, green_flag_utc):
    if not periods:
        return []
    fp = green_flag_utc.replace(minute=0, second=0, microsecond=0)
    start = fp - timedelta(hours=HOURS_BEFORE)
    end   = fp + timedelta(hours=HOURS_RACE + HOURS_AFTER)
    out = []
    for p in periods:
        st = datetime.fromisoformat(p["start_time"])
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        st_utc = st.astimezone(timezone.utc)
        if start <= st_utc < end:
            st_eastern = st_utc.astimezone(EASTERN_TZ)
            p2 = dict(p)
            p2["hour_eastern"] = st_eastern.strftime("%-I %p").lstrip("0")
            p2["hour_eastern_dt"] = st_eastern
            p2["is_race_hour"] = fp <= st_utc < fp + timedelta(hours=HOURS_RACE)
            out.append(p2)
    return out


def build_race(event):
    """Build a fully-loaded race dict ready for the template."""
    track = lookup_track(event["track"])
    forecast = None
    hourly = []
    source = None
    err = None
    gf_utc = gf_local = gf_eastern = None

    try:
        gf_utc = datetime.fromisoformat(event["green_flag_utc"].replace("Z", "+00:00"))
    except Exception:
        pass

    hrrr_hourly = []
    if track and gf_utc:
        forecast, periods, source, err = _forecast_for_track(track, gf_utc)
        hourly = _hourly_window(periods or [], gf_utc)
        tz = ZoneInfo(track["timezone"])
        gf_local = gf_utc.astimezone(tz)
        gf_eastern = gf_utc.astimezone(EASTERN_TZ)

        # HRRR (CONUS only, ~48 h horizon). Bounding-box check inside
        # get_hrrr_periods decides coverage — independent of NWS. Silent
        # on failure; toggle just won't render.
        try:
            hrrr_periods = get_hrrr_periods(track["lat"], track["lon"])
            if hrrr_periods:
                hrrr_hourly = _hourly_window(hrrr_periods, gf_utc)
        except Exception as e:
            print(f"[nascar.slate] HRRR fetch error for {track.get('name','?')}: {e}", flush=True)

    return {
        **event,
        "track_meta":  track,
        "green_flag_utc_dt": gf_utc,
        "green_flag_local":  gf_local,
        "green_flag_eastern": gf_eastern,
        "green_flag_eastern_str": gf_eastern.strftime("%-I:%M %p ET").lstrip("0") if gf_eastern else "",
        "forecast":    forecast,
        "hourly":      hourly,
        "hrrr_hourly": hrrr_hourly,
        "slug":        race_slug(event["short_name"] or event["name"]),
        "weather_source": source,
        "weather_error":  err,
    }


def build_nascar_slate():
    """Build current/upcoming NASCAR Cup races."""
    raw = get_nascar_scoreboard()
    out = []
    for event in raw:
        parsed = parse_nascar_event(event)
        if not parsed:
            continue
        out.append(build_race(parsed))
    out.sort(key=lambda r: r.get("green_flag_utc", ""))
    return out
