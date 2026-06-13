"""cws.slate — build the Omaha slate for a date."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from .venue import CHARLES_SCHWAB_FIELD
from .schedule import get_cws_schedule, parse_cws_event, game_slug
from . import forecast_freeze
from mlb.nws import get_nws_hourly_url, get_nws_periods, find_period_for_time, extract_forecast
from mlb.wind import get_wind_info


EASTERN_TZ = ZoneInfo("America/New_York")
HOURS_BEFORE = 1
HOURS_GAME   = 3
HOURS_AFTER  = 1


def _forecast_for_omaha(target_utc):
    try:
        url = get_nws_hourly_url(CHARLES_SCHWAB_FIELD["lat"], CHARLES_SCHWAB_FIELD["lon"])
        raw = get_nws_periods(url)
        chosen_raw = find_period_for_time(raw, target_utc)
        chosen = extract_forecast(chosen_raw)
        normalized = [extract_forecast(p) for p in raw]
        return chosen, normalized, None
    except Exception as e:
        return None, None, str(e)


def _hourly_window(periods, fp_utc):
    if not periods: return []
    fp = fp_utc.replace(minute=0, second=0, microsecond=0)
    start = fp - timedelta(hours=HOURS_BEFORE)
    end   = fp + timedelta(hours=HOURS_GAME + HOURS_AFTER)
    out = []
    for p in periods:
        st = datetime.fromisoformat(p["start_time"])
        if st.tzinfo is None: st = st.replace(tzinfo=timezone.utc)
        st_utc = st.astimezone(timezone.utc)
        if start <= st_utc < end:
            st_eastern = st_utc.astimezone(EASTERN_TZ)
            p2 = dict(p)
            p2["hour_eastern"] = st_eastern.strftime("%-I %p").lstrip("0")
            p2["hour_eastern_dt"] = st_eastern
            p2["is_game_hour"] = fp <= st_utc < fp + timedelta(hours=HOURS_GAME)
            out.append(p2)
    return out


def build_cws_slate(date_str: str):
    raw = get_cws_schedule(date_str)
    out = []
    for event in raw:
        parsed = parse_cws_event(event)
        if not parsed: continue
        try:
            fp_utc = datetime.fromisoformat(parsed["first_pitch_utc"].replace("Z", "+00:00"))
        except Exception:
            continue
        venue_tz = ZoneInfo(CHARLES_SCHWAB_FIELD["timezone"])
        fp_local = fp_utc.astimezone(venue_tz)
        fp_eastern = fp_utc.astimezone(EASTERN_TZ)

        # FREEZE pattern (mirrors MLB): once a game starts, read the locked
        # snapshot from disk. While the game is still in the future, fetch
        # fresh NWS each warmer cycle and re-save the snapshot so it tracks
        # NWS up to first pitch.
        now_utc = datetime.now(timezone.utc)
        event_id = parsed.get("event_id", "")
        err = None
        if fp_utc <= now_utc and event_id and forecast_freeze.has(event_id):
            frozen = forecast_freeze.get(event_id)
            forecast  = frozen["forecast"]
            wind_info = frozen["wind_info"]
            hourly    = frozen["hourly"]
        else:
            forecast, all_periods, err = _forecast_for_omaha(fp_utc)
            wind_info = None
            if forecast:
                wind_info = get_wind_info(forecast["wind_deg"], CHARLES_SCHWAB_FIELD["cf_bearing_degrees"], forecast["wind_speed"])
            hourly = _hourly_window(all_periods or [], fp_utc)
            if fp_utc > now_utc and event_id and forecast and hourly:
                forecast_freeze.freeze(event_id, forecast, wind_info, hourly)

        slug = game_slug(parsed["away"]["name"], parsed["home"]["name"])

        out.append({
            **parsed,
            "venue":              CHARLES_SCHWAB_FIELD["name"],
            "venue_meta":         CHARLES_SCHWAB_FIELD,
            "park":               CHARLES_SCHWAB_FIELD,  # field_diagram macro reads game.park
            "first_pitch_utc_dt": fp_utc,
            "first_pitch_local":  fp_local,
            "first_pitch_eastern": fp_eastern,
            "first_pitch_eastern_str": fp_eastern.strftime("%-I:%M %p ET").lstrip("0"),
            "forecast":           forecast,
            "wind_info":          wind_info,
            "hourly":             hourly,
            "slug":               slug,
            "weather_source":     "nws",
            "weather_error":      err,
        })
    out.sort(key=lambda g: g["first_pitch_utc_dt"])
    return out
